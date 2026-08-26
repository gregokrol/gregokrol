from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.db import db, init_db
from app.personal_lists import (
    add_basket_item,
    add_watch_item,
    check_price_drops,
    clear_basket,
    list_basket_items,
    list_watch_items,
    remove_basket_item,
    remove_watch_item,
)


def _seed_price(db_path: Path, barcode: str, name: str, city: str, store_id: str, price: float) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with db(db_path) as con:
        con.execute(
            """INSERT OR IGNORE INTO stores(id,chain_key,chain_name,store_number,name,city,address,updated_at,is_demo)
               VALUES(?,'X','רשת','1','סניף',?,'כתובת',?,0)""",
            (store_id, city, now),
        )
        con.execute(
            "INSERT OR IGNORE INTO products(barcode,name,manufacturer,updated_at,is_demo) VALUES(?,?,'',?,0)",
            (barcode, name, now),
        )
        con.execute(
            """INSERT INTO prices(store_id,barcode,price,unit_price,updated_at,observed_at,is_demo)
               VALUES(?,?,?,NULL,?,?,0)
               ON CONFLICT(store_id,barcode) DO UPDATE SET price=excluded.price,observed_at=excluded.observed_at""",
            (store_id, barcode, price, now, now),
        )


def test_watch_item_alerts_only_on_price_drop(tmp_path: Path):
    db_path = tmp_path / "watch.sqlite3"
    init_db(db_path)
    _seed_price(db_path, "111", "חלב 3%", "באר שבע", "s1", 10)

    match = add_watch_item(db_path, "חלב 3%", "באר שבע")
    assert match is not None
    assert list_watch_items(db_path)[0]["last_notified_price"] == 10

    alerts: list[str] = []
    assert check_price_drops(db_path, alerts.append) == 0

    _seed_price(db_path, "111", "חלב 3%", "באר שבע", "s1", 8)
    assert check_price_drops(db_path, alerts.append) == 1
    assert "8" in alerts[0]
    assert list_watch_items(db_path)[0]["last_notified_price"] == 8

    assert check_price_drops(db_path, alerts.append) == 0
    assert remove_watch_item(db_path, "חלב") is True
    assert list_watch_items(db_path) == []


def test_saved_basket_round_trip(tmp_path: Path):
    db_path = tmp_path / "basket.sqlite3"
    init_db(db_path)
    _seed_price(db_path, "222", "לחם אחיד", "חיפה", "s2", 6)

    match = add_basket_item(db_path, "לחם אחיד", 2, "חיפה")
    assert match is not None
    items = list_basket_items(db_path)
    assert items[0]["qty"] == 2
    assert items[0]["label"] == "לחם אחיד"

    assert remove_basket_item(db_path, "לחם") is True
    assert list_basket_items(db_path) == []

    add_basket_item(db_path, "לחם אחיד", 1, "חיפה")
    clear_basket(db_path)
    assert list_basket_items(db_path) == []


def test_add_watch_item_with_no_match_returns_none(tmp_path: Path):
    db_path = tmp_path / "empty.sqlite3"
    init_db(db_path)
    assert add_watch_item(db_path, "מוצר שלא קיים בכלל", None) is None
