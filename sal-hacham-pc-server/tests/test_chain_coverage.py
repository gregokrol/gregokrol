from app.source_registry import CHAIN_DISPLAY, REQUIRED_CORE

def test_required_chains_configured():
    assert REQUIRED_CORE.issubset(CHAIN_DISPLAY.keys())
