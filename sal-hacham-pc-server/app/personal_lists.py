from __future__ import annotations

from typing import Callable

from .config import settings
from .db import db, utc_now_iso
from .service import search_prices


def best_match(db_path, query: str, city: str | None) -> dict | None:
    """Resolve free text to the single cheapest fresh offer, used by the Telegram bot."""
    result = search_prices(
        db_path,
        query,
        city,
        None,
        None,
        settings.default_radius_km,
        settings.max_price_age_hours,
        None,
        max_results=1,
        history_days=settings.price_history_days,
    )
    hits = result.get("results") or []
    return hits[0] if hits else None


def add_watch_item(db_path, query: str, city: str | None) -> dict | None:
    match = best_match(db_path, query, city)
    if not match:
        return None
    with db(db_path) as con:
        con.execute(
            """INSERT INTO watch_items(barcode,label,city,baseline_price,last_notified_price,added_at)
               VALUES(?,?,?,?,?,?)
               ON CONFLICT(barcode) DO UPDATE SET
                 label=excluded.label, city=excluded.city,
                 baseline_price=excluded.baseline_price, last_notified_price=excluded.baseline_price""",
            (match["barcode"], match["product_name"], city, match["price"], match["price"], utc_now_iso()),
        )
    return match


def remove_watch_item(db_path, token: str) -> bool:
    with db(db_path) as con:
        cur = con.execute(
            "DELETE FROM watch_items WHERE barcode=? OR label LIKE ?", (token, f"%{token}%")
        )
        return cur.rowcount > 0


def list_watch_items(db_path) -> list[dict]:
    with db(db_path) as con:
        rows = con.execute(
            "SELECT barcode,label,city,baseline_price,last_notified_price,added_at FROM watch_items ORDER BY added_at"
        ).fetchall()
    return [dict(r) for r in rows]


def check_price_drops(db_path, notify: Callable[[str], None]) -> int:
    """Compare each watched item's current cheapest fresh price to the last alert.

    Sends one Telegram message per item whose price dropped since the last
    notification and updates the stored baseline so the same drop is not
    reported twice. Returns the number of alerts sent.
    """
    items = list_watch_items(db_path)
    sent = 0
    for item in items:
        match = best_match(db_path, item["label"], item["city"])
        if not match or match["price"] >= item["last_notified_price"]:
            continue
        notify(
            "\N{DOWN-POINTING RED TRIANGLE} ירידת מחיר: {name}\n"
            "{price} ש\"ח ב{chain} {store}, {city}\n"
            "(היה {old} ש\"ח)".format(
                name=match["product_name"],
                price=match["price"],
                chain=match["chain_name"],
                store=match["store_name"],
                city=match["city"] or "",
                old=item["last_notified_price"],
            )
        )
        with db(db_path) as con:
            con.execute(
                "UPDATE watch_items SET last_notified_price=? WHERE barcode=?",
                (match["price"], item["barcode"]),
            )
        sent += 1
    return sent


def add_basket_item(db_path, query: str, qty: float, city: str | None) -> dict | None:
    match = best_match(db_path, query, city)
    if not match:
        return None
    with db(db_path) as con:
        con.execute(
            """INSERT INTO saved_basket_items(barcode,label,qty,added_at) VALUES(?,?,?,?)
               ON CONFLICT(barcode) DO UPDATE SET label=excluded.label, qty=excluded.qty""",
            (match["barcode"], match["product_name"], qty, utc_now_iso()),
        )
    return match


def remove_basket_item(db_path, token: str) -> bool:
    with db(db_path) as con:
        cur = con.execute(
            "DELETE FROM saved_basket_items WHERE barcode=? OR label LIKE ?", (token, f"%{token}%")
        )
        return cur.rowcount > 0


def clear_basket(db_path) -> None:
    with db(db_path) as con:
        con.execute("DELETE FROM saved_basket_items")


def list_basket_items(db_path) -> list[dict]:
    with db(db_path) as con:
        rows = con.execute(
            "SELECT barcode,label,qty,added_at FROM saved_basket_items ORDER BY added_at"
        ).fetchall()
    return [dict(r) for r in rows]
