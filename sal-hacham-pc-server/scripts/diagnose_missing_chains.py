#!/usr/bin/env python3
"""One-off diagnostic: for specific chains the user expects to see in a city,
show how many stores that chain has nationally, and what city text they carry,
to tell apart "chain not scraped at all" from "scraped but city mismatch" from
"genuinely has no branch there"."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.city_cache import _store_belongs_to_city
from app.config import settings
from app.db import db
from app.service import normalize_city
from app.source_registry import CHAIN_SOURCES, CHAIN_DISPLAY


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: python diagnose_missing_chains.py <city name> <chain_key> [chain_key ...]", flush=True)
        return 1
    city = sys.argv[1]
    chain_keys = sys.argv[2:]
    city_key = normalize_city(city)

    known_keys = {key for key, _ in CHAIN_SOURCES}
    for chain_key in chain_keys:
        display = CHAIN_DISPLAY.get(chain_key, chain_key)
        in_registry = chain_key in known_keys
        print(f"\n=== {chain_key} ({display}) - in our CHAIN_SOURCES: {in_registry} ===", flush=True)
        with db(settings.db_path) as con:
            rows = con.execute(
                "SELECT name,city,address FROM stores WHERE is_demo=0 AND chain_key=?", (chain_key,)
            ).fetchall()
        print(f"Stores nationally for this chain: {len(rows)}", flush=True)
        if not rows:
            continue
        matches = [r for r in rows if _store_belongs_to_city(r, city_key)]
        print(f"Of those, matching city '{city}': {len(matches)}", flush=True)
        for r in matches:
            print(f"  MATCH: {r['name']!r} | city={r['city']!r} | address={r['address']!r}", flush=True)
        print("Sample of all this chain's stores (first 8, to see the city-field pattern):", flush=True)
        for r in rows[:8]:
            print(f"  {r['name']!r} | city={r['city']!r} | address={r['address']!r}", flush=True)

    print("\n=== Scraper identifiers not in our CHAIN_SOURCES at all ===", flush=True)
    try:
        from app.win_compat import install_fcntl_stub
        install_fcntl_stub()
        from il_supermarket_scarper import ScraperFactory
        available = set(ScraperFactory.all_scrapers_name())
        missing_from_ours = sorted(available - known_keys)
        print("Available in the scraper library but NOT in our registry:", flush=True)
        for name in missing_from_ours:
            print(f"  {name}", flush=True)
    except Exception as exc:
        print(f"(could not check scraper library: {type(exc).__name__}: {exc})", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
