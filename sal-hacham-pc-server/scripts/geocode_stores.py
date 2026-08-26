#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import httpx

from app.config import settings
from app.db import db, init_db

URL = "https://nominatim.openstreetmap.org/search"


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Geocode stores missing coordinates using OpenStreetMap Nominatim"
    )
    ap.add_argument("--limit", type=int, default=100)
    args = ap.parse_args()
    init_db(settings.db_path)
    with db(settings.db_path) as con:
        rows = con.execute(
            """SELECT id,address,city,name FROM stores
               WHERE lat IS NULL AND lng IS NULL AND name IS NOT NULL LIMIT ?""",
            (args.limit,),
        ).fetchall()
    headers = {"User-Agent": "sal-hacham/7.1 supermarket-price-comparison"}
    updated = 0
    with httpx.Client(timeout=15, headers=headers) as client:
        for r in rows:
            queries = []
            if r["address"] and r["city"]:
                queries.append(f"{r['address']}, {r['city']}, Israel")
            if r["city"]:
                queries.append(f"{r['name']}, {r['city']}, Israel")
            else:
                queries.append(f"{r['name']}, Israel")
            hit = None
            for q in queries:
                try:
                    res = client.get(
                        URL,
                        params={"q": q, "format": "jsonv2", "limit": 1, "countrycodes": "il"},
                    )
                    res.raise_for_status()
                    data = res.json()
                    if data:
                        hit = data[0]
                        break
                except Exception as exc:
                    print(f"{r['id']}: geocode error: {exc}")
                time.sleep(1.1)
            if hit:
                with db(settings.db_path) as con:
                    con.execute(
                        "UPDATE stores SET lat=?,lng=? WHERE id=?",
                        (float(hit["lat"]), float(hit["lon"]), r["id"]),
                    )
                updated += 1
                print(f"{r['id']}: {hit['lat']},{hit['lon']}")
            time.sleep(1.1)
    print(f"Geocoded {updated}/{len(rows)} stores")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
