from __future__ import annotations

from pathlib import Path

from ..db import db, utc_now_iso
from ..config import settings
from ..price_history import record_price_observation
from ..source_registry import CHAIN_DISPLAY
from .xml_parser import parse_records, timestamp_from_filename

PARSER_VERSION = 5

CHAIN_ID_TO_KEY = {
    "7290027600007": "SHUFERSAL",
    "7290058140886": "RAMI_LEVY",
    "7290803800003": "YOHANANOF",
    "7290103152017": "OSHER_AD",
    "7290696200003": "VICTORY_NEW_SOURCE",
    "7290661400001": "MAHSANI_ASHUK_NEW_SOURCE",
}


def _normalize_store_number(store_number: str) -> str:
    value = str(store_number).strip()
    # Store IDs are numeric in the transparency specification. Canonicalizing
    # leading zeroes prevents Stores=12 and filename=012 from becoming two branches.
    return str(int(value)) if value.isdigit() else value


def _stable_store_id(chain_key: str, store_number: str) -> str:
    return f"{chain_key}:{_normalize_store_number(store_number)}"


def infer_chain_key(path: Path) -> str | None:
    hay = " ".join(path.parts).upper().replace("-", "_").replace(" ", "_")
    # The scraper library's own folder names are camelCase run together with no
    # separator (e.g. "TivTaam", not "Tiv_Taam"), so a multi-word registry key
    # like TIV_TAAM never matches hay literally - only its underscore-stripped
    # form does. Without this, such a chain's own key is never recognized and
    # every file falls back to its raw numeric chain id instead.
    # Longest first so VICTORY_NEW_SOURCE wins over a shorter legacy name.
    for key in sorted(CHAIN_DISPLAY, key=len, reverse=True):
        if key in hay or key.replace("_", "") in hay:
            return key
    aliases = {
        "DABACH": "SALACH_DABACH",
        "DABBAH": "SALACH_DABACH",
        "KING": "KING_STORE",
        "MAHSANEI_HASHUK": "MAHSANI_ASHUK_NEW_SOURCE",
        "MACHSANEI_HASHUK": "MAHSANI_ASHUK_NEW_SOURCE",
    }
    for needle, key in aliases.items():
        if needle in hay:
            return key
    return None


def ingest_file(db_path: Path, path: Path, chain_key_override: str | None = None) -> dict:
    rec = parse_records(path)
    chain_key = (
        chain_key_override
        or CHAIN_ID_TO_KEY.get(rec["chain_id"] or "")
        or (rec["chain_id"] or "UNKNOWN")
    )
    chain_name = CHAIN_DISPLAY.get(chain_key, chain_key)
    store_map: dict[str, str] = {}

    with db(db_path) as con:
        if rec["stores"] or rec["products"] or rec["prices"] or rec["promotions"]:
            # Real data and synthetic demo data must never mix in comparisons.
            con.execute("DELETE FROM promotion_items WHERE store_id IN (SELECT id FROM stores WHERE is_demo=1)")
            con.execute("DELETE FROM promotions WHERE is_demo=1")
            con.execute("DELETE FROM prices WHERE is_demo=1")
            con.execute("DELETE FROM products WHERE is_demo=1")
            con.execute("DELETE FROM stores WHERE is_demo=1")

        for s in rec["stores"]:
            sn = _normalize_store_number(s["store_number"])
            sid = _stable_store_id(chain_key, sn)
            store_map[sn] = sid
            con.execute(
                """INSERT INTO stores(id,chain_key,chain_name,store_number,name,city,address,lat,lng,updated_at,is_demo)
                VALUES(?,?,?,?,?,?,?,?,?,?,0)
                ON CONFLICT(id) DO UPDATE SET
                  chain_key=excluded.chain_key,chain_name=excluded.chain_name,store_number=excluded.store_number,
                  name=excluded.name,city=excluded.city,address=excluded.address,
                  lat=COALESCE(excluded.lat,stores.lat),lng=COALESCE(excluded.lng,stores.lng),
                  updated_at=excluded.updated_at,is_demo=0
                WHERE excluded.updated_at >= stores.updated_at""",
                (
                    sid, chain_key, chain_name, sn, s["name"], s["city"], s["address"],
                    s["lat"], s["lng"], s["updated_at"],
                ),
            )
        for p in rec["products"]:
            con.execute(
                """INSERT INTO products(barcode,name,manufacturer,package_label,updated_at,is_demo) VALUES(?,?,?,?,?,0)
                ON CONFLICT(barcode) DO UPDATE SET
                  name=excluded.name,manufacturer=excluded.manufacturer,package_label=excluded.package_label,
                  updated_at=excluded.updated_at,is_demo=0
                WHERE excluded.updated_at >= products.updated_at""",
                (p["barcode"], p["name"], p["manufacturer"], p.get("package_label"), p["updated_at"]),
            )

        removed = 0
        for p in rec["prices"]:
            sn_raw = p["store_number"]
            if not sn_raw:
                continue
            sn = _normalize_store_number(sn_raw)
            sid = store_map.get(sn) or _stable_store_id(chain_key, sn)

            # Incremental files can arrive before Stores. Preserve the price with a
            # placeholder store and fill metadata later when the Stores file arrives.
            if not con.execute("SELECT 1 FROM stores WHERE id=?", (sid,)).fetchone():
                con.execute(
                    """INSERT OR IGNORE INTO stores
                    (id,chain_key,chain_name,store_number,name,city,address,updated_at,is_demo)
                    VALUES(?,?,?,?,?,?,?,?,0)""",
                    (sid, chain_key, chain_name, sn, f"סניף {sn}", None, None, p["updated_at"]),
                )

            # Per the Israeli transparency specification, status 0 means the item
            # was removed from sale. Never keep it as a fresh price.
            if p.get("status") == "0":
                cur = con.execute(
                    "DELETE FROM prices WHERE store_id=? AND barcode=? AND observed_at<=?",
                    (sid, p["barcode"], rec["file_timestamp"]),
                )
                removed += max(cur.rowcount, 0)
                continue

            if p["price"] is None:
                continue
            if not con.execute("SELECT 1 FROM products WHERE barcode=?", (p["barcode"],)).fetchone():
                continue

            # Never let an older file overwrite a newer snapshot/update. observed_at
            # tracks source-file freshness; updated_at tracks the item's price change.
            con.execute(
                """INSERT INTO prices(store_id,barcode,price,unit_price,updated_at,observed_at,is_demo)
                VALUES(?,?,?,?,?,?,0)
                ON CONFLICT(store_id,barcode) DO UPDATE SET
                  price=excluded.price,unit_price=excluded.unit_price,
                  updated_at=excluded.updated_at,observed_at=excluded.observed_at,is_demo=0
                WHERE excluded.observed_at > prices.observed_at
                   OR (excluded.observed_at = prices.observed_at AND excluded.updated_at >= prices.updated_at)""",
                (
                    sid, p["barcode"], p["price"], p["unit_price"],
                    p["updated_at"], rec["file_timestamp"],
                ),
            )
            record_price_observation(
                con,
                sid,
                p["barcode"],
                float(p["price"]),
                rec["file_timestamp"],
                settings.price_history_days,
            )

        # Promotions are published per store. A PromoFull file is a complete
        # snapshot: remove older/equal promotion state for that store, even when
        # the snapshot contains zero promotions. Preserve a newer incremental update.
        promo_store_raw = rec.get("store_number") or (rec["promotions"][0].get("store_number") if rec["promotions"] else None)
        promo_store = _normalize_store_number(promo_store_raw) if promo_store_raw else None
        if rec["file_type"] == "promo_full" and promo_store:
            promo_sid = store_map.get(promo_store) or _stable_store_id(chain_key, promo_store)
            if not con.execute("SELECT 1 FROM stores WHERE id=?", (promo_sid,)).fetchone():
                con.execute(
                    """INSERT OR IGNORE INTO stores
                    (id,chain_key,chain_name,store_number,name,city,address,updated_at,is_demo)
                    VALUES(?,?,?,?,?,?,?,?,0)""",
                    (promo_sid, chain_key, chain_name, promo_store, f"סניף {promo_store}", None, None, rec["file_timestamp"]),
                )
            con.execute(
                "DELETE FROM promotions WHERE store_id=? AND observed_at<=?",
                (promo_sid, rec["file_timestamp"]),
            )

        if rec["promotions"]:
            for promo in rec["promotions"]:
                sn_raw = promo.get("store_number") or rec.get("store_number")
                if not sn_raw:
                    continue
                sn = _normalize_store_number(sn_raw)
                sid = store_map.get(sn) or _stable_store_id(chain_key, sn)
                if not con.execute("SELECT 1 FROM stores WHERE id=?", (sid,)).fetchone():
                    con.execute(
                        """INSERT OR IGNORE INTO stores
                        (id,chain_key,chain_name,store_number,name,city,address,updated_at,is_demo)
                        VALUES(?,?,?,?,?,?,?,?,0)""",
                        (sid, chain_key, chain_name, sn, f"סניף {sn}", None, None, promo["updated_at"]),
                    )

                con.execute(
                    """INSERT INTO promotions(
                         store_id,promotion_id,description,start_at,end_at,updated_at,observed_at,
                         reward_type,allow_multiple_discounts,is_weighted,min_qty,discounted_price,
                         discounted_unit_price,is_coupon,is_active,club_ids,remarks,is_demo)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)
                       ON CONFLICT(store_id,promotion_id) DO UPDATE SET
                         description=excluded.description,start_at=excluded.start_at,end_at=excluded.end_at,
                         updated_at=excluded.updated_at,observed_at=excluded.observed_at,reward_type=excluded.reward_type,
                         allow_multiple_discounts=excluded.allow_multiple_discounts,is_weighted=excluded.is_weighted,
                         min_qty=excluded.min_qty,discounted_price=excluded.discounted_price,
                         discounted_unit_price=excluded.discounted_unit_price,is_coupon=excluded.is_coupon,
                         is_active=excluded.is_active,club_ids=excluded.club_ids,remarks=excluded.remarks,is_demo=0
                       WHERE excluded.observed_at > promotions.observed_at
                          OR (excluded.observed_at = promotions.observed_at AND excluded.updated_at >= promotions.updated_at)""",
                    (
                        sid, promo["promotion_id"], promo["description"], promo["start_at"], promo["end_at"],
                        promo["updated_at"], rec["file_timestamp"], promo["reward_type"],
                        promo["allow_multiple_discounts"], promo["is_weighted"], promo["min_qty"],
                        promo["discounted_price"], promo["discounted_unit_price"], promo["is_coupon"],
                        promo["is_active"], ",".join(promo["club_ids"]), promo["remarks"],
                    ),
                )
                # Replace item membership only if this promotion version won the upsert.
                current = con.execute(
                    "SELECT observed_at,updated_at FROM promotions WHERE store_id=? AND promotion_id=?",
                    (sid, promo["promotion_id"]),
                ).fetchone()
                if current and current["observed_at"] == rec["file_timestamp"] and current["updated_at"] == promo["updated_at"]:
                    con.execute(
                        "DELETE FROM promotion_items WHERE store_id=? AND promotion_id=?",
                        (sid, promo["promotion_id"]),
                    )
                    con.executemany(
                        """INSERT OR REPLACE INTO promotion_items
                           (store_id,promotion_id,barcode,is_gift,item_type) VALUES(?,?,?,?,?)""",
                        [
                            (sid, promo["promotion_id"], item["barcode"], int(item["is_gift"]), item["item_type"])
                            for item in promo["items"]
                        ],
                    )

        # Important: a Price/Promo incremental file only confirms records included
        # in that delta. It must NOT refresh every other product/promotion in the store.

    return {
        "file": path.name,
        "chain": chain_key,
        "file_type": rec["file_type"],
        "stores": len(rec["stores"]),
        "products": len(rec["products"]),
        "prices": len(rec["prices"]),
        "promotions": len(rec["promotions"]),
        "coupons": sum(1 for p in rec["promotions"] if p["is_coupon"]),
        "removed": removed,
    }


def _signature(path: Path) -> tuple[str, int, int]:
    stat = path.stat()
    return str(path.resolve()), stat.st_size, stat.st_mtime_ns


def _already_ingested(db_path: Path, path: Path) -> bool:
    key, size, mtime_ns = _signature(path)
    with db(db_path) as con:
        row = con.execute(
            "SELECT size,mtime_ns,parser_version FROM ingested_files WHERE path=?", (key,)
        ).fetchone()
    return bool(
        row
        and row["size"] == size
        and row["mtime_ns"] == mtime_ns
        and row["parser_version"] == PARSER_VERSION
    )


def _mark_ingested(db_path: Path, path: Path) -> None:
    key, size, mtime_ns = _signature(path)
    with db(db_path) as con:
        con.execute(
            """INSERT INTO ingested_files(path,size,mtime_ns,parser_version,ingested_at)
            VALUES(?,?,?,?,?)
            ON CONFLICT(path) DO UPDATE SET
              size=excluded.size,mtime_ns=excluded.mtime_ns,
              parser_version=excluded.parser_version,ingested_at=excluded.ingested_at""",
            (key, size, mtime_ns, PARSER_VERSION, utc_now_iso()),
        )


def _looks_like_transparency_file(path: Path) -> bool:
    if not path.is_file():
        return False
    name = path.name.lower()
    if path.suffix.lower() in {".xml", ".gz"} or name.endswith(".xml.gz"):
        return True
    # Some publishers/scrapers keep the official filename without an extension.
    # Only accept known transparency prefixes so logs/status files are not parsed.
    compact = name.replace("_", "").replace("-", "")
    return not path.suffix and compact.startswith((
        "pricefull", "price", "promofull", "promo", "promotionsfull",
        "promotions", "storesfull", "stores", "store",
    ))


def ingest_directory(db_path: Path, raw_dir: Path, *, delete_ingested: bool = False) -> list[dict]:
    results: list[dict] = []
    candidates = [path for path in raw_dir.rglob("*") if _looks_like_transparency_file(path)]
    candidates.sort(key=lambda path: (timestamp_from_filename(path) or "9999", path.as_posix()))
    for path in candidates:
        try:
            if _already_ingested(db_path, path):
                if delete_ingested:
                    path.unlink(missing_ok=True)
                results.append({"file": path.name, "skipped": True})
                continue
            result = ingest_file(db_path, path, infer_chain_key(path))
            if delete_ingested:
                path.unlink(missing_ok=True)
                result["deleted_after_ingest"] = True
            else:
                _mark_ingested(db_path, path)
            results.append(result)
        except Exception as exc:
            results.append({"file": path.name, "error": f"{type(exc).__name__}: {exc}"})
    return results
