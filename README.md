# hw-preflight

`hw-preflight` is a Linux hardware pre-flight check runner: 24 checks
across CPU, memory, disk, kernel, thermal, serial, network, GPIO, I2C,
systemd, NVMe SMART, USB, RTC drift, IOMMU groups, VM overcommit, and
SELinux mode, each emitting one of `pass | fail | skip | unavailable`. The
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

The table below is the actual output of `hw-preflight run` on the
GitHub Actions `ubuntu-24.04` runner (the JSON it came from is
[`examples/sample-run.json`](examples/sample-run.json), produced by the
`e2e` job and committed verbatim).

- host: `ubuntu-runner` (kernel `6.17.0-1010-azure`, 4 CPUs)
- summary: 11 pass / 1 fail / 2 skip / 4 unavailable (18 total)

| # | Check | Status | Detail |
|---|---|---|---|
| 1 | `clock_source` | PASS | clocksource=`tsc` |
| 2 | `cpu_count` | PASS | cpu_count=4 |
| 3 | `cpu_features` | PASS | 102 flags read from `/proc/cpuinfo` (C++ ext built in `build-cpp` job; the `test-py` job uses the Python fallback) |
| 4 | `disk_free` | PASS | 88.7 GiB free on `/` |
| 5 | `gpio_chips` | UNAVAIL | no gpiochips exposed |
| 6 | `i2c_bus_present` | UNAVAIL | no `/dev/i2c-*` nodes |
| 7 | `kernel_module_loaded` | FAIL | `loop` not loaded (Azure runner kernel ships it built-in, not as a module — adjust `system.required_modules` for tier) |
| 8 | `kernel_version` | PASS | release `6.17.0-1010-azure` |
| 9 | `loadavg_short` | PASS | loadavg=1.28, 4 CPUs |
| 10 | `memory_available` | PASS | 14.6 GiB available |
| 11 | `memory_total` | PASS | 15.6 GiB total |
| 12 | `network_default_route` | PASS | 1 default route present |
| 13 | `serial_handshake` | UNAVAIL | `/dev/ttyS0` exists but EACCES (runner not in `dialout`); the e2e job exercises the same code through socat with a real round-trip |
| 14 | `serial_port_present` | PASS | path=`/dev/ttyS0` |
| 15 | `service_unit_active` | SKIP | no service units configured |
| 16 | `swap_disabled` | SKIP | swap-disabled requirement not enforced |
| 17 | `thermal_max` | UNAVAIL | no thermal zones in `/sys/class/thermal` |
| 18 | `time_sync` | PASS | `NTPSynchronized=yes` |

The single `fail` is honest: the default config requires the `loop`
module, and the Azure runner kernel does not load it as a separate
module. A real deployment changes `system.required_modules` to match
its tier, or removes the constraint.

The full machine-readable artifact is at
[`examples/sample-run.json`](examples/sample-run.json) and the rendered
Markdown at [`examples/sample-run.md`](examples/sample-run.md).

## The 24 checks

| # | Check | What it reads |
|---|---|---|
| 1 | `cpu_count` | `os.cpu_count()` against `cpu.min_count` |
| 2 | `cpu_features` | C++ `__builtin_cpu_supports` ∪ `/proc/cpuinfo flags:` against `cpu.required_features` |
| 3 | `memory_total` | `/proc/meminfo MemTotal` |
| 4 | `memory_available` | `/proc/meminfo MemAvailable` |
| 5 | `swap_disabled` | `/proc/meminfo SwapTotal == 0` (toggle) |
| 6 | `disk_free` | `os.statvfs(path)` |
| 7 | `loadavg_short` | `/proc/loadavg` 1-minute load against `cpu_count * factor` |
| 8 | `kernel_version` | `os.uname().release` against `system.min_kernel_version` |
| 9 | `kernel_module_loaded` | `/proc/modules` against `system.required_modules` |
| 10 | `clock_source` | `/sys/devices/system/clocksource/clocksource0/current_clocksource` against allowlist |
| 11 | `time_sync` | `timedatectl show -p NTPSynchronized --value` |
| 12 | `thermal_max` | max of `/sys/class/thermal/thermal_zone*/temp` |
| 13 | `serial_port_present` | `HW_PREFLIGHT_SERIAL_PATH` -> `serial.by_id_glob` -> `serial.candidate_paths` |
| 14 | `serial_handshake` | open at 115200, write `AT\r\n`, regex-match response |
| 15 | `network_default_route` | `ip route show default` |
| 16 | `gpio_chips` | count of `gpiochip*` in `/sys/class/gpio` |
| 17 | `i2c_bus_present` | count of `/dev/i2c-*` |
| 18 | `service_unit_active` | `systemctl is-active <unit>` for each entry in `service.units` |
| 19 | `nvme_smart` | `nvme smart-log /dev/nvme0n1` `critical_warning` field |
| 20 | `usb_device_count` | count of entries under `/sys/bus/usb/devices/` |
| 21 | `rtc_drift` | `/sys/class/rtc/rtc0/since_epoch` vs `time.time()` |
| 22 | `pci_iommu_groups` | count of `/sys/kernel/iommu_groups/*` |
| 23 | `vm_overcommit` | `/proc/sys/vm/overcommit_memory` against allowlist |
| 24 | `selinux_status` | `getenforce` output (Enforcing / Permissive / Disabled) |

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
