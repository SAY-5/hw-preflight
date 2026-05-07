"""Unit tests for service_unit_active."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from hw_preflight.checks import service as svcmod
from hw_preflight.config import PreflightConfig


def _completed(stdout: str = "", returncode: int = 0) -> Any:
    return SimpleNamespace(stdout=stdout, returncode=returncode, stderr="")


def test_skip_when_no_units() -> None:
    r = svcmod.service_unit_active(PreflightConfig())
    assert r.status == "skip"


def test_unavailable_when_no_systemctl(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = PreflightConfig()
    cfg.service.units = ["sshd"]
    monkeypatch.setattr(svcmod.shutil, "which", lambda _: None)
    r = svcmod.service_unit_active(cfg)
    assert r.status == "unavailable"


def test_all_active(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = PreflightConfig()
    cfg.service.units = ["sshd", "chronyd"]
    monkeypatch.setattr(svcmod.shutil, "which", lambda _: "/bin/systemctl")
    monkeypatch.setattr(svcmod.subprocess, "run", lambda *a, **k: _completed("active\n"))
    r = svcmod.service_unit_active(cfg)
    assert r.status == "pass"


def test_one_inactive(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = PreflightConfig()
    cfg.service.units = ["sshd", "ghost"]
    monkeypatch.setattr(svcmod.shutil, "which", lambda _: "/bin/systemctl")
    calls = iter([_completed("active\n"), _completed("inactive\n", 3)])
    monkeypatch.setattr(svcmod.subprocess, "run", lambda *a, **k: next(calls))
    r = svcmod.service_unit_active(cfg)
    assert r.status == "fail"
