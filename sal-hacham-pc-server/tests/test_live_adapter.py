from __future__ import annotations

import sys
import types
from pathlib import Path

import scripts.sync_prices as sync_prices
from scripts.sync_prices import LIVE_FILE_TYPES, run_scraper


def test_live_scraper_receives_correct_output_directory_and_single_pass(tmp_path: Path, monkeypatch):
    calls = {}

    class FakeFactory:
        @staticmethod
        def all_scrapers_name():
            return ["RAMI_LEVY", "YOHANANOF"]

    class FakeTask:
        def __init__(self, **kwargs):
            calls["kwargs"] = kwargs

        def start(self, **kwargs):
            calls["start"] = kwargs

        def join(self):
            calls["join"] = True

    fake = types.SimpleNamespace(ScarpingTask=FakeTask, ScraperFactory=FakeFactory)
    monkeypatch.setitem(sys.modules, "il_supermarket_scarper", fake)

    run_scraper(tmp_path, ["RAMI_LEVY", "YOHANANOF"])
    assert calls["kwargs"]["enabled_scrapers"] == ["RAMI_LEVY", "YOHANANOF"]
    assert calls["kwargs"]["files_types"] == LIVE_FILE_TYPES
    assert calls["kwargs"]["multiprocessing"] == 2
    assert calls["kwargs"]["output_configuration"]["base_storage_path"] == str(tmp_path)
    assert calls["kwargs"]["status_configuration"]["base_path"] == str(tmp_path / ".status")
    assert calls["start"] == {"single_pass": True}
    assert calls["join"] is True


def test_city_scraper_requests_every_store_in_the_city(tmp_path: Path, monkeypatch):
    calls = []

    class FakeFactory:
        @staticmethod
        def all_scrapers_name():
            return ["RAMI_LEVY", "YOHANANOF"]

    async def fake_store_scrape(raw_dir, status_dir, chain, number):
        calls.append((chain, number))
        return {"chain": chain, "store_number": number, "downloaded": 1, "failed": 0}

    monkeypatch.setattr(sync_prices, "_scraper_imports", lambda: (object, FakeFactory))
    monkeypatch.setattr(sync_prices, "_scrape_chain_store", fake_store_scrape)
    stores = [
        {"chain_key": "RAMI_LEVY", "store_number": "3"},
        {"chain_key": "RAMI_LEVY", "store_number": "17"},
        {"chain_key": "YOHANANOF", "store_number": "42"},
        {"chain_key": "OTHER", "store_number": "99"},
    ]
    results = sync_prices.run_city_scraper(tmp_path / "raw", tmp_path / "status", stores, ["RAMI_LEVY", "YOHANANOF"])
    assert calls == [("RAMI_LEVY", "3"), ("RAMI_LEVY", "17"), ("YOHANANOF", "42")]
    assert len(results) == 3
