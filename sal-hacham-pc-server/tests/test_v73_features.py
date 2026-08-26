from __future__ import annotations

from datetime import datetime, timezone, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

import app.main as main
from app.basket import compare_basket
from app.db import db, init_db
from app.demo import seed_demo
from app.ingest.loader import ingest_directory, ingest_file
from app.ingest.xml_parser import parse_records
from app.offers import list_store_offers
from app.service import data_health, search_prices


def _fresh_name(prefix: str, chain="7290058140886", store="123", delta_seconds=0) -> str:
    dt = datetime.now(timezone.utc) + timedelta(seconds=delta_seconds)
    # Parser interprets filename timestamps as Israel local time, so render local clock.
    local = dt.astimezone().strftime("%Y%m%d-%H%M%S")
    return f"{prefix}{chain}-001-{store}-{local}"


def _promo_xml(promo_id="P1", coupon=1, description="קופון חלב", barcode="7290001") -> str:
    return f"""<Root><ChainId>7290058140886</ChainId><StoreId>123</StoreId>
    <Promotions><Promotion><PromotionId>{promo_id}</PromotionId>
    <PromotionDescription>{description}</PromotionDescription>
    <RewardType>1</RewardType><MinQty>2</MinQty><DiscountedPrice>10</DiscountedPrice>
    <AdditionalRestrictions><AdditionalIsCoupon>{coupon}</AdditionalIsCoupon><AdditionalIsActive>1</AdditionalIsActive></AdditionalRestrictions>
    <Clubs><ClubId>7</ClubId></Clubs>
    <PromotionItems><Item><ItemCode>{barcode}</ItemCode><ItemType>1</ItemType><IsGiftItem>0</IsGiftItem></Item></PromotionItems>
    </Promotion></Promotions></Root>"""


def test_parse_promofull_coupon_without_extension(tmp_path: Path):
    p = tmp_path / _fresh_name("PromoFull")
    p.write_text(_promo_xml(), encoding="utf-8")
    r = parse_records(p)
    assert r["file_type"] == "promo_full"
    assert r["store_number"] == "123"
    assert len(r["promotions"]) == 1
    promo = r["promotions"][0]
    assert promo["promotion_id"] == "P1"
    assert promo["is_coupon"] == 1
    assert promo["is_active"] == 1
    assert promo["min_qty"] == 2
    assert promo["discounted_price"] == 10
    assert promo["club_ids"] == ["7"]
    assert promo["items"][0]["barcode"] == "7290001"


def test_ingest_directory_accepts_official_file_without_extension(tmp_path: Path):
    dbp = tmp_path / "db.sqlite3"
    raw = tmp_path / "raw"
    raw.mkdir()
    init_db(dbp)
    p = raw / _fresh_name("PromoFull")
    p.write_text(_promo_xml(), encoding="utf-8")
    results = ingest_directory(dbp, raw)
    assert len(results) == 1
    assert results[0]["promotions"] == 1
    with db(dbp) as con:
        assert con.execute("SELECT COUNT(*) FROM promotions").fetchone()[0] == 1
        assert con.execute("SELECT COUNT(*) FROM promotion_items").fetchone()[0] == 1


def test_empty_newer_promofull_clears_old_snapshot(tmp_path: Path):
    dbp = tmp_path / "db.sqlite3"
    init_db(dbp)
    old = tmp_path / _fresh_name("PromoFull", delta_seconds=-120)
    new = tmp_path / _fresh_name("PromoFull", delta_seconds=120)
    old.write_text(_promo_xml(), encoding="utf-8")
    new.write_text("<Root><ChainId>7290058140886</ChainId><StoreId>123</StoreId><Promotions/></Root>", encoding="utf-8")
    ingest_file(dbp, old, "RAMI_LEVY")
    with db(dbp) as con:
        assert con.execute("SELECT COUNT(*) FROM promotions").fetchone()[0] == 1
    ingest_file(dbp, new, "RAMI_LEVY")
    with db(dbp) as con:
        assert con.execute("SELECT COUNT(*) FROM promotions").fetchone()[0] == 0
        assert con.execute("SELECT COUNT(*) FROM promotion_items").fetchone()[0] == 0


def test_older_full_does_not_remove_newer_incremental_promo(tmp_path: Path):
    dbp = tmp_path / "db.sqlite3"
    init_db(dbp)
    newer = tmp_path / _fresh_name("Promo", delta_seconds=120)
    older_full = tmp_path / _fresh_name("PromoFull", delta_seconds=-120)
    newer.write_text(_promo_xml("NEW", 0, "מבצע חדש"), encoding="utf-8")
    older_full.write_text(_promo_xml("OLD", 0, "מבצע ישן"), encoding="utf-8")
    ingest_file(dbp, newer, "RAMI_LEVY")
    ingest_file(dbp, older_full, "RAMI_LEVY")
    with db(dbp) as con:
        ids = {r[0] for r in con.execute("SELECT promotion_id FROM promotions")}
    assert "NEW" in ids


def _demo_db(tmp_path: Path) -> Path:
    dbp = tmp_path / "demo.sqlite3"
    init_db(dbp)
    seed_demo(dbp)
    return dbp


def test_store_offer_drilldown_has_coupon_and_official_link(tmp_path: Path):
    dbp = _demo_db(tmp_path)
    out = list_store_offers(dbp, "demo-rami-bs", 5)
    assert out["found"] is True
    assert out["coupon_count"] == 1
    assert any(x["is_coupon"] for x in out["offers"])
    assert out["official_benefits"]["url"].startswith("https://")


def test_search_result_is_enriched_with_offer_badges(tmp_path: Path):
    dbp = _demo_db(tmp_path)
    out = search_prices(dbp, "שוקו", "באר שבע", None, None, 30, 5)
    rami = next(x for x in out["results"] if x["store_id"] == "demo-rami-bs")
    assert rami["offers"]
    assert any(x["is_coupon"] for x in rami["offers"])


def test_basket_public_promo_is_applied(tmp_path: Path):
    dbp = _demo_db(tmp_path)
    out = compare_basket(dbp, [{"q":"חלב 3%", "qty":3}], "באר שבע", None, None, 30, 5)
    rami = next(x for x in out["stores"] if x["store_id"] == "demo-rami-bs")
    assert rami["base_total"] == 18.6
    assert rami["total"] == 15.0
    assert rami["savings"] == 3.6
    assert rami["applied_offers"][0]["is_coupon"] is False


def test_basket_coupon_requires_explicit_opt_in(tmp_path: Path):
    dbp = _demo_db(tmp_path)
    no_coupon = compare_basket(dbp, [{"q":"שוקו", "qty":1}], "באר שבע", None, None, 30, 5, include_coupons=False)
    yes_coupon = compare_basket(dbp, [{"q":"שוקו", "qty":1}], "באר שבע", None, None, 30, 5, include_coupons=True)
    r0 = next(x for x in no_coupon["stores"] if x["store_id"] == "demo-rami-bs")
    r1 = next(x for x in yes_coupon["stores"] if x["store_id"] == "demo-rami-bs")
    assert r0["total"] == 8.9
    assert r0["coupon_matches"] == 1
    assert r1["total"] == 5.0
    assert r1["savings"] == 3.9
    assert r1["applied_offers"][0]["is_coupon"] is True


def test_incomplete_basket_never_ranks_before_complete_store(tmp_path: Path):
    dbp = _demo_db(tmp_path)
    with db(dbp) as con:
        con.execute("DELETE FROM prices WHERE store_id='demo-rami-bs' AND barcode='7290000000002'")
    out = compare_basket(dbp, [{"q":"חלב 3%","qty":1},{"q":"שוקו","qty":1}], "באר שבע", None, None, 30, 5)
    rami = next(x for x in out["stores"] if x["store_id"] == "demo-rami-bs")
    assert rami["missing_count"] == 1
    assert all(x["missing_count"] == 0 for x in out["stores"][:rami["rank"]-1])


def test_store_and_basket_api(tmp_path: Path, monkeypatch):
    dbp = _demo_db(tmp_path)
    monkeypatch.setattr(main.settings, "db_path", dbp)
    with TestClient(main.app) as c:
        offers = c.get("/api/store-offers", params={"store_id":"demo-rami-bs"})
        assert offers.status_code == 200 and offers.json()["coupon_count"] == 1
        basket = c.post("/api/basket", json={"city":"באר שבע","include_coupons":True,"items":[{"q":"שוקו","qty":1}]})
        assert basket.status_code == 200
        assert basket.json()["stores"][0]["total"] <= 5.0


def test_real_data_health_counts_without_join_multiplication(tmp_path: Path):
    dbp = tmp_path / "real.sqlite3"
    init_db(dbp)
    now = datetime.now(timezone.utc).isoformat()
    with db(dbp) as con:
        con.execute("INSERT INTO stores(id,chain_key,chain_name,store_number,name,city,address,updated_at,is_demo) VALUES('s','RAMI_LEVY','רמי לוי','1','סניף','באר שבע','א',?,0)", (now,))
        for i in range(3):
            b=f"b{i}"
            con.execute("INSERT INTO products(barcode,name,manufacturer,updated_at,is_demo) VALUES(?,?,?, ?,0)", (b,f"מוצר {i}","x",now))
            con.execute("INSERT INTO prices(store_id,barcode,price,unit_price,updated_at,observed_at,is_demo) VALUES('s',?,1,NULL,?,?,0)", (b,now,now))
        for i in range(2):
            con.execute("""INSERT INTO promotions(store_id,promotion_id,description,updated_at,observed_at,is_coupon,is_active,is_demo)
                         VALUES('s',?,?,?, ?,?,1,0)""", (f"p{i}",f"מבצע {i}",now,now,1 if i==1 else 0))
    out=data_health(dbp,5)
    assert len(out["chains"]) == 1
    row=out["chains"][0]
    assert row["total_stores"] == 1
    assert row["fresh_stores"] == 1
    assert row["active_promotions"] == 1
    assert row["active_coupons"] == 1


def test_ui_contains_clickable_store_coupon_basket_and_health_controls():
    root = Path(__file__).resolve().parents[1]
    html=(root/'app/static/index.html').read_text(encoding='utf-8')
    js=(root/'app/static/app.js').read_text(encoding='utf-8')
    assert 'id="basketPanel"' in html
    assert 'id="includeCoupons"' in html
    assert 'id="dataHealthPanel"' in html
    assert "toggleStoreOffers" in js
    assert "/api/store-offers" in js
    assert "לחץ להצגת מבצעים וקופונים" in js


def test_stale_or_inactive_coupon_is_not_presented(tmp_path: Path):
    dbp = _demo_db(tmp_path)
    old = (datetime.now(timezone.utc) - timedelta(hours=8)).isoformat()
    with db(dbp) as con:
        con.execute("UPDATE promotions SET observed_at=? WHERE store_id='demo-rami-bs' AND promotion_id='demo-c1'", (old,))
    out = list_store_offers(dbp, "demo-rami-bs", 5)
    assert out["coupon_count"] == 0
    assert all(not x["is_coupon"] for x in out["offers"])


def test_multi_item_promotion_is_shown_but_not_guessed_into_basket_total(tmp_path: Path):
    dbp = _demo_db(tmp_path)
    # Make the demo milk promotion a mixed-assortment promotion by adding another eligible item.
    with db(dbp) as con:
        con.execute("INSERT INTO promotion_items(store_id,promotion_id,barcode,is_gift,item_type) VALUES('demo-rami-bs','demo-p1','7290000000002',0,'1')")
    out = compare_basket(dbp, [{"q":"חלב 3%","qty":3}], "באר שבע", None, None, 30, 5)
    rami = next(x for x in out["stores"] if x["store_id"] == "demo-rami-bs")
    assert rami["base_total"] == 18.6
    assert rami["total"] == 18.6
    assert rami["offer_matches"] == 1
    assert rami["applied_offers"] == []


def test_live_adapter_requests_promotions_and_prices():
    from scripts.sync_prices import LIVE_FILE_TYPES
    assert {"STORE_FILE","PRICE_FULL_FILE","PRICE_FILE","PROMO_FULL_FILE","PROMO_FILE"}.issubset(set(LIVE_FILE_TYPES))
