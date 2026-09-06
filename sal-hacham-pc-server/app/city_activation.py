"""Shared "a city was searched" bookkeeping used by both the HTTP API and the
Telegram bot: touches the five-city cache and spawns a background refresh for
a city that is due, so any entry point that searches also keeps data fresh.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from .city_cache import (
    city_storage_token,
    cleanup_evicted_storage,
    city_cache_status,
    queue_city_if_due,
    touch_city,
)
from .config import settings

ROOT = Path(__file__).resolve().parent.parent


def _launch_city_refresh(city: str, city_key: str) -> None:
    logs = settings.raw_dir.parent.parent / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    # One file per city, not shared with the scheduled task's sync.log or with
    # each other: on Windows, a PowerShell/Python redirection holds the log file
    # open with a sharing mode that denies other writers for as long as the
    # process runs, so two refreshes racing on the same path fail with
    # PermissionError (this happened with the scheduled task before; with two
    # cities refreshing at once it would happen here too without this).
    log_path = logs / f"city_refresh_{city_storage_token(city_key)}.log"
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    # Redirecting to a UTF-8-opened file here doesn't make the child use UTF-8:
    # the child picks its own stdout encoding from the OS locale once its stdout
    # isn't an actual console, which on Windows is a non-Unicode codepage (e.g.
    # cp1252) that can't encode Hebrew city/chain names - crashing the whole
    # sync with UnicodeEncodeError. Force UTF-8 for the child explicitly.
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    with log_path.open("a", encoding="utf-8") as log:
        subprocess.Popen(
            [sys.executable, str(ROOT / "scripts" / "sync_prices.py"), "--city", city],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            close_fds=True,
            creationflags=creationflags,
            env=env,
        )


def activate_city(city: str | None) -> dict | None:
    if not city or not city.strip():
        return None
    if settings.demo_mode:
        return None
    touched = touch_city(settings.db_path, city, settings.max_cached_cities)
    if not touched:
        return None
    cleanup_evicted_storage(settings.raw_dir, touched["evicted"])
    queued = queue_city_if_due(
        settings.db_path,
        touched["city_key"],
        active_hours=settings.active_city_refresh_hours,
        inactive_hours=settings.inactive_city_refresh_hours,
    )
    if queued and not settings.demo_mode:
        try:
            _launch_city_refresh(touched["city_name"], touched["city_key"])
        except Exception as exc:
            # The hourly scheduler will pick up the queued city even if spawning the
            # immediate worker failed, so the caller can still return cached data.
            print(f"Could not start city refresh: {type(exc).__name__}: {exc}", flush=True)
    return city_cache_status(
        settings.db_path,
        touched["city_name"],
        max_cities=settings.max_cached_cities,
        active_hours=settings.active_city_refresh_hours,
        inactive_hours=settings.inactive_city_refresh_hours,
    )
