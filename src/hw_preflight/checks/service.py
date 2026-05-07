"""systemd service-unit liveness check."""

from __future__ import annotations

import shutil
import subprocess

from hw_preflight.config import PreflightConfig

from ._base import CheckResult, make_result, register_check


@register_check("service_unit_active")
def service_unit_active(config: PreflightConfig) -> CheckResult:
    units = config.service.units
    expected = {"units": units}
    if not units:
        return make_result(
            "service_unit_active",
            "skip",
            expected=expected,
            reason="no service units configured",
        )
    bin_path = shutil.which("systemctl")
    if bin_path is None:
        return make_result(
            "service_unit_active",
            "unavailable",
            expected=expected,
            reason="systemctl not on PATH",
        )
    inactive: list[dict[str, str]] = []
    states: list[dict[str, str]] = []
    for unit in units:
        try:
            result = subprocess.run(
                [bin_path, "is-active", unit],
                capture_output=True,
                text=True,
                timeout=3.0,
                check=False,
            )
        except (subprocess.TimeoutExpired, OSError) as exc:
            inactive.append({"unit": unit, "error": str(exc)})
            continue
        state = result.stdout.strip()
        states.append({"unit": unit, "state": state})
        if state != "active":
            inactive.append({"unit": unit, "state": state})
    measured = {"states": states}
    if inactive:
        return make_result(
            "service_unit_active",
            "fail",
            measured={**measured, "inactive": inactive},
            expected=expected,
            reason=f"{len(inactive)} of {len(units)} units not active",
        )
    return make_result("service_unit_active", "pass", measured=measured, expected=expected)
