"""Unit tests for vm_overcommit and selinux_status."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from hw_preflight.checks import security as smod
from hw_preflight.config import PreflightConfig

# --- vm_overcommit ---------------------------------------------------------


def _patch_overcommit(monkeypatch: pytest.MonkeyPatch, value: str | None) -> None:
    real_exists = Path.exists
    real_read = Path.read_text

    def fake_exists(self: Path) -> bool:
        if str(self) == smod._OVERCOMMIT_PATH:
            return value is not None
        return real_exists(self)

    def fake_read(self: Path, *a: object, **k: object) -> str:
        if str(self) == smod._OVERCOMMIT_PATH:
            assert value is not None
            return value
        return real_read(self, *a, **k)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "exists", fake_exists)
    monkeypatch.setattr(Path, "read_text", fake_read)


def test_vm_overcommit_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_overcommit(monkeypatch, "0\n")
    r = smod.vm_overcommit(PreflightConfig())
    assert r.status == "pass"


def test_vm_overcommit_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_overcommit(monkeypatch, "2\n")
    r = smod.vm_overcommit(PreflightConfig())
    assert r.status == "fail"


def test_vm_overcommit_unparseable(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_overcommit(monkeypatch, "garbage\n")
    r = smod.vm_overcommit(PreflightConfig())
    assert r.status == "unavailable"


def test_vm_overcommit_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_overcommit(monkeypatch, None)
    r = smod.vm_overcommit(PreflightConfig())
    assert r.status == "unavailable"


def test_vm_overcommit_custom_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_overcommit(monkeypatch, "2\n")
    cfg = PreflightConfig()
    cfg.vm_overcommit.allowed_values = [0, 1, 2]
    r = smod.vm_overcommit(cfg)
    assert r.status == "pass"


# --- selinux_status --------------------------------------------------------


def test_selinux_unavailable_when_no_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(smod.shutil, "which", lambda _: None)
    r = smod.selinux_status(PreflightConfig())
    assert r.status == "unavailable"


def test_selinux_pass_enforcing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(smod.shutil, "which", lambda _: "/usr/sbin/getenforce")

    class CompletedProc:
        returncode = 0
        stdout = "Enforcing\n"
        stderr = ""

    monkeypatch.setattr(smod.subprocess, "run", lambda *a, **k: CompletedProc())
    r = smod.selinux_status(PreflightConfig())
    assert r.status == "pass"


def test_selinux_pass_permissive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(smod.shutil, "which", lambda _: "/usr/sbin/getenforce")

    class CompletedProc:
        returncode = 0
        stdout = "Permissive\n"
        stderr = ""

    monkeypatch.setattr(smod.subprocess, "run", lambda *a, **k: CompletedProc())
    r = smod.selinux_status(PreflightConfig())
    assert r.status == "pass"


def test_selinux_fail_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(smod.shutil, "which", lambda _: "/usr/sbin/getenforce")

    class CompletedProc:
        returncode = 0
        stdout = "Disabled\n"
        stderr = ""

    monkeypatch.setattr(smod.subprocess, "run", lambda *a, **k: CompletedProc())
    r = smod.selinux_status(PreflightConfig())
    assert r.status == "fail"


def test_selinux_subprocess_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(smod.shutil, "which", lambda _: "/usr/sbin/getenforce")

    def boom(*a: object, **k: object) -> object:
        raise subprocess.TimeoutExpired(cmd="getenforce", timeout=2.0)

    monkeypatch.setattr(smod.subprocess, "run", boom)
    r = smod.selinux_status(PreflightConfig())
    assert r.status == "unavailable"


def test_selinux_returncode_nonzero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(smod.shutil, "which", lambda _: "/usr/sbin/getenforce")

    class CompletedProc:
        returncode = 1
        stdout = ""
        stderr = "no SELinux"

    monkeypatch.setattr(smod.subprocess, "run", lambda *a, **k: CompletedProc())
    r = smod.selinux_status(PreflightConfig())
    assert r.status == "unavailable"
