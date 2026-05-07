"""Tests for the runner: registration, timeouts, and aggregation."""

from __future__ import annotations

import time

from hw_preflight.checks._base import (
    CheckResult,
    all_checks,
    make_result,
)
from hw_preflight.config import PreflightConfig
from hw_preflight.runner import _run_one, run_all

# Eighteen checks must be registered when the package is imported.
EXPECTED_CHECKS = {
    "cpu_count",
    "cpu_features",
    "memory_total",
    "memory_available",
    "swap_disabled",
    "disk_free",
    "loadavg_short",
    "kernel_version",
    "kernel_module_loaded",
    "clock_source",
    "time_sync",
    "thermal_max",
    "serial_port_present",
    "serial_handshake",
    "network_default_route",
    "gpio_chips",
    "i2c_bus_present",
    "service_unit_active",
    # v3 additions (numbers 19-24).
    "nvme_smart",
    "usb_device_count",
    "rtc_drift",
    "pci_iommu_groups",
    "vm_overcommit",
    "selinux_status",
}


def test_twentyfour_checks_registered() -> None:
    names = set(all_checks().keys())
    assert names == EXPECTED_CHECKS
    assert len(names) == 24


def test_run_one_records_duration() -> None:
    def fast(_: PreflightConfig) -> CheckResult:
        return make_result("fast", "pass")

    out = _run_one("fast", fast, PreflightConfig(), timeout=2.0)
    assert out.status == "pass"
    assert out.duration_ms >= 0.0


def test_run_one_timeout() -> None:
    def slow(_: PreflightConfig) -> CheckResult:
        time.sleep(2.0)
        return make_result("slow", "pass")

    out = _run_one("slow", slow, PreflightConfig(), timeout=0.05)
    assert out.status == "fail"
    assert out.reason is not None and "timed out" in out.reason


def test_run_one_records_exception() -> None:
    def boom(_: PreflightConfig) -> CheckResult:
        raise RuntimeError("oops")

    out = _run_one("boom", boom, PreflightConfig(), timeout=2.0)
    assert out.status == "fail"
    assert out.reason is not None and "RuntimeError" in out.reason


def test_run_all_disabled_filter() -> None:
    cfg = PreflightConfig()
    cfg.runner.disabled_checks = ["serial_handshake", "serial_port_present"]
    cfg.runner.per_check_timeout_seconds = 5.0
    report = run_all(cfg)
    names = [c.name for c in report.checks]
    assert "serial_handshake" not in names
    assert "serial_port_present" not in names
    assert "cpu_count" in names


def test_run_all_emits_complete_summary() -> None:
    cfg = PreflightConfig()
    cfg.runner.enabled_checks = ["cpu_count", "memory_total"]
    report = run_all(cfg)
    assert {c.name for c in report.checks} == {"cpu_count", "memory_total"}
    summary = report.summary
    assert summary["total"] == 2
    assert sum(summary[k] for k in ("pass", "fail", "skip", "unavailable")) == 2
