"""Unit tests for nvme_smart and usb_device_count."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from hw_preflight.checks import storage as smod
from hw_preflight.config import PreflightConfig


def test_parse_smart_critical_warning_decimal() -> None:
    sample = (
        "Smart Log for NVME device:nvme0n1 namespace-id:ffffffff\ncritical_warning : 0\nfoo : bar\n"
    )
    assert smod._parse_smart_critical_warning(sample) == 0


def test_parse_smart_critical_warning_hex() -> None:
    sample = "critical_warning : 0x02\n"
    assert smod._parse_smart_critical_warning(sample) == 2


def test_parse_smart_critical_warning_missing() -> None:
    assert smod._parse_smart_critical_warning("nothing here") is None


def test_parse_smart_critical_warning_unparseable() -> None:
    assert smod._parse_smart_critical_warning("critical_warning : nope\n") is None


def test_nvme_smart_no_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(smod.shutil, "which", lambda _: None)
    r = smod.nvme_smart(PreflightConfig())
    assert r.status == "unavailable"


def test_nvme_smart_no_devices(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(smod.shutil, "which", lambda _: "/usr/sbin/nvme")
    monkeypatch.setattr(smod.glob, "glob", lambda _: [])
    r = smod.nvme_smart(PreflightConfig())
    assert r.status == "unavailable"


def test_nvme_smart_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(smod.shutil, "which", lambda _: "/usr/sbin/nvme")
    monkeypatch.setattr(smod.glob, "glob", lambda _: ["/dev/nvme0n1"])

    class CompletedProc:
        returncode = 0
        stdout = "critical_warning : 0\ntemperature : 38\n"
        stderr = ""

    monkeypatch.setattr(smod.subprocess, "run", lambda *a, **k: CompletedProc())
    r = smod.nvme_smart(PreflightConfig())
    assert r.status == "pass"
    assert r.measured == {"device": "/dev/nvme0n1", "critical_warning": 0}


def test_nvme_smart_fail_warning_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(smod.shutil, "which", lambda _: "/usr/sbin/nvme")
    monkeypatch.setattr(smod.glob, "glob", lambda _: ["/dev/nvme0n1"])

    class CompletedProc:
        returncode = 0
        stdout = "critical_warning : 0x04\n"
        stderr = ""

    monkeypatch.setattr(smod.subprocess, "run", lambda *a, **k: CompletedProc())
    r = smod.nvme_smart(PreflightConfig())
    assert r.status == "fail"


def test_nvme_smart_returncode_nonzero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(smod.shutil, "which", lambda _: "/usr/sbin/nvme")
    monkeypatch.setattr(smod.glob, "glob", lambda _: ["/dev/nvme0n1"])

    class CompletedProc:
        returncode = 13
        stdout = ""
        stderr = "permission denied"

    monkeypatch.setattr(smod.subprocess, "run", lambda *a, **k: CompletedProc())
    r = smod.nvme_smart(PreflightConfig())
    assert r.status == "unavailable"


def test_nvme_smart_subprocess_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(smod.shutil, "which", lambda _: "/usr/sbin/nvme")
    monkeypatch.setattr(smod.glob, "glob", lambda _: ["/dev/nvme0n1"])

    def boom(*a: object, **k: object) -> object:
        raise subprocess.TimeoutExpired(cmd="nvme", timeout=3.0)

    monkeypatch.setattr(smod.subprocess, "run", boom)
    r = smod.nvme_smart(PreflightConfig())
    assert r.status == "unavailable"


def test_nvme_smart_unparseable_output(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(smod.shutil, "which", lambda _: "/usr/sbin/nvme")
    monkeypatch.setattr(smod.glob, "glob", lambda _: ["/dev/nvme0n1"])

    class CompletedProc:
        returncode = 0
        stdout = "no critical warning here\n"
        stderr = ""

    monkeypatch.setattr(smod.subprocess, "run", lambda *a, **k: CompletedProc())
    r = smod.nvme_smart(PreflightConfig())
    assert r.status == "unavailable"


def test_usb_device_count_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    real_exists = Path.exists

    def fake_exists(self: Path) -> bool:
        if str(self) == "/sys/bus/usb/devices":
            return False
        return real_exists(self)

    monkeypatch.setattr(Path, "exists", fake_exists)
    r = smod.usb_device_count(PreflightConfig())
    assert r.status == "unavailable"


def test_usb_device_count_pass(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake_root = tmp_path / "usb_devices"
    fake_root.mkdir()
    for n in ("usb1", "1-1", "1-1.1", "2-0:1.0"):
        (fake_root / n).mkdir()

    real_exists = Path.exists
    real_iterdir = Path.iterdir

    def fake_exists(self: Path) -> bool:
        if str(self) == "/sys/bus/usb/devices":
            return True
        return real_exists(self)

    def fake_iterdir(self: Path) -> object:
        if str(self) == "/sys/bus/usb/devices":
            return iter(fake_root.iterdir())
        return real_iterdir(self)

    monkeypatch.setattr(Path, "exists", fake_exists)
    monkeypatch.setattr(Path, "iterdir", fake_iterdir)
    r = smod.usb_device_count(PreflightConfig())
    assert r.status == "pass"
    assert r.measured is not None
    assert r.measured["count"] == 4
