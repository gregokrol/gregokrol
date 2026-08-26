from datetime import datetime, timezone
from pathlib import Path
from app.db import init_db
from app.ingest.loader import ingest_file
from app.service import search_prices

def test_xml_to_database_to_search(tmp_path: Path):
    dbp=tmp_path/'db.sqlite3'; init_db(dbp)
    now=datetime.now(timezone.utc).astimezone().strftime('%Y%m%d-%H%M%S')
    stores=tmp_path/f'Stores7290696200003-001-{now}.xml'
    stores.write_text("""<Root><ChainId>7290696200003</ChainId><Stores><Store><StoreId>101</StoreId><StoreName>ויקטורי בדיקה</StoreName><City>באר שבע</City><Address>בדיקה 1</Address></Store></Stores></Root>""", encoding='utf-8')
    price=tmp_path/f'Price7290696200003-001-101-{now}.xml'
    price.write_text("""<Root><ChainId>7290696200003</ChainId><StoreId>101</StoreId><Items><Item><ItemCode>729123</ItemCode><ItemName>חלב טרי 3% 1 ליטר</ItemName><ItemPrice>6.49</ItemPrice></Item></Items></Root>""", encoding='utf-8')
    ingest_file(dbp, stores, 'VICTORY_NEW_SOURCE')
    ingest_file(dbp, price, 'VICTORY_NEW_SOURCE')
    out=search_prices(dbp,'חלב 3%', 'באר שבע', None,None,30,5)
    assert out['count']==1
    assert out['results'][0]['chain_name']=='ויקטורי'
    assert out['results'][0]['price']==6.49
    assert out['results'][0]['history']['low_price']==6.49
    assert out['results'][0]['history']['high_price']==6.49
    assert out['results'][0]['history']['average_price']==6.49
