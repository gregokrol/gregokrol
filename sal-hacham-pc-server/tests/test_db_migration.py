from __future__ import annotations

import sqlite3
from pathlib import Path

from app.db import connect, init_db


def test_v7_database_without_observed_at_migrates(tmp_path: Path):
    p = tmp_path / "old.sqlite3"
    con = sqlite3.connect(p)
    con.executescript(
        """
        CREATE TABLE stores(id TEXT PRIMARY KEY,chain_key TEXT NOT NULL,chain_name TEXT NOT NULL,store_number TEXT,name TEXT NOT NULL,city TEXT,address TEXT,lat REAL,lng REAL,updated_at TEXT NOT NULL,is_demo INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE products(barcode TEXT PRIMARY KEY,name TEXT NOT NULL,manufacturer TEXT,updated_at TEXT NOT NULL,is_demo INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE prices(store_id TEXT NOT NULL,barcode TEXT NOT NULL,price REAL NOT NULL,unit_price REAL,updated_at TEXT NOT NULL,is_demo INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(store_id,barcode));
        INSERT INTO stores VALUES('s','X','X','1','S',NULL,NULL,NULL,NULL,'2026-08-23T10:00:00+00:00',0);
        INSERT INTO products VALUES('b','P',NULL,'2026-08-23T10:00:00+00:00',0);
        INSERT INTO prices VALUES('s','b',1,NULL,'2026-08-23T10:00:00+00:00',0);
        """
    )
    con.commit(); con.close()
    init_db(p)
    with connect(p) as con2:
        cols = {r[1] for r in con2.execute("PRAGMA table_info(prices)")}
        row = con2.execute("SELECT observed_at FROM prices").fetchone()
        ledger = con2.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ingested_files'").fetchone()
    assert "observed_at" in cols
    assert row[0] == "2026-08-23T10:00:00+00:00"
    assert ledger is not None
