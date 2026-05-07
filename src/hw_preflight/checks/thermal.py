"""Thermal zone check."""

from __future__ import annotations

from pathlib import Path

from hw_preflight.config import PreflightConfig

from ._base import CheckResult, make_result, register_check

_THERMAL_GLOB = "/sys/class/thermal"


def _read_zones(root: str = _THERMAL_GLOB) -> list[tuple[str, int]]:
    base = Path(root)
    if not base.exists():
        return []
    out: list[tuple[str, int]] = []
    for entry in sorted(base.iterdir()):
        if not entry.name.startswith("thermal_zone"):
            continue
        temp_file = entry / "temp"
        if not temp_file.exists():
            continue
        try:
            value = int(temp_file.read_text(errors="replace").strip())
        except (OSError, ValueError):
            continue
        out.append((entry.name, value))
    return out


@register_check("thermal_max")
def thermal_max(config: PreflightConfig) -> CheckResult:
    threshold = config.thermal.max_milli_celsius
    expected = {"max_milli_celsius": threshold}
    zones = _read_zones()
    if not zones:
        return make_result(
            "thermal_max",
            "unavailable",
            expected=expected,
            reason="no thermal zones in /sys/class/thermal",
        )
    name, top = max(zones, key=lambda x: x[1])
    measured = {
        "zones": [{"name": z[0], "milli_celsius": z[1]} for z in zones],
        "max_zone": name,
        "max_milli_celsius": top,
    }
    if top < threshold:
        return make_result("thermal_max", "pass", measured=measured, expected=expected)
    return make_result(
        "thermal_max",
        "fail",
        measured=measured,
        expected=expected,
        reason=f"zone {name} at {top} >= threshold {threshold}",
    )
