#!/usr/bin/env python3
"""One-off diagnostic: search product NAMES directly with a raw SQL LIKE,
bypassing relevance ranking and the max_results cutoff entirely, to tell
apart "the product genuinely isn't in the data we ingested" from "it's
there but ranked too low to appear in normal search results"."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import settings
from app.db import db


def main() -> int:
    needle = sys.argv[1] if len(sys.argv) > 1 else "חלב"
    chain_key = sys.argv[2] if len(sys.argv) > 2 else None
    with db(settings.db_path) as con:
        if chain_key:
            rows = con.execute(
                """SELECT p.barcode,p.name,p.package_label,s.chain_key,s.name store_name,pr.price
                   FROM products p
                   JOIN prices pr ON pr.barcode=p.barcode
                   JOIN stores s ON s.id=pr.store_id
                   WHERE p.name LIKE ? AND s.chain_key=?
                   ORDER BY p.name""",
                (f"%{needle}%", chain_key),
            ).fetchall()
        else:
            rows = con.execute(
                """SELECT p.barcode,p.name,p.package_label,s.chain_key,s.name store_name,pr.price
                   FROM products p
                   JOIN prices pr ON pr.barcode=p.barcode
                   JOIN stores s ON s.id=pr.store_id
                   WHERE p.name LIKE ?
                   ORDER BY s.chain_key,p.name""",
                (f"%{needle}%",),
            ).fetchall()
    print(f"Products with a fresh price whose name contains {needle!r}: {len(rows)}", flush=True)
    for r in rows:
        print(f"  {r['chain_key']:<20} {r['store_name']:<25} {r['price']:<8} {r['name']!r} pkg={r['package_label']!r}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
