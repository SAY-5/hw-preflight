"""Network default-route check."""

from __future__ import annotations

import shutil
import subprocess

from hw_preflight.config import PreflightConfig

from ._base import CheckResult, make_result, register_check


@register_check("network_default_route")
def network_default_route(config: PreflightConfig) -> CheckResult:
    bin_path = shutil.which("ip")
    if bin_path is None:
        return make_result(
            "network_default_route",
            "unavailable",
            reason="ip(8) not on PATH",
        )
    try:
        result = subprocess.run(
            [bin_path, "route", "show", "default"],
            capture_output=True,
            text=True,
            timeout=3.0,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return make_result(
            "network_default_route",
            "unavailable",
            reason=f"ip route invocation failed: {exc}",
        )
    if result.returncode != 0:
        return make_result(
            "network_default_route",
            "unavailable",
            measured={"returncode": result.returncode, "stderr": result.stderr.strip()},
            reason=f"ip route exited {result.returncode}",
        )
    routes = [ln for ln in result.stdout.splitlines() if ln.strip()]
    measured = {"routes": routes}
    if routes:
        return make_result("network_default_route", "pass", measured=measured)
    return make_result(
        "network_default_route",
        "unavailable",
        measured=measured,
        reason="no default route present (isolated network)",
    )
