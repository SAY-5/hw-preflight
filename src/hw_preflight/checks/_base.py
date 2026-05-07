"""Check protocol, result schema, and registry."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Literal, Protocol

from pydantic import BaseModel

if TYPE_CHECKING:
    from hw_preflight.config import PreflightConfig

CheckStatus = Literal["pass", "fail", "skip", "unavailable"]


class CheckResult(BaseModel):
    name: str
    status: CheckStatus
    measured: dict[str, Any] | None = None
    expected: dict[str, Any] | None = None
    duration_ms: float = 0.0
    reason: str | None = None


class Check(Protocol):
    """A single preflight check.

    Implementations are async-free callables: given the loaded PreflightConfig,
    return a CheckResult. They must not raise; surface errors as `fail` results
    or `unavailable` when the underlying interface is missing.
    """

    name: str

    def __call__(self, config: PreflightConfig) -> CheckResult: ...


_REGISTRY: dict[str, Callable[[PreflightConfig], CheckResult]] = {}


def register_check(
    name: str,
) -> Callable[
    [Callable[[PreflightConfig], CheckResult]],
    Callable[[PreflightConfig], CheckResult],
]:
    """Decorator that registers a check function under a stable name."""

    def decorator(
        func: Callable[[PreflightConfig], CheckResult],
    ) -> Callable[[PreflightConfig], CheckResult]:
        if name in _REGISTRY:
            raise ValueError(f"check already registered: {name}")
        # Attach the name onto the function for introspection.
        func.__check_name__ = name  # type: ignore[attr-defined]
        _REGISTRY[name] = func
        return func

    return decorator


def all_checks() -> dict[str, Callable[[PreflightConfig], CheckResult]]:
    """Return the immutable check registry (sorted by name)."""
    return dict(sorted(_REGISTRY.items()))


def make_result(
    name: str,
    status: CheckStatus,
    *,
    measured: dict[str, Any] | None = None,
    expected: dict[str, Any] | None = None,
    reason: str | None = None,
) -> CheckResult:
    return CheckResult(
        name=name,
        status=status,
        measured=measured,
        expected=expected,
        reason=reason,
    )
