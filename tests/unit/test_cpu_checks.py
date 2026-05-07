"""Unit tests for cpu_count and cpu_features."""

from __future__ import annotations

import pytest

from hw_preflight import _hwprobe
from hw_preflight.checks.cpu import cpu_count, cpu_features
from hw_preflight.config import PreflightConfig


def test_cpu_count_pass(default_config: PreflightConfig) -> None:
    # The host running pytest essentially always has >= 1 CPU.
    cfg = PreflightConfig()
    cfg.cpu.min_count = 1
    r = cpu_count(cfg)
    assert r.status == "pass"
    assert r.measured is not None
    assert r.measured["cpu_count"] >= 1


def test_cpu_count_fail() -> None:
    cfg = PreflightConfig()
    cfg.cpu.min_count = 10_000
    r = cpu_count(cfg)
    assert r.status == "fail"
    assert r.reason is not None and "below threshold" in r.reason


def test_cpu_features_skip_when_no_required() -> None:
    cfg = PreflightConfig()
    cfg.cpu.required_features = []
    r = cpu_features(cfg)
    assert r.status == "skip"


def test_cpu_features_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = PreflightConfig()
    cfg.cpu.required_features = ["sse4_2"]
    monkeypatch.setattr(_hwprobe, "cpu_features", lambda: [])
    r = cpu_features(cfg)
    assert r.status == "unavailable"


def test_cpu_features_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = PreflightConfig()
    cfg.cpu.required_features = ["sse4_2", "avx"]
    monkeypatch.setattr(_hwprobe, "cpu_features", lambda: ["fpu", "sse4_2", "avx", "bmi"])
    r = cpu_features(cfg)
    assert r.status == "pass"


def test_cpu_features_fail_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = PreflightConfig()
    cfg.cpu.required_features = ["sse4_2", "avx512f"]
    monkeypatch.setattr(_hwprobe, "cpu_features", lambda: ["sse4_2"])
    r = cpu_features(cfg)
    assert r.status == "fail"
    assert r.measured is not None
    assert r.measured["missing"] == ["avx512f"]


def test_features_from_cpuinfo_arm(tmp_path) -> None:  # type: ignore[no-untyped-def]
    p = tmp_path / "cpuinfo"
    p.write_text("processor\t: 0\nFeatures\t: fp asimd aes\n")
    out = _hwprobe._features_from_cpuinfo(str(p))
    assert "fp" in out and "asimd" in out and "aes" in out


def test_features_from_cpuinfo_x86(tmp_path) -> None:  # type: ignore[no-untyped-def]
    p = tmp_path / "cpuinfo"
    p.write_text("processor\t: 0\nflags\t\t: fpu sse4_2 avx\n")
    out = _hwprobe._features_from_cpuinfo(str(p))
    assert "sse4_2" in out and "avx" in out


def test_features_from_cpuinfo_missing_file() -> None:
    assert _hwprobe._features_from_cpuinfo("/no/such/file/12345") == []
