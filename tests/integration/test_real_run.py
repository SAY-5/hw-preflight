"""Integration tests that exercise the live host.

Gated by ``RUN_INTEGRATION=1`` so they don't run in the default pytest path.
On Linux they read real /proc and /sys data. On macOS or other non-Linux
hosts the run produces an honest mix of pass/fail/unavailable depending on
which kernel surfaces are exposed.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from hw_preflight.config import PreflightConfig
from hw_preflight.runner import run_all

pytestmark = pytest.mark.integration

if os.environ.get("RUN_INTEGRATION") != "1":  # pragma: no cover
    pytest.skip("set RUN_INTEGRATION=1 to run", allow_module_level=True)


def test_real_run_emits_eighteen() -> None:
    cfg = PreflightConfig()
    report = run_all(cfg)
    assert report.summary["total"] == 18


def test_real_run_writes_artifact(tmp_path: Path) -> None:
    cfg = PreflightConfig()
    report = run_all(cfg)
    out = tmp_path / "real-run.json"
    out.write_text(json.dumps(report.to_dict(), indent=2))
    data = json.loads(out.read_text())
    # Every check must have a recognized status.
    valid = {"pass", "fail", "skip", "unavailable"}
    for c in data["checks"]:
        assert c["status"] in valid, c
