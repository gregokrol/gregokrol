from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from app.city_cache import (
    cached_cities,
    claim_city_refresh,
    finish_city_refresh,
    queue_city_if_due,
    touch_city,
)
from app.db import db, init_db
from app.price_history import record_price_observation


def _add_store(db_path: Path, number: int, city: str) -> None:
    now = "2026-08-24T08:00:00+00:00"
    with db(db_path) as con:
        con.execute(
            """INSERT INTO stores(id,chain_key,chain_name,store_number,name,city,address,updated_at,is_demo)
               VALUES(?,?,?,?,?,?,?,?,0)""",
            (f"X:{number}", "X", "רשת", str(number), f"סניף {city}", city, f"רחוב {number}", now),
        )
        con.execute(
            "INSERT OR IGNORE INTO products(barcode,name,manufacturer,updated_at,is_demo) VALUES(?,?,?,?,0)",
            (f"b{number}", f"מוצר {number}", "יצרן", now),
        )
        con.execute(
            """INSERT INTO prices(store_id,barcode,price,updated_at,observed_at,is_demo)
               VALUES(?,?,?,?,?,0)""",
            (f"X:{number}", f"b{number}", float(number), now, now),
        )
        record_price_observation(con, f"X:{number}", f"b{number}", float(number), now)


def test_cache_keeps_five_recent_cities_and_evicts_price_data(tmp_path: Path):
    db_path = tmp_path / "cache.sqlite3"
    init_db(db_path)
    start = datetime(2026, 8, 24, 8, tzinfo=timezone.utc)
    names = ["עיר א", "עיר ב", "עיר ג", "עיר ד", "עיר ה", "עיר ו"]
    for index, name in enumerate(names, start=1):
        _add_store(db_path, index, name)
        touch_city(db_path, name, max_cities=5, now=start + timedelta(minutes=index))

    cities = cached_cities(db_path)
    assert len(cities) == 5
    assert cities[0]["city_name"] == "עיר ו"
    assert all(row["city_name"] != "עיר א" for row in cities)
    assert sum(int(row["is_active"]) for row in cities) == 1
    with db(db_path) as con:
        assert con.execute("SELECT COUNT(*) FROM prices WHERE store_id='X:1'").fetchone()[0] == 0
        assert con.execute("SELECT COUNT(*) FROM prices").fetchone()[0] == 5
        assert con.execute("SELECT COUNT(*) FROM price_history WHERE store_id='X:1'").fetchone()[0] == 0
        assert con.execute("SELECT COUNT(*) FROM price_history").fetchone()[0] == 5


def test_active_city_is_due_after_four_hours_and_saved_city_after_day(tmp_path: Path):
    db_path = tmp_path / "policy.sqlite3"
    init_db(db_path)
    t0 = datetime(2026, 8, 24, 8, tzinfo=timezone.utc)
    _add_store(db_path, 1, "עיר א")
    first = touch_city(db_path, "עיר א", now=t0)
    assert first and queue_city_if_due(db_path, first["city_key"], now=t0)
    assert claim_city_refresh(db_path, first["city_key"], now=t0)
    finish_city_refresh(db_path, first["city_key"], status="ready", now=t0)
    assert not queue_city_if_due(db_path, first["city_key"], now=t0 + timedelta(hours=3, minutes=59))
    assert queue_city_if_due(db_path, first["city_key"], now=t0 + timedelta(hours=4, seconds=1))

    assert claim_city_refresh(db_path, first["city_key"], now=t0 + timedelta(hours=4, seconds=1))
    finish_city_refresh(db_path, first["city_key"], status="ready", now=t0 + timedelta(hours=4, seconds=1))
    _add_store(db_path, 2, "עיר ב")
    touch_city(db_path, "עיר ב", now=t0 + timedelta(hours=5))
    assert not queue_city_if_due(db_path, first["city_key"], now=t0 + timedelta(hours=27))
    assert queue_city_if_due(db_path, first["city_key"], now=t0 + timedelta(hours=28, seconds=2))


def test_search_queues_non_blocking_refresh_and_returns_cache_status(tmp_path: Path, monkeypatch):
    from app import main

    db_path = tmp_path / "api.sqlite3"
    init_db(db_path)
    _add_store(db_path, 1, "באר שבע")
    launched: list[str] = []
    monkeypatch.setattr(main.settings, "db_path", db_path)
    monkeypatch.setattr(main.settings, "raw_dir", tmp_path / "raw")
    monkeypatch.setattr(main.settings, "demo_mode", False)
    monkeypatch.setattr(main, "_launch_city_refresh", launched.append)
    with TestClient(main.app) as client:
        response = client.get("/api/search", params={"q": "מוצר", "city": "באר שבע"})
    assert response.status_code == 200
    cache = response.json()["city_cache"]
    assert cache["city"] == "באר שבע"
    assert cache["refresh_in_progress"] is True
    assert cache["retained_count"] == 1
    assert launched == ["באר שבע"]
