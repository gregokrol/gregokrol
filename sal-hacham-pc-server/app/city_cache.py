from __future__ import annotations

import hashlib
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .db import connect, db, utc_now_iso
from .search import normalize
from .service import normalize_city


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def city_storage_token(city_key: str) -> str:
    """Return a stable, path-safe identifier without exposing the city name in paths."""
    return hashlib.sha256(city_key.encode("utf-8")).hexdigest()[:16]


def _store_belongs_to_city(store, city_key: str) -> bool:
    if normalize_city(store["city"]) == city_key:
        return True
    location = normalize(f"{store['name'] or ''} {store['address'] or ''}")
    return bool(city_key and city_key in location)


def _refresh_memberships(con) -> None:
    cities = con.execute("SELECT city_key FROM city_cache").fetchall()
    stores = con.execute("SELECT id,name,city,address FROM stores WHERE is_demo=0").fetchall()
    for city in cities:
        key = city["city_key"]
        con.execute("DELETE FROM city_stores WHERE city_key=?", (key,))
        con.executemany(
            "INSERT OR IGNORE INTO city_stores(city_key,store_id) VALUES(?,?)",
            [(key, store["id"]) for store in stores if _store_belongs_to_city(store, key)],
        )


def _prune_uncached_data(con) -> None:
    """Keep the small national store directory, but retain prices for cached cities only."""
    con.execute(
        "DELETE FROM promotion_items WHERE store_id NOT IN (SELECT store_id FROM city_stores)"
    )
    con.execute(
        "DELETE FROM promotions WHERE store_id NOT IN (SELECT store_id FROM city_stores)"
    )
    con.execute(
        "DELETE FROM price_history WHERE store_id NOT IN (SELECT store_id FROM city_stores)"
    )
    con.execute("DELETE FROM prices WHERE store_id NOT IN (SELECT store_id FROM city_stores)")
    con.execute(
        """DELETE FROM products
           WHERE barcode NOT IN (SELECT barcode FROM prices)
             AND barcode NOT IN (SELECT barcode FROM promotion_items)
             AND barcode NOT IN (SELECT barcode FROM price_history)"""
    )


def refresh_city_memberships(db_path: Path, *, prune: bool = True) -> None:
    with db(db_path) as con:
        _refresh_memberships(con)
        if prune:
            _prune_uncached_data(con)


def cleanup_evicted_storage(raw_dir: Path, city_keys: list[str]) -> None:
    roots = [raw_dir / "cities", raw_dir / ".status" / "cities"]
    for city_key in city_keys:
        token = city_storage_token(city_key)
        for root in roots:
            target = root / token
            if target.parent == root and target.exists():
                shutil.rmtree(target, ignore_errors=True)


def touch_city(db_path: Path, city: str, max_cities: int = 5, now: datetime | None = None) -> dict[str, Any] | None:
    key = normalize_city(city)
    display = key
    if not key or not display:
        return None
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    now_iso = now.isoformat()
    con = connect(db_path)
    evicted: list[str] = []
    try:
        con.execute("BEGIN IMMEDIATE")
        existed = bool(con.execute("SELECT 1 FROM city_cache WHERE city_key=?", (key,)).fetchone())
        con.execute("UPDATE city_cache SET is_active=0 WHERE is_active<>0")
        con.execute(
            """INSERT INTO city_cache(city_key,city_name,is_active,status,last_requested_at)
               VALUES(?,?,1,'pending',?)
               ON CONFLICT(city_key) DO UPDATE SET
                 city_name=excluded.city_name,is_active=1,last_requested_at=excluded.last_requested_at""",
            (key, display, now_iso),
        )
        if not existed:
            _refresh_memberships(con)
        rows = con.execute(
            """SELECT city_key FROM city_cache
               WHERE city_key<>?
               ORDER BY last_requested_at ASC,city_key ASC""",
            (key,),
        ).fetchall()
        excess = max(0, len(rows) + 1 - max(1, max_cities))
        evicted = [row["city_key"] for row in rows[:excess]]
        for old_key in evicted:
            con.execute("DELETE FROM city_cache WHERE city_key=?", (old_key,))
        if not existed or evicted:
            _prune_uncached_data(con)
        # Avoid a false 'already ingested' decision if an evicted city is selected
        # again, without invalidating the ledgers of the other four cities.
        for old_key in evicted:
            con.execute(
                "DELETE FROM ingested_files WHERE instr(path,?)>0",
                (city_storage_token(old_key),),
            )
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()
    return {"city_key": key, "city_name": display, "evicted": evicted}


def _row_due(row, now: datetime, active_hours: int, inactive_hours: int) -> bool:
    completed = _parse_timestamp(row["last_refresh_completed_at"])
    interval = active_hours if row["is_active"] else inactive_hours
    return completed is None or completed <= now - timedelta(hours=interval)


def queue_city_if_due(
    db_path: Path,
    city_key: str,
    *,
    active_hours: int = 4,
    inactive_hours: int = 24,
    now: datetime | None = None,
) -> bool:
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    now_iso = now.isoformat()
    stale_work = now - timedelta(hours=3)
    con = connect(db_path)
    try:
        con.execute("BEGIN IMMEDIATE")
        row = con.execute("SELECT * FROM city_cache WHERE city_key=?", (city_key,)).fetchone()
        if not row or not _row_due(row, now, active_hours, inactive_hours):
            con.commit()
            return False
        work_at = _parse_timestamp(row["last_refresh_started_at"] or row["queued_at"])
        if row["status"] in {"queued", "running"} and work_at and work_at > stale_work:
            con.commit()
            return False
        con.execute(
            "UPDATE city_cache SET status='queued',queued_at=?,last_error=NULL WHERE city_key=?",
            (now_iso, city_key),
        )
        con.commit()
        return True
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def due_cities(
    db_path: Path,
    *,
    active_hours: int = 4,
    inactive_hours: int = 24,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    stale_work = now - timedelta(hours=3)
    with db(db_path) as con:
        rows = con.execute(
            "SELECT * FROM city_cache ORDER BY is_active DESC,last_requested_at DESC"
        ).fetchall()
    due = []
    for row in rows:
        work_at = _parse_timestamp(row["last_refresh_started_at"] or row["queued_at"])
        work_stale = not work_at or work_at <= stale_work
        if row["status"] == "queued" or (
            _row_due(row, now, active_hours, inactive_hours)
            and (row["status"] != "running" or work_stale)
        ):
            due.append(dict(row))
    return due


def claim_city_refresh(db_path: Path, city_key: str, now: datetime | None = None) -> bool:
    now_iso = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
    con = connect(db_path)
    try:
        con.execute("BEGIN IMMEDIATE")
        row = con.execute("SELECT status FROM city_cache WHERE city_key=?", (city_key,)).fetchone()
        if not row:
            con.commit()
            return False
        con.execute(
            """UPDATE city_cache SET status='running',queued_at=NULL,
               last_refresh_started_at=?,last_error=NULL WHERE city_key=?""",
            (now_iso, city_key),
        )
        con.commit()
        return True
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def finish_city_refresh(
    db_path: Path,
    city_key: str,
    *,
    status: str,
    file_count: int = 0,
    store_count: int = 0,
    error: str | None = None,
    now: datetime | None = None,
) -> None:
    now_iso = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
    with db(db_path) as con:
        con.execute(
            """UPDATE city_cache SET status=?,queued_at=NULL,last_refresh_completed_at=?,
               last_error=?,last_file_count=?,last_store_count=? WHERE city_key=?""",
            (status, now_iso, error, file_count, store_count, city_key),
        )


def fail_city_refresh(db_path: Path, city_key: str, error: str) -> None:
    with db(db_path) as con:
        con.execute(
            "UPDATE city_cache SET status='error',queued_at=NULL,last_error=? WHERE city_key=?",
            (error[:500], city_key),
        )


def stores_for_city(db_path: Path, city_key: str) -> list[dict[str, str]]:
    with db(db_path) as con:
        rows = con.execute(
            """SELECT s.id,s.chain_key,s.store_number,s.name,s.city
               FROM city_stores cs JOIN stores s ON s.id=cs.store_id
               WHERE cs.city_key=? AND s.is_demo=0
               ORDER BY s.chain_key,s.store_number""",
            (city_key,),
        ).fetchall()
    return [dict(row) for row in rows]


def cached_cities(db_path: Path) -> list[dict[str, Any]]:
    with db(db_path) as con:
        rows = con.execute(
            """SELECT c.*,(SELECT COUNT(*) FROM city_stores cs WHERE cs.city_key=c.city_key) store_count
               FROM city_cache c ORDER BY c.is_active DESC,c.last_requested_at DESC"""
        ).fetchall()
    return [dict(row) for row in rows]


def city_cache_status(
    db_path: Path,
    city: str,
    *,
    max_cities: int = 5,
    active_hours: int = 4,
    inactive_hours: int = 24,
    now: datetime | None = None,
) -> dict[str, Any] | None:
    key = normalize_city(city)
    if not key:
        return None
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    with db(db_path) as con:
        row = con.execute(
            """SELECT c.*,(SELECT COUNT(*) FROM city_stores cs WHERE cs.city_key=c.city_key) store_count,
                      (SELECT COUNT(*) FROM city_cache) retained_count
               FROM city_cache c WHERE c.city_key=?""",
            (key,),
        ).fetchone()
        retained = [
            item["city_name"]
            for item in con.execute(
                "SELECT city_name FROM city_cache ORDER BY is_active DESC,last_requested_at DESC"
            ).fetchall()
        ]
    if not row:
        return None
    completed = _parse_timestamp(row["last_refresh_completed_at"])
    interval = active_hours if row["is_active"] else inactive_hours
    next_refresh = completed + timedelta(hours=interval) if completed else now
    return {
        "city": row["city_name"],
        "active": bool(row["is_active"]),
        "status": row["status"],
        "refresh_in_progress": row["status"] in {"queued", "running"},
        "last_refresh_at": row["last_refresh_completed_at"],
        "next_refresh_at": next_refresh.isoformat(),
        "refresh_interval_hours": interval,
        "last_error": row["last_error"],
        "store_count": int(row["store_count"] or 0),
        "retained_count": int(row["retained_count"] or 0),
        "retained_cities": retained,
        "max_cities": max_cities,
    }


def collector_state_get(db_path: Path, key: str) -> str | None:
    with db(db_path) as con:
        row = con.execute("SELECT value FROM collector_state WHERE key=?", (key,)).fetchone()
    return row["value"] if row else None


def collector_state_set(db_path: Path, key: str, value: str | None) -> None:
    with db(db_path) as con:
        con.execute(
            """INSERT INTO collector_state(key,value,updated_at) VALUES(?,?,?)
               ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at""",
            (key, value, utc_now_iso()),
        )


def state_is_older_than(db_path: Path, key: str, hours: int, now: datetime | None = None) -> bool:
    value = _parse_timestamp(collector_state_get(db_path, key))
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return value is None or value <= now - timedelta(hours=hours)


def cache_health(db_path: Path, max_cities: int = 5) -> dict[str, Any]:
    cities = cached_cities(db_path)
    return {
        "cached_city_count": len(cities),
        "max_cached_cities": max_cities,
        "active_city": next((row["city_name"] for row in cities if row["is_active"]), None),
        "cached_cities": [
            {
                "city": row["city_name"],
                "active": bool(row["is_active"]),
                "status": row["status"],
                "last_refresh_at": row["last_refresh_completed_at"],
                "stores": int(row["store_count"] or 0),
            }
            for row in cities
        ],
    }
