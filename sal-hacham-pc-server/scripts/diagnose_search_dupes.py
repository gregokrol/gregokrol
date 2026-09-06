#!/usr/bin/env python3
"""One-off diagnostic: show the raw barcode/store/price rows behind a search
query, to tell apart genuinely distinct products (different barcodes, e.g.
different container sizes) from a real duplicate-row bug (same barcode,
same store, appearing more than once)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import settings
from app.personal_lists import get_bot_city
from app.service import search_prices


def main() -> int:
    query = sys.argv[1] if len(sys.argv) > 1 else "חלב"
    city = get_bot_city(settings.db_path)
    result = search_prices(
        settings.db_path, query, city, None, None,
        settings.default_radius_km, settings.max_price_age_hours, None,
        max_results=30, history_days=settings.price_history_days,
    )
    hits = result.get("results") or []
    print(f"query={query!r} city={city!r} hits={len(hits)}", flush=True)
    for h in hits:
        print(
            f"  barcode={h['barcode']:<16} price={h['price']:<6} "
            f"pkg={h.get('package_label')!r:<12} store_id={h['store_id']:<20} "
            f"chain={h['chain_key']:<20} name={h['product_name']!r}",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
