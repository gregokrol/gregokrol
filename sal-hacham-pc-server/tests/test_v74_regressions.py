from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from app import main
from app.basket import compare_basket
from app.db import db, init_db
from app.offers import list_store_offers
from app.service import list_stores_filtered, search_prices


def _db_with_equal_coupon(tmp_path: Path) -> Path:
    dbp = tmp_path / "equal-coupon.sqlite3"
    init_db(dbp)
    now = datetime.now(timezone.utc).isoformat()
    with db(dbp) as con:
        con.execute(
            "INSERT INTO stores(id,chain_key,chain_name,store_number,name,city,address,updated_at,is_demo) VALUES(?,?,?,?,?,?,?,?,0)",
            ("s1", "X", "רשת", "1", "סניף", "באר שבע", "כתובת", now),
        )
        con.execute(
            "INSERT INTO products(barcode,name,manufacturer,updated_at,is_demo) VALUES(?,?,?,?,0)",
            ("b1", "חלב 3% 1 ליטר", "יצרן", now),
        )
        con.execute(
            "INSERT INTO prices(store_id,barcode,price,unit_price,updated_at,observed_at,is_demo) VALUES(?,?,?,?,?,?,0)",
            ("s1", "b1", 7.90, None, now, now),
        )
        con.execute(
            """INSERT INTO promotions(store_id,promotion_id,description,updated_at,observed_at,min_qty,
                       discounted_price,is_coupon,is_active,is_demo)
               VALUES(?,?,?,?,?,?,?,?,?,0)""",
            ("s1", "c1", "קופון ללא חיסכון", now, now, 1, 7.90, 1, 1),
        )
        con.execute(
            "INSERT INTO promotion_items(store_id,promotion_id,barcode,is_gift,item_type) VALUES(?,?,?,?,?)",
            ("s1", "c1", "b1", 0, "1"),
        )
    return dbp


def test_store_panel_uses_explicit_hidden_toggle_not_details():
    root = Path(__file__).resolve().parents[1]
    html = (root / "app/static/index.html").read_text(encoding="utf-8")
    js = (root / "app/static/app.js").read_text(encoding="utf-8")
    css = (root / "app/static/styles.css").read_text(encoding="utf-8")
    assert '<section id="storesPanel"' in html
    assert 'id="storesToggle"' in html
    assert 'id="storesBody" class="details-body" hidden' in html
    assert '<details id="storesPanel"' not in html
    assert "function setStoresOpen(open)" in js
    assert "setStoresOpen(false)" in js
    assert "storesToggle').addEventListener('click'" in js
    assert "[hidden]{display:none!important}" in css


def test_equal_price_coupon_is_hidden_from_store_detail(tmp_path: Path):
    dbp = _db_with_equal_coupon(tmp_path)
    out = list_store_offers(dbp, "s1", 5)
    assert out["coupon_count"] == 0
    assert out["active_count"] == 0
    assert out["offers"] == []


def test_equal_price_coupon_is_not_counted_on_store_list(tmp_path: Path):
    dbp = _db_with_equal_coupon(tmp_path)
    stores = list_stores_filtered(dbp, city="באר שבע", max_age_hours=5)
    assert len(stores) == 1
    assert stores[0]["active_coupons"] == 0
    assert stores[0]["active_offers"] == 0


def test_equal_price_coupon_is_not_shown_in_search(tmp_path: Path):
    dbp = _db_with_equal_coupon(tmp_path)
    out = search_prices(dbp, "חלב 3%", "באר שבע", None, None, 30, 5)
    assert out["results"]
    assert out["results"][0]["offers"] == []


def test_equal_price_coupon_not_counted_or_applied_in_basket(tmp_path: Path):
    dbp = _db_with_equal_coupon(tmp_path)
    out = compare_basket(
        dbp,
        [{"q": "חלב 3%", "qty": 1}],
        "באר שבע",
        None,
        None,
        30,
        5,
        include_coupons=True,
    )
    assert out["stores"]
    store = out["stores"][0]
    assert store["coupon_matches"] == 0
    assert store["savings"] == 0
    assert store["total"] == 7.90
    assert store["applied_offers"] == []


def test_cheaper_coupon_still_appears_and_reports_saving(tmp_path: Path):
    dbp = _db_with_equal_coupon(tmp_path)
    with db(dbp) as con:
        con.execute("UPDATE promotions SET discounted_price=5.90 WHERE store_id='s1' AND promotion_id='c1'")
    out = list_store_offers(dbp, "s1", 5)
    assert out["coupon_count"] == 1
    assert out["offers"][0]["saving"] == 2.0


def test_equal_price_coupon_api_returns_zero(tmp_path: Path, monkeypatch):
    dbp = _db_with_equal_coupon(tmp_path)
    monkeypatch.setattr(main.settings, "db_path", dbp)
    with TestClient(main.app) as client:
        data = client.get("/api/store-offers", params={"store_id": "s1"}).json()
        assert data["coupon_count"] == 0
        stores = client.get("/api/stores", params={"city": "באר שבע"}).json()
        assert stores["stores"][0]["active_coupons"] == 0


def test_equal_price_coupon_not_counted_in_health_or_status(tmp_path: Path):
    from app.service import data_health, status
    dbp = _db_with_equal_coupon(tmp_path)
    assert status(dbp, 5)["active_coupons"] == 0
    health = data_health(dbp, 5)
    assert health["chains"][0]["active_coupons"] == 0
