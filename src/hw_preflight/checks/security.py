"""VM overcommit policy and SELinux mode checks."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from hw_preflight.config import PreflightConfig

from ._base import CheckResult, make_result, register_check

_OVERCOMMIT_PATH = "/proc/sys/vm/overcommit_memory"


@register_check("vm_overcommit")
def vm_overcommit(config: PreflightConfig) -> CheckResult:
    """Validate ``/proc/sys/vm/overcommit_memory`` against an allowlist.

    Defaults to ``[0, 1]`` — heuristic and always-overcommit. Mode ``2``
    (strict accounting) is intentionally omitted from the default
    allowlist because it's an outlier for general-purpose workloads.
    """
    allowed = list(config.vm_overcommit.allowed_values)
    expected = {"allowed_values": allowed}
    p = Path(_OVERCOMMIT_PATH)
    if not p.exists():
        return make_result(
            "vm_overcommit",
            "unavailable",
            expected=expected,
            reason=f"{_OVERCOMMIT_PATH} not present",
        )
    try:
        raw = p.read_text().strip()
        value = int(raw)
    except (OSError, ValueError) as exc:
        return make_result(
            "vm_overcommit",
            "unavailable",
            expected=expected,
            reason=f"could not parse overcommit_memory: {exc}",
        )
    measured = {"value": value}
    if value in allowed:
        return make_result("vm_overcommit", "pass", measured=measured, expected=expected)
    return make_result(
        "vm_overcommit",
        "fail",
        measured=measured,
        expected=expected,
        reason=f"overcommit_memory={value} not in allowlist {allowed}",
    )


@register_check("selinux_status")
def selinux_status(config: PreflightConfig) -> CheckResult:
    """Report SELinux mode if ``getenforce`` is present.

    Pass requires the reported mode to be ``Enforcing`` or ``Permissive``;
    ``Disabled`` is a fail. Hosts without ``getenforce`` (Ubuntu, Alpine,
    container runtimes) report ``unavailable``.
    """
    accepted = {"Enforcing", "Permissive"}
    expected = {"accepted_modes": sorted(accepted)}
    bin_path = shutil.which("getenforce")
    if bin_path is None:
        return make_result(
            "selinux_status",
            "unavailable",
            expected=expected,
            reason="getenforce not on PATH (SELinux userspace not installed)",
        )
    try:
        result = subprocess.run(
            [bin_path],
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return make_result(
            "selinux_status",
            "unavailable",
            expected=expected,
            reason=f"getenforce invocation failed: {exc}",
        )
    if result.returncode != 0:
        return make_result(
            "selinux_status",
            "unavailable",
            measured={"returncode": result.returncode, "stderr": result.stderr.strip()},
            expected=expected,
            reason=f"getenforce exited {result.returncode}",
        )
    mode = result.stdout.strip()
    measured = {"mode": mode}
    if mode in accepted:
        return make_result("selinux_status", "pass", measured=measured, expected=expected)
    return make_result(
        "selinux_status",
        "fail",
        measured=measured,
        expected=expected,
        reason=f"SELinux mode={mode!r}, expected one of {sorted(accepted)}",
    )


__all__ = ["selinux_status", "vm_overcommit"]
