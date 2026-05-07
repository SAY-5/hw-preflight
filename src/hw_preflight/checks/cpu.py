"""CPU checks: cpu_count, cpu_features."""

from __future__ import annotations

import os

from hw_preflight import _hwprobe
from hw_preflight.config import PreflightConfig

from ._base import CheckResult, make_result, register_check


@register_check("cpu_count")
def cpu_count(config: PreflightConfig) -> CheckResult:
    threshold = config.cpu.min_count
    n = os.cpu_count() or 0
    if n >= threshold:
        return make_result(
            "cpu_count",
            "pass",
            measured={"cpu_count": n},
            expected={"min_count": threshold},
        )
    return make_result(
        "cpu_count",
        "fail",
        measured={"cpu_count": n},
        expected={"min_count": threshold},
        reason=f"cpu_count={n} below threshold={threshold}",
    )


@register_check("cpu_features")
def cpu_features(config: PreflightConfig) -> CheckResult:
    required = [f.lower() for f in config.cpu.required_features]
    if not required:
        return make_result(
            "cpu_features",
            "skip",
            expected={"required": []},
            reason="no required features configured",
        )
    have = {f.lower() for f in _hwprobe.cpu_features()}
    missing = [f for f in required if f not in have]
    measured = {
        "feature_count": len(have),
        "extension_available": _hwprobe.extension_available(),
    }
    if not have:
        return make_result(
            "cpu_features",
            "unavailable",
            measured=measured,
            expected={"required": required},
            reason="no CPU feature flags readable (non-Linux host or unsupported arch)",
        )
    if missing:
        return make_result(
            "cpu_features",
            "fail",
            measured={**measured, "missing": missing},
            expected={"required": required},
            reason=f"missing required features: {missing}",
        )
    return make_result(
        "cpu_features",
        "pass",
        measured=measured,
        expected={"required": required},
    )
