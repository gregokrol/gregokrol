from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from .db import db

def _observed_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def record_price_observation(
    con,
    store_id: str,
    barcode: str,
    price: float,
    observed_at: str,
    window_days: int = 30,
) -> None:
    """Keep one aggregate row per store/product for the current 30-day window."""
    if price <= 0:
        return
    observed = _observed_datetime(observed_at)
    row = con.execute(
        "SELECT * FROM price_history WHERE store_id=? AND barcode=?",
        (store_id, barcode),
    ).fetchone()
    if row and observed <= _observed_datetime(row["last_observed_at"]):
        return
    reset = not row or observed >= _observed_datetime(row["window_started_at"]) + timedelta(days=max(1, window_days))
    if reset:
        con.execute(
            """INSERT INTO price_history(
                 store_id,barcode,window_started_at,low_price,high_price,price_sum,sample_count,last_observed_at)
               VALUES(?,?,?,?,?,?,1,?)
               ON CONFLICT(store_id,barcode) DO UPDATE SET
                 window_started_at=excluded.window_started_at,low_price=excluded.low_price,
                 high_price=excluded.high_price,price_sum=excluded.price_sum,
                 sample_count=1,last_observed_at=excluded.last_observed_at""",
            (store_id, barcode, observed_at, price, price, price, observed_at),
        )
        return
    con.execute(
        """UPDATE price_history SET low_price=MIN(low_price,?),high_price=MAX(high_price,?),
             price_sum=price_sum+?,sample_count=sample_count+1,last_observed_at=?
           WHERE store_id=? AND barcode=?""",
        (price, price, price, observed_at, store_id, barcode),
    )


def prune_price_history(db_path: Path, days: int = 30, now: datetime | None = None) -> int:
    cutoff = ((now or datetime.now(timezone.utc)).astimezone(timezone.utc) - timedelta(days=max(1, days))).isoformat()
    with db(db_path) as con:
        cursor = con.execute("DELETE FROM price_history WHERE last_observed_at<?", (cutoff,))
        con.execute(
            """DELETE FROM products
               WHERE barcode NOT IN (SELECT barcode FROM prices)
                 AND barcode NOT IN (SELECT barcode FROM promotion_items)
                 AND barcode NOT IN (SELECT barcode FROM price_history)"""
        )
        return max(cursor.rowcount, 0)


def observed_day_count(started_at: str, last_observed_at: str) -> int:
    delta = _observed_datetime(last_observed_at) - _observed_datetime(started_at)
    return max(1, delta.days + 1)
