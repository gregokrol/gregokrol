import gzip
from pathlib import Path
from app.ingest.xml_parser import parse_records

XML='''<?xml version="1.0" encoding="UTF-8"?>
<Root><ChainId>7290058140886</ChainId><StoreId>123</StoreId>
<Items><Item><ItemCode>7290001</ItemCode><ItemName>חלב טרי 3%</ItemName><ManufacturerName>בדיקה</ManufacturerName><ItemPrice>6.25</ItemPrice><PriceUpdateDate>2026-08-23T20:00:00+00:00</PriceUpdateDate></Item></Items></Root>'''.encode('utf-8')

def test_parse_gz_price(tmp_path: Path):
    p=tmp_path/'PriceFull7290058140886-001-123-202608232000.gz'
    p.write_bytes(gzip.compress(XML))
    r=parse_records(p)
    assert r['chain_id']=='7290058140886'
    assert r['products'][0]['name']=='חלב טרי 3%'
    assert r['prices'][0]['price']==6.25
    assert r['prices'][0]['store_number']=='123'


def test_filename_timestamp_used_when_xml_has_no_timestamp(tmp_path: Path):
    xml = """<Root><ChainId>7290058140886</ChainId><StoreId>123</StoreId><Items><Item><ItemCode>1</ItemCode><ItemName>חלב 3%</ItemName><ItemPrice>5</ItemPrice></Item></Items></Root>""".encode("utf-8")
    p=tmp_path/'Price7290058140886-001-123-20260821-220000.gz'
    p.write_bytes(gzip.compress(xml))
    r=parse_records(p)
    assert r['prices'][0]['updated_at'].startswith('2026-08-21T19:00:00')


def test_unit_measure_price_is_not_used_as_item_price(tmp_path: Path):
    xml = """<Root><ChainId>7290058140886</ChainId><StoreId>123</StoreId><Items><Item><ItemCode>1</ItemCode><ItemName>מוצר שקיל</ItemName><UnitOfMeasurePrice>12.5</UnitOfMeasurePrice></Item></Items></Root>""".encode("utf-8")
    p=tmp_path/'Price7290058140886-001-123-202608232000.xml'
    p.write_bytes(xml)
    r=parse_records(p)
    assert r['products'][0]['name']=='מוצר שקיל'
    assert r['prices']==[]
