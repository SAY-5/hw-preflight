# hw-preflight report

- host: `localhost` (kernel `25.0.0`, 10 CPUs)
- started: `2026-05-07T08:34:49.191654+00:00`
- finished: `2026-05-07T08:34:49.194511+00:00`
- summary: 3 pass / 0 fail / 2 skip / 13 unavailable (18 total)

## Checks

| # | Check | Status | Duration (ms) | Detail |
|---|---|---|---:|---|
| 1 | `clock_source` | UNAVAIL | 0.25 | /sys/devices/system/clocksource/clocksource0/current_clocksource not present |
| 2 | `cpu_count` | PASS | 0.15 | {'cpu_count': 10} |
| 3 | `cpu_features` | UNAVAIL | 0.12 | no CPU feature flags readable (non-Linux host or unsupported arch) |
| 4 | `disk_free` | PASS | 0.10 | {'free_bytes': 8991776768, 'path': '/'} |
| 5 | `gpio_chips` | UNAVAIL | 0.08 | /sys/class/gpio not present (no GPIO subsystem on host) |
| 6 | `i2c_bus_present` | UNAVAIL | 0.31 | no /dev/i2c-* nodes (no I2C buses on host) |
| 7 | `kernel_module_loaded` | UNAVAIL | 0.07 | /proc/modules not present |
| 8 | `kernel_version` | PASS | 0.12 | {'parsed': [25, 0, 0], 'release': '25.0.0'} |
| 9 | `loadavg_short` | UNAVAIL | 0.09 | /proc/loadavg not present |
| 10 | `memory_available` | UNAVAIL | 0.08 | /proc/meminfo missing MemAvailable |
| 11 | `memory_total` | UNAVAIL | 0.08 | /proc/meminfo missing MemTotal |
| 12 | `network_default_route` | UNAVAIL | 0.27 | ip(8) not on PATH |
| 13 | `serial_handshake` | UNAVAIL | 0.22 | no serial port resolved |
| 14 | `serial_port_present` | UNAVAIL | 0.17 | no serial port found via env, by-id glob, or candidate list |
| 15 | `service_unit_active` | SKIP | 0.08 | no service units configured |
| 16 | `swap_disabled` | SKIP | 0.06 | swap-disabled requirement not enforced by config |
| 17 | `thermal_max` | UNAVAIL | 0.09 | no thermal zones in /sys/class/thermal |
| 18 | `time_sync` | UNAVAIL | 0.22 | timedatectl not on PATH |

## Failures and unavailable

### `clock_source` — unavailable

- reason: /sys/devices/system/clocksource/clocksource0/current_clocksource not present
- expected: `{'allowed': ['tsc', 'kvm-clock', 'xen', 'arch_sys_counter']}`

### `cpu_features` — unavailable

- reason: no CPU feature flags readable (non-Linux host or unsupported arch)
- expected: `{'required': ['sse4_2']}`
- measured: `{'extension_available': False, 'feature_count': 0}`

### `gpio_chips` — unavailable

- reason: /sys/class/gpio not present (no GPIO subsystem on host)
- expected: `{'min_chips': 0}`

### `i2c_bus_present` — unavailable

- reason: no /dev/i2c-* nodes (no I2C buses on host)
- expected: `{'min_buses': 0}`
- measured: `{'bus_count': 0, 'buses': []}`

### `kernel_module_loaded` — unavailable

- reason: /proc/modules not present
- expected: `{'any_of': ['loop']}`

### `loadavg_short` — unavailable

- reason: /proc/loadavg not present

### `memory_available` — unavailable

- reason: /proc/meminfo missing MemAvailable
- expected: `{'min_bytes': 268435456}`

### `memory_total` — unavailable

- reason: /proc/meminfo missing MemTotal
- expected: `{'min_bytes': 1073741824}`

### `network_default_route` — unavailable

- reason: ip(8) not on PATH

### `serial_handshake` — unavailable

- reason: no serial port resolved
- expected: `{'baud': 115200, 'response_regex': '^OK', 'send': 'AT\r\n', 'timeout_seconds': 1.0}`

### `serial_port_present` — unavailable

- reason: no serial port found via env, by-id glob, or candidate list
- expected: `{'by_id_glob': '/dev/serial/by-id/*', 'candidates': ['/dev/ttyS0', '/dev/ttyUSB0'], 'env_override': 'HW_PREFLIGHT_SERIAL_PATH'}`

### `thermal_max` — unavailable

- reason: no thermal zones in /sys/class/thermal
- expected: `{'max_milli_celsius': 80000}`

### `time_sync` — unavailable

- reason: timedatectl not on PATH

