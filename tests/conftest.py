"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from hw_preflight.config import PreflightConfig


@pytest.fixture
def default_config() -> PreflightConfig:
    return PreflightConfig()
