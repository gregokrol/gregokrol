from __future__ import annotations

import gzip
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ISRAEL_TZ = ZoneInfo("Asia/Jerusalem")


def _lname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _text_map(elem: ET.Element) -> dict[str, str]:
    out: dict[str, str] = {}
    for child in list(elem):
        val = (child.text or "").strip()
        if val:
            out[_lname(child.tag)] = val
    return out


def _first(d: dict[str, str], *names: str) -> str | None:
    for n in names:
        value = d.get(n.lower())
        if value:
            return value
    return None


def _desc_first(elem: ET.Element, *names: str) -> str | None:
    wanted = {n.lower() for n in names}
    for child in elem.iter():
        if child is elem:
            continue
        if _lname(child.tag) in wanted:
            value = (child.text or "").strip()
            if value:
                return value
    return None


def _float(v: str | None) -> float | None:
    if v is None:
        return None
    try:
        return float(v.replace(",", "."))
    except ValueError:
        return None


def _int(v: str | None) -> int | None:
    if v is None:
        return None
    try:
        return int(float(v))
    except ValueError:
        return None


def _timestamp(v: str | None, fallback: str | None = None) -> str | None:
    if v:
        s = v.strip().replace("Z", "+00:00")
        compact_fmt = None
        if re.fullmatch(r"\d{14}", s):
            compact_fmt = "%Y%m%d%H%M%S"
        elif re.fullmatch(r"\d{12}", s):
            compact_fmt = "%Y%m%d%H%M"
        formats = [compact_fmt] if compact_fmt else [None, "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M:%S"]
        for fmt in formats:
            try:
                dt = datetime.fromisoformat(s) if fmt is None else datetime.strptime(s, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=ISRAEL_TZ)
                return dt.astimezone(timezone.utc).isoformat()
            except ValueError:
                pass
    return fallback


def _date_time(date_value: str | None, time_value: str | None) -> str | None:
    if not date_value:
        return None
    date_value = date_value.strip()
    time_value = (time_value or "00:00:00").strip()
    return _timestamp(f"{date_value} {time_value}")


def read_xml_bytes(path: Path) -> bytes:
    raw = path.read_bytes()
    if path.suffix.lower() == ".gz" or raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return raw


def chain_id_from_filename(path: Path) -> str | None:
    m = re.search(r"(729\d{10})", path.name)
    return m.group(1) if m else None


def store_number_from_filename(path: Path) -> str | None:
    # Handles common chain-subchain-store-timestamp as well as chain-store-timestamp.
    m = re.search(r"729\d{10}-(?:\d+)-([0-9]+)-(?:20\d{6})", path.name)
    if m:
        return m.group(1)
    m = re.search(r"729\d{10}-([0-9]+)-(?:20\d{6})", path.name)
    return m.group(1) if m else None


def timestamp_from_filename(path: Path) -> str | None:
    m = re.search(r"(20\d{6})[-_]?([0-2]\d[0-5]\d(?:[0-5]\d)?)", path.name)
    if not m:
        return None
    return _timestamp(m.group(1) + m.group(2))


def file_type_from_filename(path: Path) -> str:
    n = path.name.lower()
    if n.startswith(("promofull", "promosfull", "promotionsfull")):
        return "promo_full"
    if n.startswith(("promo", "promos", "promotion")):
        return "promo"
    if n.startswith("pricefull"):
        return "price_full"
    if n.startswith("price"):
        return "price"
    if n.startswith("stores") or n.startswith("store"):
        return "stores"
    return "unknown"


def _mtime_timestamp(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()


def _parse_promotion(elem: ET.Element, root_store: str | None, root_updated: str, file_timestamp: str) -> dict | None:
    m = _text_map(elem)
    promo_id = _first(m, "promotionid", "promotion_id", "promoid") or _desc_first(elem, "promotionid", "promotion_id", "promoid")
    if not promo_id:
        return None
    description = (_first(m, "promotiondescription", "description", "promodescription")
                   or _desc_first(elem, "promotiondescription", "description", "promodescription")
                   or f"מבצע {promo_id}")
    updated_at = _timestamp(_first(m, "promotionupdatedate", "updatedate") or _desc_first(elem, "promotionupdatedate", "updatedate"), root_updated) or file_timestamp
    start_at = _date_time(_first(m, "promotionstartdate", "startdate") or _desc_first(elem, "promotionstartdate", "startdate"), _first(m, "promotionstarthour", "starthour") or _desc_first(elem, "promotionstarthour", "starthour"))
    end_at = _date_time(_first(m, "promotionenddate", "enddate") or _desc_first(elem, "promotionenddate", "enddate"), _first(m, "promotionendhour", "endhour") or _desc_first(elem, "promotionendhour", "endhour"))

    items: list[dict] = []
    for node in elem.iter():
        if _lname(node.tag) != "item":
            continue
        im = _text_map(node)
        barcode = _first(im, "itemcode", "barcode", "productcode")
        if barcode:
            items.append({
                "barcode": barcode,
                "is_gift": bool(_int(_first(im, "isgiftitem", "giftitem")) or 0),
                "item_type": _first(im, "itemtype", "type"),
            })

    club_ids: list[str] = []
    for node in elem.iter():
        if _lname(node.tag) == "clubid":
            value = (node.text or "").strip()
            if value and value not in club_ids:
                club_ids.append(value)

    active_value = _desc_first(elem, "additionalisactive", "isactive", "promotionstatus")
    active = 1 if active_value is None else int((_int(active_value) or 0) != 0)
    coupon = int((_int(_desc_first(elem, "additionaliscoupon", "iscoupon")) or 0) != 0)

    return {
        "promotion_id": promo_id,
        "store_number": root_store,
        "description": description,
        "start_at": start_at,
        "end_at": end_at,
        "updated_at": updated_at,
        "reward_type": _first(m, "rewardtype") or _desc_first(elem, "rewardtype"),
        "allow_multiple_discounts": int((_int(_first(m, "allowmultiplediscounts") or _desc_first(elem, "allowmultiplediscounts")) or 0) != 0),
        "is_weighted": int((_int(_first(m, "isweightedpromo") or _desc_first(elem, "isweightedpromo")) or 0) != 0),
        "min_qty": _float(_first(m, "minqty") or _desc_first(elem, "minqty")),
        "discounted_price": _float(_first(m, "discountedprice") or _desc_first(elem, "discountedprice")),
        "discounted_unit_price": _float(_first(m, "discountedpricepermida", "discountedunitprice") or _desc_first(elem, "discountedpricepermida", "discountedunitprice")),
        "is_coupon": coupon,
        "is_active": active,
        "club_ids": club_ids,
        "remarks": _first(m, "remarks") or _desc_first(elem, "remarks"),
        "items": items,
    }


def parse_records(path: Path) -> dict:
    root = ET.fromstring(read_xml_bytes(path))
    root_map = _text_map(root)
    chain_id = _first(root_map, "chainid", "chain_id") or chain_id_from_filename(path)
    root_store = _first(root_map, "storeid", "store_id") or store_number_from_filename(path)

    filename_ts = timestamp_from_filename(path)
    root_ts = _timestamp(_first(root_map, "lastupdatedate", "updatedate", "date", "priceupdatedate", "promotionupdatedate"))
    file_timestamp = filename_ts or root_ts or _mtime_timestamp(path)
    root_updated = root_ts or file_timestamp

    stores: list[dict] = []
    products: list[dict] = []
    prices: list[dict] = []
    promotions: list[dict] = []

    for elem in root.iter():
        name = _lname(elem.tag)
        if name in {"store", "branch"}:
            m = _text_map(elem)
            sid = _first(m, "storeid", "store_id", "storenum", "storenumber")
            sname = _first(m, "storename", "store_name", "name")
            if sid and sname:
                stores.append({
                    "chain_id": chain_id,
                    "store_number": sid,
                    "name": sname,
                    "city": _first(m, "city", "storecity"),
                    "address": _first(m, "address", "storeaddress"),
                    "lat": _float(_first(m, "lat", "latitude")),
                    "lng": _float(_first(m, "lng", "lon", "longitude")),
                    "updated_at": _timestamp(_first(m, "updatedate", "lastupdatedate"), root_updated) or file_timestamp,
                })
        elif name == "promotion":
            promotion = _parse_promotion(elem, root_store, root_updated, file_timestamp)
            if promotion:
                promotions.append(promotion)
        elif name in {"item", "product", "priceitem"}:
            m = _text_map(elem)
            barcode = _first(m, "itemcode", "barcode", "productcode", "item_code")
            pname = _first(m, "itemname", "productname", "name")
            price = _float(_first(m, "itemprice", "price"))
            status = _first(m, "itemstatus", "recordstatus", "status")
            updated_at = _timestamp(_first(m, "priceupdatedate", "updatedate"), root_updated) or file_timestamp

            if barcode and pname:
                products.append({
                    "barcode": barcode,
                    "name": pname,
                    "manufacturer": _first(m, "manufacturename", "manufacturer", "brand"),
                    "updated_at": updated_at,
                })
            if barcode and (price is not None or status == "0"):
                prices.append({
                    "barcode": barcode,
                    "store_number": _first(m, "storeid", "store_id") or root_store,
                    "price": price,
                    "unit_price": _float(_first(m, "unitofmeasureprice", "unitprice")),
                    "updated_at": updated_at,
                    "status": status,
                })

    return {
        "chain_id": chain_id,
        "store_number": root_store,
        "file_timestamp": file_timestamp,
        "file_type": file_type_from_filename(path),
        "stores": stores,
        "products": products,
        "prices": prices,
        "promotions": promotions,
    }
