from app.search import relevance, normalize

def test_percentage_normalization():
    assert normalize("חלב 3 אחוז") == "חלב 3%"

def test_milk_3_percent_matches():
    assert relevance("חלב 3%", "חלב טרי 3% 1 ליטר") > 0

def test_milk_3_percent_rejects_other_percent():
    assert relevance("חלב 3%", "חלב טרי 1% 1 ליטר") == 0

def test_choco_drink_does_not_match_chocolate():
    assert relevance("שוקו", "שוקולד חלב פרה 100 גרם") == 0

def test_choco_drink_matches_exact_word():
    assert relevance("שוקו", "משקה שוקו 1 ליטר") > 0

def test_milk_does_not_match_protein_word():
    assert relevance("חלב", "חלבון מי גבינה") == 0


def test_without_lactose_does_not_match_with_lactose():
    assert relevance("חלב ללא לקטוז", "חלב עם לקטוז 1 ליטר") == 0
    assert relevance("חלב ללא לקטוז", "חלב ללא לקטוז 1 ליטר") > 0

def test_with_vitamin_d_does_not_match_without():
    assert relevance("חלב עם ויטמין d", "חלב ללא ויטמין d") == 0


def test_percentage_plural_normalization():
    assert normalize("חלב 3 אחוזים") == "חלב 3%"
