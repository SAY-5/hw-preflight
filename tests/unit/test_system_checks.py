"""Unit tests for the system checks (loadavg, kernel, modules, clocksource, time_sync)."""

from __future__ import annotations

import os
import subprocess
from types import SimpleNamespace
from typing import Any

import pytest

from hw_preflight.checks import system as sysmod
from hw_preflight.config import PreflightConfig


def test_parse_semver_ok() -> None:
    assert sysmod._parse_semver("5.15.0-foo") == (5, 15, 0)
    assert sysmod._parse_semver("6.5") == (6, 5, 0)
    assert sysmod._parse_semver("garbage") is None


def test_loadavg_pass(fs) -> None:  # type: ignore[no-untyped-def]
    fs.create_file("/proc/loadavg", contents="0.10 0.20 0.30 1/200 12345\n")
    r = sysmod.loadavg_short(PreflightConfig())
    assert r.status == "pass"


def test_loadavg_fail(fs, monkeypatch: pytest.MonkeyPatch) -> None:  # type: ignore[no-untyped-def]
    fs.create_file("/proc/loadavg", contents="100.00 0.20 0.30 1/200 12345\n")
    monkeypatch.setattr(os, "cpu_count", lambda: 4)
    r = sysmod.loadavg_short(PreflightConfig())
    assert r.status == "fail"


def test_loadavg_unavailable(fs) -> None:  # type: ignore[no-untyped-def]
    r = sysmod.loadavg_short(PreflightConfig())
    assert r.status == "unavailable"


def test_loadavg_parse_error(fs) -> None:  # type: ignore[no-untyped-def]
    fs.create_file("/proc/loadavg", contents="garbage\n")
    r = sysmod.loadavg_short(PreflightConfig())
    assert r.status == "fail"


def test_kernel_version_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(os, "uname", lambda: SimpleNamespace(release="6.5.0-generic", nodename="x"))
    r = sysmod.kernel_version(PreflightConfig())
    assert r.status == "pass"


def test_kernel_version_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(os, "uname", lambda: SimpleNamespace(release="3.10.0", nodename="x"))
    r = sysmod.kernel_version(PreflightConfig())
    assert r.status == "fail"


def test_kernel_module_pass(fs) -> None:  # type: ignore[no-untyped-def]
    fs.create_file(
        "/proc/modules",
        contents="loop 28672 0 - Live 0x0\nfoo 4096 0 - Live 0x0\n",
    )
    r = sysmod.kernel_module_loaded(PreflightConfig())
    assert r.status == "pass"


def test_kernel_module_fail(fs) -> None:  # type: ignore[no-untyped-def]
    fs.create_file("/proc/modules", contents="foo 4096 0 - Live 0x0\n")
    r = sysmod.kernel_module_loaded(PreflightConfig())
    assert r.status == "fail"


def test_kernel_module_skip_when_empty_required() -> None:
    cfg = PreflightConfig()
    cfg.system.required_modules = []
    r = sysmod.kernel_module_loaded(cfg)
    assert r.status == "skip"


def test_kernel_module_unavailable(fs) -> None:  # type: ignore[no-untyped-def]
    r = sysmod.kernel_module_loaded(PreflightConfig())
    assert r.status == "unavailable"


def test_clock_source_pass(fs) -> None:  # type: ignore[no-untyped-def]
    fs.create_file(sysmod._CLOCKSOURCE, contents="tsc\n")
    r = sysmod.clock_source(PreflightConfig())
    assert r.status == "pass"


def test_clock_source_fail(fs) -> None:  # type: ignore[no-untyped-def]
    fs.create_file(sysmod._CLOCKSOURCE, contents="hpet\n")
    r = sysmod.clock_source(PreflightConfig())
    assert r.status == "fail"


def test_clock_source_unavailable(fs) -> None:  # type: ignore[no-untyped-def]
    r = sysmod.clock_source(PreflightConfig())
    assert r.status == "unavailable"


def _completed(stdout: str = "", returncode: int = 0, stderr: str = "") -> Any:
    return SimpleNamespace(stdout=stdout, returncode=returncode, stderr=stderr)


def test_time_sync_unavailable_when_no_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sysmod.shutil, "which", lambda _: None)
    r = sysmod.time_sync(PreflightConfig())
    assert r.status == "unavailable"


def test_time_sync_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sysmod.shutil, "which", lambda _: "/usr/bin/timedatectl")
    monkeypatch.setattr(sysmod.subprocess, "run", lambda *a, **k: _completed("yes\n"))
    r = sysmod.time_sync(PreflightConfig())
    assert r.status == "pass"


def test_time_sync_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sysmod.shutil, "which", lambda _: "/usr/bin/timedatectl")
    monkeypatch.setattr(sysmod.subprocess, "run", lambda *a, **k: _completed("no\n"))
    r = sysmod.time_sync(PreflightConfig())
    assert r.status == "fail"


def test_time_sync_unavailable_on_nonzero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sysmod.shutil, "which", lambda _: "/usr/bin/timedatectl")
    monkeypatch.setattr(sysmod.subprocess, "run", lambda *a, **k: _completed("", 1, "boom"))
    r = sysmod.time_sync(PreflightConfig())
    assert r.status == "unavailable"


def test_time_sync_unavailable_on_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sysmod.shutil, "which", lambda _: "/usr/bin/timedatectl")

    def boom(*a: Any, **k: Any) -> Any:
        raise subprocess.TimeoutExpired(cmd="timedatectl", timeout=1)

    monkeypatch.setattr(sysmod.subprocess, "run", boom)
    r = sysmod.time_sync(PreflightConfig())
    assert r.status == "unavailable"
