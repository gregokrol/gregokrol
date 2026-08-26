from pathlib import Path
from fastapi.testclient import TestClient
import app.main as main
from app.db import init_db
from app.demo import seed_demo


def make_client(tmp_path: Path, monkeypatch):
    dbp=tmp_path/'t.sqlite3'
    monkeypatch.setattr(main.settings, 'db_path', dbp)
    init_db(dbp); seed_demo(dbp)
    return TestClient(main.app)


def test_health(tmp_path, monkeypatch):
    c=make_client(tmp_path, monkeypatch)
    r=c.get('/api/health')
    assert r.status_code==200 and r.json()['status']=='ok'


def test_search_precision_shoko(tmp_path, monkeypatch):
    c=make_client(tmp_path, monkeypatch)
    data=c.get('/api/search', params={'q':'שוקו','city':'באר שבע'}).json()
    assert data['count'] == 6
    assert all('שוקו' in x['product_name'] for x in data['results'])


def test_search_milk_percent(tmp_path, monkeypatch):
    c=make_client(tmp_path, monkeypatch)
    data=c.get('/api/search', params={'q':'חלב 3 אחוז','city':'באר שבע'}).json()
    assert data['count'] == 6
    assert all('3%' in x['product_name'] for x in data['results'])


def test_city_alias_beer_sheva(tmp_path, monkeypatch):
    c=make_client(tmp_path, monkeypatch)
    data=c.get('/api/search', params={'q':'שוקו','city':'באר-שבע'}).json()
    assert data['count']==6


def test_store_listing_by_city(tmp_path, monkeypatch):
    c=make_client(tmp_path, monkeypatch)
    data=c.get('/api/stores', params={'city':'באר שבע'}).json()
    assert data['count']==6
    assert {'יוחננוף','ויקטורי','מחסני השוק','סאלח דבאח','קינג סטור'}.issubset({x['chain_name'] for x in data['stores']})

def test_store_listing_by_gps_radius(tmp_path, monkeypatch):
    c=make_client(tmp_path, monkeypatch)
    data=c.get('/api/stores', params={'lat':31.252,'lng':34.791,'radius_km':1}).json()
    assert data['count'] >= 1
    assert all(x['distance_km'] <= 1 for x in data['stores'])


def test_search_limit(tmp_path, monkeypatch):
    c=make_client(tmp_path, monkeypatch)
    data=c.get('/api/search', params={'q':'שוקו','city':'באר שבע','limit':2}).json()
    assert data['count']==2
    assert data['truncated'] is True


def test_search_returns_every_matching_branch_in_city(tmp_path, monkeypatch):
    c = make_client(tmp_path, monkeypatch)
    stores = c.get('/api/stores', params={'city': 'באר שבע'}).json()['stores']
    data = c.get('/api/search', params={'q': 'שוקו', 'city': 'באר שבע', 'limit': 5000}).json()
    assert {row['store_id'] for row in data['results']} == {store['id'] for store in stores}


def test_api_token_protects_public_endpoints(tmp_path, monkeypatch):
    c = make_client(tmp_path, monkeypatch)
    monkeypatch.setattr(main.settings, 'api_token', 'server-secret')
    assert c.get('/api/search', params={'q': 'שוקו', 'city': 'באר שבע'}).status_code == 401
    authorized = c.get(
        '/api/search',
        params={'q': 'שוקו', 'city': 'באר שבע'},
        headers={'Authorization': 'Bearer server-secret'},
    )
    assert authorized.status_code == 200
