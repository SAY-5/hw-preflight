"""Benchmark the full check suite serial vs parallel.

Records wall-clock for ``run_all`` at parallelism=1 and parallelism=cpu_count
across N repetitions. Writes a JSON file at
``bench/results/<utc-isoformat>.json`` with the timing distribution and
metadata about the host.

Usage:
    python -m bench.run_suite_bench [--repeats N] [--out PATH]

The ``Makefile`` target ``bench-regress`` invokes this with --check-regress
to fail when serial degrades by more than the configured drift fraction
relative to the latest baseline.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from hw_preflight.config import PreflightConfig
from hw_preflight.runner import run_all

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO_ROOT / "bench" / "results"


def _measure(parallelism: int, repeats: int) -> list[float]:
    cfg = PreflightConfig()
    cfg.runner.parallelism = parallelism
    cfg.runner.per_check_timeout_seconds = 5.0
    samples: list[float] = []
    # One warm-up run to populate caches and pre-import modules.
    run_all(cfg)
    for _ in range(repeats):
        t0 = time.perf_counter()
        run_all(cfg)
        samples.append(time.perf_counter() - t0)
    return samples


def _latest_baseline(platform_key: str | None = None) -> dict[str, object] | None:
    """Find the latest baseline JSON.

    When ``platform_key`` is provided, only baselines whose
    ``host.platform`` field starts with the same OS family are considered;
    macOS measurements should not gate Linux CI and vice versa.
    """
    if not RESULTS_DIR.exists():
        return None
    candidates = sorted(RESULTS_DIR.glob("*.json"))
    if not candidates:
        return None
    if platform_key is None:
        with candidates[-1].open() as f:
            return json.load(f)
    for path in reversed(candidates):
        with path.open() as f:
            data = json.load(f)
        host_platform = str(data.get("host", {}).get("platform", ""))
        if host_platform.split("-", 1)[0] == platform_key.split("-", 1)[0]:
            return data
    return None


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repeats", type=int, default=5)
    p.add_argument("--out", type=Path, default=None)
    p.add_argument(
        "--check-regress",
        action="store_true",
        help="Compare serial median against latest baseline; exit 1 if drift > threshold.",
    )
    p.add_argument(
        "--threshold",
        type=float,
        default=0.30,
        help="Drift fraction tolerated before --check-regress fails (default 0.30 = 30%).",
    )
    args = p.parse_args(argv)

    serial = _measure(parallelism=1, repeats=args.repeats)
    parallel = _measure(parallelism=0, repeats=args.repeats)

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "host": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "cpu_count": os.cpu_count(),
        },
        "repeats": args.repeats,
        "serial_seconds": serial,
        "parallel_seconds": parallel,
        "summary": {
            "serial_median": statistics.median(serial),
            "parallel_median": statistics.median(parallel),
            "speedup_x": (
                statistics.median(serial) / statistics.median(parallel)
                if statistics.median(parallel) > 0
                else None
            ),
        },
    }

    out_path: Path
    if args.out is not None:
        out_path = args.out
    else:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        ts = payload["generated_at"].replace(":", "-")
        out_path = RESULTS_DIR / f"{ts}.json"
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))
    print(f"wrote {out_path}", file=sys.stderr)

    if args.check_regress:
        baseline = _latest_baseline(platform_key=platform.platform())
        if baseline is None or baseline.get("generated_at") == payload["generated_at"]:
            print(
                "no prior same-platform baseline; nothing to compare",
                file=sys.stderr,
            )
            return 0
        prev_serial = float(baseline["summary"]["serial_median"])  # type: ignore[index]
        cur_serial = payload["summary"]["serial_median"]
        drift = (cur_serial - prev_serial) / prev_serial if prev_serial > 0 else 0.0
        print(
            f"serial drift: {drift:+.1%} " f"(prev={prev_serial:.4f}s, cur={cur_serial:.4f}s)",
            file=sys.stderr,
        )
        if drift > args.threshold:
            print(
                f"REGRESSION: drift {drift:+.1%} exceeds {args.threshold:+.1%}",
                file=sys.stderr,
            )
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
