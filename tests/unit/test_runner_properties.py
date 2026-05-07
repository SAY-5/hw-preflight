"""Hypothesis property tests for the runner.

Properties asserted:

* Summary aggregation totals every status bucket and matches the input.
* Result ordering is determined by the registry, not by submission order
  inside the runner.
* Disabling and enabling checks composes correctly: an enabled set minus
  a disabled set always yields the intersection (with disabled removed).
* The runner never raises on arbitrary status mixes; failing/exception
  checks are surfaced as `fail` results, not propagated.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from hw_preflight.checks._base import (
    _REGISTRY,
    CheckResult,
    all_checks,
    make_result,
)
from hw_preflight.config import PreflightConfig
from hw_preflight.runner import RunReport, _run_one, run_all

STATUSES = ["pass", "fail", "skip", "unavailable"]


def _make_synth_check(name: str, status: str) -> Callable[[PreflightConfig], CheckResult]:
    def _check(_: PreflightConfig) -> CheckResult:
        if status == "raise":
            raise RuntimeError(f"synthetic boom for {name}")
        return make_result(name, status)  # type: ignore[arg-type]

    _check.__check_name__ = name  # type: ignore[attr-defined]
    return _check


@pytest.fixture
def isolated_registry() -> object:
    """Snapshot the registry, let the test mutate, restore on teardown."""

    saved = dict(_REGISTRY)
    _REGISTRY.clear()
    try:
        yield _REGISTRY
    finally:
        _REGISTRY.clear()
        _REGISTRY.update(saved)


@settings(
    max_examples=80,
    deadline=2000,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    statuses=st.lists(
        st.sampled_from([*STATUSES, "raise"]),
        min_size=1,
        max_size=20,
    ),
)
def test_summary_buckets_sum_to_total(
    isolated_registry: dict[str, Callable[[PreflightConfig], CheckResult]],
    statuses: list[str],
) -> None:
    isolated_registry.clear()
    for i, st_ in enumerate(statuses):
        name = f"synth_{i:02d}"
        isolated_registry[name] = _make_synth_check(name, st_)
    cfg = PreflightConfig()
    cfg.runner.per_check_timeout_seconds = 5.0
    report = run_all(cfg)
    summary = report.summary
    bucket_total = sum(summary[k] for k in ("pass", "fail", "skip", "unavailable"))
    assert bucket_total == summary["total"] == len(statuses)
    # Each `raise` becomes a `fail` (exception captured).
    expected_fail = sum(1 for s in statuses if s in ("fail", "raise"))
    assert summary["fail"] == expected_fail
    for k in ("pass", "skip", "unavailable"):
        assert summary[k] == sum(1 for s in statuses if s == k)


@settings(
    max_examples=60,
    deadline=2000,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    n=st.integers(min_value=1, max_value=12),
    statuses=st.lists(st.sampled_from(STATUSES), min_size=1, max_size=12),
)
def test_result_order_is_registry_order(
    isolated_registry: dict[str, Callable[[PreflightConfig], CheckResult]],
    n: int,
    statuses: list[str],
) -> None:
    """Sorting by registry name is the contract callers depend on."""
    isolated_registry.clear()
    # Insert in scrambled order to prove the runner re-sorts.
    inserts = [(f"chk_{i:02d}", statuses[i % len(statuses)]) for i in range(n)]
    for name, st_ in reversed(inserts):  # reverse insertion
        isolated_registry[name] = _make_synth_check(name, st_)
    cfg = PreflightConfig()
    report = run_all(cfg)
    names = [c.name for c in report.checks]
    assert names == sorted(names), f"runner did not preserve sorted order: {names}"


@settings(
    max_examples=40,
    deadline=2000,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    statuses=st.lists(st.sampled_from(STATUSES), min_size=4, max_size=10),
    disabled_idx=st.lists(
        st.integers(min_value=0, max_value=9), min_size=0, max_size=4, unique=True
    ),
)
def test_disabled_checks_filter_is_honored(
    isolated_registry: dict[str, Callable[[PreflightConfig], CheckResult]],
    statuses: list[str],
    disabled_idx: list[int],
) -> None:
    isolated_registry.clear()
    names = [f"f_{i:02d}" for i in range(len(statuses))]
    for name, st_ in zip(names, statuses, strict=True):
        isolated_registry[name] = _make_synth_check(name, st_)
    disabled = [names[i] for i in disabled_idx if i < len(names)]
    cfg = PreflightConfig()
    cfg.runner.disabled_checks = disabled
    report = run_all(cfg)
    seen = {c.name for c in report.checks}
    for d in disabled:
        assert d not in seen
    expected_run = set(names) - set(disabled)
    assert seen == expected_run


@settings(
    max_examples=20,
    deadline=2000,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    explicit_enabled=st.lists(
        st.integers(min_value=0, max_value=5), min_size=1, max_size=4, unique=True
    ),
)
def test_enabled_checks_intersect(
    isolated_registry: dict[str, Callable[[PreflightConfig], CheckResult]],
    explicit_enabled: list[int],
) -> None:
    isolated_registry.clear()
    names = [f"f_{i:02d}" for i in range(6)]
    for name in names:
        isolated_registry[name] = _make_synth_check(name, "pass")
    keep = [names[i] for i in explicit_enabled if i < len(names)]
    cfg = PreflightConfig()
    cfg.runner.enabled_checks = keep
    report = run_all(cfg)
    assert {c.name for c in report.checks} == set(keep)


@settings(max_examples=30, deadline=1500)
@given(reason_seed=st.integers(min_value=0, max_value=10**6))
def test_run_one_never_raises(reason_seed: int) -> None:
    def boom(_: PreflightConfig) -> CheckResult:
        raise RuntimeError(f"seed={reason_seed}")

    result = _run_one("boom", boom, PreflightConfig(), timeout=2.0)
    assert result.status == "fail"
    assert result.reason is not None
    assert str(reason_seed) in result.reason


def test_real_registry_runs_and_summary_matches_total() -> None:
    """Smoke: production registry produces a summary whose buckets total to
    `total`, regardless of host environment."""
    cfg = PreflightConfig()
    cfg.runner.per_check_timeout_seconds = 5.0
    report = run_all(cfg)
    s = report.summary
    assert s["total"] == len(all_checks())
    assert sum(s[k] for k in ("pass", "fail", "skip", "unavailable")) == s["total"]
    assert isinstance(report, RunReport)
