#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTERVAL_MINUTES = max(30, int(os.getenv("SAL_HACHAM_SYNC_MINUTES", "60")))


def run_once() -> int:
    print(f"[{datetime.now().isoformat(timespec='seconds')}] evaluating city refresh policy...", flush=True)
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "sync_prices.py")],
        cwd=ROOT,
        check=False,
    )
    print(f"sync exit={result.returncode}", flush=True)
    return result.returncode


def main() -> None:
    while True:
        run_once()
        time.sleep(INTERVAL_MINUTES * 60)


if __name__ == "__main__":
    main()
