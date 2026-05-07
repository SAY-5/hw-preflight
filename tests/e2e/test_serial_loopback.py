"""End-to-end test: socat-managed virtual tty pair + serial_handshake.

socat is invoked as

    socat -d -d pty,raw,echo=0 pty,raw,echo=0

which prints lines like ``N PTY is /dev/pts/12`` to stderr. We parse those
two paths, point ``HW_PREFLIGHT_SERIAL_PATH`` at one, and run a small
"device" thread on the other that echoes ``OK\\r\\n`` to whatever it
receives.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import threading
import time

import pytest
import serial  # type: ignore[import-untyped]

from hw_preflight.checks.serial import serial_handshake
from hw_preflight.config import PreflightConfig

pytestmark = pytest.mark.e2e

if shutil.which("socat") is None:  # pragma: no cover
    pytest.skip("socat not on PATH", allow_module_level=True)


_PTY_RE = re.compile(r"PTY is (\S+)")


def _start_socat() -> tuple[subprocess.Popen[bytes], str, str]:
    proc = subprocess.Popen(
        ["socat", "-d", "-d", "pty,raw,echo=0", "pty,raw,echo=0"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    paths: list[str] = []
    deadline = time.time() + 5.0
    assert proc.stderr is not None
    while time.time() < deadline and len(paths) < 2:
        line = proc.stderr.readline()
        if not line:
            time.sleep(0.05)
            continue
        m = _PTY_RE.search(line.decode(errors="replace"))
        if m:
            paths.append(m.group(1))
    if len(paths) < 2:
        proc.terminate()
        proc.wait(timeout=2.0)
        raise RuntimeError("socat did not announce two pty paths in 5s")
    # Wait briefly for the device files to settle.
    time.sleep(0.1)
    return proc, paths[0], paths[1]


def _device_thread(pty_path: str, stop_event: threading.Event) -> None:
    try:
        ser = serial.Serial(pty_path, baudrate=115200, timeout=0.2)
    except (OSError, serial.SerialException):  # pragma: no cover
        return
    try:
        while not stop_event.is_set():
            data = ser.read(64)
            if data:
                ser.write(b"OK\r\n")
                ser.flush()
    finally:
        ser.close()


def test_socat_loopback_handshake() -> None:
    proc, dev_path, host_path = _start_socat()
    stop = threading.Event()
    th = threading.Thread(target=_device_thread, args=(dev_path, stop), daemon=True)
    th.start()
    try:
        # Give the device thread a moment to open its end.
        time.sleep(0.2)
        os.environ["HW_PREFLIGHT_SERIAL_PATH"] = host_path
        try:
            cfg = PreflightConfig()
            cfg.serial.handshake_timeout_seconds = 1.0
            r = serial_handshake(cfg)
        finally:
            os.environ.pop("HW_PREFLIGHT_SERIAL_PATH", None)
        assert r.status == "pass", (r.status, r.reason, r.measured)
    finally:
        stop.set()
        proc.terminate()
        try:
            proc.wait(timeout=2.0)
        except subprocess.TimeoutExpired:  # pragma: no cover
            proc.kill()
        th.join(timeout=2.0)
