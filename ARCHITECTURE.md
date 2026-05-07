# Architecture

## The four-state result model

Most validation tooling collapses outcomes into pass/fail or
pass/fail/skip. `hw-preflight` keeps `skip` and `unavailable` as separate
states because the operator-facing meaning differs:

| Status | Meaning | When |
|---|---|---|
| `pass` | A measurement was made and it satisfied the constraint. |
| `fail` | A measurement was made and it did not satisfy the constraint. |
| `skip` | No measurement was attempted; the user told the runner to skip. | Empty `required_modules`, `service.units == []`, `runner.disabled_checks` entry, etc. |
| `unavailable` | The runner attempted a measurement but the underlying interface is missing. | `/proc/loadavg` absent, `timedatectl` not installed, no thermal zones in `/sys/class/thermal`. |

The distinction matters when the framework is used to gate a real run:
`--exit-on-fail` only triggers on `fail`, not `unavailable`. A green-but-
unavailable check is honest about what was and wasn't measured. Hiding that
behind a fake `pass` would be the kind of dishonest reporting this project
exists to avoid.

## Check protocol and registry

`src/hw_preflight/checks/_base.py` defines:

```python
class CheckResult(BaseModel):
    name: str
    status: Literal["pass", "fail", "skip", "unavailable"]
    measured: dict | None
    expected: dict | None
    duration_ms: float
    reason: str | None

@register_check("name")
def my_check(config: PreflightConfig) -> CheckResult: ...
```

Modules under `checks/` are auto-imported via `checks/__init__.py`, which
side-effect-registers each `@register_check` decorator. `runner.run_all()`
sorts the registry by name for deterministic ordering, then invokes each
check in a single-worker `ThreadPoolExecutor` so a per-check timeout can
be enforced. A check that raises is converted to a `fail` result with the
exception type in `reason`; a check that exceeds the timeout is similarly
converted. The runner never aborts on a single failure — the full report
is always emitted.

## Why both a C++ helper and a Python fallback

`src/hw_preflight/_hwprobe.py` prefers a compiled extension
(`hw_preflight._hwprobe_ext`, built by CMake + pybind11 from
`hwprobe/`) and falls back to parsing `/proc/cpuinfo` directly when the
extension is absent.

The C++ helper exists for two reasons:

1. **Runtime feature detection that compiler flags know about.** GCC and
   Clang expose `__builtin_cpu_supports("avx2")` etc. on x86; this matches
   what userspace binaries can rely on, which is what most pre-flight
   checks actually want to validate.
2. **A demonstration that the framework is real about heterogeneous
   stacks.** Hardware tooling routinely needs C/C++ for low-level access
   that has no stable Python equivalent (CPUID, ioctls, vendor SDKs);
   shipping a working pybind11 binding shows the integration works rather
   than handwaving it.

`pybind11` is preferred over `ctypes` because:

- The API surface is small (two functions); a `ctypes` wrapper would still
  need handwritten conversion of `std::vector<std::string>` to a Python
  list and `std::map<std::string,std::string>` to a dict.
- The build is hermetic (FetchContent at configure time), so contributors
  do not need a pre-installed pybind11.
- The type annotations on the Python side stay clean (no `c_void_p`).

The Python fallback is a real implementation, not a stub: `/proc/cpuinfo`
is the canonical source on Linux, and the parser handles both x86
(`flags:`) and arm64 (`Features:`) lines. The C++ helper merely adds
`__builtin_cpu_supports` on top.

## Mocking strategy by tier

| Tier | Tool | Where |
|---|---|---|
| Unit (`tests/unit/`) | `pyfakefs` for `/proc` and `/sys`; `monkeypatch` for `subprocess` and `os.statvfs`. | Cheap, isolated, deterministic. |
| Integration (`tests/integration/`) | None — gated by `RUN_INTEGRATION=1`, runs against the live host. | Captures honest behavior on the GitHub Actions Linux runner. |
| End-to-end (`tests/e2e/`) | `socat` virtual pty pair + a Python device thread that echoes `OK\r\n`. | Reproducible serial handshake without real hardware. |

The serial check is the only one that talks to a device file rather than
a kernel interface. To keep it unit-testable, `serial_handshake` accepts
an optional backend callable in tests so the real `pyserial` open is never
exercised in unit tests; the e2e test exercises pyserial against the
socat pty.

## Threshold versus availability

A subtle design choice: numeric thresholds (RAM, disk free, kernel
version) emit `fail` when the host produces a value that doesn't satisfy
the bound, but `unavailable` when the source file or binary is absent.
Presence checks (GPIO chips, I2C buses, default route, serial port)
default to threshold zero, in which case "no devices present" is reported
as `unavailable` rather than `fail`. The intent: a tier file changes a
presence check to `fail` by raising the threshold, not by altering the
check.

## What's deliberately not here

- **Continuous monitoring.** Each invocation is a one-shot snapshot. A
  long-running daemon is a different shape of system.
- **Remote agents.** Everything runs locally; there is no transport
  layer, no auth, no scheduling.
- **Firmware updates or diagnostics.** Read-only checks only; nothing in
  this tree writes to a hardware register.
- **GPU validation.** Out of scope. Vendor SDKs differ enough to deserve
  their own framework.
- **Network throughput.** Only peripheral *availability* (default route
  presence) is checked, not bandwidth.
- **Windows or macOS support.** Many checks read `/proc` and `/sys`;
  porting to other platforms would require a parallel set of checks
  rather than a thin abstraction. Linux-only is a feature, not a gap.
