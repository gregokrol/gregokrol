from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

HEBREW_DIACRITICS = re.compile(r"[\u0591-\u05C7]")
NON_WORD = re.compile(r"[^0-9a-zA-Zא-ת%]+")
PCT_SPACED = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:אחוזים|אחוז|%)")
STOPWORDS = {"של", "את", "ה", "ו"}

# Only true semantic aliases. Do not use substring aliases (e.g. שוקו != שוקולד).
ALIASES = {
    "קולה": {"קולה"},
    "שוקו": {"שוקו", "משקה שוקו"},
    "חלב": {"חלב"},
    "קוטג": {"קוטג", "קוטג'"},
}


def normalize(text: str | None) -> str:
    text = unicodedata.normalize("NFKC", text or "").lower().strip()
    text = HEBREW_DIACRITICS.sub("", text)
    text = text.replace("׳", "'").replace("״", '"')
    text = PCT_SPACED.sub(lambda m: m.group(1).replace(",", ".") + "%", text)
    text = NON_WORD.sub(" ", text)
    return " ".join(text.split())


def tokens(text: str | None) -> list[str]:
    return [t for t in normalize(text).split() if t not in STOPWORDS]


def _token_satisfied(qt: str, candidate_tokens: set[str], candidate_norm: str) -> bool:
    if qt in candidate_tokens:
        return True
    for alt in ALIASES.get(qt, set()):
        alt_norm = normalize(alt)
        if " " in alt_norm:
            if alt_norm in candidate_norm:
                return True
        elif alt_norm in candidate_tokens:
            return True
    # Numeric percentages must match exactly.
    if qt.endswith("%"):
        return qt in candidate_tokens
    # Controlled fuzzy only for longer words; avoids חלב->חלבון and שוקו->שוקולד.
    if len(qt) >= 5:
        for ct in candidate_tokens:
            if len(ct) >= 5 and SequenceMatcher(None, qt, ct).ratio() >= 0.90:
                return True
    return False


def relevance(query: str, name: str, manufacturer: str = "", barcode: str = "") -> float:
    qn = normalize(query)
    if not qn:
        return 0.0
    if qn.isdigit() and qn == str(barcode):
        return 1000.0

    qt = tokens(qn)
    cn = normalize(f"{name} {manufacturer}")
    cts = set(tokens(cn))
    if not qt:
        return 0.0

    # Hard precision gate: every meaningful query token must be represented.
    if any(not _token_satisfied(t, cts, cn) for t in qt):
        return 0.0

    score = 60.0
    name_norm = normalize(name)
    if qn == name_norm:
        score += 50
    elif qn in name_norm:
        score += 25

    exact = sum(1 for t in qt if t in cts)
    score += 8 * exact
    score -= max(0, len(tokens(name_norm)) - len(qt)) * 0.25
    return max(score, 0.0)


def candidate_products(con, query: str, max_candidates: int = 2000):
    """Return product rows prefiltered with FTS5 when available, then precision-score.

    Falls back to the V7 full scan for environments without FTS5 or typo cases where
    strict token matching yields no useful candidate.
    """
    qn = normalize(query)
    if not qn:
        return []
    if qn.isdigit():
        row = con.execute(
            "SELECT barcode,name,manufacturer FROM products WHERE barcode=?", (qn,)
        ).fetchone()
        rows = [row] if row else []
    else:
        rows = []
        fts_tokens = [re.sub(r"[^0-9a-zA-Zא-ת]", "", t.rstrip("%")) for t in tokens(qn)]
        fts_tokens = [t for t in fts_tokens if t]
        if fts_tokens:
            match = " AND ".join(f'"{t}"*' for t in fts_tokens)
            try:
                rows = con.execute(
                    """SELECT p.barcode,p.name,p.manufacturer
                       FROM products_fts f
                       JOIN products p ON p.rowid=f.rowid
                       WHERE products_fts MATCH ? LIMIT ?""",
                    (match, max_candidates),
                ).fetchall()
            except Exception:
                rows = []
    scored = []
    for p in rows:
        score = relevance(query, p["name"], p["manufacturer"] or "", p["barcode"])
        if score > 0:
            scored.append((p, score))
    if scored:
        scored.sort(key=lambda x: (-x[1], x[0]["name"]))
        return scored

    # Controlled fallback preserves typo tolerance and compatibility.
    rows = con.execute("SELECT barcode,name,manufacturer FROM products").fetchall()
    for p in rows:
        score = relevance(query, p["name"], p["manufacturer"] or "", p["barcode"])
        if score > 0:
            scored.append((p, score))
    scored.sort(key=lambda x: (-x[1], x[0]["name"]))
    return scored[:max_candidates]
