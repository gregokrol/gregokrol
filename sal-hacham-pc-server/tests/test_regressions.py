from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient

import app.main as main
from app.db import db, init_db
from app.ingest.loader import ingest_directory, ingest_file
from app.ingest.xml_parser import parse_records
from app.service import search_prices


def _stores_xml(store_id: str = "101", city: str = "באר שבע") -> str:
    return (
        "<Root><ChainId>7290696200003</ChainId><Stores><Store>"
        f"<StoreId>{store_id}</StoreId><StoreName>ויקטורי {city}</StoreName><City>{city}</City>"
        "</Store></Stores></Root>"
    )


def _price_xml(items: str, store_id: str = "101") -> str:
    return (
        "<Root><ChainId>7290696200003</ChainId>"
        f"<StoreId>{store_id}</StoreId><Items>{items}</Items></Root>"
    )


def test_minute_precision_filename_timestamp(tmp_path: Path):
    p = tmp_path / "PriceFull7290696200003-001-101-202608232315.xml"
    p.write_text(_price_xml("<Item><ItemCode>1</ItemCode><ItemName>חלב 3%</ItemName><ItemPrice>6</ItemPrice></Item>"), encoding="utf-8")
    rec = parse_records(p)
    # Israel was UTC+3 on this date.
    assert rec["file_timestamp"].startswith("2026-08-23T20:15:00")
    assert rec["store_number"] == "101"


def test_missing_source_timestamp_uses_file_mtime_not_now(tmp_path: Path):
    p = tmp_path / "price.xml"
    p.write_text(_price_xml("<Item><ItemCode>1</ItemCode><ItemName>חלב 3%</ItemName><ItemPrice>6</ItemPrice></Item>"), encoding="utf-8")
    old = datetime.now(timezone.utc) - timedelta(days=2)
    os.utime(p, (old.timestamp(), old.timestamp()))
    rec = parse_records(p)
    parsed = datetime.fromisoformat(rec["file_timestamp"])
    assert abs((parsed - old).total_seconds()) < 2


def test_incremental_file_does_not_refresh_unchanged_items(tmp_path: Path):
    dbp = tmp_path / "db.sqlite3"
    init_db(dbp)
    stores = tmp_path / "Stores7290696200003-001-20260823-180000.xml"
    stores.write_text(_stores_xml(), encoding="utf-8")
    full = tmp_path / "PriceFull7290696200003-001-101-20260823-180000.xml"
    full.write_text(
        _price_xml(
            "<Item><ItemCode>A</ItemCode><ItemName>חלב 3%</ItemName><ItemPrice>6</ItemPrice></Item>"
            "<Item><ItemCode>B</ItemCode><ItemName>שוקו</ItemName><ItemPrice>8</ItemPrice></Item>"
        ),
        encoding="utf-8",
    )
    delta = tmp_path / "Price7290696200003-001-101-20260823-200000.xml"
    delta.write_text(
        _price_xml("<Item><ItemCode>A</ItemCode><ItemName>חלב 3%</ItemName><ItemPrice>6.2</ItemPrice><ItemStatus>1</ItemStatus></Item>"),
        encoding="utf-8",
    )
    ingest_file(dbp, stores, "VICTORY_NEW_SOURCE")
    ingest_file(dbp, full, "VICTORY_NEW_SOURCE")
    ingest_file(dbp, delta, "VICTORY_NEW_SOURCE")
    with db(dbp) as con:
        rows = {r["barcode"]: r["observed_at"] for r in con.execute("SELECT barcode,observed_at FROM prices")}
    assert rows["A"] > rows["B"]
    assert rows["B"].startswith("2026-08-23T15:00:00")


def test_removal_status_deletes_store_price(tmp_path: Path):
    dbp = tmp_path / "db.sqlite3"
    init_db(dbp)
    stores = tmp_path / "Stores7290696200003-001-20260823-180000.xml"
    stores.write_text(_stores_xml(), encoding="utf-8")
    full = tmp_path / "PriceFull7290696200003-001-101-20260823-180000.xml"
    full.write_text(
        _price_xml("<Item><ItemCode>A</ItemCode><ItemName>חלב 3%</ItemName><ItemPrice>6</ItemPrice><ItemStatus>2</ItemStatus></Item>"),
        encoding="utf-8",
    )
    remove = tmp_path / "Price7290696200003-001-101-20260823-200000.xml"
    remove.write_text(
        _price_xml("<Item><ItemCode>A</ItemCode><ItemName>חלב 3%</ItemName><ItemStatus>0</ItemStatus></Item>"),
        encoding="utf-8",
    )
    ingest_file(dbp, stores, "VICTORY_NEW_SOURCE")
    ingest_file(dbp, full, "VICTORY_NEW_SOURCE")
    ingest_file(dbp, remove, "VICTORY_NEW_SOURCE")
    with db(dbp) as con:
        assert con.execute("SELECT COUNT(*) FROM prices WHERE barcode='A'").fetchone()[0] == 0


def test_older_file_cannot_overwrite_newer_price(tmp_path: Path):
    dbp = tmp_path / "db.sqlite3"
    init_db(dbp)
    stores = tmp_path / "Stores7290696200003-001-20260823-180000.xml"
    stores.write_text(_stores_xml(), encoding="utf-8")
    newer = tmp_path / "Price7290696200003-001-101-20260823-210000.xml"
    newer.write_text(_price_xml("<Item><ItemCode>A</ItemCode><ItemName>חלב 3%</ItemName><ItemPrice>7</ItemPrice></Item>"), encoding="utf-8")
    older = tmp_path / "PriceFull7290696200003-001-101-20260823-190000.xml"
    older.write_text(_price_xml("<Item><ItemCode>A</ItemCode><ItemName>חלב 3%</ItemName><ItemPrice>5</ItemPrice></Item>"), encoding="utf-8")
    ingest_file(dbp, stores, "VICTORY_NEW_SOURCE")
    ingest_file(dbp, newer, "VICTORY_NEW_SOURCE")
    ingest_file(dbp, older, "VICTORY_NEW_SOURCE")
    with db(dbp) as con:
        row = con.execute("SELECT price,observed_at FROM prices WHERE barcode='A'").fetchone()
    assert row["price"] == 7
    assert row["observed_at"].startswith("2026-08-23T18:00:00")


def test_ingest_directory_skips_unchanged_files(tmp_path: Path):
    dbp = tmp_path / "db.sqlite3"
    raw = tmp_path / "raw"
    raw.mkdir()
    init_db(dbp)
    p = raw / "Price7290696200003-001-101-20260823-210000.xml"
    p.write_text(_price_xml("<Item><ItemCode>A</ItemCode><ItemName>חלב 3%</ItemName><ItemPrice>7</ItemPrice></Item>"), encoding="utf-8")
    first = ingest_directory(dbp, raw)
    second = ingest_directory(dbp, raw)
    assert first and not first[0].get("skipped", False)
    assert second == [{"file": p.name, "skipped": True}]


def test_api_rejects_partial_gps(tmp_path: Path, monkeypatch):
    dbp = tmp_path / "t.sqlite3"
    monkeypatch.setattr(main.settings, "db_path", dbp)
    init_db(dbp)
    with TestClient(main.app) as client:
        r = client.get("/api/search", params={"q": "חלב", "lat": 31.25})
    assert r.status_code == 422


def test_gps_takes_precedence_over_city(tmp_path: Path, monkeypatch):
    from app.demo import seed_demo

    dbp = tmp_path / "t.sqlite3"
    monkeypatch.setattr(main.settings, "db_path", dbp)
    init_db(dbp)
    seed_demo(dbp)
    # Deliberately pass the wrong city; GPS mode should still find nearby Beer Sheva stores.
    with TestClient(main.app) as client:
        r = client.get(
            "/api/search",
            params={"q": "שוקו", "city": "ירושלים", "lat": 31.252, "lng": 34.791, "radius_km": 5},
        )
    assert r.status_code == 200
    assert r.json()["count"] > 0


def test_store_number_leading_zeroes_do_not_create_duplicate_branch(tmp_path: Path):
    dbp = tmp_path / "db.sqlite3"
    init_db(dbp)
    stores = tmp_path / "Stores7290696200003-001-20260823-180000.xml"
    stores.write_text(_stores_xml(store_id="12"), encoding="utf-8")
    # No StoreId in XML: parser must use 012 from filename and loader must normalize it to 12.
    price = tmp_path / "Price7290696200003-001-012-20260823-200000.xml"
    price.write_text("<Root><ChainId>7290696200003</ChainId><Items><Item><ItemCode>A</ItemCode><ItemName>שוקו</ItemName><ItemPrice>8</ItemPrice></Item></Items></Root>", encoding="utf-8")
    ingest_file(dbp, stores, "VICTORY_NEW_SOURCE")
    ingest_file(dbp, price, "VICTORY_NEW_SOURCE")
    with db(dbp) as con:
        ids = [r[0] for r in con.execute("SELECT id FROM stores").fetchall()]
    assert ids == ["VICTORY_NEW_SOURCE:12"]
