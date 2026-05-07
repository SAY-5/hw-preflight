"""Tests for the CLI surface."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from hw_preflight.cli import main


def test_list_command() -> None:
    runner = CliRunner()
    res = runner.invoke(main, ["list"])
    assert res.exit_code == 0
    names = res.output.strip().splitlines()
    assert "cpu_count" in names
    assert len(names) == 24


def test_run_writes_files(tmp_path: Path) -> None:
    runner = CliRunner()
    j = tmp_path / "r.json"
    m = tmp_path / "r.md"
    res = runner.invoke(main, ["run", "--json", str(j), "--md", str(m), "--quiet"])
    assert res.exit_code == 0
    data = json.loads(j.read_text())
    assert "summary" in data and data["summary"]["total"] == 24
    assert m.exists()


def test_render_md_command(tmp_path: Path) -> None:
    runner = CliRunner()
    j = tmp_path / "r.json"
    res = runner.invoke(main, ["run", "--json", str(j), "--quiet"])
    assert res.exit_code == 0
    res2 = runner.invoke(main, ["render-md", str(j)])
    assert res2.exit_code == 0
    assert "hw-preflight report" in res2.output


def test_run_exit_on_fail(tmp_path: Path) -> None:
    """With a deliberately impossible CPU count, --exit-on-fail must exit 1."""
    runner = CliRunner()
    cfg_path = tmp_path / "p.yaml"
    cfg_path.write_text("cpu:\n  min_count: 100000\n")
    j = tmp_path / "r.json"
    res = runner.invoke(
        main,
        [
            "run",
            "--config",
            str(cfg_path),
            "--json",
            str(j),
            "--exit-on-fail",
            "--quiet",
        ],
    )
    assert res.exit_code == 1
