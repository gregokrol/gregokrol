from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from app import telegram_bot
from app.config import settings
from app.db import db, init_db


@pytest.fixture
def wired_db(tmp_path: Path, monkeypatch):
    """A DB with sample data and a city already configured (an already-set-up bot)."""
    db_path = tmp_path / "bot.sqlite3"
    init_db(db_path)
    now = datetime.now(timezone.utc).isoformat()
    with db(db_path) as con:
        con.execute(
            """INSERT INTO stores(id,chain_key,chain_name,store_number,name,city,address,updated_at,is_demo)
               VALUES('s1','X','רשת','1','סניף','באר שבע','כתובת',?,0)""",
            (now,),
        )
        con.execute(
            "INSERT INTO products(barcode,name,manufacturer,updated_at,is_demo) VALUES('7291','חלב 3%','יצרן',?,0)",
            (now,),
        )
        con.execute(
            """INSERT INTO prices(store_id,barcode,price,unit_price,updated_at,observed_at,is_demo)
               VALUES('s1','7291',10,NULL,?,?,0)""",
            (now, now),
        )
    monkeypatch.setattr(settings, "db_path", db_path)

    from app.personal_lists import set_bot_city

    set_bot_city(db_path, "באר שבע")
    return db_path


@pytest.fixture
def captured_replies(monkeypatch):
    sent: list[tuple[object, str]] = []

    def fake_call(method, http_timeout=20.0, **params):
        if method == "sendMessage":
            sent.append((params.get("chat_id"), params.get("text", "")))
        return {"ok": True, "result": []}

    monkeypatch.setattr(telegram_bot, "_call", fake_call)
    return sent


def test_unknown_command_shows_hint(captured_replies):
    telegram_bot._handle_message(1, "/does_not_exist")
    assert "לא מוכרת" in captured_replies[0][1]


def test_help_lists_commands(captured_replies):
    telegram_bot._handle_message(1, "/help")
    assert "/search" in captured_replies[0][1]
    assert "/watch" in captured_replies[0][1]


def test_search_returns_offer(wired_db, captured_replies):
    telegram_bot._handle_message(1, "/search חלב 3%")
    assert "10" in captured_replies[0][1]
    assert "חלב" in captured_replies[0][1]


def test_basket_add_parses_quantity_and_query(wired_db, captured_replies):
    telegram_bot._handle_message(1, "/basket_add 3 חלב 3%")
    assert "3" in captured_replies[0][1]

    from app.personal_lists import list_basket_items

    items = list_basket_items(wired_db)
    assert items[0]["qty"] == 3


def test_watch_then_watchlist(wired_db, captured_replies):
    telegram_bot._handle_message(1, "/watch חלב 3%")
    telegram_bot._handle_message(1, "/watchlist")
    assert "חלב" in captured_replies[-1][1]


def test_plain_text_without_slash_is_treated_as_search(wired_db, captured_replies):
    telegram_bot._handle_message(1, "חלב 3%")
    assert "10" in captured_replies[0][1]
    assert "חלב" in captured_replies[0][1]


def test_bidi_control_char_before_command_is_stripped(wired_db, captured_replies):
    telegram_bot._handle_message(1, "‏/search חלב 3%")
    assert "10" in captured_replies[0][1]


def test_first_contact_prompts_for_city(tmp_path, monkeypatch, captured_replies):
    db_path = tmp_path / "fresh.sqlite3"
    init_db(db_path)
    monkeypatch.setattr(settings, "db_path", db_path)

    telegram_bot._handle_message(1, "/start")
    assert "באיזו עיר" in captured_replies[-1][1]

    telegram_bot._handle_message(1, "באר שבע")
    assert "העיר עודכנה" in captured_replies[-1][1]

    from app.personal_lists import get_bot_city

    assert get_bot_city(db_path) == "באר שבע"

    telegram_bot._handle_message(1, "/start")
    assert "פקודות זמינות" in captured_replies[-1][1]


def test_city_command_shows_and_changes_city(wired_db, captured_replies):
    telegram_bot._handle_message(1, "/city")
    assert "באר שבע" in captured_replies[-1][1]

    telegram_bot._handle_message(1, "/city תל אביב")
    assert "תל אביב" in captured_replies[-1][1]

    from app.personal_lists import get_bot_city

    assert get_bot_city(wired_db) == "תל אביב"


def test_register_bot_commands_calls_set_my_commands(monkeypatch):
    calls: list[tuple[str, dict]] = []

    def fake_call(method, http_timeout=20.0, **params):
        calls.append((method, params))
        return {"ok": True}

    monkeypatch.setattr(telegram_bot, "_call", fake_call)
    telegram_bot._register_bot_commands()

    assert calls[0][0] == "setMyCommands"
    names = {c["command"] for c in calls[0][1]["commands"]}
    assert {"search", "help", "basket_add", "watch"}.issubset(names)
