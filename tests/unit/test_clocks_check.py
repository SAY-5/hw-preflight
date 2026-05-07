"""Unit tests for rtc_drift."""

from __future__ import annotations

from pathlib import Path

import pytest

from hw_preflight.checks import clocks as cmod
from hw_preflight.config import PreflightConfig


def test_rtc_drift_unavailable_when_path_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    real_exists = Path.exists

    def fake_exists(self: Path) -> bool:
        if str(self) == cmod._RTC_SINCE_EPOCH:
            return False
        return real_exists(self)

    monkeypatch.setattr(Path, "exists", fake_exists)
    r = cmod.rtc_drift(PreflightConfig())
    assert r.status == "unavailable"


def test_rtc_drift_pass_when_within_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cmod.time, "time", lambda: 1_700_000_000.0)
    real_exists = Path.exists
    real_read = Path.read_text

    def fake_exists(self: Path) -> bool:
        if str(self) == cmod._RTC_SINCE_EPOCH:
            return True
        return real_exists(self)

    def fake_read(self: Path, *a: object, **k: object) -> str:
        if str(self) == cmod._RTC_SINCE_EPOCH:
            return "1700000002\n"
        return real_read(self, *a, **k)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "exists", fake_exists)
    monkeypatch.setattr(Path, "read_text", fake_read)
    r = cmod.rtc_drift(PreflightConfig())
    assert r.status == "pass"


def test_rtc_drift_fail_when_above_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cmod.time, "time", lambda: 1_700_000_000.0)
    real_exists = Path.exists
    real_read = Path.read_text

    def fake_exists(self: Path) -> bool:
        if str(self) == cmod._RTC_SINCE_EPOCH:
            return True
        return real_exists(self)

    def fake_read(self: Path, *a: object, **k: object) -> str:
        if str(self) == cmod._RTC_SINCE_EPOCH:
            return "1699999900\n"
        return real_read(self, *a, **k)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "exists", fake_exists)
    monkeypatch.setattr(Path, "read_text", fake_read)
    cfg = PreflightConfig()
    cfg.rtc.max_drift_seconds = 5.0
    r = cmod.rtc_drift(cfg)
    assert r.status == "fail"


def test_rtc_drift_unparseable(monkeypatch: pytest.MonkeyPatch) -> None:
    real_exists = Path.exists
    real_read = Path.read_text

    def fake_exists(self: Path) -> bool:
        if str(self) == cmod._RTC_SINCE_EPOCH:
            return True
        return real_exists(self)

    def fake_read(self: Path, *a: object, **k: object) -> str:
        if str(self) == cmod._RTC_SINCE_EPOCH:
            return "definitely-not-a-number"
        return real_read(self, *a, **k)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "exists", fake_exists)
    monkeypatch.setattr(Path, "read_text", fake_read)
    r = cmod.rtc_drift(PreflightConfig())
    assert r.status == "unavailable"


def test_rtc_drift_oserror_on_read(monkeypatch: pytest.MonkeyPatch) -> None:
    real_exists = Path.exists
    real_read = Path.read_text

    def fake_exists(self: Path) -> bool:
        if str(self) == cmod._RTC_SINCE_EPOCH:
            return True
        return real_exists(self)

    def fake_read(self: Path, *a: object, **k: object) -> str:
        if str(self) == cmod._RTC_SINCE_EPOCH:
            raise OSError("EACCES")
        return real_read(self, *a, **k)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "exists", fake_exists)
    monkeypatch.setattr(Path, "read_text", fake_read)
    r = cmod.rtc_drift(PreflightConfig())
    assert r.status == "unavailable"
