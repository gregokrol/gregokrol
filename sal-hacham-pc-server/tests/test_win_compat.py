from __future__ import annotations

import sys

from app import win_compat


def test_stub_not_installed_on_posix(monkeypatch):
    monkeypatch.setattr(win_compat.os, "name", "posix")
    sys.modules.pop("fcntl", None)
    win_compat.install_fcntl_stub()
    assert "fcntl" not in sys.modules or sys.modules["fcntl"].__name__ != "fcntl"


def test_stub_installed_on_windows_and_is_a_noop(monkeypatch):
    monkeypatch.setattr(win_compat.os, "name", "nt")
    sys.modules.pop("fcntl", None)
    try:
        win_compat.install_fcntl_stub()
        import fcntl

        assert fcntl.flock(0, fcntl.LOCK_EX) is None
        assert fcntl.lockf(0, fcntl.LOCK_UN) is None
        assert {fcntl.LOCK_EX, fcntl.LOCK_SH, fcntl.LOCK_UN, fcntl.LOCK_NB} == {2, 1, 8, 4}
    finally:
        sys.modules.pop("fcntl", None)


def test_stub_does_not_override_an_already_imported_fcntl(monkeypatch):
    monkeypatch.setattr(win_compat.os, "name", "nt")
    sentinel = object()
    sys.modules["fcntl"] = sentinel  # type: ignore[assignment]
    try:
        win_compat.install_fcntl_stub()
        assert sys.modules["fcntl"] is sentinel
    finally:
        sys.modules.pop("fcntl", None)
