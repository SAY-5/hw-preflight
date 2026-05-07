"""Unit tests for serial_port_present and serial_handshake."""

from __future__ import annotations

from pathlib import Path

import pytest

from hw_preflight.checks import serial as smod
from hw_preflight.config import PreflightConfig


def test_resolve_env_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = tmp_path / "ttyfake"
    fake.write_text("")
    monkeypatch.setenv(smod.ENV_PATH, str(fake))
    cfg = PreflightConfig()
    assert smod.resolve_serial_path(cfg) == str(fake)


def test_resolve_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(smod.ENV_PATH, raising=False)
    cfg = PreflightConfig()
    cfg.serial.candidate_paths = ["/no/such/path/abc", "/no/such/path/def"]
    cfg.serial.by_id_glob = "/no/such/glob/*"
    assert smod.resolve_serial_path(cfg) is None


def test_serial_port_present_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(smod.ENV_PATH, raising=False)
    cfg = PreflightConfig()
    cfg.serial.candidate_paths = ["/no/such/path"]
    cfg.serial.by_id_glob = "/no/such/glob/*"
    r = smod.serial_port_present(cfg)
    assert r.status == "unavailable"


def test_serial_port_present_pass(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = tmp_path / "tty"
    fake.write_text("")
    monkeypatch.setenv(smod.ENV_PATH, str(fake))
    r = smod.serial_port_present(PreflightConfig())
    assert r.status == "pass"
    assert r.measured == {"path": str(fake)}


def test_serial_handshake_pass(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = tmp_path / "tty"
    fake.write_text("")
    monkeypatch.setenv(smod.ENV_PATH, str(fake))

    def stub(path: str, baud: int, payload: bytes, timeout: float):
        assert path == str(fake)
        assert payload == b"AT\r\n"
        return True, b"OK\r\n", None

    r = smod.serial_handshake(PreflightConfig(), backend=stub)
    assert r.status == "pass"


def test_serial_handshake_fail_regex(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = tmp_path / "tty"
    fake.write_text("")
    monkeypatch.setenv(smod.ENV_PATH, str(fake))

    def stub(path: str, baud: int, payload: bytes, timeout: float):
        return True, b"ERROR\r\n", None

    r = smod.serial_handshake(PreflightConfig(), backend=stub)
    assert r.status == "fail"


def test_serial_handshake_unavailable_on_eacces(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """EACCES on a real device path is reported as unavailable, not fail.

    Many CI runners expose /dev/ttyS0 but disallow open() unless the
    process is in the dialout group. That's a measurement problem, not
    a hardware failure.
    """
    fake = tmp_path / "tty"
    fake.write_text("")
    monkeypatch.setenv(smod.ENV_PATH, str(fake))

    def stub(path: str, baud: int, payload: bytes, timeout: float):
        return False, b"", "serial error: [Errno 13] Permission denied: '/dev/ttyS0'"

    r = smod.serial_handshake(PreflightConfig(), backend=stub)
    assert r.status == "unavailable"


def test_serial_handshake_fail_io(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = tmp_path / "tty"
    fake.write_text("")
    monkeypatch.setenv(smod.ENV_PATH, str(fake))

    def stub(path: str, baud: int, payload: bytes, timeout: float):
        return False, b"", "serial error: device disappeared mid-read"

    r = smod.serial_handshake(PreflightConfig(), backend=stub)
    assert r.status == "fail"


def test_serial_handshake_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(smod.ENV_PATH, raising=False)
    cfg = PreflightConfig()
    cfg.serial.candidate_paths = []
    cfg.serial.by_id_glob = "/no/such/*"
    r = smod.serial_handshake(cfg)
    assert r.status == "unavailable"
