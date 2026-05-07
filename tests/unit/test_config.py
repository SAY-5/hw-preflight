"""Tests for config loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from hw_preflight.config import PreflightConfig, load_config


def test_default_config() -> None:
    c = load_config(None)
    assert isinstance(c, PreflightConfig)
    assert c.cpu.min_count == 2


def test_load_yaml(tmp_path: Path) -> None:
    p = tmp_path / "p.yaml"
    p.write_text(
        "cpu:\n  min_count: 8\nmemory:\n  min_total_bytes: 4096\n"
        "runner:\n  disabled_checks: [time_sync]\n"
    )
    c = load_config(p)
    assert c.cpu.min_count == 8
    assert c.memory.min_total_bytes == 4096
    assert c.runner.disabled_checks == ["time_sync"]


def test_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "nope.yaml")


def test_empty_yaml_uses_defaults(tmp_path: Path) -> None:
    p = tmp_path / "empty.yaml"
    p.write_text("")
    c = load_config(p)
    assert c.cpu.min_count == 2
