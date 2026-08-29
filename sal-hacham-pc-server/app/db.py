from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS stores (
  id TEXT PRIMARY KEY,
  chain_key TEXT NOT NULL,
  chain_name TEXT NOT NULL,
  store_number TEXT,
  name TEXT NOT NULL,
  city TEXT,
  address TEXT,
  lat REAL,
  lng REAL,
  updated_at TEXT NOT NULL,
  is_demo INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_stores_city ON stores(city);
CREATE INDEX IF NOT EXISTS idx_stores_chain ON stores(chain_key);

CREATE TABLE IF NOT EXISTS products (
  barcode TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  manufacturer TEXT,
  package_label TEXT,
  updated_at TEXT NOT NULL,
  is_demo INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS prices (
  store_id TEXT NOT NULL,
  barcode TEXT NOT NULL,
  price REAL NOT NULL,
  unit_price REAL,
  updated_at TEXT NOT NULL,
  observed_at TEXT NOT NULL,
  is_demo INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (store_id, barcode),
  FOREIGN KEY(store_id) REFERENCES stores(id),
  FOREIGN KEY(barcode) REFERENCES products(barcode)
);
CREATE INDEX IF NOT EXISTS idx_prices_updated ON prices(updated_at);
CREATE INDEX IF NOT EXISTS idx_prices_observed ON prices(observed_at);
CREATE INDEX IF NOT EXISTS idx_prices_barcode ON prices(barcode);
CREATE INDEX IF NOT EXISTS idx_prices_store_observed ON prices(store_id, observed_at);

CREATE TABLE IF NOT EXISTS price_history (
  store_id TEXT NOT NULL,
  barcode TEXT NOT NULL,
  window_started_at TEXT NOT NULL,
  low_price REAL NOT NULL,
  high_price REAL NOT NULL,
  price_sum REAL NOT NULL,
  sample_count INTEGER NOT NULL,
  last_observed_at TEXT NOT NULL,
  PRIMARY KEY (store_id, barcode),
  FOREIGN KEY(store_id) REFERENCES stores(id) ON DELETE CASCADE,
  FOREIGN KEY(barcode) REFERENCES products(barcode) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_price_history_observed ON price_history(last_observed_at);
CREATE INDEX IF NOT EXISTS idx_price_history_product ON price_history(barcode);

CREATE TABLE IF NOT EXISTS promotions (
  store_id TEXT NOT NULL,
  promotion_id TEXT NOT NULL,
  description TEXT NOT NULL,
  start_at TEXT,
  end_at TEXT,
  updated_at TEXT NOT NULL,
  observed_at TEXT NOT NULL,
  reward_type TEXT,
  allow_multiple_discounts INTEGER NOT NULL DEFAULT 0,
  is_weighted INTEGER NOT NULL DEFAULT 0,
  min_qty REAL,
  discounted_price REAL,
  discounted_unit_price REAL,
  is_coupon INTEGER NOT NULL DEFAULT 0,
  is_active INTEGER NOT NULL DEFAULT 1,
  club_ids TEXT,
  remarks TEXT,
  is_demo INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (store_id, promotion_id),
  FOREIGN KEY(store_id) REFERENCES stores(id)
);
CREATE INDEX IF NOT EXISTS idx_promotions_store_observed ON promotions(store_id, observed_at);
CREATE INDEX IF NOT EXISTS idx_promotions_active_period ON promotions(is_active, start_at, end_at);
CREATE INDEX IF NOT EXISTS idx_promotions_coupon ON promotions(is_coupon);

CREATE TABLE IF NOT EXISTS promotion_items (
  store_id TEXT NOT NULL,
  promotion_id TEXT NOT NULL,
  barcode TEXT NOT NULL,
  is_gift INTEGER NOT NULL DEFAULT 0,
  item_type TEXT,
  PRIMARY KEY (store_id, promotion_id, barcode),
  FOREIGN KEY(store_id, promotion_id) REFERENCES promotions(store_id, promotion_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_promotion_items_barcode ON promotion_items(barcode);

CREATE TABLE IF NOT EXISTS ingested_files (
  path TEXT PRIMARY KEY,
  size INTEGER NOT NULL,
  mtime_ns INTEGER NOT NULL,
  parser_version INTEGER NOT NULL,
  ingested_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS city_cache (
  city_key TEXT PRIMARY KEY,
  city_name TEXT NOT NULL,
  is_active INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'pending',
  last_requested_at TEXT NOT NULL,
  queued_at TEXT,
  last_refresh_started_at TEXT,
  last_refresh_completed_at TEXT,
  last_error TEXT,
  last_file_count INTEGER NOT NULL DEFAULT 0,
  last_store_count INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_city_cache_requested ON city_cache(last_requested_at);
CREATE INDEX IF NOT EXISTS idx_city_cache_active ON city_cache(is_active);

CREATE TABLE IF NOT EXISTS city_stores (
  city_key TEXT NOT NULL,
  store_id TEXT NOT NULL,
  PRIMARY KEY (city_key, store_id),
  FOREIGN KEY(city_key) REFERENCES city_cache(city_key) ON DELETE CASCADE,
  FOREIGN KEY(store_id) REFERENCES stores(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_city_stores_store ON city_stores(store_id);

CREATE TABLE IF NOT EXISTS collector_state (
  key TEXT PRIMARY KEY,
  value TEXT,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS watch_items (
  barcode TEXT PRIMARY KEY,
  label TEXT NOT NULL,
  city TEXT,
  baseline_price REAL NOT NULL,
  last_notified_price REAL NOT NULL,
  added_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS saved_basket_items (
  barcode TEXT PRIMARY KEY,
  label TEXT NOT NULL,
  qty REAL NOT NULL DEFAULT 1,
  added_at TEXT NOT NULL
);
"""

FTS_SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS products_fts USING fts5(
  barcode UNINDEXED,
  name,
  manufacturer,
  tokenize='unicode61'
);
CREATE TRIGGER IF NOT EXISTS products_fts_ai AFTER INSERT ON products BEGIN
  INSERT INTO products_fts(rowid,barcode,name,manufacturer)
  VALUES (new.rowid,new.barcode,new.name,COALESCE(new.manufacturer,''));
END;
CREATE TRIGGER IF NOT EXISTS products_fts_ad AFTER DELETE ON products BEGIN
  DELETE FROM products_fts WHERE rowid=old.rowid;
END;
CREATE TRIGGER IF NOT EXISTS products_fts_au AFTER UPDATE ON products BEGIN
  DELETE FROM products_fts WHERE rowid=old.rowid;
  INSERT INTO products_fts(rowid,barcode,name,manufacturer)
  VALUES (new.rowid,new.barcode,new.name,COALESCE(new.manufacturer,''));
END;
"""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA busy_timeout=30000")
    return con


def _init_fts(con: sqlite3.Connection) -> bool:
    """Enable optional FTS5 acceleration without making startup depend on it."""
    try:
        con.executescript(FTS_SCHEMA)
        products = con.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        indexed = con.execute("SELECT COUNT(*) FROM products_fts").fetchone()[0]
        if products != indexed:
            con.execute("DELETE FROM products_fts")
            con.execute(
                """INSERT INTO products_fts(rowid,barcode,name,manufacturer)
                   SELECT rowid,barcode,name,COALESCE(manufacturer,'') FROM products"""
            )
        return True
    except sqlite3.OperationalError:
        return False


def init_db(path: Path) -> None:
    with connect(path) as con:
        # Migration safety from V7/V7.1/V7.2 databases.
        existing_tables = {
            r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        if "prices" in existing_tables:
            cols = {r[1] for r in con.execute("PRAGMA table_info(prices)").fetchall()}
            if "observed_at" not in cols:
                con.execute("ALTER TABLE prices ADD COLUMN observed_at TEXT")
                con.execute("UPDATE prices SET observed_at=updated_at WHERE observed_at IS NULL")
        if "products" in existing_tables:
            cols = {r[1] for r in con.execute("PRAGMA table_info(products)").fetchall()}
            if "package_label" not in cols:
                con.execute("ALTER TABLE products ADD COLUMN package_label TEXT")
        con.executescript(SCHEMA)
        con.execute("UPDATE prices SET observed_at=updated_at WHERE observed_at IS NULL")
        _init_fts(con)


def fts_available(con: sqlite3.Connection) -> bool:
    try:
        con.execute("SELECT 1 FROM products_fts LIMIT 1").fetchone()
        return True
    except sqlite3.OperationalError:
        return False


@contextmanager
def db(path: Path):
    con = connect(path)
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()
