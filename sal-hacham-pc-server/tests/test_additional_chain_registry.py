from app.source_registry import CHAIN_DISPLAY


def test_keshet_teamim_and_tiv_taam_are_enabled_live_sources():
    assert CHAIN_DISPLAY["KESHET"] == "קשת טעמים"
    assert CHAIN_DISPLAY["TIV_TAAM"] == "טיב טעם"
