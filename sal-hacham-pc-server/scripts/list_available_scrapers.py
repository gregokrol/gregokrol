#!/usr/bin/env python3
"""One-off diagnostic: print every scraper name il_supermarket_scarper actually
supports, to compare against app/source_registry.py's CHAIN_SOURCES list."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.win_compat import install_fcntl_stub

install_fcntl_stub()

from il_supermarket_scarper import ScraperFactory

for name in sorted(ScraperFactory.all_scrapers_name()):
    print(name)
