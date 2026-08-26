from __future__ import annotations

from datetime import datetime, timezone

from .db import db

# Synthetic test data. Names/prices are deliberately marked demo and are not presented as live prices.
DEMO_STORES = [
    ("demo-rami-bs", "RAMI_LEVY", "רמי לוי", "001", "סניף בדיקה באר שבע", "באר שבע", "כתובת בדיקה", 31.252, 34.791),
    ("demo-yoh-bs", "YOHANANOF", "יוחננוף", "002", "סניף בדיקה באר שבע", "באר שבע", "כתובת בדיקה", 31.247, 34.799),
    ("demo-vic-bs", "VICTORY_NEW_SOURCE", "ויקטורי", "003", "סניף בדיקה באר שבע", "באר שבע", "כתובת בדיקה", 31.258, 34.803),
    ("demo-mah-bs", "MAHSANI_ASHUK_NEW_SOURCE", "מחסני השוק", "004", "סניף בדיקה באר שבע", "באר שבע", "כתובת בדיקה", 31.243, 34.784),
    ("demo-dab-bs", "SALACH_DABACH", "סאלח דבאח", "005", "סניף בדיקה באר שבע", "באר שבע", "כתובת בדיקה", 31.260, 34.776),
    ("demo-king-bs", "KING_STORE", "קינג סטור", "006", "סניף בדיקה באר שבע", "באר שבע", "כתובת בדיקה", 31.235, 34.810),
]
DEMO_PRODUCTS = [
    ("7290000000001", "חלב טרי 3% 1 ליטר", "מחלבה לדוגמה"),
    ("7290000000002", "שוקו 1 ליטר", "מחלבה לדוגמה"),
    ("7290000000003", "שוקולד חלב פרה 100 גרם", "יצרן לדוגמה"),
]

DEMO_PROMOTIONS = [
    # store_id, promotion_id, description, min_qty, discounted_price, is_coupon, barcode
    ("demo-rami-bs", "demo-p1", "3 יחידות חלב ב-15 ₪", 3.0, 15.0, 0, "7290000000001"),
    ("demo-rami-bs", "demo-c1", "קופון שוקו ב-5 ₪", 1.0, 5.0, 1, "7290000000002"),
    ("demo-yoh-bs", "demo-p2", "2 יחידות שוקו ב-15 ₪", 2.0, 15.0, 0, "7290000000002"),
]

DEMO_PRICES = {
    "demo-rami-bs": [6.20, 8.90, 7.10],
    "demo-yoh-bs": [6.30, 8.70, 7.20],
    "demo-vic-bs": [6.50, 9.10, 7.00],
    "demo-mah-bs": [6.10, 8.80, 7.40],
    "demo-dab-bs": [6.40, 9.00, 7.30],
    "demo-king-bs": [6.35, 8.85, 7.25],
}


def seed_demo(path) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with db(path) as con:
        count = con.execute("SELECT COUNT(*) FROM prices").fetchone()[0]
        if count:
            return
        con.executemany(
            "INSERT OR REPLACE INTO stores(id,chain_key,chain_name,store_number,name,city,address,lat,lng,updated_at,is_demo) VALUES(?,?,?,?,?,?,?,?,?,?,1)",
            [(*s, now) for s in DEMO_STORES],
        )
        con.executemany(
            "INSERT OR REPLACE INTO products(barcode,name,manufacturer,updated_at,is_demo) VALUES(?,?,?,?,1)",
            [(*p, now) for p in DEMO_PRODUCTS],
        )
        for sid, vals in DEMO_PRICES.items():
            for (barcode, *_), price in zip(DEMO_PRODUCTS, vals):
                con.execute(
                    "INSERT OR REPLACE INTO prices(store_id,barcode,price,unit_price,updated_at,observed_at,is_demo) VALUES(?,?,?,?,?,?,1)",
                    (sid, barcode, price, None, now, now),
                )
        for sid, pid, desc, min_qty, discounted_price, is_coupon, barcode in DEMO_PROMOTIONS:
            con.execute(
                """INSERT OR REPLACE INTO promotions(
                   store_id,promotion_id,description,start_at,end_at,updated_at,observed_at,reward_type,
                   allow_multiple_discounts,is_weighted,min_qty,discounted_price,discounted_unit_price,
                   is_coupon,is_active,club_ids,remarks,is_demo)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)""",
                (sid,pid,desc,None,None,now,now,"1",1,0,min_qty,discounted_price,None,is_coupon,1,"0",None),
            )
            con.execute(
                "INSERT OR REPLACE INTO promotion_items(store_id,promotion_id,barcode,is_gift,item_type) VALUES(?,?,?,?,?)",
                (sid,pid,barcode,0,"1"),
            )
