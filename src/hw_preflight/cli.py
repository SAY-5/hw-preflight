"""hw-preflight CLI."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from . import __version__
from .config import load_config
from .reports import to_json, to_markdown, write_json, write_markdown
from .runner import run_all


@click.group()
@click.version_option(__version__, prog_name="hw-preflight")
def main() -> None:
    """Linux hardware preflight check runner."""


@main.command()
@click.option(
    "--config",
    "config_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Path to YAML config; defaults are used when omitted.",
)
@click.option(
    "--json",
    "json_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Write the JSON report to this path.",
)
@click.option(
    "--md",
    "md_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Write the Markdown report to this path.",
)
@click.option(
    "--exit-on-fail",
    is_flag=True,
    help="Exit non-zero if any check is `fail` (skip and unavailable do not trigger).",
)
@click.option(
    "--parallelism",
    type=int,
    default=None,
    help="Worker thread count (default 1 = serial; pass 0 for cpu_count()).",
)
@click.option("--quiet", is_flag=True, help="Suppress stdout summary.")
def run(
    config_path: Path | None,
    json_path: Path | None,
    md_path: Path | None,
    exit_on_fail: bool,
    parallelism: int | None,
    quiet: bool,
) -> None:
    """Run every registered check and emit a report."""
    config = load_config(config_path)
    if parallelism is not None:
        config.runner.parallelism = parallelism
    report = run_all(config)

    if json_path is not None:
        write_json(report, json_path)
    if md_path is not None:
        write_markdown(report, md_path)

    if not quiet:
        if json_path is None and md_path is None:
            # Default to JSON on stdout when no files requested.
            click.echo(to_json(report))
        else:
            s = report.summary
            click.echo(
                f"hw-preflight: {s['pass']} pass / {s['fail']} fail / "
                f"{s['skip']} skip / {s['unavailable']} unavailable "
                f"({s['total']} total)"
            )

    if exit_on_fail and report.summary["fail"] > 0:
        sys.exit(1)


@main.command("list")
def list_checks() -> None:
    """List every registered check name."""
    from .checks._base import all_checks

    for name in all_checks():
        click.echo(name)


@main.command("render-md")
@click.argument("json_in", type=click.Path(exists=True, dir_okay=False, path_type=Path))
def render_md(json_in: Path) -> None:
    """Render an existing JSON report file to Markdown on stdout."""
    import json

    from .checks._base import CheckResult
    from .runner import HostInfo, RunReport

    raw = json.loads(json_in.read_text())
    report = RunReport(
        started_at=raw["started_at"],
        finished_at=raw["finished_at"],
        host=HostInfo(**raw["host"]),
        checks=[CheckResult(**c) for c in raw["checks"]],
    )
    click.echo(to_markdown(report), nl=False)


if __name__ == "__main__":  # pragma: no cover
    main()
