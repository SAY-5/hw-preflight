"""Disk free check."""

from __future__ import annotations

import os

from hw_preflight.config import PreflightConfig

from ._base import CheckResult, make_result, register_check


@register_check("disk_free")
def disk_free(config: PreflightConfig) -> CheckResult:
    path = config.disk.path
    threshold = config.disk.min_free_bytes
    try:
        st = os.statvfs(path)
    except OSError as exc:
        return make_result(
            "disk_free",
            "unavailable",
            expected={"path": path, "min_bytes": threshold},
            reason=f"statvfs({path}) failed: {exc}",
        )
    free = st.f_bavail * st.f_frsize
    measured = {"free_bytes": free, "path": path}
    expected = {"min_bytes": threshold}
    if free >= threshold:
        return make_result("disk_free", "pass", measured=measured, expected=expected)
    return make_result(
        "disk_free",
        "fail",
        measured=measured,
        expected=expected,
        reason=f"free={free} below threshold={threshold} on {path}",
    )
