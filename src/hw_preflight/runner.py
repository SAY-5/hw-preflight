"""Runner: orchestrates per-check execution with timeouts and aggregation."""

from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

# Importing the checks package side-effect-registers every check.
from . import checks  # noqa: F401
from .checks import _base
from .checks._base import CheckResult, make_result
from .config import PreflightConfig


@dataclass
class HostInfo:
    hostname: str
    kernel: str
    cpu_count: int


@dataclass
class RunReport:
    started_at: str
    finished_at: str
    host: HostInfo
    checks: list[CheckResult] = field(default_factory=list)  # noqa: F811

    @property
    def summary(self) -> dict[str, int]:
        out = {"pass": 0, "fail": 0, "skip": 0, "unavailable": 0}
        for c in self.checks:
            out[c.status] += 1
        out["total"] = len(self.checks)
        return out

    def to_dict(self) -> dict[str, Any]:
        return {
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "host": {
                "hostname": self.host.hostname,
                "kernel": self.host.kernel,
                "cpu_count": self.host.cpu_count,
            },
            "checks": [c.model_dump() for c in self.checks],
            "summary": self.summary,
        }


def _gather_host_info() -> HostInfo:
    try:
        u = os.uname()
        return HostInfo(
            hostname=u.nodename,
            kernel=u.release,
            cpu_count=os.cpu_count() or 0,
        )
    except (AttributeError, OSError):
        return HostInfo(hostname="unknown", kernel="unknown", cpu_count=os.cpu_count() or 0)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _select_checks(config: PreflightConfig) -> list[tuple[str, Any]]:
    items = list(_base.all_checks().items())
    enabled = config.runner.enabled_checks
    disabled = set(config.runner.disabled_checks)
    if enabled is not None:
        keep = set(enabled)
        items = [(n, fn) for n, fn in items if n in keep]
    if disabled:
        items = [(n, fn) for n, fn in items if n not in disabled]
    return items


def _run_one(name: str, func: Any, config: PreflightConfig, timeout: float) -> CheckResult:
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"chk-{name}") as ex:
        future = ex.submit(func, config)
        try:
            result = future.result(timeout=timeout)
        except FuturesTimeout:
            duration = (time.perf_counter() - start) * 1000.0
            r = make_result(
                name,
                "fail",
                reason=f"check timed out after {timeout}s",
            )
            r.duration_ms = round(duration, 3)
            return r
        except Exception as exc:
            duration = (time.perf_counter() - start) * 1000.0
            r = make_result(
                name,
                "fail",
                reason=f"check raised {type(exc).__name__}: {exc}",
            )
            r.duration_ms = round(duration, 3)
            return r
    duration = (time.perf_counter() - start) * 1000.0
    if not isinstance(result, CheckResult):
        return make_result(
            name,
            "fail",
            reason=f"check returned non-CheckResult: {type(result).__name__}",
        )
    result.duration_ms = round(duration, 3)
    return result


def run_all(config: PreflightConfig) -> RunReport:
    """Execute every selected check sequentially and produce a report.

    Checks run sequentially because several reach into shared OS state
    (subprocess, /proc) and parallelism would obscure attribution if a
    single check misbehaves. Each is bounded by a per-check timeout.
    """
    started = _now_iso()
    selected = _select_checks(config)
    results: list[CheckResult] = []
    for name, fn in selected:
        results.append(_run_one(name, fn, config, config.runner.per_check_timeout_seconds))
    finished = _now_iso()
    return RunReport(
        started_at=started,
        finished_at=finished,
        host=_gather_host_info(),
        checks=results,
    )
