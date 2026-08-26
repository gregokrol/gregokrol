from datetime import datetime, timedelta, timezone
from pathlib import Path
from app.db import init_db, db
from app.demo import seed_demo
from app.service import search_prices

def test_stale_price_is_hidden(tmp_path: Path):
    p=tmp_path/'d.sqlite3'; init_db(p); seed_demo(p)
    stale=(datetime.now(timezone.utc)-timedelta(hours=6)).isoformat()
    with db(p) as con: con.execute('UPDATE prices SET observed_at=?',(stale,))
    r=search_prices(p,'חלב 3%', 'באר שבע', None,None,30,5)
    assert r['count']==0
