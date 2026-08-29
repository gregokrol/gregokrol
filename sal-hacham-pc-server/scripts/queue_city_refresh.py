#!/usr/bin/env python3
"""Force an immediate refresh of the bot's configured city, bypassing the
normal staleness gate (active cities only re-sync every few hours). Useful
right after a parser/schema change, to re-pull data with the new fields
without waiting for the next scheduled window. Reads the city from the DB
so nothing has to be typed here (see manual_sync.py for why).
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import settings
from app.db import db
from app.personal_lists import get_bot_city
from app.service import normalize_city


def main() -> int:
    city = get_bot_city(settings.db_path)
    if not city:
        print("No city configured yet - set one via the Telegram bot first.", flush=True)
        return 1
    city_key = normalize_city(city)
    now_iso = datetime.now(timezone.utc).isoformat()
    with db(settings.db_path) as con:
        cur = con.execute(
            "UPDATE city_cache SET status='queued',queued_at=?,last_error=NULL WHERE city_key=?",
            (now_iso, city_key),
        )
        print(f"Queued {city} for immediate refresh ({cur.rowcount} row updated).", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
