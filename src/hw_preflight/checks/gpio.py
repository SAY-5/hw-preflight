"""GPIO and I2C bus presence checks."""

from __future__ import annotations

import glob
from pathlib import Path

from hw_preflight.config import PreflightConfig

from ._base import CheckResult, make_result, register_check

_GPIO_ROOT = "/sys/class/gpio"
_I2C_GLOB = "/dev/i2c-*"


@register_check("gpio_chips")
def gpio_chips(config: PreflightConfig) -> CheckResult:
    threshold = config.gpio.min_chips
    expected = {"min_chips": threshold}
    base = Path(_GPIO_ROOT)
    if not base.exists():
        if threshold == 0:
            return make_result(
                "gpio_chips",
                "unavailable",
                expected=expected,
                reason="/sys/class/gpio not present (no GPIO subsystem on host)",
            )
        return make_result(
            "gpio_chips",
            "fail",
            expected=expected,
            reason="/sys/class/gpio not present",
        )
    chips = [p.name for p in base.iterdir() if p.name.startswith("gpiochip")]
    measured = {"chip_count": len(chips), "chips": chips}
    if threshold == 0 and len(chips) == 0:
        return make_result(
            "gpio_chips",
            "unavailable",
            measured=measured,
            expected=expected,
            reason="no gpiochips exposed",
        )
    if len(chips) >= threshold:
        return make_result("gpio_chips", "pass", measured=measured, expected=expected)
    return make_result(
        "gpio_chips",
        "fail",
        measured=measured,
        expected=expected,
        reason=f"chip_count={len(chips)} below threshold={threshold}",
    )


@register_check("i2c_bus_present")
def i2c_bus_present(config: PreflightConfig) -> CheckResult:
    threshold = config.gpio.min_i2c_buses
    expected = {"min_buses": threshold}
    buses = sorted(glob.glob(_I2C_GLOB))
    measured = {"bus_count": len(buses), "buses": buses}
    if threshold == 0 and len(buses) == 0:
        return make_result(
            "i2c_bus_present",
            "unavailable",
            measured=measured,
            expected=expected,
            reason="no /dev/i2c-* nodes (no I2C buses on host)",
        )
    if len(buses) >= threshold:
        return make_result("i2c_bus_present", "pass", measured=measured, expected=expected)
    return make_result(
        "i2c_bus_present",
        "fail",
        measured=measured,
        expected=expected,
        reason=f"bus_count={len(buses)} below threshold={threshold}",
    )
