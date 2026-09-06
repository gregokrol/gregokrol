#!/usr/bin/env python3
"""One-off migration: re-key any city_cache row whose stored city_key no
longer matches what normalize_city() computes today.

Needed after the Hebrew double/single-vav spelling fix changed what
normalize_city() returns for cities like Petah Tikva (e.g. "פתח תקווה" now
folds to "פתח תקוה"). A row created under the old key becomes invisible to
touch_city/queue_city_if_due (which look it up by the new key), so a fresh
search would silently start a brand new, unsynced city instead of reusing
the one already refreshed. This renames it in place instead of losing it.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import settings
from app.db import db
from app.service import normalize_city


def main() -> int:
    changed = 0
    with db(settings.db_path) as con:
        rows = con.execute("SELECT * FROM city_cache").fetchall()
        for row in rows:
            old_key = row["city_key"]
            new_key = normalize_city(row["city_name"])
            if new_key == old_key:
                continue
            existing = con.execute(
                "SELECT 1 FROM city_cache WHERE city_key=?", (new_key,)
            ).fetchone()
            if existing:
                print(f"Dropping stale duplicate {old_key!r} (kept existing {new_key!r})", flush=True)
                con.execute("DELETE FROM city_cache WHERE city_key=?", (old_key,))
            else:
                cols = list(row.keys())
                values = [new_key if c == "city_key" else row[c] for c in cols]
                placeholders = ",".join("?" for _ in cols)
                con.execute(
                    f"INSERT INTO city_cache({','.join(cols)}) VALUES({placeholders})", values
                )
                con.execute("DELETE FROM city_cache WHERE city_key=?", (old_key,))
                print(f"Renamed {old_key!r} -> {new_key!r}", flush=True)
            changed += 1
    print(f"Done. {changed} row(s) re-keyed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
