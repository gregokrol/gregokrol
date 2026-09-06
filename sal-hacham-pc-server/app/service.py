from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from .db import db, fts_available
from .geo import haversine_km
from .offers import enrich_results_with_offers, offer_has_real_saving, meaningful_offer_counts
from .price_history import observed_day_count
from .search import candidate_products, normalize

CITY_ALIASES = {
    "באר שבע": "באר שבע",
    "בארשבע": "באר שבע",
    "תל אביב": "תל אביב",
    "תל אביב יפו": "תל אביב",
    "תא": "תל אביב",
    "ירושלים": "ירושלים",
}


def fold_city_spelling(text: str) -> str:
    """Collapse the double-vav/single-vav spelling ambiguity common to many
    Hebrew place names (e.g. תקווה/תקוה - both are standard for Petah Tikva),
    which chains spell inconsistently in their own store city/name/address
    fields. Applied only to city matching, never to general product search."""
    return text.replace("וו", "ו")


def normalize_city(value: str | None) -> str:
    n = normalize(value or "")
    if n in CITY_ALIASES:
        return CITY_ALIASES[n]
    return fold_city_spelling(n)


def _store_matches(
    row,
    city: str | None,
    lat: float | None,
    lng: float | None,
    radius_km: float,
    chains: list[str] | None,
) -> tuple[bool, float | None]:
    if chains and row["chain_key"] not in chains:
        return False, None

    use_geo = lat is not None and lng is not None
    if not use_geo:
        city_norm = normalize_city(city)
        if city_norm and normalize_city(row["city"]) != city_norm:
            location_text = fold_city_spelling(normalize(f"{row['name'] or ''} {row['address'] or ''}"))
            if city_norm not in location_text:
                return False, None

    distance = None
    if use_geo:
        if row["lat"] is None or row["lng"] is None:
            return False, None
        distance = haversine_km(lat, lng, float(row["lat"]), float(row["lng"]))
        if distance > radius_km:
            return False, None
    return True, distance


def search_prices(
    db_path,
    query: str,
    city: str | None,
    lat: float | None,
    lng: float | None,
    radius_km: float,
    max_age_hours: int,
    chains: list[str] | None = None,
    max_results: int = 500,
    history_days: int = 30,
) -> dict[str, Any]:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=max_age_hours)).isoformat()

    with db(db_path) as con:
        candidates_scored = candidate_products(con, query, max_candidates=2500)
        candidates = [(p["barcode"], score) for p, score in candidates_scored]
        if not candidates:
            return {"query": query, "count": 0, "max_age_hours": max_age_hours, "truncated": False, "results": []}

        store_rows = con.execute(
            """SELECT id,chain_key,chain_name,store_number,name,city,address,lat,lng,
                      updated_at,is_demo FROM stores"""
        ).fetchall()
        stores: list[tuple[str, float | None]] = []
        for s in store_rows:
            matched, distance = _store_matches(s, city, lat, lng, radius_km, chains)
            if matched:
                stores.append((s["id"], distance))
        if not stores:
            return {"query": query, "count": 0, "max_age_hours": max_age_hours, "truncated": False, "results": []}

        con.execute("CREATE TEMP TABLE wanted_products(barcode TEXT PRIMARY KEY,relevance REAL NOT NULL)")
        con.execute("CREATE TEMP TABLE wanted_stores(id TEXT PRIMARY KEY,distance REAL)")
        con.executemany("INSERT INTO wanted_products(barcode,relevance) VALUES(?,?)", candidates)
        con.executemany("INSERT INTO wanted_stores(id,distance) VALUES(?,?)", stores)
        per_store_limit = max(1, min(20, max_results // max(1, len(stores))))
        rows = con.execute(
            """WITH ranked AS (
                   SELECT p.barcode,p.name,p.manufacturer,p.package_label,pr.price,pr.unit_price,pr.updated_at,
                          pr.observed_at,pr.is_demo,s.id store_id,s.chain_key,s.chain_name,
                          s.store_number,s.name store_name,s.city,s.address,s.lat,s.lng,
                          wp.relevance,ws.distance,h.low_price history_low_price,
                          h.high_price history_high_price,
                          h.price_sum / NULLIF(h.sample_count,0) history_average_price,
                          h.sample_count history_sample_count,h.window_started_at history_started_at,
                          h.last_observed_at history_last_observed_at,
                          ROW_NUMBER() OVER (
                              PARTITION BY s.id
                              ORDER BY wp.relevance DESC,pr.price ASC,p.name ASC
                          ) store_rank
                   FROM prices pr
                   JOIN wanted_products wp ON wp.barcode=pr.barcode
                   JOIN wanted_stores ws ON ws.id=pr.store_id
                   JOIN products p ON p.barcode=pr.barcode
                   JOIN stores s ON s.id=pr.store_id
                   LEFT JOIN price_history h ON h.store_id=pr.store_id AND h.barcode=pr.barcode
                   WHERE pr.observed_at >= ?
               )
               SELECT * FROM ranked
               WHERE store_rank<=?
               ORDER BY relevance DESC,price ASC,
                        CASE WHEN distance IS NULL THEN 1 ELSE 0 END,distance ASC
               LIMIT ?""",
            (cutoff, per_store_limit, max_results + 1),
        ).fetchall()

    truncated = len(rows) > max_results
    rows = rows[:max_results]
    out = [{
        "barcode": r["barcode"],
        "product_name": r["name"],
        "manufacturer": r["manufacturer"],
        "package_label": r["package_label"],
        "price": r["price"],
        "unit_price": r["unit_price"],
        "updated_at": r["updated_at"],
        "observed_at": r["observed_at"],
        "store_id": r["store_id"],
        "chain_key": r["chain_key"],
        "chain_name": r["chain_name"],
        "store_number": r["store_number"],
        "store_name": r["store_name"],
        "city": r["city"],
        "address": r["address"],
        "lat": r["lat"],
        "lng": r["lng"],
        "distance_km": round(float(r["distance"]), 2) if r["distance"] is not None else None,
        "relevance": round(float(r["relevance"]), 2),
        "is_demo": bool(r["is_demo"]),
        "history": {
            "period_days": history_days,
            "low_price": round(float(r["history_low_price"]), 2),
            "high_price": round(float(r["history_high_price"]), 2),
            "average_price": round(float(r["history_average_price"]), 2),
            "sample_count": int(r["history_sample_count"]),
            "days_observed": observed_day_count(r["history_started_at"], r["history_last_observed_at"]),
        } if r["history_sample_count"] else None,
    } for r in rows]

    out.sort(
        key=lambda x: (
            -x["relevance"],
            x["price"],
            x["distance_km"] if x["distance_km"] is not None else 1e9,
        )
    )
    enrich_results_with_offers(db_path, out, max_age_hours, per_result=2)
    return {
        "query": query,
        "count": len(out),
        "max_age_hours": max_age_hours,
        "truncated": truncated,
        "results": out,
    }


def list_cities(db_path) -> list[str]:
    with db(db_path) as con:
        return [
            r[0]
            for r in con.execute(
                "SELECT DISTINCT city FROM stores WHERE city IS NOT NULL AND city<>'' ORDER BY city"
            ).fetchall()
        ]


def list_chains(db_path) -> list[dict]:
    with db(db_path) as con:
        rows = con.execute(
            "SELECT chain_key,chain_name,COUNT(*) c FROM stores GROUP BY chain_key,chain_name ORDER BY chain_name"
        ).fetchall()
    return [{"key": r["chain_key"], "name": r["chain_name"], "stores": r["c"]} for r in rows]


def list_stores_filtered(
    db_path,
    city: str | None = None,
    lat: float | None = None,
    lng: float | None = None,
    radius_km: float = 30,
    chains: list[str] | None = None,
    max_age_hours: int = 5,
) -> list[dict]:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=max_age_hours)).isoformat()
    now = datetime.now(timezone.utc).isoformat()
    with db(db_path) as con:
        rows = con.execute(
            """SELECT id,chain_key,chain_name,store_number,name,city,address,lat,lng,
                      updated_at,is_demo FROM stores ORDER BY chain_name,name"""
        ).fetchall()
        matched_rows: list[tuple[Any, float | None]] = []
        for r in rows:
            matched, distance = _store_matches(r, city, lat, lng, radius_km, chains)
            if matched:
                matched_rows.append((r, distance))

        if not matched_rows:
            return []

        con.execute("CREATE TEMP TABLE wanted_store_coverage(id TEXT PRIMARY KEY)")
        con.executemany(
            "INSERT INTO wanted_store_coverage(id) VALUES(?)",
            [(r["id"],) for r, _ in matched_rows],
        )
        coverage_rows = con.execute(
            """SELECT pr.store_id,COUNT(*) fresh_prices,MAX(pr.observed_at) latest_price_at
               FROM prices pr
               JOIN wanted_store_coverage ws ON ws.id=pr.store_id
               WHERE pr.observed_at >= ?
               GROUP BY pr.store_id""",
            (cutoff,),
        ).fetchall()
        coverage = {
            r["store_id"]: (int(r["fresh_prices"]), r["latest_price_at"])
            for r in coverage_rows
        }
        offer_rows = con.execute(
            """SELECT pr.store_id,pr.is_coupon,pr.min_qty,pr.discounted_price,pr.discounted_unit_price,
                      (SELECT COUNT(*) FROM promotion_items pi
                       WHERE pi.store_id=pr.store_id AND pi.promotion_id=pr.promotion_id AND pi.is_gift=0) item_count,
                      (SELECT p.price
                       FROM promotion_items pi2
                       JOIN prices p ON p.store_id=pi2.store_id AND p.barcode=pi2.barcode
                       WHERE pi2.store_id=pr.store_id AND pi2.promotion_id=pr.promotion_id
                         AND pi2.is_gift=0 AND p.observed_at>=?
                       LIMIT 1) base_price
               FROM promotions pr
               JOIN wanted_store_coverage ws ON ws.id=pr.store_id
               WHERE pr.is_active=1 AND pr.observed_at>=?
                 AND (pr.start_at IS NULL OR pr.start_at<=?)
                 AND (pr.end_at IS NULL OR pr.end_at>=?)""",
            (cutoff, cutoff, now, now),
        ).fetchall()
        offer_coverage = {}
        for r in offer_rows:
            if not offer_has_real_saving(r, r["base_price"]):
                continue
            total, promos, coupons = offer_coverage.get(r["store_id"], (0, 0, 0))
            if r["is_coupon"]:
                coupons += 1
            else:
                promos += 1
            offer_coverage[r["store_id"]] = (total + 1, promos, coupons)

    out = []
    for r, distance in matched_rows:
        fresh_prices, latest_price_at = coverage.get(r["id"], (0, None))
        active_offers, active_promotions, active_coupons = offer_coverage.get(r["id"], (0, 0, 0))
        out.append({
            "id": r["id"],
            "chain_key": r["chain_key"],
            "chain_name": r["chain_name"],
            "store_number": r["store_number"],
            "name": r["name"],
            "city": r["city"],
            "address": r["address"],
            "lat": r["lat"],
            "lng": r["lng"],
            "distance_km": round(distance, 2) if distance is not None else None,
            "fresh_prices": fresh_prices,
            "latest_price_at": latest_price_at,
            "active_offers": active_offers,
            "active_promotions": active_promotions,
            "active_coupons": active_coupons,
            "is_demo": bool(r["is_demo"]),
        })
    out.sort(
        key=lambda x: (
            x["distance_km"] if x["distance_km"] is not None else 1e9,
            x["chain_name"],
            x["name"],
        )
    )
    return out


def data_health(db_path, max_age_hours: int) -> dict:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=max_age_hours)).isoformat()
    now = datetime.now(timezone.utc).isoformat()
    with db(db_path) as con:
        rows = con.execute(
            """WITH price_by_store AS (
                   SELECT store_id,
                          MAX(observed_at) latest_price_at,
                          MAX(CASE WHEN observed_at>=? THEN 1 ELSE 0 END) is_fresh
                   FROM prices
                   WHERE is_demo=0
                   GROUP BY store_id
               ),
               promo_by_store AS (
                   SELECT store_id,
                          SUM(CASE WHEN is_active=1 AND is_coupon=0 AND observed_at>=?
                               AND (start_at IS NULL OR start_at<=?)
                               AND (end_at IS NULL OR end_at>=?) THEN 1 ELSE 0 END) active_promotions,
                          SUM(CASE WHEN is_active=1 AND is_coupon=1 AND observed_at>=?
                               AND (start_at IS NULL OR start_at<=?)
                               AND (end_at IS NULL OR end_at>=?) THEN 1 ELSE 0 END) active_coupons,
                          MAX(observed_at) latest_promo_at
                   FROM promotions
                   WHERE is_demo=0
                   GROUP BY store_id
               )
               SELECT s.chain_key,s.chain_name,
                      COUNT(*) total_stores,
                      SUM(COALESCE(ps.is_fresh,0)) fresh_stores,
                      MAX(CASE WHEN ps.is_fresh=1 THEN ps.latest_price_at END) latest_price_at,
                      SUM(COALESCE(ms.active_promotions,0)) active_promotions,
                      SUM(COALESCE(ms.active_coupons,0)) active_coupons,
                      MAX(ms.latest_promo_at) latest_promo_at
               FROM stores s
               LEFT JOIN price_by_store ps ON ps.store_id=s.id
               LEFT JOIN promo_by_store ms ON ms.store_id=s.id
               WHERE s.is_demo=0
               GROUP BY s.chain_key,s.chain_name
               ORDER BY s.chain_name""",
            (cutoff, cutoff, now, now, cutoff, now, now),
        ).fetchall()
        fts = fts_available(con)
        store_chain = {r["id"]: r["chain_key"] for r in con.execute("SELECT id,chain_key FROM stores WHERE is_demo=0").fetchall()}
    meaningful = meaningful_offer_counts(db_path, max_age_hours, real_only=True)
    counts_by_chain: dict[str, dict[str, int]] = {}
    for store_id, counts in meaningful["by_store"].items():
        chain_key = store_chain.get(store_id)
        if not chain_key:
            continue
        bucket = counts_by_chain.setdefault(chain_key, {"promotions": 0, "coupons": 0})
        bucket["promotions"] += counts["promotions"]
        bucket["coupons"] += counts["coupons"]
    chains = []
    for r in rows:
        total = int(r["total_stores"] or 0)
        fresh = int(r["fresh_stores"] or 0)
        chains.append({
            "chain_key": r["chain_key"],
            "chain_name": r["chain_name"],
            "total_stores": total,
            "fresh_stores": fresh,
            "coverage_pct": round(100 * fresh / total) if total else 0,
            "latest_price_at": r["latest_price_at"],
            "active_promotions": counts_by_chain.get(r["chain_key"], {}).get("promotions", 0),
            "active_coupons": counts_by_chain.get(r["chain_key"], {}).get("coupons", 0),
            "latest_promo_at": r["latest_promo_at"],
        })
    return {"max_age_hours": max_age_hours, "fts_enabled": fts, "chains": chains}


def status(db_path, max_age_hours: int, history_days: int = 30) -> dict:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=max_age_hours)).isoformat()
    now = datetime.now(timezone.utc).isoformat()
    with db(db_path) as con:
        total_prices = con.execute("SELECT COUNT(*) FROM prices").fetchone()[0]
        fresh_prices = con.execute("SELECT COUNT(*) FROM prices WHERE observed_at>=?", (cutoff,)).fetchone()[0]
        real_prices = con.execute("SELECT COUNT(*) FROM prices WHERE is_demo=0").fetchone()[0]
        fresh_real_prices = con.execute(
            "SELECT COUNT(*) FROM prices WHERE is_demo=0 AND observed_at>=?", (cutoff,)
        ).fetchone()[0]
        latest = con.execute("SELECT MAX(observed_at) FROM prices").fetchone()[0]
        real_stores = con.execute("SELECT COUNT(*) FROM stores WHERE is_demo=0").fetchone()[0]
        fresh_real_stores = con.execute(
            """SELECT COUNT(DISTINCT s.id)
               FROM stores s JOIN prices p ON p.store_id=s.id
               WHERE s.is_demo=0 AND p.is_demo=0 AND p.observed_at>=?""",
            (cutoff,),
        ).fetchone()[0]
        real_chains = con.execute("SELECT COUNT(DISTINCT chain_key) FROM stores WHERE is_demo=0").fetchone()[0]
        fresh_real_chains = con.execute(
            """SELECT COUNT(DISTINCT s.chain_key)
               FROM stores s JOIN prices p ON p.store_id=s.id
               WHERE s.is_demo=0 AND p.is_demo=0 AND p.observed_at>=?""",
            (cutoff,),
        ).fetchone()[0]
        history_rows = con.execute("SELECT COUNT(*) FROM price_history").fetchone()[0]
        history_products = history_rows
        fts = fts_available(con)
    meaningful = meaningful_offer_counts(db_path, max_age_hours, real_only=None)
    active_promotions = meaningful["promotions"]
    active_coupons = meaningful["coupons"]
    coverage_complete = real_stores > 0 and fresh_real_stores == real_stores
    return {
        "total_prices": total_prices,
        "fresh_prices": fresh_prices,
        "real_prices": real_prices,
        "fresh_real_prices": fresh_real_prices,
        "latest_update": latest,
        "max_age_hours": max_age_hours,
        "real_stores": real_stores,
        "fresh_real_stores": fresh_real_stores,
        "real_chains": real_chains,
        "fresh_real_chains": fresh_real_chains,
        "coverage_complete": coverage_complete,
        "live_ready": fresh_real_prices > 0,
        "active_promotions": active_promotions,
        "active_coupons": active_coupons,
        "history_days": history_days,
        "history_rows": history_rows,
        "history_products": history_products,
        "fts_enabled": fts,
    }
