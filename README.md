# hw-preflight

`hw-preflight` is a Linux hardware pre-flight check runner: 18 checks
across CPU, memory, disk, kernel, thermal, serial, network, GPIO, I2C, and
systemd, each emitting one of `pass | fail | skip | unavailable`. The
runner produces a JSON and Markdown report with raw measured values,
expected thresholds, and a failure-detail section. Checks read `/proc`,
`/sys`, run a few standard binaries (`ip`, `timedatectl`, `systemctl`),
talk to a serial device via `pyserial`, and (for CPUID feature flags)
call into a small C++ helper compiled via CMake + pybind11.

## What this studies

- **The four-state result model.** Most validation tools collapse `skip`
  and `unavailable`. Keeping them distinct means a runner that lacks
  `/sys/class/thermal` is reported honestly as "unavailable", not
  fake-passed and not falsely failed. `--exit-on-fail` only triggers on
  `fail`, so missing optional hardware does not break a CI gate.
- **Hermetic CI for hardware code.** Real `/proc` and `/sys` reads run on
  the GitHub Actions Linux runner; pyfakefs simulates kernel surfaces in
  unit tests; `socat` creates a virtual pty pair so the serial handshake
  can be reproduced without a USB dongle. Nothing is faked at the result
  layer — every check has a real implementation that runs against the
  host or against a documented mock.
- **Threshold versus availability.** Numeric thresholds (RAM, disk,
  kernel version) emit `fail` when the host produced a measurement that
  didn't satisfy the bound. Presence checks (GPIO, I2C, serial) default
  to `unavailable` when the underlying device file is missing, since the
  absence of optional peripherals is not a failure.

## Sample report

The table below is the output of `hw-preflight run --json
examples/sample-run.json --md examples/sample-run.md` on a development
host. The 13 `unavailable` rows are honest: this run was on macOS, where
`/proc` and `/sys` are absent. On the GitHub Actions Linux runner most
of those become `pass` (see the `e2e` workflow artifact for that file).

- host: `localhost` (kernel `25.0.0`, 10 CPUs)
- summary: 3 pass / 0 fail / 2 skip / 13 unavailable (18 total)

| # | Check | Status | Detail |
|---|---|---|---|
| 1 | `clock_source` | UNAVAIL | `/sys/devices/system/clocksource/clocksource0/current_clocksource` not present |
| 2 | `cpu_count` | PASS | `cpu_count=10` |
| 3 | `cpu_features` | UNAVAIL | no CPU feature flags readable (non-Linux host) |
| 4 | `disk_free` | PASS | 8.4 GiB free on `/` |
| 5 | `gpio_chips` | UNAVAIL | `/sys/class/gpio` not present |
| 6 | `i2c_bus_present` | UNAVAIL | no `/dev/i2c-*` nodes |
| 7 | `kernel_module_loaded` | UNAVAIL | `/proc/modules` not present |
| 8 | `kernel_version` | PASS | release `25.0.0` >= 5.10.0 |
| 9 | `loadavg_short` | UNAVAIL | `/proc/loadavg` not present |
| 10 | `memory_available` | UNAVAIL | `/proc/meminfo` missing MemAvailable |
| 11 | `memory_total` | UNAVAIL | `/proc/meminfo` missing MemTotal |
| 12 | `network_default_route` | UNAVAIL | `ip(8)` not on PATH |
| 13 | `serial_handshake` | UNAVAIL | no serial port resolved |
| 14 | `serial_port_present` | UNAVAIL | no candidate path matched |
| 15 | `service_unit_active` | SKIP | no service units configured |
| 16 | `swap_disabled` | SKIP | swap-disabled requirement not enforced |
| 17 | `thermal_max` | UNAVAIL | no thermal zones in `/sys/class/thermal` |
| 18 | `time_sync` | UNAVAIL | `timedatectl` not on PATH |

The full machine-readable artifact is at [`examples/sample-run.json`](examples/sample-run.json)
and the rendered Markdown at [`examples/sample-run.md`](examples/sample-run.md).

## The 18 checks

| Check | What it reads |
|---|---|
| `cpu_count` | `os.cpu_count()` against `cpu.min_count` |
| `cpu_features` | C++ `__builtin_cpu_supports` ∪ `/proc/cpuinfo flags:` against `cpu.required_features` |
| `memory_total` | `/proc/meminfo MemTotal` |
| `memory_available` | `/proc/meminfo MemAvailable` |
| `swap_disabled` | `/proc/meminfo SwapTotal == 0` (toggle) |
| `disk_free` | `os.statvfs(path)` |
| `loadavg_short` | `/proc/loadavg` 1-minute load against `cpu_count * factor` |
| `kernel_version` | `os.uname().release` against `system.min_kernel_version` |
| `kernel_module_loaded` | `/proc/modules` against `system.required_modules` |
| `clock_source` | `/sys/devices/system/clocksource/clocksource0/current_clocksource` against allowlist |
| `time_sync` | `timedatectl show -p NTPSynchronized --value` |
| `thermal_max` | max of `/sys/class/thermal/thermal_zone*/temp` |
| `serial_port_present` | `HW_PREFLIGHT_SERIAL_PATH` -> `serial.by_id_glob` -> `serial.candidate_paths` |
| `serial_handshake` | open at 115200, write `AT\r\n`, regex-match response |
| `network_default_route` | `ip route show default` |
| `gpio_chips` | count of `gpiochip*` in `/sys/class/gpio` |
| `i2c_bus_present` | count of `/dev/i2c-*` |
| `service_unit_active` | `systemctl is-active <unit>` for each entry in `service.units` |

See [`docs/checks.md`](docs/checks.md) for the per-check reference,
including how each is mocked in CI.

## Modules

| Module | Purpose |
|---|---|
| `hw_preflight.cli` | Click CLI: `run`, `list`, `render-md` |
| `hw_preflight.runner` | Discovers checks, runs each with a per-check timeout, aggregates results |
| `hw_preflight.config` | Pydantic v2 settings tree, YAML loader |
| `hw_preflight.reports` | JSON and Markdown emitters |
| `hw_preflight.checks._base` | `CheckResult` schema + `@register_check` decorator |
| `hw_preflight.checks.*` | One module per check group (cpu, memory, disk, system, thermal, serial, network, gpio, service) |
| `hw_preflight._hwprobe` | Wrapper around the C++ helper with a `/proc/cpuinfo` fallback |
| `hwprobe/` | C++ 20 helper: `cpuid`, `dmi`, `main` (CLI), `bindings` (pybind11) |

## Quickstart

```bash
# from the source tree
pip install -e ".[dev]"

# optional: build the C++ helper (CMake + pybind11)
cmake -S hwprobe -B hwprobe/build -DCMAKE_BUILD_TYPE=Release
cmake --build hwprobe/build -j

# run it
hw-preflight run --json out.json --md out.md
hw-preflight list                       # list registered check names
hw-preflight render-md out.json         # rerender JSON to stdout Markdown

# with a custom config
hw-preflight run --config config/preflight.example.yaml --exit-on-fail
```

## Architecture

```
                     +----------------------+
   YAML config  ---> |  PreflightConfig     |
                     |  (pydantic v2)       |
                     +----------+-----------+
                                |
                                v
       +-----------------+   +--+--+   +------------------+
       |  CLI (click)    |-->|run  |-->| reports.to_json /|
       +-----------------+   |all  |   | to_markdown      |
                             +--+--+   +------------------+
                                |
                  per-check     |
                  ThreadPool    |
                  + timeout     v
        +-----------------------+----------------------+
        |       checks/ (auto-registered)              |
        |  cpu.py memory.py disk.py system.py          |
        |  thermal.py serial.py network.py gpio.py     |
        |  service.py                                  |
        +----------+-------------+---------------------+
                   |             |
                   v             v
      /proc, /sys, syscalls    pyserial / subprocess
                   ^
                   |
        +----------+----------+
        |  _hwprobe.py        |
        |  (C++ ext OR        |
        |  /proc/cpuinfo)     |
        +----------+----------+
                   |
                   v
        +---------------------+
        | hwprobe/  (C++ 20)  |
        | CMake + pybind11    |
        +---------------------+
```

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the four-state result-model
rationale, the C++ binding decision, and tier-by-tier mocking strategy.

## What this is *not*

- **Not** a continuous-monitoring agent. Each invocation is a one-shot
  snapshot.
- **Not** a remote-agent framework. Runs locally; there is no transport,
  auth, or scheduler.
- **Not** a firmware-update or hardware-diagnostic path. Read-only.
- **Not** a GPU or accelerator validator. Vendor SDKs differ enough that
  GPU validation deserves its own framework.
- **Not** a network throughput or latency probe. Only checks the
  *availability* of a default route — peripheral presence, not bandwidth.
- **Not** Windows or macOS compatible. Many checks read `/proc` and
  `/sys` directly; cross-platform support would require a parallel
  registry rather than a thin abstraction. Linux-only by design.

## License

MIT — see [`LICENSE`](LICENSE).
