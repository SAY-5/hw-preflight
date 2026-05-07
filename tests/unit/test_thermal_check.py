"""Unit tests for thermal_max."""

from __future__ import annotations

from hw_preflight.checks.thermal import thermal_max
from hw_preflight.config import PreflightConfig


def test_thermal_pass(fs) -> None:  # type: ignore[no-untyped-def]
    fs.create_file("/sys/class/thermal/thermal_zone0/temp", contents="42000\n")
    fs.create_file("/sys/class/thermal/thermal_zone1/temp", contents="55000\n")
    r = thermal_max(PreflightConfig())
    assert r.status == "pass"
    assert r.measured is not None
    assert r.measured["max_milli_celsius"] == 55000


def test_thermal_fail(fs) -> None:  # type: ignore[no-untyped-def]
    fs.create_file("/sys/class/thermal/thermal_zone0/temp", contents="95000\n")
    r = thermal_max(PreflightConfig())
    assert r.status == "fail"


def test_thermal_unavailable(fs) -> None:  # type: ignore[no-untyped-def]
    r = thermal_max(PreflightConfig())
    assert r.status == "unavailable"


def test_thermal_ignores_unparsable(fs) -> None:  # type: ignore[no-untyped-def]
    fs.create_file("/sys/class/thermal/thermal_zone0/temp", contents="garbage\n")
    fs.create_file("/sys/class/thermal/thermal_zone1/temp", contents="50000\n")
    r = thermal_max(PreflightConfig())
    assert r.status == "pass"
    assert r.measured is not None
    assert r.measured["max_milli_celsius"] == 50000
