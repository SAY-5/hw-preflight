"""Tests for ``bench/run_suite_bench.py``: schema correctness and regress logic."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bench import run_suite_bench as bench


def test_bench_writes_expected_schema(tmp_path: Path) -> None:
    out = tmp_path / "result.json"
    rc = bench.main(["--repeats", "1", "--out", str(out)])
    assert rc == 0
    payload = json.loads(out.read_text())
    assert {
        "generated_at",
        "host",
        "repeats",
        "serial_seconds",
        "parallel_seconds",
        "summary",
    } <= set(payload.keys())
    assert payload["summary"]["serial_median"] >= 0.0
    assert payload["summary"]["parallel_median"] >= 0.0


def test_bench_regress_passes_when_no_baseline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(bench, "RESULTS_DIR", tmp_path / "empty")
    out = tmp_path / "result.json"
    rc = bench.main(["--repeats", "1", "--out", str(out), "--check-regress"])
    assert rc == 0


def test_bench_regress_fails_when_drift_too_high(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import platform as plat

    results = tmp_path / "results"
    results.mkdir()
    # Plant a synthetic prior baseline with a tiny serial median for the
    # current platform family.
    (results / "0001-01-01T00-00-00.json").write_text(
        json.dumps(
            {
                "generated_at": "0001-01-01T00:00:00+00:00",
                "host": {"platform": plat.platform()},
                "summary": {
                    "serial_median": 0.0001,
                    "parallel_median": 0.00005,
                },
            }
        )
    )
    monkeypatch.setattr(bench, "RESULTS_DIR", results)
    out = tmp_path / "current.json"
    # The fresh measurement on real registry will be way slower than 0.0001s,
    # so regression must trigger.
    rc = bench.main(
        [
            "--repeats",
            "1",
            "--out",
            str(out),
            "--check-regress",
            "--threshold",
            "0.10",
        ]
    )
    assert rc == 1


def test_bench_regress_passes_when_within_threshold(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If the prior baseline is much SLOWER than current, drift is negative
    and the gate must pass."""
    import platform as plat

    results = tmp_path / "results"
    results.mkdir()
    (results / "0001-01-01T00-00-00.json").write_text(
        json.dumps(
            {
                "generated_at": "0001-01-01T00:00:00+00:00",
                "host": {"platform": plat.platform()},
                "summary": {
                    "serial_median": 9999.0,
                    "parallel_median": 9000.0,
                },
            }
        )
    )
    monkeypatch.setattr(bench, "RESULTS_DIR", results)
    out = tmp_path / "current.json"
    rc = bench.main(["--repeats", "1", "--out", str(out), "--check-regress", "--threshold", "0.30"])
    assert rc == 0
