"""Windows compatibility shims for third-party libraries that assume POSIX.

il_supermarket_scraper (imported as il_supermarket_scarper) unconditionally
imports fcntl for advisory file locking, which does not exist on Windows and
crashes the import outright. sync_prices.py already serializes scraper runs
itself (see SyncLock), so that locking isn't needed here - a no-op stand-in
lets the real import succeed instead.
"""
from __future__ import annotations

import os
import sys
import types


def install_fcntl_stub() -> None:
    if os.name != "nt" or "fcntl" in sys.modules:
        return

    stub = types.ModuleType("fcntl")
    stub.LOCK_EX = 2
    stub.LOCK_SH = 1
    stub.LOCK_UN = 8
    stub.LOCK_NB = 4
    stub.flock = lambda *args, **kwargs: None
    stub.lockf = lambda *args, **kwargs: None
    sys.modules["fcntl"] = stub
