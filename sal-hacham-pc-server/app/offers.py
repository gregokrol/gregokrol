from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable

from .benefits import benefit_for_chain
from .db import db


def _cutoff(max_age_hours: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=max_age_hours)).isoformat()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _active_clause() -> str:
    return """pr.is_active=1
              AND pr.observed_at>=?
              AND (pr.start_at IS NULL OR pr.start_at<=?)
              AND (pr.end_at IS NULL OR pr.end_at>=?)"""


def _promo_dict(r, items=None) -> dict:
    return {
        "promotion_id": r["promotion_id"],
        "description": r["description"],
        "start_at": r["start_at"],
        "end_at": r["end_at"],
        "updated_at": r["updated_at"],
        "observed_at": r["observed_at"],
        "min_qty": r["min_qty"],
        "discounted_price": r["discounted_price"],
        "discounted_unit_price": r["discounted_unit_price"],
        "is_coupon": bool(r["is_coupon"]),
        "club_ids": [x for x in (r["club_ids"] or "").split(",") if x],
        "remarks": r["remarks"],
        "item_count": int(r["item_count"]) if "item_count" in r.keys() else None,
        "items": items or [],
    }




def offer_has_real_saving(row, base_price: float | None) -> bool:
    """Hide only offers we can prove do not save money.

    For one eligible non-gift item with a fresh shelf price and an explicit
    promo/package price, the offer must be strictly cheaper. Ambiguous mixed
    baskets, gifts, weighted offers or offers without a comparable price stay
    visible rather than being guessed.
    """
    if base_price is None:
        return True
    try:
        base = float(base_price)
    except (TypeError, ValueError):
        return True
    try:
        item_count = int(row["item_count"] or 0)
    except (KeyError, TypeError, ValueError, IndexError):
        item_count = 0
    if item_count != 1 or base <= 0:
        return True
    try:
        min_qty = float(row["min_qty"] or 0)
    except (KeyError, TypeError, ValueError, IndexError):
        min_qty = 0
    try:
        package = row["discounted_price"]
    except (KeyError, TypeError, IndexError):
        package = None
    try:
        unit = row["discounted_unit_price"]
    except (KeyError, TypeError, IndexError):
        unit = None
    # Prefer the explicit package/quantity comparison when available.
    if package is not None and min_qty > 0:
        try:
            return float(package) < (base * min_qty) - 0.005
        except (TypeError, ValueError):
            return True
    if unit is not None:
        try:
            return float(unit) < base - 0.005
        except (TypeError, ValueError):
            return True
    return True



def meaningful_offer_counts(db_path, max_age_hours: int, real_only: bool | None = None) -> dict:
    """Return active offer counts after removing provably zero/negative savings.

    Used by health/status views so their coupon totals match what users can
    actually open in a store.
    """
    cutoff = _cutoff(max_age_hours)
    now = _now_iso()
    demo_filter = ""
    params: list = [cutoff, cutoff, now, now]
    if real_only is True:
        demo_filter = " AND pr.is_demo=0"
    elif real_only is False:
        demo_filter = " AND pr.is_demo=1"
    with db(db_path) as con:
        rows = con.execute(
            f"""SELECT pr.store_id,pr.is_coupon,pr.min_qty,pr.discounted_price,pr.discounted_unit_price,
                       (SELECT COUNT(*) FROM promotion_items pi
                        WHERE pi.store_id=pr.store_id AND pi.promotion_id=pr.promotion_id AND pi.is_gift=0) item_count,
                       (SELECT p.price FROM promotion_items pi2
                        JOIN prices p ON p.store_id=pi2.store_id AND p.barcode=pi2.barcode
                        WHERE pi2.store_id=pr.store_id AND pi2.promotion_id=pr.promotion_id
                          AND pi2.is_gift=0 AND p.observed_at>=? LIMIT 1) base_price
                FROM promotions pr
                WHERE pr.is_active=1 AND pr.observed_at>=?
                  AND (pr.start_at IS NULL OR pr.start_at<=?)
                  AND (pr.end_at IS NULL OR pr.end_at>=?){demo_filter}""",
            params,
        ).fetchall()
    by_store: dict[str, dict[str, int]] = {}
    promotions = coupons = 0
    for r in rows:
        if not offer_has_real_saving(r, r["base_price"]):
            continue
        b = by_store.setdefault(r["store_id"], {"promotions": 0, "coupons": 0})
        if r["is_coupon"]:
            coupons += 1
            b["coupons"] += 1
        else:
            promotions += 1
            b["promotions"] += 1
    return {"promotions": promotions, "coupons": coupons, "by_store": by_store}

def list_store_offers(db_path, store_id: str, max_age_hours: int, limit: int = 60) -> dict:
    cutoff = _cutoff(max_age_hours)
    now = _now_iso()
    with db(db_path) as con:
        store = con.execute(
            """SELECT id,chain_key,chain_name,store_number,name,city,address,is_demo
               FROM stores WHERE id=?""",
            (store_id,),
        ).fetchone()
        if not store:
            return {"found": False, "store_id": store_id}

        # Load active offers with enough price context to suppress offers that
        # are provably not cheaper than the current fresh shelf price.
        rows = con.execute(
            f"""SELECT pr.*,
                       (SELECT COUNT(*) FROM promotion_items pi
                        WHERE pi.store_id=pr.store_id AND pi.promotion_id=pr.promotion_id
                          AND pi.is_gift=0) item_count,
                       (SELECT p.price
                        FROM promotion_items pi3
                        JOIN prices p ON p.store_id=pi3.store_id AND p.barcode=pi3.barcode
                        WHERE pi3.store_id=pr.store_id AND pi3.promotion_id=pr.promotion_id
                          AND pi3.is_gift=0 AND p.observed_at>=?
                        LIMIT 1) base_price
                FROM promotions pr
                WHERE pr.store_id=? AND {_active_clause()}
                ORDER BY pr.is_coupon DESC,
                         CASE WHEN pr.end_at IS NULL THEN 1 ELSE 0 END,
                         pr.end_at ASC, pr.description ASC""",
            (cutoff, store_id, cutoff, now, now),
        ).fetchall()
        useful_rows = [r for r in rows if offer_has_real_saving(r, r["base_price"])]
        coupons = sum(1 for r in useful_rows if r["is_coupon"])
        promotions = len(useful_rows) - coupons

        offers = []
        for r in useful_rows[:limit]:
            item_rows = con.execute(
                """SELECT pi.barcode,pi.is_gift,p.name
                   FROM promotion_items pi
                   LEFT JOIN products p ON p.barcode=pi.barcode
                   WHERE pi.store_id=? AND pi.promotion_id=?
                   ORDER BY pi.is_gift,p.name
                   LIMIT 8""",
                (store_id, r["promotion_id"]),
            ).fetchall()
            items = [
                {"barcode": x["barcode"], "name": x["name"], "is_gift": bool(x["is_gift"])}
                for x in item_rows
            ]
            offer = _promo_dict(r, items)
            if r["base_price"] is not None and int(r["item_count"] or 0) == 1:
                offer["regular_price"] = float(r["base_price"])
                min_qty = float(r["min_qty"] or 0)
                if r["discounted_price"] is not None and min_qty > 0:
                    offer["saving"] = round(float(r["base_price"]) * min_qty - float(r["discounted_price"]), 2)
                elif r["discounted_unit_price"] is not None:
                    offer["saving"] = round(float(r["base_price"]) - float(r["discounted_unit_price"]), 2)
            offers.append(offer)

    return {
        "found": True,
        "store": {
            "id": store["id"],
            "chain_key": store["chain_key"],
            "chain_name": store["chain_name"],
            "store_number": store["store_number"],
            "name": store["name"],
            "city": store["city"],
            "address": store["address"],
            "is_demo": bool(store["is_demo"]),
        },
        "active_count": len(useful_rows),
        "promotion_count": promotions,
        "coupon_count": coupons,
        "truncated": len(useful_rows) > limit,
        "offers": offers,
        "official_benefits": benefit_for_chain(store["chain_key"]),
        "max_age_hours": max_age_hours,
    }


def enrich_results_with_offers(db_path, results: list[dict], max_age_hours: int, per_result: int = 2) -> list[dict]:
    if not results:
        return results
    cutoff = _cutoff(max_age_hours)
    now = _now_iso()
    pairs = {(r["store_id"], r["barcode"]) for r in results if r.get("store_id") and r.get("barcode")}
    if not pairs:
        return results

    with db(db_path) as con:
        con.execute("CREATE TEMP TABLE wanted_offer_pairs(store_id TEXT,barcode TEXT,PRIMARY KEY(store_id,barcode))")
        con.executemany("INSERT INTO wanted_offer_pairs(store_id,barcode) VALUES(?,?)", pairs)
        rows = con.execute(
            f"""SELECT w.store_id,w.barcode,pr.promotion_id,pr.description,pr.start_at,pr.end_at,
                       pr.updated_at,pr.observed_at,pr.min_qty,pr.discounted_price,
                       pr.discounted_unit_price,pr.is_coupon,pr.club_ids,pr.remarks,
                       (SELECT COUNT(*) FROM promotion_items pi2
                        WHERE pi2.store_id=pr.store_id AND pi2.promotion_id=pr.promotion_id AND pi2.is_gift=0) item_count
                FROM wanted_offer_pairs w
                JOIN promotion_items pi ON pi.store_id=w.store_id AND pi.barcode=w.barcode AND pi.is_gift=0
                JOIN promotions pr ON pr.store_id=pi.store_id AND pr.promotion_id=pi.promotion_id
                WHERE {_active_clause()}
                ORDER BY w.store_id,w.barcode,pr.is_coupon ASC,
                         CASE WHEN pr.discounted_price IS NULL THEN 1 ELSE 0 END,
                         pr.discounted_price ASC""",
            (cutoff, now, now),
        ).fetchall()

    base_prices = {(r.get("store_id"), r.get("barcode")): r.get("price") for r in results}
    mapping: dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        key = (r["store_id"], r["barcode"])
        if not offer_has_real_saving(r, base_prices.get(key)):
            continue
        bucket = mapping.setdefault(key, [])
        if len(bucket) < per_result:
            offer = _promo_dict(r)
            base = base_prices.get(key)
            if base is not None and int(r["item_count"] or 0) == 1:
                min_qty = float(r["min_qty"] or 0)
                if r["discounted_price"] is not None and min_qty > 0:
                    offer["saving"] = round(float(base) * min_qty - float(r["discounted_price"]), 2)
            bucket.append(offer)
    for result in results:
        result["offers"] = mapping.get((result.get("store_id"), result.get("barcode")), [])
    return results
