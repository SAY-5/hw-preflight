"""Serial-port checks: serial_port_present, serial_handshake.

The serial port path is resolved in this order:

1. ``HW_PREFLIGHT_SERIAL_PATH`` env var (used by CI to point at a socat-managed pty)
2. First match of ``config.serial.by_id_glob``
3. First file from ``config.serial.candidate_paths`` that exists

If no path resolves, both checks emit ``unavailable`` (not ``fail``), since
serial peripherals are optional on most CI runners.
"""

from __future__ import annotations

import glob
import os
import re
from collections.abc import Callable
from pathlib import Path

from hw_preflight.config import PreflightConfig

from ._base import CheckResult, make_result, register_check

ENV_PATH = "HW_PREFLIGHT_SERIAL_PATH"


def resolve_serial_path(config: PreflightConfig) -> str | None:
    env = os.environ.get(ENV_PATH, "").strip()
    if env and Path(env).exists():
        return env
    by_id = sorted(glob.glob(config.serial.by_id_glob))
    if by_id:
        return by_id[0]
    for cand in config.serial.candidate_paths:
        if Path(cand).exists():
            return cand
    return None


@register_check("serial_port_present")
def serial_port_present(config: PreflightConfig) -> CheckResult:
    expected = {
        "candidates": config.serial.candidate_paths,
        "by_id_glob": config.serial.by_id_glob,
        "env_override": ENV_PATH,
    }
    path = resolve_serial_path(config)
    if path is None:
        return make_result(
            "serial_port_present",
            "unavailable",
            expected=expected,
            reason="no serial port found via env, by-id glob, or candidate list",
        )
    return make_result(
        "serial_port_present",
        "pass",
        measured={"path": path},
        expected=expected,
    )


# Backend type: callable that returns (success, response_bytes, error_message).
SerialBackend = Callable[[str, int, bytes, float], tuple[bool, bytes, str | None]]


def _real_pyserial_backend(
    path: str, baud: int, payload: bytes, timeout: float
) -> tuple[bool, bytes, str | None]:
    """Open ``path`` with pyserial, write payload, read up to 64 bytes."""
    try:
        import serial
    except ImportError as exc:  # pragma: no cover - pyserial is a hard dep
        return False, b"", f"pyserial unavailable: {exc}"
    try:
        with serial.Serial(path, baudrate=baud, timeout=timeout) as ser:
            ser.write(payload)
            ser.flush()
            data = ser.read(64)
        return True, bytes(data), None
    except (OSError, serial.SerialException) as exc:
        return False, b"", f"serial error: {exc}"


@register_check("serial_handshake")
def serial_handshake(
    config: PreflightConfig,
    backend: SerialBackend | None = None,
) -> CheckResult:
    expected = {
        "send": config.serial.handshake_send,
        "response_regex": config.serial.handshake_response_regex,
        "baud": config.serial.baudrate,
        "timeout_seconds": config.serial.handshake_timeout_seconds,
    }
    path = resolve_serial_path(config)
    if path is None:
        return make_result(
            "serial_handshake",
            "unavailable",
            expected=expected,
            reason="no serial port resolved",
        )
    use_backend = backend or _real_pyserial_backend
    payload = config.serial.handshake_send.encode("utf-8")
    ok, data, err = use_backend(
        path, config.serial.baudrate, payload, config.serial.handshake_timeout_seconds
    )
    measured: dict[str, object] = {"path": path}
    if not ok:
        measured["error"] = err
        return make_result(
            "serial_handshake",
            "fail",
            measured=measured,
            expected=expected,
            reason=err or "serial backend reported failure",
        )
    text = data.decode("utf-8", errors="replace")
    measured["response_bytes"] = len(data)
    measured["response_preview"] = text[:32]
    if re.search(config.serial.handshake_response_regex, text):
        return make_result("serial_handshake", "pass", measured=measured, expected=expected)
    return make_result(
        "serial_handshake",
        "fail",
        measured=measured,
        expected=expected,
        reason=f"response {text!r} did not match regex",
    )
