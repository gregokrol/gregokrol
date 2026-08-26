from __future__ import annotations

# Verified official destinations for chain-run promotions/benefit programs.
# They are supplementary to the legally published Promo/PromoFull data; the app
# does not scrape personal accounts or claim eligibility for personal coupons.
CHAIN_BENEFITS: dict[str, dict] = {
    "SHUFERSAL": {
        "label": "שופרסל Online / קופונים אישיים",
        "url": "https://www.shufersal.co.il/online/he/A",
        "note": "קופונים אישיים עשויים לדרוש התחברות למועדון.",
    },
    "RAMI_LEVY": {
        "label": "מועדון והטבות רמי לוי",
        "url": "https://hamoadon.rami-levy.co.il",
        "note": "חלק מהקופונים אישיים או מותנים בחברות/אמצעי תשלום.",
    },
    "YOHANANOF": {
        "label": "יוחננוף — מבצעים ומועדון",
        "url": "https://www.yochananof.co.il/",
        "note": "באתר ובאפליקציה של הרשת מתפרסמים מבצעים וקופונים.",
    },
    "VICTORY_NEW_SOURCE": {
        "label": "ויקטורי — מבצעי השבוע",
        "url": "https://victory.co.il/%D7%9E%D7%91%D7%A6%D7%A2%D7%99-%D7%94%D7%A9%D7%91%D7%95%D7%A2/",
        "note": "חלק מההטבות מותנות במועדון או בכרטיס אשראי של הרשת.",
    },
    "MAHSANI_ASHUK_NEW_SOURCE": {
        "label": "מחסני השוק — מועדון וקופונים",
        "url": "https://m-shuk.net/",
        "note": "הרשת מפרסמת הטבות וקופונים דרך המועדון וערוציה הרשמיים.",
    },
}


def benefit_for_chain(chain_key: str) -> dict | None:
    value = CHAIN_BENEFITS.get(chain_key)
    return dict(value) if value else None
