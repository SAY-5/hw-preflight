# Check reference

Each section explains what a check measures, how to mock it in CI, and how
to read a failure. The four possible result statuses are:

- **pass** — measured value satisfied the threshold or constraint
- **fail** — the host produced data and that data did not meet the threshold
- **skip** — the check is configured off (empty required list, toggle false)
- **unavailable** — the underlying interface (file, binary, device) is missing

`unavailable` is deliberately distinct from `fail`: a runner that lacks
`/sys/class/thermal` should not be reported as having "failing" thermals,
because no measurement was made.

---

## 1. `cpu_count`

Reads `os.cpu_count()`. Fails if below `cpu.min_count`.

- Default threshold: 2
- Mocking: not mocked; `os.cpu_count()` returns the runner's actual core count.

## 2. `cpu_features`

Returns the union of `__builtin_cpu_supports` and `/proc/cpuinfo flags:` /
`Features:` tokens via the C++ `hwprobe` helper, falling back to a pure
Python parser. Fails if any name in `cpu.required_features` is missing.

- Default required: `["sse4_2"]`
- Unavailable when no flags are readable (non-Linux host or unsupported arch).
- Unit test mocks `_hwprobe.cpu_features()` to inject feature lists.

## 3. `memory_total`

`/proc/meminfo MemTotal`, converted from kB to bytes.

- Default threshold: 1 GiB
- Mocked in unit tests with pyfakefs against `/proc/meminfo`.
- Unavailable when `/proc/meminfo` is missing or malformed.

## 4. `memory_available`

`/proc/meminfo MemAvailable` (kernel-computed; preferred over MemFree+Cached).

- Default threshold: 256 MiB
- Same mocking strategy as `memory_total`.

## 5. `swap_disabled`

`/proc/meminfo SwapTotal == 0`. Skipped unless `memory.require_swap_disabled`
is true. Useful for embedded tiers where swap thrashes flash storage.

## 6. `disk_free`

`os.statvfs(disk.path).f_bavail * f_frsize`.

- Default path `/`, threshold 1 GiB
- Unit tests monkeypatch `os.statvfs` with a `NamedTuple`.

## 7. `loadavg_short`

`/proc/loadavg` 1-minute load. Fails when `load >= cpu_count * loadavg_factor`.

- Default factor: 1.5
- pyfakefs is used to inject `/proc/loadavg` content.

## 8. `kernel_version`

Compares `os.uname().release` against `system.min_kernel_version` using a
permissive semver parser (matches `MAJOR.MINOR[.PATCH]`, ignores suffixes).

## 9. `kernel_module_loaded`

Reads `/proc/modules` first column. Pass if any name in `system.required_modules`
is loaded. Skipped when the list is empty; unavailable when `/proc/modules` is
missing.

## 10. `clock_source`

Reads `/sys/devices/system/clocksource/clocksource0/current_clocksource` and
checks membership in `system.allowed_clocksources`. Default allowlist:
`tsc`, `kvm-clock`, `xen`, `arch_sys_counter`.

## 11. `time_sync`

Invokes `timedatectl show -p NTPSynchronized --value`. Pass when stdout is
`yes`. Unavailable when `timedatectl` is missing, returns non-zero, or times
out. Subprocess and `shutil.which` are monkeypatched in tests.

## 12. `thermal_max`

Globs `/sys/class/thermal/thermal_zone*/temp` and tests the maximum value
against `thermal.max_milli_celsius`. Unavailable when no zones exist.

## 13. `serial_port_present`

Resolves a serial path in this order:

1. `HW_PREFLIGHT_SERIAL_PATH` env var (used by CI/socat)
2. First match of `serial.by_id_glob` (default `/dev/serial/by-id/*`)
3. First file from `serial.candidate_paths` that exists

Pass if a path resolves; unavailable otherwise.

## 14. `serial_handshake`

Opens the resolved port at the configured baudrate, writes
`serial.handshake_send`, reads up to 64 bytes within
`serial.handshake_timeout_seconds`, and pattern-matches the response against
`serial.handshake_response_regex`.

CI reproduction:

```bash
socat -d -d pty,raw,echo=0 pty,raw,echo=0 &
# socat prints two pty paths to stderr; e.g. /dev/pts/3 and /dev/pts/4.
# Run a "device" that echoes OK\r\n on one end:
python -c "import serial; s = serial.Serial('/dev/pts/3'); \
    while True: \
        b = s.read(64) \
        if b: s.write(b'OK\r\n')" &
HW_PREFLIGHT_SERIAL_PATH=/dev/pts/4 hw-preflight run --json out.json
```

The full e2e test in `tests/e2e/test_serial_loopback.py` automates this.

## 15. `network_default_route`

`ip route show default`. Pass when at least one route line is returned;
unavailable when the binary is missing, the command fails, or no default
route exists (treated as informational rather than fail since CI runners
may run in isolated namespaces).

## 16. `gpio_chips`

Counts `gpiochip*` entries under `/sys/class/gpio`. With the default
threshold of 0, an absent subsystem returns `unavailable` (not `fail`),
because a server-class host is not expected to expose GPIO.

## 17. `i2c_bus_present`

Counts `/dev/i2c-*` entries. Default threshold 0; unavailable when none
present.

## 18. `service_unit_active`

For each unit in `service.units`, runs `systemctl is-active <unit>` and
expects `active`. Skipped when the list is empty (the default).

---

## Adding a new check

1. Create `src/hw_preflight/checks/<your_module>.py` (or extend an existing one).
2. Decorate with `@register_check("descriptive_snake_case_name")`.
3. Return `make_result(name, status, ...)` — never raise.
4. Add the module name to `src/hw_preflight/checks/__init__.py` so it's
   imported during package load.
5. Add a unit test under `tests/unit/`.
6. Update `tests/unit/test_runner.py::EXPECTED_CHECKS` so the count assertion
   stays accurate.
