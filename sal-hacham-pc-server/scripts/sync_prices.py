#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.city_cache import (
    claim_city_refresh,
    collector_state_set,
    due_cities,
    fail_city_refresh,
    finish_city_refresh,
    refresh_city_memberships,
    state_is_older_than,
    stores_for_city,
    city_storage_token,
)
from app.config import settings
from app.db import init_db
from app.ingest.loader import ingest_directory
from app.price_history import prune_price_history
from app.service import normalize_city
from app.source_registry import CHAIN_SOURCES

STORE_FILE_TYPES = ["STORE_FILE"]
CITY_FILE_TYPES = ["PRICE_FULL_FILE", "PRICE_FILE", "PROMO_FULL_FILE", "PROMO_FILE"]
LIVE_FILE_TYPES = [*STORE_FILE_TYPES, *CITY_FILE_TYPES]


class SyncLock:
    """Small cross-process lock shared by searches and Windows Task Scheduler."""

    def __init__(self, path: Path):
        self.path = path
        self.acquired = False
        self.handle = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.path.open("a+b")
        self.handle.seek(0, os.SEEK_END)
        if self.handle.tell() == 0:
            self.handle.write(b"0")
            self.handle.flush()
        self.handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.handle.close()
            self.handle = None
            return self
        self.acquired = True
        return self

    def __exit__(self, exc_type, exc, tb):
        if not self.handle:
            return
        try:
            self.handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        finally:
            self.handle.close()
            self.handle = None


def _scraper_imports():
    try:
        from il_supermarket_scarper import ScarpingTask, ScraperFactory
    except ImportError:
        raise SystemExit(
            "Missing live scraper. Install it with:\n"
            "  python -m pip install -r requirements-live.txt\n"
            "Then run this command again."
        )
    return ScarpingTask, ScraperFactory


def _validate_chains(chains: list[str], factory) -> None:
    valid = set(factory.all_scrapers_name())
    invalid = [chain for chain in chains if chain not in valid]
    if invalid:
        raise SystemExit(f"Unsupported scraper identifiers: {', '.join(invalid)}")


def run_scraper(
    raw_dir: Path,
    chains: list[str],
    file_types: list[str] | None = None,
    status_dir: Path | None = None,
) -> None:
    """Run one national pass. Used only for the small Stores directory."""
    ScarpingTask, ScraperFactory = _scraper_imports()
    _validate_chains(chains, ScraperFactory)
    raw_dir.mkdir(parents=True, exist_ok=True)
    task = ScarpingTask(
        enabled_scrapers=chains,
        files_types=file_types or LIVE_FILE_TYPES,
        multiprocessing=2,
        output_configuration={
            "output_mode": "disk",
            "base_storage_path": str(raw_dir),
        },
        status_configuration={
            "database_type": "json",
            "base_path": str(status_dir or raw_dir / ".status"),
        },
    )
    task.start(single_pass=True)
    task.join()


async def _scrape_chain_store(
    raw_dir: Path,
    status_dir: Path,
    chain: str,
    store_number: str,
) -> dict[str, int | str]:
    _, ScraperFactory = _scraper_imports()
    from il_supermarket_scarper.utils import FilterState
    from il_supermarket_scarper.utils.databases import (
        create_file_output_for_scraper,
        create_status_database_for_scraper,
    )

    output = create_file_output_for_scraper(
        chain,
        {"output_mode": "disk", "base_storage_path": str(raw_dir)},
    )
    status_database = create_status_database_for_scraper(
        chain,
        {"database_type": "json", "base_path": str(status_dir)},
    )
    scraper_class = ScraperFactory.get(chain)
    scraper = scraper_class(file_output=output, status_database=status_database)
    if not str(store_number).isdigit():
        raise ValueError(f"Store identifier is not numeric: {store_number}")
    store_id = int(store_number)
    downloaded = 0
    failed = 0
    async for result in scraper.scrape(
        state=FilterState(),
        files_types=CITY_FILE_TYPES,
        store_id=store_id,
        filter_null=False,
        filter_zero=False,
    ):
        if getattr(result, "extract_succefully", False):
            downloaded += 1
        elif getattr(result, "error", None):
            failed += 1
    return {"chain": chain, "store_number": str(store_number), "downloaded": downloaded, "failed": failed}


def run_city_scraper(raw_dir: Path, status_dir: Path, stores: list[dict[str, str]], chains: list[str]) -> list[dict]:
    """Use each source's store filter so files from other cities are not downloaded."""
    _, ScraperFactory = _scraper_imports()
    _validate_chains(chains, ScraperFactory)
    raw_dir.mkdir(parents=True, exist_ok=True)
    status_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for store in stores:
        chain = store["chain_key"]
        number = store.get("store_number") or ""
        if chain not in chains or not number:
            continue
        try:
            results.append(asyncio.run(_scrape_chain_store(raw_dir, status_dir, chain, number)))
        except Exception as exc:
            results.append({"chain": chain, "store_number": number, "downloaded": 0, "failed": 1, "error": f"{type(exc).__name__}: {exc}"})
    return results


def _ingest_and_report(raw_dir: Path, *, delete_ingested: bool = False) -> tuple[int, list[dict]]:
    results = ingest_directory(settings.db_path, raw_dir, delete_ingested=delete_ingested)
    prune_price_history(settings.db_path, settings.price_history_days)
    errors = [row for row in results if "error" in row]
    skipped = [row for row in results if row.get("skipped")]
    processed = len(results) - len(errors) - len(skipped)
    for row in results:
        if not row.get("skipped"):
            print(row, flush=True)
    print(
        f"Files seen={len(results)}; processed={processed}; "
        f"skipped_unchanged={len(skipped)}; errors={len(errors)}",
        flush=True,
    )
    return processed, errors


def refresh_store_directory(chains: list[str], *, force: bool = False) -> bool:
    if not force and not state_is_older_than(
        settings.db_path,
        "store_directory_refreshed_at",
        settings.store_directory_refresh_hours,
    ):
        return False
    store_raw = settings.raw_dir / "stores"
    print("Refreshing the national store directory (Store files only)...", flush=True)
    run_scraper(store_raw, chains, STORE_FILE_TYPES, settings.raw_dir / ".status" / "stores")
    _, errors = _ingest_and_report(store_raw)
    if errors:
        raise RuntimeError(f"{len(errors)} store-directory files could not be parsed")
    refresh_city_memberships(settings.db_path, prune=True)
    collector_state_set(settings.db_path, "store_directory_refreshed_at", datetime.now(timezone.utc).isoformat())
    return True


def refresh_city(city_key: str, city_name: str, chains: list[str]) -> bool:
    if not claim_city_refresh(settings.db_path, city_key):
        return False
    try:
        refresh_store_directory(chains)
        refresh_city_memberships(settings.db_path, prune=True)
        stores = stores_for_city(settings.db_path, city_key)
        token = city_storage_token(city_key)
        city_raw = settings.raw_dir / "cities" / token
        city_status = settings.raw_dir / ".status" / "cities" / token
        source_results = run_city_scraper(city_raw, city_status, stores, chains) if stores else []
        processed, parse_errors = _ingest_and_report(city_raw, delete_ingested=True)
        refresh_city_memberships(settings.db_path, prune=True)
        source_errors = [row for row in source_results if row.get("error") or row.get("failed")]
        error_count = len(source_errors) + len(parse_errors)
        status = "partial" if error_count else "ready"
        detail = f"{error_count} source/parser errors" if error_count else None
        finish_city_refresh(
            settings.db_path,
            city_key,
            status=status,
            file_count=processed,
            store_count=len(stores),
            error=detail,
        )
        print(
            f"City refresh complete: {city_name}; stores={len(stores)}; "
            f"processed={processed}; source_errors={error_count}",
            flush=True,
        )
        return True
    except Exception as exc:
        fail_city_refresh(settings.db_path, city_key, f"{type(exc).__name__}: {exc}")
        raise


def run_scheduled(chains: list[str]) -> int:
    errors = 0
    try:
        refresh_store_directory(chains)
    except Exception as exc:
        errors += 1
        print(f"Store directory refresh failed: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
    for row in due_cities(
        settings.db_path,
        active_hours=settings.active_city_refresh_hours,
        inactive_hours=settings.inactive_city_refresh_hours,
    ):
        try:
            refresh_city(row["city_key"], row["city_name"], chains)
        except Exception as exc:
            errors += 1
            print(f"City refresh failed for {row['city_name']}: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
    return 1 if errors else 0


def _run_locked(args, chains: list[str]) -> int:
    if args.refresh_stores:
        refresh_store_directory(chains, force=True)
    if args.city:
        city_key = normalize_city(args.city)
        rows = {
            row["city_key"]: row
            for row in due_cities(
                settings.db_path,
                active_hours=settings.active_city_refresh_hours,
                inactive_hours=settings.inactive_city_refresh_hours,
            )
        }
        row = rows.get(city_key)
        if not row:
            return 0
        return 0 if refresh_city(city_key, row["city_name"], chains) else 0
    return run_scheduled(chains)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Maintain a five-city cache from official Israeli supermarket transparency files."
    )
    parser.add_argument("--ingest-only", action="store_true", help="Only parse files already downloaded")
    parser.add_argument("--city", help="Refresh one retained city immediately")
    parser.add_argument("--refresh-stores", action="store_true", help="Force a national Store-file refresh")
    parser.add_argument(
        "--chains",
        default=",".join(key for key, _ in CHAIN_SOURCES),
        help="Comma-separated scraper identifiers",
    )
    args = parser.parse_args()
    chains = [value.strip() for value in args.chains.split(",") if value.strip()]
    init_db(settings.db_path)
    if args.ingest_only:
        _, errors = _ingest_and_report(settings.raw_dir)
        refresh_city_memberships(settings.db_path, prune=True)
        return 1 if errors else 0

    lock_path = settings.raw_dir.parent / "sync.lock"
    wait_until = time.monotonic() + 2 * 3600 if args.city else time.monotonic()
    while True:
        with SyncLock(lock_path) as lock:
            if lock.acquired:
                return _run_locked(args, chains)
        if time.monotonic() >= wait_until:
            print("Another city refresh is already running; the queued city will be picked up later.", flush=True)
            return 0
        time.sleep(15)


if __name__ == "__main__":
    raise SystemExit(main())
