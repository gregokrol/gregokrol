#!/usr/bin/env python3
"""Manually trigger a sync for the bot's configured city.

Run this file directly (`python manual_sync.py`), not via -c/runpy: the
scraper uses multiprocessing internally, and on Windows that needs a real
script file with a proper `if __name__ == "__main__":` guard to spawn worker
processes correctly - a runpy/-c invocation can spawn workers that never
finish. Reads the city from the DB so nothing has to be typed here.
"""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
ROOT = SCRIPTS_DIR.parent
for path in (str(ROOT), str(SCRIPTS_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

from app.win_compat import install_fcntl_stub

install_fcntl_stub()

from app.config import settings
from app.personal_lists import get_bot_city


def main() -> int:
    city = get_bot_city(settings.db_path)
    if not city:
        print("No city configured yet - set one via the Telegram bot first.", flush=True)
        return 1
    print(f"Refreshing city: {city}", flush=True)
    sys.argv = [str(SCRIPTS_DIR / "sync_prices.py"), "--city", city]

    import sync_prices

    return sync_prices.main()


if __name__ == "__main__":
    raise SystemExit(main())
