from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from app.db import init_db
from app.ingest.loader import ingest_file
from app.service import search_prices

def test_old_price_change_is_valid_when_fresh_file_confirms_it(tmp_path: Path):
    dbp=tmp_path/'db.sqlite3'; init_db(dbp)
    local=datetime.now(ZoneInfo('Asia/Jerusalem'))
    ts=local.strftime('%Y%m%d-%H%M%S')
    stores=tmp_path/f'Stores7290696200003-001-{ts}.xml'
    stores.write_text('<Root><ChainId>7290696200003</ChainId><Stores><Store><StoreId>101</StoreId><StoreName>ויקטורי באר שבע</StoreName><City>באר שבע</City></Store></Stores></Root>',encoding='utf-8')
    price=tmp_path/f'Price7290696200003-001-101-{ts}.xml'
    price.write_text('<Root><ChainId>7290696200003</ChainId><StoreId>101</StoreId><Items><Item><ItemCode>729123</ItemCode><ItemName>חלב טרי 3%</ItemName><ItemPrice>6.49</ItemPrice><PriceUpdateDate>2026-08-01T10:00:00</PriceUpdateDate></Item></Items></Root>',encoding='utf-8')
    ingest_file(dbp,stores,'VICTORY_NEW_SOURCE'); ingest_file(dbp,price,'VICTORY_NEW_SOURCE')
    out=search_prices(dbp,'חלב 3%','באר שבע',None,None,30,5)
    assert out['count']==1
    assert out['results'][0]['updated_at'] < out['results'][0]['observed_at']
