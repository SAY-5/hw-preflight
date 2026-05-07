"""Targeted tests to lift coverage past 96%.

Each test maps to a specific previously-uncovered line range identified by
``pytest --cov-report=term-missing``.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from hw_preflight.checks import memory as mmod
from hw_preflight.checks import network as nmod
from hw_preflight.checks import serial as smod
from hw_preflight.checks import service as svcmod
from hw_preflight.checks import system as sysmod
from hw_preflight.checks import thermal as tmod
from hw_preflight.config import PreflightConfig

# ----- memory: bad meminfo lines (28-29, 78, 98) ------------------------------


def test_meminfo_skips_bad_lines(tmp_path: Path) -> None:
    p = tmp_path / "meminfo"
    p.write_text(
        "MemTotal: 8388608 kB\n"
        "Garbage:\n"
        "Weird: not-a-number kB\n"
        "MemAvailable: 1048576 kB\n"
        "SwapTotal: 0 kB\n"
    )
    info = mmod._read_meminfo(str(p))
    assert info["MemTotal"] == 8388608 * 1024
    assert "Garbage" not in info
    assert "Weird" not in info


def test_meminfo_missing_returns_empty(tmp_path: Path) -> None:
    info = mmod._read_meminfo(str(tmp_path / "no_such"))
    assert info == {}


def test_memory_total_fail_below_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        mmod, "_read_meminfo", lambda: {"MemTotal": 100, "MemAvailable": 50, "SwapTotal": 0}
    )
    cfg = PreflightConfig()
    cfg.memory.min_total_bytes = 10**12
    r = mmod.memory_total(cfg)
    assert r.status == "fail"


def test_memory_available_fail_below_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        mmod, "_read_meminfo", lambda: {"MemTotal": 10**12, "MemAvailable": 50, "SwapTotal": 0}
    )
    cfg = PreflightConfig()
    cfg.memory.min_available_bytes = 10**9
    r = mmod.memory_available(cfg)
    assert r.status == "fail"


def test_swap_disabled_unavailable_when_swaptotal_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(mmod, "_read_meminfo", lambda: {"MemTotal": 1, "MemAvailable": 1})
    cfg = PreflightConfig()
    cfg.memory.require_swap_disabled = True
    r = mmod.swap_disabled(cfg)
    assert r.status == "unavailable"


# ----- network: rejection of DNS without route (30-31) ------------------------


def test_network_default_route_when_subprocess_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import subprocess as sp

    monkeypatch.setattr(nmod.shutil, "which", lambda _: "/usr/bin/ip")

    def boom(*a: object, **kw: object) -> object:
        raise sp.TimeoutExpired(cmd="ip", timeout=3.0)

    monkeypatch.setattr(nmod.subprocess, "run", boom)
    r = nmod.network_default_route(PreflightConfig())
    assert r.status == "unavailable"


def test_network_default_route_no_ip_binary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(nmod.shutil, "which", lambda _: None)
    r = nmod.network_default_route(PreflightConfig())
    assert r.status == "unavailable"


# ----- serial: real-pyserial backend (77-88) ----------------------------------


def test_real_pyserial_backend_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Drive the production backend with an in-memory fake serial.Serial."""

    class FakeSerial:
        def __init__(self, path: str, baudrate: int = 0, timeout: float = 0.0) -> None:
            self.path = path
            self.baudrate = baudrate
            self.timeout = timeout
            self._sent = b""

        def __enter__(self) -> FakeSerial:
            return self

        def __exit__(self, *a: object) -> None:
            return None

        def write(self, data: bytes) -> int:
            self._sent = data
            return len(data)

        def flush(self) -> None:
            pass

        def read(self, n: int) -> bytes:
            return b"OK\r\n"

    fake_serial_mod = types.ModuleType("serial")

    class FakeSerialError(Exception):
        pass

    fake_serial_mod.Serial = FakeSerial  # type: ignore[attr-defined]
    fake_serial_mod.SerialException = FakeSerialError  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "serial", fake_serial_mod)

    ok, data, err = smod._real_pyserial_backend("/dev/null", 115200, b"AT\r\n", 0.1)
    assert ok is True
    assert data == b"OK\r\n"
    assert err is None


def test_real_pyserial_backend_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeSerialError(Exception):
        pass

    class BoomSerial:
        def __init__(self, *a: object, **kw: object) -> None:
            raise FakeSerialError("device disappeared")

    fake_serial_mod = types.ModuleType("serial")
    fake_serial_mod.Serial = BoomSerial  # type: ignore[attr-defined]
    fake_serial_mod.SerialException = FakeSerialError  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "serial", fake_serial_mod)

    ok, data, err = smod._real_pyserial_backend("/dev/null", 115200, b"AT", 0.1)
    assert ok is False
    assert data == b""
    assert err is not None
    assert "device disappeared" in err


def test_is_permission_error_handles_none() -> None:
    assert smod._is_permission_error(None) is False
    assert smod._is_permission_error("") is False
    assert smod._is_permission_error("Permission denied: /dev/ttyS0") is True
    assert smod._is_permission_error("Errno 13") is True


def test_resolve_serial_path_by_id_glob(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(smod.ENV_PATH, raising=False)
    fake = tmp_path / "tty-by-id-x"
    fake.write_text("")
    cfg = PreflightConfig()
    cfg.serial.by_id_glob = str(tmp_path / "tty-by-id-*")
    cfg.serial.candidate_paths = []
    assert smod.resolve_serial_path(cfg) == str(fake)


def test_resolve_serial_path_candidate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(smod.ENV_PATH, raising=False)
    fake = tmp_path / "tty-cand"
    fake.write_text("")
    cfg = PreflightConfig()
    cfg.serial.by_id_glob = "/no/such/glob/*"
    cfg.serial.candidate_paths = ["/no/such/path", str(fake)]
    assert smod.resolve_serial_path(cfg) == str(fake)


# ----- service: subprocess unavailable (43-45) --------------------------------


def test_service_check_no_systemctl(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(svcmod.shutil, "which", lambda _: None)
    cfg = PreflightConfig()
    cfg.service.units = ["nginx.service"]
    r = svcmod.service_unit_active(cfg)
    assert r.status == "unavailable"


def test_service_check_subprocess_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    import subprocess as sp

    monkeypatch.setattr(svcmod.shutil, "which", lambda _: "/usr/bin/systemctl")

    def boom(*a: object, **kw: object) -> object:
        raise sp.TimeoutExpired(cmd="systemctl", timeout=3.0)

    monkeypatch.setattr(svcmod.subprocess, "run", boom)
    cfg = PreflightConfig()
    cfg.service.units = ["nginx.service"]
    r = svcmod.service_unit_active(cfg)
    # All units fall into the inactive list; status is "fail".
    assert r.status == "fail"


# ----- system: kernel parse failure / module miss (66-67, 78, 146-147) --------


def test_kernel_version_unparseable(monkeypatch: pytest.MonkeyPatch) -> None:
    real_uname = sysmod.os.uname

    class FakeUname:
        def __init__(self, release: str) -> None:
            self.release = release
            self.nodename = "h"
            self.sysname = "Linux"
            self.version = ""
            self.machine = "x86_64"

    monkeypatch.setattr(sysmod.os, "uname", lambda: FakeUname("nonsense-no-numbers"))
    try:
        cfg = PreflightConfig()
        r = sysmod.kernel_version(cfg)
        assert r.status in ("fail", "unavailable")
    finally:
        monkeypatch.setattr(sysmod.os, "uname", real_uname)


def test_clock_source_unavailable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    real_exists = Path.exists

    def fake_exists(self: Path) -> bool:
        if "clocksource" in str(self):
            return False
        return real_exists(self)

    monkeypatch.setattr(Path, "exists", fake_exists)
    cfg = PreflightConfig()
    r = sysmod.clock_source(cfg)
    assert r.status == "unavailable"


# ----- thermal: degenerate (21, 24) -------------------------------------------


def test_thermal_no_zones(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tmod, "THERMAL_ROOT", str(tmp_path), raising=False)
    real_iterdir = Path.iterdir

    def fake_iterdir(self: Path) -> object:
        if str(self).endswith("thermal"):
            return iter([])
        return real_iterdir(self)

    # We exercise the no-zone path by pointing at an empty dir.
    real_exists = Path.exists

    def fake_exists(self: Path) -> bool:
        if str(self) == "/sys/class/thermal":
            return True
        return real_exists(self)

    monkeypatch.setattr(Path, "exists", fake_exists)
    monkeypatch.setattr(Path, "iterdir", fake_iterdir)
    cfg = PreflightConfig()
    r = tmod.thermal_max(cfg)
    assert r.status in ("unavailable", "skip", "pass")


# ----- reports: edge case (line 30) -------------------------------------------


def test_reports_truncates_long_measured() -> None:
    from datetime import UTC, datetime

    from hw_preflight.checks._base import CheckResult
    from hw_preflight.reports import _truncate, to_json, to_markdown
    from hw_preflight.runner import HostInfo, RunReport

    long_dict = {"k": "a" * 200}
    s = _truncate(long_dict, length=20)
    assert len(s) == 20
    assert s.endswith("...")

    now = datetime.now(UTC).isoformat()
    rpt = RunReport(
        started_at=now,
        finished_at=now,
        host=HostInfo(hostname="h", kernel="k", cpu_count=0),
        checks=[
            CheckResult(
                name="t",
                status="pass",
                measured=long_dict,
            ),
        ],
    )
    md = to_markdown(rpt)
    assert "..." in md
    assert "summary" in to_json(rpt)
