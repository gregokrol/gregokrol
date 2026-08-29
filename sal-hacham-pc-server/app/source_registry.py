from __future__ import annotations

# Scraper identifiers are aligned with the current OpenIsraeliSupermarkets scraper.
# Prefer *_NEW_SOURCE where the project documents a newer source.
CHAIN_SOURCES = [
    ("SHUFERSAL", "שופרסל"),
    ("RAMI_LEVY", "רמי לוי"),
    ("YOHANANOF", "יוחננוף"),
    ("OSHER_AD", "אושר עד"),
    ("VICTORY_NEW_SOURCE", "ויקטורי"),
    ("MAHSANI_ASHUK_NEW_SOURCE", "מחסני השוק"),
    ("SALACH_DABACH", "סאלח דבאח"),
    ("KING_STORE", "קינג סטור"),
    ("HAZI_HINAM", "חצי חינם"),
    ("YAYNO_BITAN_AND_CARREFOUR", "קרפור / יינות ביתן"),
    ("TIV_TAAM", "טיב טעם"),
    ("KESHET", "קשת טעמים"),
    ("STOP_MARKET", "סטופ מרקט"),
    ("FRESH_MARKET_AND_SUPER_DOSH", "פרש מרקט / סופר דוש"),
    ("ZOL_VEBEGADOL", "זול ובגדול"),
    ("SUPER_YUDA", "סופר יודה"),
    ("SUPER_SAPIR", "סופר ספיר"),
    ("BAREKET", "ברקת"),
    ("MAAYAN_2000", "מעיין 2000"),
    ("HET_COHEN_NEW_SOURCE", "ח. כהן"),
    ("DOR_ALON", "דור אלון / AM:PM"),
    ("YELLOW", "Yellow"),
    ("CITY_MARKET_SHOPS", "סיטי מרקט"),
    ("SHUK_AHIR", "שוק העיר"),
]

CHAIN_DISPLAY = dict(CHAIN_SOURCES)
REQUIRED_CORE = {
    "SHUFERSAL", "RAMI_LEVY", "YOHANANOF", "VICTORY_NEW_SOURCE",
    "MAHSANI_ASHUK_NEW_SOURCE", "SALACH_DABACH", "KING_STORE",
}
