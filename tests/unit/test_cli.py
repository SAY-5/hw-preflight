"""Tests for the CLI surface."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
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


def test_profiles_command_lists_three() -> None:
    runner = CliRunner()
    res = runner.invoke(main, ["profiles"])
    assert res.exit_code == 0
    names = res.output.strip().splitlines()
    assert {"production-server", "edge-device", "ci-runner"} <= set(names)


def test_run_with_profile_flag(tmp_path: Path) -> None:
    runner = CliRunner()
    j = tmp_path / "r.json"
    res = runner.invoke(main, ["run", "--profile", "ci-runner", "--json", str(j), "--quiet"])
    assert res.exit_code == 0
    data = json.loads(j.read_text())
    # ci-runner profile selects fewer than 24 checks.
    assert data["summary"]["total"] < 24
    assert data["summary"]["total"] > 0


def test_run_config_and_profile_mutually_exclusive(tmp_path: Path) -> None:
    runner = CliRunner()
    cfg_path = tmp_path / "p.yaml"
    cfg_path.write_text("cpu:\n  min_count: 1\n")
    res = runner.invoke(
        main,
        ["run", "--config", str(cfg_path), "--profile", "ci-runner", "--quiet"],
    )
    assert res.exit_code != 0
    assert "mutually exclusive" in (res.output or "") or "mutually exclusive" in str(
        res.exception or ""
    )


def test_run_webhook_url_posts_signed_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import hashlib
    import hmac
    from typing import Any

    from hw_preflight import webhook as wh

    captured: dict[str, Any] = {}

    class FakeResponse:
        status = 200

        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, *a: object) -> None:
            return None

    def fake_urlopen(req: Any, timeout: float = 5.0) -> FakeResponse:
        captured["url"] = req.full_url
        captured["data"] = req.data
        captured["headers"] = {k.lower(): v for k, v in req.headers.items()}
        return FakeResponse()

    monkeypatch.setenv(wh.ENV_SECRET, "cli-secret")
    monkeypatch.setattr(wh.urllib.request, "urlopen", fake_urlopen)

    runner = CliRunner()
    res = runner.invoke(main, ["run", "--webhook-url", "https://hook.example/x", "--quiet"])
    assert res.exit_code == 0
    assert captured["url"] == "https://hook.example/x"
    expected_sig = hmac.new(b"cli-secret", captured["data"], hashlib.sha256).hexdigest()
    assert captured["headers"]["x-hw-preflight-signature"] == f"sha256={expected_sig}"


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
