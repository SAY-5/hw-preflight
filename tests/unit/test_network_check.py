"""Unit tests for network_default_route."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from hw_preflight.checks import network as netmod
from hw_preflight.config import PreflightConfig


def _completed(stdout: str = "", returncode: int = 0, stderr: str = "") -> Any:
    return SimpleNamespace(stdout=stdout, returncode=returncode, stderr=stderr)


def test_no_ip_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(netmod.shutil, "which", lambda _: None)
    r = netmod.network_default_route(PreflightConfig())
    assert r.status == "unavailable"


def test_default_route_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(netmod.shutil, "which", lambda _: "/usr/sbin/ip")
    monkeypatch.setattr(
        netmod.subprocess,
        "run",
        lambda *a, **k: _completed("default via 10.0.0.1 dev eth0\n"),
    )
    r = netmod.network_default_route(PreflightConfig())
    assert r.status == "pass"


def test_default_route_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(netmod.shutil, "which", lambda _: "/usr/sbin/ip")
    monkeypatch.setattr(netmod.subprocess, "run", lambda *a, **k: _completed(""))
    r = netmod.network_default_route(PreflightConfig())
    assert r.status == "unavailable"


def test_ip_route_nonzero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(netmod.shutil, "which", lambda _: "/usr/sbin/ip")
    monkeypatch.setattr(netmod.subprocess, "run", lambda *a, **k: _completed("", 1, "boom"))
    r = netmod.network_default_route(PreflightConfig())
    assert r.status == "unavailable"
