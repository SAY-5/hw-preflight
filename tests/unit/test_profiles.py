"""Tests for the profile loader and bundled profile YAMLs."""

from __future__ import annotations

from pathlib import Path

import pytest

from hw_preflight import profiles
from hw_preflight.config import PreflightConfig


def test_list_profiles_includes_three_builtins() -> None:
    names = set(profiles.list_profiles())
    assert {"production-server", "edge-device", "ci-runner"} <= names


@pytest.mark.parametrize(
    "name",
    ["production-server", "edge-device", "ci-runner"],
)
def test_each_builtin_validates_as_preflight_config(name: str) -> None:
    cfg = profiles.load_profile(name)
    assert isinstance(cfg, PreflightConfig)
    # Each profile constrains the runner timeout to a sensible bound.
    assert 0 < cfg.runner.per_check_timeout_seconds <= 60


def test_resolve_profile_path_accepts_absolute_path(tmp_path: Path) -> None:
    custom = tmp_path / "custom.yaml"
    custom.write_text("cpu:\n  min_count: 1\n")
    resolved = profiles.resolve_profile_path(str(custom))
    assert resolved == custom.resolve()


def test_resolve_profile_path_unknown_raises() -> None:
    with pytest.raises(FileNotFoundError) as exc_info:
        profiles.resolve_profile_path("definitely-not-a-real-profile")
    msg = str(exc_info.value)
    assert "definitely-not-a-real-profile" in msg
    # Error message lists what was searched and what's available.
    assert "available:" in msg


def test_production_server_enables_strict_thresholds() -> None:
    cfg = profiles.load_profile("production-server")
    assert cfg.cpu.min_count >= 4
    assert cfg.memory.min_total_bytes >= 8 * 1024 * 1024 * 1024
    assert cfg.rtc.max_drift_seconds <= 1.0


def test_edge_device_enables_peripheral_checks() -> None:
    cfg = profiles.load_profile("edge-device")
    assert cfg.gpio.min_chips >= 1
    assert cfg.memory.require_swap_disabled is True
    assert cfg.runner.enabled_checks is not None
    assert "serial_handshake" in cfg.runner.enabled_checks
    assert "gpio_chips" in cfg.runner.enabled_checks


def test_ci_runner_disables_peripheral_checks() -> None:
    cfg = profiles.load_profile("ci-runner")
    assert cfg.runner.enabled_checks is not None
    # Peripheral and security checks are not in the enabled list.
    enabled = set(cfg.runner.enabled_checks)
    assert "serial_handshake" not in enabled
    assert "gpio_chips" not in enabled
    assert "selinux_status" not in enabled
