"""System-level checks: loadavg_short, kernel_version, kernel_module_loaded,
clock_source, time_sync."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

from hw_preflight.config import PreflightConfig

from ._base import CheckResult, make_result, register_check

_LOADAVG = "/proc/loadavg"
_MODULES = "/proc/modules"
_CLOCKSOURCE = "/sys/devices/system/clocksource/clocksource0/current_clocksource"


def _parse_semver(value: str) -> tuple[int, int, int] | None:
    """Parse a semver-ish string. Returns (major, minor, patch) or None."""
    m = re.match(r"^(\d+)\.(\d+)(?:\.(\d+))?", value)
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3) or 0))


@register_check("loadavg_short")
def loadavg_short(config: PreflightConfig) -> CheckResult:
    p = Path(_LOADAVG)
    if not p.exists():
        return make_result(
            "loadavg_short",
            "unavailable",
            reason="/proc/loadavg not present",
        )
    try:
        text = p.read_text(errors="replace").strip()
        one_min = float(text.split()[0])
    except (OSError, ValueError, IndexError) as exc:
        return make_result(
            "loadavg_short",
            "fail",
            reason=f"failed to parse /proc/loadavg: {exc}",
        )
    cpus = os.cpu_count() or 1
    threshold = cpus * config.system.loadavg_factor
    measured = {"loadavg_1min": one_min, "cpu_count": cpus}
    expected = {"max_loadavg_1min": threshold, "factor": config.system.loadavg_factor}
    if one_min < threshold:
        return make_result("loadavg_short", "pass", measured=measured, expected=expected)
    return make_result(
        "loadavg_short",
        "fail",
        measured=measured,
        expected=expected,
        reason=f"loadavg_1min={one_min} >= threshold={threshold}",
    )


@register_check("kernel_version")
def kernel_version(config: PreflightConfig) -> CheckResult:
    try:
        release = os.uname().release
    except (AttributeError, OSError) as exc:
        return make_result(
            "kernel_version",
            "unavailable",
            reason=f"os.uname() unavailable: {exc}",
        )
    parsed = _parse_semver(release)
    threshold_str = config.system.min_kernel_version
    threshold = _parse_semver(threshold_str)
    measured = {"release": release, "parsed": list(parsed) if parsed else None}
    expected = {"min_version": threshold_str}
    if parsed is None or threshold is None:
        return make_result(
            "kernel_version",
            "fail",
            measured=measured,
            expected=expected,
            reason=f"could not parse kernel version: release={release}, threshold={threshold_str}",
        )
    if parsed >= threshold:
        return make_result("kernel_version", "pass", measured=measured, expected=expected)
    return make_result(
        "kernel_version",
        "fail",
        measured=measured,
        expected=expected,
        reason=f"kernel {release} below threshold {threshold_str}",
    )


@register_check("kernel_module_loaded")
def kernel_module_loaded(config: PreflightConfig) -> CheckResult:
    required = config.system.required_modules
    expected = {"any_of": required}
    if not required:
        return make_result(
            "kernel_module_loaded",
            "skip",
            expected=expected,
            reason="no required modules configured",
        )
    p = Path(_MODULES)
    if not p.exists():
        return make_result(
            "kernel_module_loaded",
            "unavailable",
            expected=expected,
            reason="/proc/modules not present",
        )
    loaded: set[str] = set()
    for line in p.read_text(errors="replace").splitlines():
        first = line.split()
        if first:
            loaded.add(first[0])
    found = [m for m in required if m in loaded]
    measured = {"loaded_count": len(loaded), "found": found}
    if found:
        return make_result("kernel_module_loaded", "pass", measured=measured, expected=expected)
    return make_result(
        "kernel_module_loaded",
        "fail",
        measured=measured,
        expected=expected,
        reason=f"none of {required} loaded",
    )


@register_check("clock_source")
def clock_source(config: PreflightConfig) -> CheckResult:
    p = Path(_CLOCKSOURCE)
    expected = {"allowed": config.system.allowed_clocksources}
    if not p.exists():
        return make_result(
            "clock_source",
            "unavailable",
            expected=expected,
            reason=f"{_CLOCKSOURCE} not present",
        )
    try:
        current = p.read_text(errors="replace").strip()
    except OSError as exc:
        return make_result(
            "clock_source",
            "unavailable",
            expected=expected,
            reason=f"could not read clocksource: {exc}",
        )
    measured = {"current": current}
    if current in config.system.allowed_clocksources:
        return make_result("clock_source", "pass", measured=measured, expected=expected)
    return make_result(
        "clock_source",
        "fail",
        measured=measured,
        expected=expected,
        reason=f"clocksource '{current}' not in allowlist",
    )


@register_check("time_sync")
def time_sync(config: PreflightConfig) -> CheckResult:
    bin_path = shutil.which("timedatectl")
    if bin_path is None:
        return make_result(
            "time_sync",
            "unavailable",
            reason="timedatectl not on PATH",
        )
    try:
        result = subprocess.run(
            [bin_path, "show", "-p", "NTPSynchronized", "--value"],
            capture_output=True,
            text=True,
            timeout=3.0,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return make_result(
            "time_sync",
            "unavailable",
            reason=f"timedatectl invocation failed: {exc}",
        )
    if result.returncode != 0:
        return make_result(
            "time_sync",
            "unavailable",
            measured={"returncode": result.returncode, "stderr": result.stderr.strip()},
            reason=f"timedatectl exited with {result.returncode}",
        )
    value = result.stdout.strip().lower()
    measured = {"ntp_synchronized": value}
    expected = {"ntp_synchronized": "yes"}
    if value == "yes":
        return make_result("time_sync", "pass", measured=measured, expected=expected)
    return make_result(
        "time_sync",
        "fail",
        measured=measured,
        expected=expected,
        reason=f"NTPSynchronized={value!r}",
    )
