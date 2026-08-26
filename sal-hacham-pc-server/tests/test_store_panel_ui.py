from pathlib import Path

STATIC = Path(__file__).resolve().parents[1] / "app" / "static"


def test_store_panel_is_collapsed_by_default():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    assert '<section id="storesPanel"' in html
    assert 'id="storesToggle"' in html
    assert 'aria-expanded="false"' in html
    assert 'id="storesBody" class="details-body" hidden' in html
    assert '<details id="storesPanel"' not in html


def test_store_list_is_lazy_loaded():
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    assert "if(!storesOpen() && !force)return" in js
    assert "fetch('/api/stores?'" in js
    assert "storesToggle').addEventListener('click'" in js
    assert "setStoresOpen(false)" in js


def test_store_api_reports_fresh_price_coverage(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from app import main
    from app.db import init_db, db, utc_now_iso

    dbp = tmp_path / "coverage.sqlite3"
    init_db(dbp)
    now = utc_now_iso()
    with db(dbp) as con:
        con.execute(
            "INSERT INTO stores(id,chain_key,chain_name,store_number,name,city,address,lat,lng,updated_at,is_demo) VALUES(?,?,?,?,?,?,?,?,?,?,0)",
            ("s1", "X", "רשת", "1", "סניף", "באר שבע", "כתובת", 31.25, 34.79, now),
        )
        con.execute(
            "INSERT INTO products(barcode,name,manufacturer,updated_at,is_demo) VALUES(?,?,?,?,0)",
            ("b1", "חלב 3%", "יצרן", now),
        )
        con.execute(
            "INSERT INTO prices(store_id,barcode,price,unit_price,updated_at,observed_at,is_demo) VALUES(?,?,?,?,?,?,0)",
            ("s1", "b1", 6.5, None, now, now),
        )
    monkeypatch.setattr(main.settings, "db_path", dbp)
    with TestClient(main.app) as client:
        data = client.get("/api/stores", params={"city": "באר שבע"}).json()
    assert data["count"] == 1
    assert data["stores"][0]["fresh_prices"] == 1
