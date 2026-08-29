"""Two-way Telegram bot: replies to commands and is used by sync to push price-drop alerts.

Only the chat configured via SAL_HACHAM_TELEGRAM_CHAT_ID is served, so a leaked bot
token cannot be used by a stranger to read this household's basket or watchlist.
"""
from __future__ import annotations

import time
import traceback

import httpx

from .basket import compare_basket
from .city_activation import activate_city
from .city_cache import cache_health
from .config import settings
from .db import init_db
from .personal_lists import (
    add_basket_item,
    add_watch_item,
    clear_basket,
    get_bot_city,
    list_basket_items,
    list_watch_items,
    remove_basket_item,
    remove_watch_item,
    set_bot_city,
)
from .service import search_prices, status

API_BASE = "https://api.telegram.org/bot{token}/{method}"

BOT_COMMANDS = [
    ("search", "חיפוש מחיר זול ביותר למוצר"),
    ("city", "הצגה או שינוי של עיר החיפוש"),
    ("status", "מצב השרת והסנכרון"),
    ("basket", "הצגת הסל השמור והחנות הזולה ביותר"),
    ("basket_add", "הוספת מוצר לסל השמור"),
    ("basket_remove", "הסרת מוצר מהסל השמור"),
    ("basket_clear", "ריקון הסל השמור"),
    ("watch", "התראה כשמחיר מוצר יורד"),
    ("unwatch", "הפסקת מעקב אחר מוצר"),
    ("watchlist", "רשימת המוצרים במעקב"),
    ("help", "רשימת הפקודות"),
]

CITY_BUTTON_TEXT = "\N{CITYSCAPE} שינוי עיר"
CITY_PROMPT_TEXT = "באיזו עיר לחפש? הקלד את שם העיר (למשל: באר שבע)."
WELCOME_TEXT = f"ברוך הבא לבוט סל חכם!\n{CITY_PROMPT_TEXT}"

HELP_TEXT = (
    "אפשר גם לכתוב רק את שם המוצר, בלי /search, כדי לחפש ישירות.\n\n"
    "פקודות זמינות:\n"
    "/search <מוצר> - חיפוש מחיר זול ביותר\n"
    "/city <עיר> - הצגה או שינוי של עיר החיפוש\n"
    "/status - מצב השרת והסנכרון\n"
    "/basket - הצגת הסל השמור והחנות הזולה ביותר\n"
    "/basket_add <כמות> <מוצר> - הוספה לסל השמור\n"
    "/basket_remove <מוצר או ברקוד> - הסרה מהסל\n"
    "/basket_clear - ריקון הסל השמור\n"
    "/watch <מוצר> - התראה כשהמחיר יורד\n"
    "/unwatch <מוצר או ברקוד> - הפסקת מעקב\n"
    "/watchlist - רשימת המוצרים במעקב\n"
)

# Hebrew/RTL keyboards can prepend invisible bidi-control characters to a typed
# message, which would otherwise silently break exact command matching below.
_BIDI_STRIP_TABLE = str.maketrans("", "", "‎‏‪‫‬‭‮⁦⁧⁨⁩")


def _call(method: str, http_timeout: float = 20.0, **params) -> dict:
    url = API_BASE.format(token=settings.telegram_bot_token, method=method)
    response = httpx.post(url, json=params, timeout=http_timeout)
    response.raise_for_status()
    return response.json()


def _main_keyboard() -> dict:
    return {"keyboard": [[{"text": CITY_BUTTON_TEXT}]], "resize_keyboard": True}


def _reply(chat_id, text: str, *, ask_for_city: bool = False) -> None:
    if not text.strip():
        text = "(אין תוצאות)"
    if ask_for_city:
        reply_markup = {"force_reply": True, "input_field_placeholder": "שם העיר..."}
    else:
        reply_markup = _main_keyboard()
    _call("sendMessage", chat_id=chat_id, text=text[:4000], reply_markup=reply_markup)


def _format_offer(offer: dict) -> str:
    name = offer["product_name"]
    if offer.get("package_label"):
        name = f"{name} ({offer['package_label']})"
    parts = [f"{offer['price']} ש\"ח - {name}", f"{offer['chain_name']} {offer['store_name']}"]
    if offer.get("city"):
        parts.append(offer["city"])
    return " | ".join(parts)


def _diversify_by_chain(hits: list[dict], limit: int, max_per_chain: int = 1) -> list[dict]:
    """Prefer one branch per chain first, so a chain with many branches in the
    same city (all at its own cheapest price) doesn't crowd out every other
    chain from a short result list - the point of the search is comparing
    across chains, not listing every branch of the cheapest one."""
    chosen: list[dict] = []
    counts: dict[str, int] = {}
    for h in hits:
        key = h.get("chain_key")
        if counts.get(key, 0) < max_per_chain:
            chosen.append(h)
            counts[key] = counts.get(key, 0) + 1
        if len(chosen) >= limit:
            return chosen
    if len(chosen) < limit:
        seen = {(h["store_id"], h["barcode"]) for h in chosen}
        for h in hits:
            if (h["store_id"], h["barcode"]) in seen:
                continue
            chosen.append(h)
            if len(chosen) >= limit:
                break
    return chosen


def _cmd_search(chat_id, arg: str) -> None:
    if not arg:
        _reply(chat_id, "שימוש: /search חלב 3%")
        return
    city = get_bot_city(settings.db_path)
    activate_city(city)
    result = search_prices(
        settings.db_path,
        arg,
        city,
        None,
        None,
        settings.default_radius_km,
        settings.max_price_age_hours,
        None,
        max_results=30,
        history_days=settings.price_history_days,
    )
    hits = _diversify_by_chain(result.get("results") or [], limit=5)
    if not hits:
        _reply(chat_id, f'לא נמצא מחיר טרי עבור "{arg}".')
        return
    _reply(chat_id, "\n".join(_format_offer(h) for h in hits))


def _cmd_status(chat_id) -> None:
    info = {**status(settings.db_path, settings.max_price_age_hours, settings.price_history_days),
            **cache_health(settings.db_path, settings.max_cached_cities)}
    lines = [
        f"סניפים טריים: {info['fresh_real_stores']}/{info['real_stores']}",
        f"עדכון אחרון: {info.get('latest_update') or 'אין'}",
        f"ערים שמורות: {info['cached_city_count']}/{info['max_cached_cities']} (פעילה: {info.get('active_city') or 'אין'})",
    ]
    _reply(chat_id, "\n".join(lines))


def _cmd_basket(chat_id) -> None:
    items = list_basket_items(settings.db_path)
    if not items:
        _reply(chat_id, "הסל השמור ריק. הוסף עם /basket_add <כמות> <מוצר>.")
        return
    city = get_bot_city(settings.db_path)
    activate_city(city)
    result = compare_basket(
        settings.db_path,
        [{"q": i["label"], "qty": i["qty"]} for i in items],
        city,
        None,
        None,
        settings.default_radius_km,
        settings.max_price_age_hours,
    )
    stores = result.get("stores") or []
    if not stores:
        _reply(chat_id, "לא נמצאו סניפים עם מחירים טריים לסל השמור כרגע.")
        return
    lines = [f"{i['qty']}x {i['label']}" for i in items]
    lines.append("")
    for store in stores[:3]:
        lines.append(
            f"#{store['rank']} {store['chain_name']} {store['store_name']} - {store['total']} ש\"ח "
            f"(כיסוי {store['coverage_pct']}%)"
        )
    _reply(chat_id, "\n".join(lines))


def _cmd_basket_add(chat_id, arg: str) -> None:
    parts = arg.split(maxsplit=1)
    qty = 1.0
    query = arg
    if parts and parts[0].replace(".", "", 1).isdigit():
        qty = float(parts[0])
        query = parts[1] if len(parts) > 1 else ""
    if not query:
        _reply(chat_id, "שימוש: /basket_add 2 חלב 3%")
        return
    match = add_basket_item(settings.db_path, query, qty, get_bot_city(settings.db_path))
    if not match:
        _reply(chat_id, f'לא נמצא מוצר תואם ל-"{query}".')
        return
    _reply(chat_id, f"נוסף לסל: {qty}x {match['product_name']}")


def _cmd_basket_remove(chat_id, arg: str) -> None:
    if not arg:
        _reply(chat_id, "שימוש: /basket_remove חלב")
        return
    removed = remove_basket_item(settings.db_path, arg)
    _reply(chat_id, "הוסר מהסל." if removed else "לא נמצא פריט תואם בסל.")


def _cmd_watch(chat_id, arg: str) -> None:
    if not arg:
        _reply(chat_id, "שימוש: /watch חלב 3%")
        return
    match = add_watch_item(settings.db_path, arg, get_bot_city(settings.db_path))
    if not match:
        _reply(chat_id, f'לא נמצא מוצר תואם ל-"{arg}".')
        return
    _reply(chat_id, f"במעקב: {match['product_name']} ({match['price']} ש\"ח). תישלח התראה בירידת מחיר.")


def _cmd_unwatch(chat_id, arg: str) -> None:
    if not arg:
        _reply(chat_id, "שימוש: /unwatch חלב")
        return
    removed = remove_watch_item(settings.db_path, arg)
    _reply(chat_id, "המעקב הופסק." if removed else "לא נמצא פריט תואם במעקב.")


def _cmd_basket_clear(chat_id) -> None:
    clear_basket(settings.db_path)
    _reply(chat_id, "הסל רוקן.")


def _cmd_watchlist(chat_id) -> None:
    items = list_watch_items(settings.db_path)
    if not items:
        _reply(chat_id, "אין מוצרים במעקב. הוסף עם /watch <מוצר>.")
        return
    lines = [f"{i['label']}: {i['last_notified_price']} ש\"ח" for i in items]
    _reply(chat_id, "\n".join(lines))


def _cmd_city(chat_id, arg: str) -> None:
    if not arg:
        current = get_bot_city(settings.db_path)
        if current:
            _reply(chat_id, f"העיר הנוכחית: {current}\nלשינוי, לחץ על הכפתור '{CITY_BUTTON_TEXT}' למטה.")
        else:
            _reply(chat_id, CITY_PROMPT_TEXT, ask_for_city=True)
        return
    set_bot_city(settings.db_path, arg)
    _reply(chat_id, f"העיר עודכנה ל-{arg}. מתחיל לסרוק מחירים - זה יכול לקחת כמה דקות בפעם הראשונה.")


def _cmd_start(chat_id, arg: str) -> None:
    if get_bot_city(settings.db_path):
        _reply(chat_id, HELP_TEXT)
    else:
        _reply(chat_id, WELCOME_TEXT, ask_for_city=True)


COMMANDS = {
    "/start": lambda chat_id, arg: _cmd_start(chat_id, arg),
    "/help": lambda chat_id, arg: _reply(chat_id, HELP_TEXT),
    "/search": lambda chat_id, arg: _cmd_search(chat_id, arg),
    "/city": lambda chat_id, arg: _cmd_city(chat_id, arg),
    "/status": lambda chat_id, arg: _cmd_status(chat_id),
    "/basket": lambda chat_id, arg: _cmd_basket(chat_id),
    "/basket_add": lambda chat_id, arg: _cmd_basket_add(chat_id, arg),
    "/basket_remove": lambda chat_id, arg: _cmd_basket_remove(chat_id, arg),
    "/basket_clear": lambda chat_id, arg: _cmd_basket_clear(chat_id),
    "/watch": lambda chat_id, arg: _cmd_watch(chat_id, arg),
    "/unwatch": lambda chat_id, arg: _cmd_unwatch(chat_id, arg),
    "/watchlist": lambda chat_id, arg: _cmd_watchlist(chat_id),
}


def _handle_message(chat_id, message: dict) -> None:
    text = (message.get("text") or "").translate(_BIDI_STRIP_TABLE).strip()
    if not text:
        return

    if text == CITY_BUTTON_TEXT:
        _reply(chat_id, CITY_PROMPT_TEXT, ask_for_city=True)
        return

    if not text.startswith("/"):
        # Telegram tags a message as replying to the bot's own force-reply prompt,
        # so that reply is unambiguously the requested city regardless of its text.
        replying_to_bot = bool((message.get("reply_to_message") or {}).get("from", {}).get("is_bot"))
        if replying_to_bot or not get_bot_city(settings.db_path):
            # No city configured yet: the first plain-text message sets it, so a
            # brand-new install works from "/start" without editing any files.
            _cmd_city(chat_id, text)
        else:
            # A message with no leading slash is treated as a plain search query,
            # so looking up a price doesn't require remembering command syntax.
            _cmd_search(chat_id, text)
        return
    parts = text.split(maxsplit=1)
    cmd = parts[0].split("@")[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""
    handler = COMMANDS.get(cmd)
    if handler is None:
        _reply(chat_id, "פקודה לא מוכרת. שלח /help לרשימת הפקודות.")
        return
    handler(chat_id, arg)


def _register_bot_commands() -> None:
    commands = [{"command": name, "description": desc} for name, desc in BOT_COMMANDS]
    try:
        _call("setMyCommands", commands=commands)
    except httpx.HTTPError as exc:
        print(f"Could not register Telegram command menu: {exc}", flush=True)


def run_polling() -> None:
    if not settings.telegram_bot_token:
        print("SAL_HACHAM_TELEGRAM_BOT_TOKEN not set; Telegram bot disabled.", flush=True)
        return
    init_db(settings.db_path)
    _register_bot_commands()
    offset = 0
    print("Telegram bot polling started.", flush=True)
    while True:
        try:
            data = _call("getUpdates", http_timeout=35, offset=offset, timeout=25)
        except httpx.HTTPError as exc:
            print(f"Telegram polling error: {exc}", flush=True)
            time.sleep(5)
            continue
        for update in data.get("result", []):
            offset = update["update_id"] + 1
            message = update.get("message") or update.get("edited_message")
            if not message or "text" not in message:
                continue
            chat_id = message["chat"]["id"]
            if settings.telegram_chat_id and str(chat_id) != str(settings.telegram_chat_id):
                continue
            try:
                _handle_message(chat_id, message)
            except Exception as exc:
                traceback.print_exc()
                try:
                    _reply(chat_id, f"שגיאה בעיבוד הפקודה: {exc}")
                except httpx.HTTPError:
                    pass


if __name__ == "__main__":
    run_polling()
