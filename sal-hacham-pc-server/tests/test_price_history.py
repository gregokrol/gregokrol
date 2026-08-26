from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.db import db, init_db
from app.ingest.loader import ingest_directory
from app.price_history import prune_price_history, record_price_observation
from app.service import search_prices


def _seed_current_price(db_path: Path, observed_at: str) -> None:
    with db(db_path) as con:
        con.execute(
            """INSERT INTO stores(id,chain_key,chain_name,store_number,name,city,address,updated_at,is_demo)
               VALUES('s','X','רשת','1','סניף','באר שבע','כתובת',?,0)""",
            (observed_at,),
        )
        con.execute(
            """INSERT INTO products(barcode,name,manufacturer,updated_at,is_demo)
               VALUES('7291','חלב 3%','יצרן',?,0)""",
            (observed_at,),
        )
        con.execute(
            """INSERT INTO prices(store_id,barcode,price,unit_price,updated_at,observed_at,is_demo)
               VALUES('s','7291',12,NULL,?,?,0)""",
            (observed_at, observed_at),
        )


def test_month_history_keeps_low_high_and_true_average(tmp_path: Path):
    db_path = tmp_path / "history.sqlite3"
    init_db(db_path)
    now = datetime.now(timezone.utc)
    _seed_current_price(db_path, now.isoformat())
    observations = [(now - timedelta(hours=3), 10), (now - timedelta(hours=2), 14), (now - timedelta(hours=1), 12)]
    with db(db_path) as con:
        for observed, price in observations:
            record_price_observation(con, "s", "7291", price, observed.isoformat())
        # The same source snapshot must not be counted twice.
        record_price_observation(con, "s", "7291", 99, observations[-1][0].isoformat())

    result = search_prices(db_path, "חלב 3%", "באר שבע", None, None, 30, 5)
    history = result["results"][0]["history"]
    assert history["period_days"] == 30
    assert history["low_price"] == 10
    assert history["high_price"] == 14
    assert history["average_price"] == 12
    assert history["sample_count"] == 3


def test_history_older_than_thirty_days_is_deleted(tmp_path: Path):
    db_path = tmp_path / "prune.sqlite3"
    init_db(db_path)
    now = datetime.now(timezone.utc)
    _seed_current_price(db_path, now.isoformat())
    with db(db_path) as con:
        record_price_observation(con, "s", "7291", 9, (now - timedelta(days=31)).isoformat())
    assert prune_price_history(db_path, 30, now) == 1
    with db(db_path) as con:
        rows = con.execute("SELECT low_price,high_price,sample_count FROM price_history").fetchall()
    assert rows == []


def test_new_observation_resets_expired_month_window(tmp_path: Path):
    db_path = tmp_path / "reset.sqlite3"
    init_db(db_path)
    now = datetime.now(timezone.utc)
    _seed_current_price(db_path, now.isoformat())
    with db(db_path) as con:
        record_price_observation(con, "s", "7291", 99, (now - timedelta(days=31)).isoformat())
        record_price_observation(con, "s", "7291", 12, now.isoformat())
        row = con.execute("SELECT low_price,high_price,price_sum,sample_count FROM price_history").fetchone()
    assert tuple(row) == (12, 12, 12, 1)


def test_successful_raw_price_file_is_deleted_after_compact_ingest(tmp_path: Path):
    db_path = tmp_path / "compact.sqlite3"
    raw = tmp_path / "raw"
    raw.mkdir()
    init_db(db_path)
    stamp = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")
    stores = raw / f"Stores7290696200003-001-{stamp}.xml"
    price = raw / f"Price7290696200003-001-101-{stamp}.xml"
    stores.write_text(
        "<Root><ChainId>7290696200003</ChainId><Stores><Store><StoreId>101</StoreId><StoreName>סניף</StoreName><City>באר שבע</City></Store></Stores></Root>",
        encoding="utf-8",
    )
    price.write_text(
        "<Root><ChainId>7290696200003</ChainId><StoreId>101</StoreId><Items><Item><ItemCode>7291</ItemCode><ItemName>חלב 3%</ItemName><ItemPrice>6.50</ItemPrice></Item></Items></Root>",
        encoding="utf-8",
    )
    results = ingest_directory(db_path, raw, delete_ingested=True)
    assert len(results) == 2
    assert not stores.exists() and not price.exists()
    with db(db_path) as con:
        assert con.execute("SELECT COUNT(*) FROM prices").fetchone()[0] == 1
        assert con.execute("SELECT COUNT(*) FROM price_history").fetchone()[0] == 1
