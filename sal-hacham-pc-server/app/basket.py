from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from math import floor
from typing import Any

from .db import db
from .search import candidate_products
from .service import _store_matches
from .offers import offer_has_real_saving


def _fresh_cutoff(max_age_hours: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=max_age_hours)).isoformat()


def _candidate_map(con, queries: list[str], per_query: int = 150) -> list[list[tuple[str, float, str]]]:
    out: list[list[tuple[str, float, str]]] = []
    for query in queries:
        scored = candidate_products(con, query, max_candidates=2000)[:per_query]
        out.append([(p["barcode"], score, p["name"]) for p, score in scored])
    return out


def _simple_offer_totals(con, lines_by_store: dict[str, list[dict]], max_age_hours: int, include_coupons: bool) -> None:
    pairs = {
        (sid, line["barcode"])
        for sid, lines in lines_by_store.items()
        for line in lines
        if line.get("barcode")
    }
    if not pairs:
        return
    cutoff = _fresh_cutoff(max_age_hours)
    now = datetime.now(timezone.utc).isoformat()
    con.execute("CREATE TEMP TABLE basket_offer_pairs(store_id TEXT,barcode TEXT,PRIMARY KEY(store_id,barcode))")
    con.executemany("INSERT INTO basket_offer_pairs(store_id,barcode) VALUES(?,?)", pairs)
    rows = con.execute(
        """SELECT bp.store_id,bp.barcode,pr.promotion_id,pr.description,pr.min_qty,
                  pr.discounted_price,pr.discounted_unit_price,pr.is_coupon,pr.is_weighted,
                  pr.club_ids,pr.end_at,
                  (SELECT COUNT(*) FROM promotion_items pi2
                   WHERE pi2.store_id=pr.store_id AND pi2.promotion_id=pr.promotion_id
                     AND pi2.is_gift=0) item_count
           FROM basket_offer_pairs bp
           JOIN promotion_items pi ON pi.store_id=bp.store_id AND pi.barcode=bp.barcode AND pi.is_gift=0
           JOIN promotions pr ON pr.store_id=pi.store_id AND pr.promotion_id=pi.promotion_id
           WHERE pr.is_active=1 AND pr.observed_at>=?
             AND (pr.start_at IS NULL OR pr.start_at<=?)
             AND (pr.end_at IS NULL OR pr.end_at>=?)
           ORDER BY pr.is_coupon ASC,pr.discounted_price ASC""",
        (cutoff, now, now),
    ).fetchall()
    offers: dict[tuple[str, str], list[Any]] = defaultdict(list)
    for r in rows:
        offers[(r["store_id"], r["barcode"])].append(r)

    for sid, lines in lines_by_store.items():
        for line in lines:
            if line.get("missing") or "line_total" not in line:
                line["offers_available"] = 0
                line["coupon_available"] = False
                line["promotion_available"] = False
                line["applied_offer"] = None
                continue
            line["total_after_offer"] = line["line_total"]
            line["applied_offer"] = None
            line["offers_available"] = 0
            line["coupon_available"] = False
            line["promotion_available"] = False
            for r in offers.get((sid, line.get("barcode")), []):
                if not offer_has_real_saving(r, line.get("unit_price")):
                    continue
                line["offers_available"] += 1
                if r["is_coupon"]:
                    line["coupon_available"] = True
                    if not include_coupons:
                        continue
                else:
                    line["promotion_available"] = True
                # Conservative automatic calculation: only a non-weighted promotion
                # with one eligible purchase item and an explicit package price.
                # Mixed-assortment/gift promotions are shown but not guessed into total.
                min_qty = float(r["min_qty"] or 0)
                package_price = r["discounted_price"]
                if r["is_weighted"] or int(r["item_count"] or 0) != 1 or min_qty <= 0 or package_price is None:
                    continue
                qty = float(line["qty"])
                groups = floor((qty + 1e-9) / min_qty)
                if groups < 1:
                    continue
                remainder = max(0.0, qty - groups * min_qty)
                candidate_total = groups * float(package_price) + remainder * float(line["unit_price"])
                if candidate_total + 1e-9 < line["total_after_offer"]:
                    line["total_after_offer"] = round(candidate_total, 2)
                    line["applied_offer"] = {
                        "promotion_id": r["promotion_id"],
                        "description": r["description"],
                        "is_coupon": bool(r["is_coupon"]),
                        "min_qty": min_qty,
                        "discounted_price": float(package_price),
                        "end_at": r["end_at"],
                        "club_ids": [x for x in (r["club_ids"] or "").split(",") if x],
                    }


def compare_basket(
    db_path,
    items: list[dict],
    city: str | None,
    lat: float | None,
    lng: float | None,
    radius_km: float,
    max_age_hours: int,
    chains: list[str] | None = None,
    include_coupons: bool = False,
    max_stores: int = 60,
) -> dict:
    cleaned = []
    for item in items:
        q = str(item.get("q") or "").strip()
        try:
            qty = float(item.get("qty", 1))
        except (TypeError, ValueError):
            qty = 0
        if q and 0 < qty <= 100:
            cleaned.append({"q": q, "qty": qty})
    if not cleaned:
        return {"items": [], "stores": [], "count": 0, "include_coupons": include_coupons}

    cutoff = _fresh_cutoff(max_age_hours)
    with db(db_path) as con:
        store_rows = con.execute(
            """SELECT id,chain_key,chain_name,store_number,name,city,address,lat,lng,updated_at,is_demo
               FROM stores"""
        ).fetchall()
        matched = []
        for s in store_rows:
            ok, distance = _store_matches(s, city, lat, lng, radius_km, chains)
            if ok:
                matched.append((s, distance))
        if not matched:
            return {"items": cleaned, "stores": [], "count": 0, "include_coupons": include_coupons}

        candidate_sets = _candidate_map(con, [x["q"] for x in cleaned])
        all_barcodes = {b for candidates in candidate_sets for b, _, _ in candidates}
        store_ids = {s["id"] for s, _ in matched}
        if not all_barcodes:
            return {"items": cleaned, "stores": [], "count": 0, "include_coupons": include_coupons}

        con.execute("CREATE TEMP TABLE basket_products(barcode TEXT PRIMARY KEY)")
        con.execute("CREATE TEMP TABLE basket_stores(id TEXT PRIMARY KEY)")
        con.executemany("INSERT INTO basket_products(barcode) VALUES(?)", [(x,) for x in all_barcodes])
        con.executemany("INSERT INTO basket_stores(id) VALUES(?)", [(x,) for x in store_ids])
        price_rows = con.execute(
            """SELECT pr.store_id,pr.barcode,pr.price,pr.updated_at,pr.observed_at,p.name,p.manufacturer
               FROM prices pr
               JOIN basket_products bp ON bp.barcode=pr.barcode
               JOIN basket_stores bs ON bs.id=pr.store_id
               JOIN products p ON p.barcode=pr.barcode
               WHERE pr.observed_at>=?""",
            (cutoff,),
        ).fetchall()
        price_map: dict[str, dict[str, Any]] = defaultdict(dict)
        for r in price_rows:
            price_map[r["store_id"]][r["barcode"]] = r

        results: list[dict] = []
        lines_by_store: dict[str, list[dict]] = {}
        for s, distance in matched:
            lines = []
            missing = 0
            for item, candidates in zip(cleaned, candidate_sets):
                available = []
                for barcode, score, _ in candidates:
                    row = price_map.get(s["id"], {}).get(barcode)
                    if row:
                        available.append((score, float(row["price"]), row))
                if not available:
                    missing += 1
                    lines.append({"query": item["q"], "qty": item["qty"], "missing": True})
                    continue
                # Precision first; cheapest among equally relevant alternatives.
                available.sort(key=lambda x: (-x[0], x[1], x[2]["name"]))
                score, price, row = available[0]
                line_total = round(price * item["qty"], 2)
                lines.append({
                    "query": item["q"],
                    "qty": item["qty"],
                    "missing": False,
                    "barcode": row["barcode"],
                    "product_name": row["name"],
                    "manufacturer": row["manufacturer"],
                    "unit_price": price,
                    "line_total": line_total,
                    "relevance": round(float(score), 2),
                    "observed_at": row["observed_at"],
                })
            lines_by_store[s["id"]] = lines
            results.append({
                "store_id": s["id"],
                "chain_key": s["chain_key"],
                "chain_name": s["chain_name"],
                "store_name": s["name"],
                "store_number": s["store_number"],
                "city": s["city"],
                "address": s["address"],
                "distance_km": round(float(distance), 2) if distance is not None else None,
                "is_demo": bool(s["is_demo"]),
                "missing_count": missing,
                "coverage_pct": round((len(cleaned) - missing) * 100 / len(cleaned)),
                "lines": lines,
            })

        _simple_offer_totals(con, lines_by_store, max_age_hours, include_coupons)

    for store in results:
        found = [x for x in store["lines"] if not x["missing"]]
        store["base_total"] = round(sum(float(x["line_total"]) for x in found), 2)
        store["total"] = round(sum(float(x.get("total_after_offer", x["line_total"])) for x in found), 2)
        store["savings"] = round(store["base_total"] - store["total"], 2)
        store["applied_offers"] = [x["applied_offer"] for x in found if x.get("applied_offer")]
        store["coupon_matches"] = sum(1 for x in found if x.get("coupon_available"))
        store["offer_matches"] = sum(1 for x in found if x.get("promotion_available"))

    # Incomplete baskets never beat complete baskets merely because missing items are cheap.
    results.sort(
        key=lambda x: (
            x["missing_count"],
            x["total"],
            x["distance_km"] if x["distance_km"] is not None else 1e9,
        )
    )
    truncated = len(results) > max_stores
    results = results[:max_stores]
    for rank, store in enumerate(results, 1):
        store["rank"] = rank
    return {
        "items": cleaned,
        "count": len(results),
        "stores": results,
        "include_coupons": include_coupons,
        "max_age_hours": max_age_hours,
        "truncated": truncated,
        "calculation_note": "מבצעים מחושבים אוטומטית רק כאשר תנאי המבצע חד-משמעיים למוצר יחיד. מבצעי תמהיל/מתנות מוצגים אך אינם מנוחשים לתוך המחיר.",
    }
