"""Unit tests for disk_free."""

from __future__ import annotations

import os
from typing import NamedTuple

import pytest

from hw_preflight.checks.disk import disk_free
from hw_preflight.config import PreflightConfig


class FakeStatvfs(NamedTuple):
    f_bavail: int
    f_frsize: int
    f_bfree: int = 0
    f_bsize: int = 0
    f_blocks: int = 0
    f_files: int = 0
    f_ffree: int = 0
    f_favail: int = 0
    f_flag: int = 0
    f_namemax: int = 0


def test_disk_free_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(os, "statvfs", lambda p: FakeStatvfs(f_bavail=10_000, f_frsize=4096))
    cfg = PreflightConfig()
    cfg.disk.min_free_bytes = 1_000_000
    r = disk_free(cfg)
    assert r.status == "pass"
    assert r.measured is not None
    assert r.measured["free_bytes"] == 40_960_000


def test_disk_free_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(os, "statvfs", lambda p: FakeStatvfs(f_bavail=10, f_frsize=4096))
    cfg = PreflightConfig()
    cfg.disk.min_free_bytes = 1_000_000
    r = disk_free(cfg)
    assert r.status == "fail"


def test_disk_free_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(_: str) -> FakeStatvfs:
        raise FileNotFoundError("no such path")

    monkeypatch.setattr(os, "statvfs", boom)
    cfg = PreflightConfig()
    cfg.disk.path = "/nonexistent/path"
    r = disk_free(cfg)
    assert r.status == "unavailable"
