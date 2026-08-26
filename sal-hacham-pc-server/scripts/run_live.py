#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    env = os.environ.copy()
    env["SAL_HACHAM_DEMO"] = "0"
    sync = subprocess.Popen(
        [sys.executable, str(ROOT / "scripts" / "sync_loop.py")],
        cwd=ROOT,
        env=env,
    )
    try:
        return subprocess.call(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
            ],
            cwd=ROOT,
            env=env,
        )
    finally:
        sync.terminate()
        try:
            sync.wait(timeout=5)
        except subprocess.TimeoutExpired:
            sync.kill()
            sync.wait()


if __name__ == "__main__":
    raise SystemExit(main())
