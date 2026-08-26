from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from app.db import init_db
from app.ingest.loader import ingest_file
from app.service import search_prices

def test_missing_city_can_match_store_name(tmp_path: Path):
    dbp=tmp_path/'db.sqlite3'; init_db(dbp)
    ts=datetime.now(ZoneInfo('Asia/Jerusalem')).strftime('%Y%m%d-%H%M%S')
    s=tmp_path/f'Stores7290803800003-001-{ts}.xml'; s.write_text('<Root><ChainId>7290803800003</ChainId><Stores><Store><StoreId>12</StoreId><StoreName>יוחננוף באר שבע</StoreName></Store></Stores></Root>',encoding='utf-8')
    p=tmp_path/f'Price7290803800003-001-012-{ts}.xml'; p.write_text('<Root><ChainId>7290803800003</ChainId><StoreId>12</StoreId><Items><Item><ItemCode>9</ItemCode><ItemName>שוקו 1 ליטר</ItemName><ItemPrice>8.9</ItemPrice></Item></Items></Root>',encoding='utf-8')
    ingest_file(dbp,s,'YOHANANOF'); ingest_file(dbp,p,'YOHANANOF')
    out=search_prices(dbp,'שוקו','באר שבע',None,None,30,5)
    assert out['count']==1
