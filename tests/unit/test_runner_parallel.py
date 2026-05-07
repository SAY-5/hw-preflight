"""Tests for runner parallelism.

* parallel results are deterministic (sorted by check name) regardless of
  schedule;
* parallel runs produce the same status set as serial runs for a given
  fixed registry;
* a single slow check does not delay the whole suite proportionally;
* the configured worker count is respected, capped at ``len(checks)``.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

import pytest

from hw_preflight.checks._base import (
    _REGISTRY,
    CheckResult,
    make_result,
)
from hw_preflight.config import PreflightConfig
from hw_preflight.runner import _resolve_parallelism, run_all


@pytest.fixture
def isolated_registry() -> object:
    saved = dict(_REGISTRY)
    _REGISTRY.clear()
    try:
        yield _REGISTRY
    finally:
        _REGISTRY.clear()
        _REGISTRY.update(saved)


def _slow_check(name: str, delay: float, status: str = "pass") -> Callable[..., CheckResult]:
    def fn(_: PreflightConfig) -> CheckResult:
        time.sleep(delay)
        return make_result(name, status)  # type: ignore[arg-type]

    fn.__check_name__ = name  # type: ignore[attr-defined]
    return fn


def test_resolve_parallelism_zero_means_cpu_count(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = PreflightConfig()
    cfg.runner.parallelism = 0
    monkeypatch.setattr("os.cpu_count", lambda: 8)
    assert _resolve_parallelism(cfg) == 8


def test_resolve_parallelism_negative_means_cpu_count(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = PreflightConfig()
    cfg.runner.parallelism = -42
    monkeypatch.setattr("os.cpu_count", lambda: 4)
    assert _resolve_parallelism(cfg) == 4


def test_resolve_parallelism_explicit_value() -> None:
    cfg = PreflightConfig()
    cfg.runner.parallelism = 3
    assert _resolve_parallelism(cfg) == 3


def test_resolve_parallelism_zero_with_no_cpu(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = PreflightConfig()
    cfg.runner.parallelism = 0
    monkeypatch.setattr("os.cpu_count", lambda: None)
    assert _resolve_parallelism(cfg) == 1


def test_parallel_results_are_sorted(
    isolated_registry: dict[str, Callable[..., CheckResult]],
) -> None:
    for n in ("z_last", "a_first", "m_middle", "b_second"):
        isolated_registry[n] = _slow_check(n, 0.0)
    cfg = PreflightConfig()
    cfg.runner.parallelism = 4
    report = run_all(cfg)
    names = [c.name for c in report.checks]
    assert names == sorted(names)
    assert names == ["a_first", "b_second", "m_middle", "z_last"]


def test_parallel_and_serial_emit_identical_results(
    isolated_registry: dict[str, Callable[..., CheckResult]],
) -> None:
    statuses = ["pass", "fail", "skip", "unavailable", "pass", "skip"]
    for i, st_ in enumerate(statuses):
        n = f"chk_{i:02d}"
        isolated_registry[n] = _slow_check(n, 0.005, status=st_)

    cfg_serial = PreflightConfig()
    cfg_serial.runner.parallelism = 1
    cfg_serial.runner.per_check_timeout_seconds = 5.0

    cfg_parallel = PreflightConfig()
    cfg_parallel.runner.parallelism = 4
    cfg_parallel.runner.per_check_timeout_seconds = 5.0

    serial = run_all(cfg_serial)
    parallel = run_all(cfg_parallel)

    serial_view = [(c.name, c.status) for c in serial.checks]
    parallel_view = [(c.name, c.status) for c in parallel.checks]
    assert serial_view == parallel_view


def test_parallel_provides_speedup(
    isolated_registry: dict[str, Callable[..., CheckResult]],
) -> None:
    """Eight 50ms checks run in <300ms with 8 workers (vs ~400ms serial).

    Loose bound to keep CI stable: parallel must beat serial by at least 1.5x.
    """
    n_checks = 8
    delay = 0.05
    for i in range(n_checks):
        n = f"slow_{i:02d}"
        isolated_registry[n] = _slow_check(n, delay)

    cfg_serial = PreflightConfig()
    cfg_serial.runner.parallelism = 1
    cfg_parallel = PreflightConfig()
    cfg_parallel.runner.parallelism = n_checks

    t0 = time.perf_counter()
    run_all(cfg_serial)
    t_serial = time.perf_counter() - t0

    t0 = time.perf_counter()
    run_all(cfg_parallel)
    t_parallel = time.perf_counter() - t0

    # Serial should be at least 1.5x slower; the actual ratio on a quiet
    # CPU is ~7-8x, but we leave generous headroom for CI noise.
    assert t_parallel * 1.5 < t_serial, (
        f"expected parallel speedup >= 1.5x; " f"serial={t_serial:.3f}s parallel={t_parallel:.3f}s"
    )


def test_parallel_uses_multiple_threads(
    isolated_registry: dict[str, Callable[..., CheckResult]],
) -> None:
    """A barrier across N checks succeeds only if N workers ran concurrently."""
    n = 4
    barrier = threading.Barrier(n, timeout=2.0)

    def make(name: str) -> Callable[..., CheckResult]:
        def fn(_: PreflightConfig) -> CheckResult:
            barrier.wait()
            return make_result(name, "pass")

        fn.__check_name__ = name  # type: ignore[attr-defined]
        return fn

    for i in range(n):
        isolated_registry[f"barrier_{i:02d}"] = make(f"barrier_{i:02d}")

    cfg = PreflightConfig()
    cfg.runner.parallelism = n
    report = run_all(cfg)
    assert all(c.status == "pass" for c in report.checks)


def test_single_check_uses_serial_path(
    isolated_registry: dict[str, Callable[..., CheckResult]],
) -> None:
    """If only one check is selected, the runner skips the thread pool."""
    isolated_registry["only_one"] = _slow_check("only_one", 0.0)
    cfg = PreflightConfig()
    cfg.runner.parallelism = 8
    report = run_all(cfg)
    assert {c.name for c in report.checks} == {"only_one"}


def test_parallel_preserves_disabled_filter(
    isolated_registry: dict[str, Callable[..., CheckResult]],
) -> None:
    for i in range(6):
        n = f"chk_{i:02d}"
        isolated_registry[n] = _slow_check(n, 0.0)
    cfg = PreflightConfig()
    cfg.runner.parallelism = 4
    cfg.runner.disabled_checks = ["chk_01", "chk_03"]
    report = run_all(cfg)
    names = {c.name for c in report.checks}
    assert "chk_01" not in names
    assert "chk_03" not in names
    assert names == {"chk_00", "chk_02", "chk_04", "chk_05"}
