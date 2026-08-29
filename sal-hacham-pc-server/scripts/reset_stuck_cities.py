#!/usr/bin/env python3
"""One-off maintenance: release any city stuck in status='running'.

A refresh that dies without going through the normal fail/finish path
(e.g. a scraper import crash before the fix in this same commit) leaves
city_cache stuck at status='running', and due_cities() then refuses to
retry a 'running' city for 3 hours. This clears that so the next sync
attempt is picked up immediately instead of waiting it out.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import settings
from app.db import db


def main() -> int:
    with db(settings.db_path) as con:
        cur = con.execute(
            "UPDATE city_cache SET status='error', queued_at=NULL WHERE status='running'"
        )
        print(f"Released {cur.rowcount} stuck city row(s).", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
