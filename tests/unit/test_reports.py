"""Tests for JSON and Markdown report rendering."""

from __future__ import annotations

import json
from pathlib import Path

from hw_preflight.checks._base import CheckResult
from hw_preflight.reports import to_json, to_markdown, write_json, write_markdown
from hw_preflight.runner import HostInfo, RunReport


def _sample() -> RunReport:
    return RunReport(
        started_at="2026-05-02T00:00:00Z",
        finished_at="2026-05-02T00:00:01Z",
        host=HostInfo(hostname="ci", kernel="6.5.0", cpu_count=4),
        checks=[
            CheckResult(name="a", status="pass", duration_ms=1.23),
            CheckResult(name="b", status="fail", reason="bad", duration_ms=2.0),
            CheckResult(name="c", status="unavailable", reason="missing", duration_ms=0.1),
            CheckResult(name="d", status="skip", reason="not configured", duration_ms=0.0),
        ],
    )


def test_summary() -> None:
    r = _sample().summary
    assert r["pass"] == 1 and r["fail"] == 1
    assert r["unavailable"] == 1 and r["skip"] == 1 and r["total"] == 4


def test_to_json_round_trips() -> None:
    rep = _sample()
    data = json.loads(to_json(rep))
    assert data["summary"]["total"] == 4
    assert data["host"]["hostname"] == "ci"
    assert {c["name"] for c in data["checks"]} == {"a", "b", "c", "d"}


def test_write_json_and_md(tmp_path: Path) -> None:
    rep = _sample()
    j = tmp_path / "out.json"
    m = tmp_path / "out.md"
    write_json(rep, j)
    write_markdown(rep, m)
    assert j.exists() and m.exists()
    assert "hw-preflight report" in m.read_text()


def test_markdown_lists_failures() -> None:
    md = to_markdown(_sample())
    assert "Failures and unavailable" in md
    assert "`b`" in md
    assert "`c`" in md
    # `a` (pass) and `d` (skip) should not appear in failure section.
    failure_section = md.split("Failures and unavailable", 1)[1]
    assert "`a`" not in failure_section
    assert "`d`" not in failure_section
