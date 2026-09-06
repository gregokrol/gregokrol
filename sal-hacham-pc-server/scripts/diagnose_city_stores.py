#!/usr/bin/env python3
"""One-off diagnostic: why does a city match fewer stores than expected?

Shows every distinct spelling of the "city" field (and a name/address-based
substring search) for stores that plausibly belong to a given city, so we can
tell apart a spelling-mismatch bug from the national store directory simply
being incomplete. Usage:
    python scripts/diagnose_city_stores.py "פתח תקווה" "תקו"
The second argument is a short substring (without niqqud) to broadly search
name/address/city with, in case the exact city name doesn't match anything.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.city_cache import _store_belongs_to_city
from app.config import settings
from app.db import db
from app.search import normalize
from app.service import normalize_city


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: python diagnose_city_stores.py <city name> <broad substring>", flush=True)
        return 1
    city = sys.argv[1]
    needle = normalize(sys.argv[2])
    city_key = normalize_city(city)

    with db(settings.db_path) as con:
        total = con.execute("SELECT COUNT(*) FROM stores WHERE is_demo=0").fetchone()[0]
        chains = con.execute("SELECT COUNT(DISTINCT chain_key) FROM stores WHERE is_demo=0").fetchone()[0]
        exact = con.execute(
            "SELECT COUNT(*) FROM stores WHERE is_demo=0 AND city=?", (city,)
        ).fetchone()[0]
        rows = con.execute(
            "SELECT chain_key,chain_name,name,city,address FROM stores WHERE is_demo=0"
        ).fetchall()

    print(f"Total stores nationally: {total} across {chains} chains", flush=True)
    print(f"Stores with city field exactly '{city}': {exact}", flush=True)

    broad_matches = [
        r for r in rows
        if needle and needle in normalize(f"{r['name'] or ''} {r['address'] or ''} {r['city'] or ''}")
    ]
    print(f"\nStores whose name/address/city loosely contains '{sys.argv[2]}': {len(broad_matches)}", flush=True)
    city_spellings: dict[str, int] = {}
    for r in broad_matches:
        city_spellings[r["city"] or "(empty)"] = city_spellings.get(r["city"] or "(empty)", 0) + 1
    print("Distinct city-field spellings among those:", flush=True)
    for spelling, count in sorted(city_spellings.items(), key=lambda kv: -kv[1]):
        matches_our_key = normalize_city(spelling) == city_key
        print(f"  {count:4d}  {spelling!r}  (matches our city_key: {matches_our_key})", flush=True)

    would_be_included = sum(1 for r in broad_matches if _store_belongs_to_city(r, city_key))
    print(f"\nOf those, would currently match _store_belongs_to_city('{city}'): {would_be_included}", flush=True)

    print("\nSample rows (first 15):", flush=True)
    for r in broad_matches[:15]:
        print(f"  chain={r['chain_key']:<28} city={r['city']!r:<20} name={r['name']!r} address={r['address']!r}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
