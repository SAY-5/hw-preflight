"""Real-time clock drift check (rtc_drift).

Reads ``/sys/class/rtc/rtc0/since_epoch``, compares against
``time.time()``, and reports the absolute drift in seconds. Threshold is
configured via ``RtcConfig.max_drift_seconds`` (default 5).
"""

from __future__ import annotations

import time
from pathlib import Path

from hw_preflight.config import PreflightConfig

from ._base import CheckResult, make_result, register_check

_RTC_SINCE_EPOCH = "/sys/class/rtc/rtc0/since_epoch"


@register_check("rtc_drift")
def rtc_drift(config: PreflightConfig) -> CheckResult:
    threshold = config.rtc.max_drift_seconds
    expected = {"max_drift_seconds": threshold}
    p = Path(_RTC_SINCE_EPOCH)
    if not p.exists():
        return make_result(
            "rtc_drift",
            "unavailable",
            expected=expected,
            reason=f"{_RTC_SINCE_EPOCH} not present (no /dev/rtc0 on host)",
        )
    try:
        rtc_seconds = int(p.read_text().strip())
    except (OSError, ValueError) as exc:
        return make_result(
            "rtc_drift",
            "unavailable",
            expected=expected,
            reason=f"could not read RTC since_epoch: {exc}",
        )
    sys_seconds = time.time()
    drift = abs(sys_seconds - rtc_seconds)
    measured = {"rtc_seconds": rtc_seconds, "system_seconds": sys_seconds, "drift_seconds": drift}
    if drift <= threshold:
        return make_result("rtc_drift", "pass", measured=measured, expected=expected)
    return make_result(
        "rtc_drift",
        "fail",
        measured=measured,
        expected=expected,
        reason=f"drift={drift:.2f}s exceeds threshold={threshold}s",
    )


__all__ = ["rtc_drift"]
