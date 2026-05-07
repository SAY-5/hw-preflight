"""Unit tests for gpio_chips and i2c_bus_present."""

from __future__ import annotations

import glob

import pytest

from hw_preflight.checks import gpio as gpiomod
from hw_preflight.config import PreflightConfig


def test_gpio_unavailable_no_subsystem(fs) -> None:  # type: ignore[no-untyped-def]
    r = gpiomod.gpio_chips(PreflightConfig())
    assert r.status == "unavailable"


def test_gpio_pass(fs) -> None:  # type: ignore[no-untyped-def]
    fs.create_dir("/sys/class/gpio/gpiochip0")
    fs.create_dir("/sys/class/gpio/gpiochip1")
    cfg = PreflightConfig()
    cfg.gpio.min_chips = 2
    r = gpiomod.gpio_chips(cfg)
    assert r.status == "pass"


def test_gpio_fail_below_threshold(fs) -> None:  # type: ignore[no-untyped-def]
    fs.create_dir("/sys/class/gpio/gpiochip0")
    cfg = PreflightConfig()
    cfg.gpio.min_chips = 4
    r = gpiomod.gpio_chips(cfg)
    assert r.status == "fail"


def test_gpio_unavailable_when_threshold_zero_and_empty(fs) -> None:  # type: ignore[no-untyped-def]
    fs.create_dir("/sys/class/gpio")
    r = gpiomod.gpio_chips(PreflightConfig())
    assert r.status == "unavailable"


def test_i2c_unavailable_no_buses(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(glob, "glob", lambda _p: [])
    r = gpiomod.i2c_bus_present(PreflightConfig())
    assert r.status == "unavailable"


def test_i2c_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(glob, "glob", lambda _p: ["/dev/i2c-0", "/dev/i2c-1"])
    cfg = PreflightConfig()
    cfg.gpio.min_i2c_buses = 1
    r = gpiomod.i2c_bus_present(cfg)
    assert r.status == "pass"


def test_i2c_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(glob, "glob", lambda _p: ["/dev/i2c-0"])
    cfg = PreflightConfig()
    cfg.gpio.min_i2c_buses = 4
    r = gpiomod.i2c_bus_present(cfg)
    assert r.status == "fail"
