"""Memory checks: memory_total, memory_available, swap_disabled."""

from __future__ import annotations

from pathlib import Path

from hw_preflight.config import PreflightConfig

from ._base import CheckResult, make_result, register_check

_MEMINFO = "/proc/meminfo"


def _read_meminfo(path: str = _MEMINFO) -> dict[str, int]:
    """Return /proc/meminfo as a dict of key -> bytes (kB lines converted)."""
    p = Path(path)
    if not p.exists():
        return {}
    out: dict[str, int] = {}
    for line in p.read_text(errors="replace").splitlines():
        key, _, rest = line.partition(":")
        rest = rest.strip()
        if not rest:
            continue
        parts = rest.split()
        try:
            value = int(parts[0])
        except (ValueError, IndexError):
            continue
        unit = parts[1].lower() if len(parts) > 1 else ""
        if unit == "kb":
            value *= 1024
        out[key.strip()] = value
    return out


@register_check("memory_total")
def memory_total(config: PreflightConfig) -> CheckResult:
    info = _read_meminfo()
    if "MemTotal" not in info:
        return make_result(
            "memory_total",
            "unavailable",
            expected={"min_bytes": config.memory.min_total_bytes},
            reason="/proc/meminfo missing MemTotal",
        )
    total = info["MemTotal"]
    threshold = config.memory.min_total_bytes
    measured = {"bytes": total}
    expected = {"min_bytes": threshold}
    if total >= threshold:
        return make_result("memory_total", "pass", measured=measured, expected=expected)
    return make_result(
        "memory_total",
        "fail",
        measured=measured,
        expected=expected,
        reason=f"MemTotal={total} below threshold={threshold}",
    )


@register_check("memory_available")
def memory_available(config: PreflightConfig) -> CheckResult:
    info = _read_meminfo()
    if "MemAvailable" not in info:
        return make_result(
            "memory_available",
            "unavailable",
            expected={"min_bytes": config.memory.min_available_bytes},
            reason="/proc/meminfo missing MemAvailable",
        )
    avail = info["MemAvailable"]
    threshold = config.memory.min_available_bytes
    measured = {"bytes": avail}
    expected = {"min_bytes": threshold}
    if avail >= threshold:
        return make_result("memory_available", "pass", measured=measured, expected=expected)
    return make_result(
        "memory_available",
        "fail",
        measured=measured,
        expected=expected,
        reason=f"MemAvailable={avail} below threshold={threshold}",
    )


@register_check("swap_disabled")
def swap_disabled(config: PreflightConfig) -> CheckResult:
    if not config.memory.require_swap_disabled:
        return make_result(
            "swap_disabled",
            "skip",
            expected={"require_swap_disabled": False},
            reason="swap-disabled requirement not enforced by config",
        )
    info = _read_meminfo()
    if "SwapTotal" not in info:
        return make_result(
            "swap_disabled",
            "unavailable",
            reason="/proc/meminfo missing SwapTotal",
        )
    total = info["SwapTotal"]
    measured = {"swap_total_bytes": total}
    expected = {"swap_total_bytes": 0}
    if total == 0:
        return make_result("swap_disabled", "pass", measured=measured, expected=expected)
    return make_result(
        "swap_disabled",
        "fail",
        measured=measured,
        expected=expected,
        reason=f"SwapTotal={total}, expected 0",
    )
