"""JSON and Markdown report emitters."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .runner import RunReport

_STATUS_GLYPH = {
    "pass": "PASS",
    "fail": "FAIL",
    "skip": "SKIP",
    "unavailable": "UNAVAIL",
}


def to_json(report: RunReport, *, indent: int = 2) -> str:
    return json.dumps(report.to_dict(), indent=indent, sort_keys=True)


def write_json(report: RunReport, path: Path | str) -> None:
    Path(path).write_text(to_json(report) + "\n")


def _truncate(value: Any, length: int = 80) -> str:
    s = repr(value) if not isinstance(value, str) else value
    if len(s) > length:
        return s[: length - 3] + "..."
    return s


def to_markdown(report: RunReport) -> str:
    summary = report.summary
    lines: list[str] = []
    lines.append("# hw-preflight report")
    lines.append("")
    lines.append(
        f"- host: `{report.host.hostname}` "
        f"(kernel `{report.host.kernel}`, "
        f"{report.host.cpu_count} CPUs)"
    )
    lines.append(f"- started: `{report.started_at}`")
    lines.append(f"- finished: `{report.finished_at}`")
    lines.append(
        f"- summary: {summary['pass']} pass / "
        f"{summary['fail']} fail / "
        f"{summary['skip']} skip / "
        f"{summary['unavailable']} unavailable "
        f"({summary['total']} total)"
    )
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    lines.append("| # | Check | Status | Duration (ms) | Detail |")
    lines.append("|---|---|---|---:|---|")
    for i, c in enumerate(report.checks, start=1):
        detail = c.reason or ""
        if not detail and c.measured:
            detail = _truncate(c.measured)
        lines.append(
            f"| {i} | `{c.name}` | {_STATUS_GLYPH[c.status]} | " f"{c.duration_ms:.2f} | {detail} |"
        )
    lines.append("")
    failures = [c for c in report.checks if c.status in {"fail", "unavailable"}]
    if failures:
        lines.append("## Failures and unavailable")
        lines.append("")
        for c in failures:
            lines.append(f"### `{c.name}` — {c.status}")
            if c.reason:
                lines.append("")
                lines.append(f"- reason: {c.reason}")
            if c.expected:
                lines.append(f"- expected: `{c.expected}`")
            if c.measured:
                lines.append(f"- measured: `{c.measured}`")
            lines.append("")
    return "\n".join(lines) + "\n"


def write_markdown(report: RunReport, path: Path | str) -> None:
    Path(path).write_text(to_markdown(report))
