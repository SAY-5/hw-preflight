# hw-preflight report

- host: `ubuntu-runner` (kernel `6.17.0-1010-azure`, 4 CPUs)
- started: `2026-05-07T08:47:31.870149+00:00`
- finished: `2026-05-07T08:47:31.952682+00:00`
- summary: 11 pass / 1 fail / 2 skip / 4 unavailable (18 total)

## Checks

| # | Check | Status | Duration (ms) | Detail |
|---|---|---|---:|---|
| 1 | `clock_source` | PASS | 0.51 | {'current': 'tsc'} |
| 2 | `cpu_count` | PASS | 0.28 | {'cpu_count': 4} |
| 3 | `cpu_features` | PASS | 0.41 | {'extension_available': False, 'feature_count': 102} |
| 4 | `disk_free` | PASS | 0.18 | {'free_bytes': 95243603968, 'path': '/'} |
| 5 | `gpio_chips` | UNAVAIL | 0.28 | no gpiochips exposed |
| 6 | `i2c_bus_present` | UNAVAIL | 0.51 | no /dev/i2c-* nodes (no I2C buses on host) |
| 7 | `kernel_module_loaded` | FAIL | 0.35 | none of ['loop'] loaded |
| 8 | `kernel_version` | PASS | 0.32 | {'parsed': [6, 17, 0], 'release': '6.17.0-1010-azure'} |
| 9 | `loadavg_short` | PASS | 0.28 | {'cpu_count': 4, 'loadavg_1min': 1.28} |
| 10 | `memory_available` | PASS | 0.35 | {'bytes': 15627517952} |
| 11 | `memory_total` | PASS | 0.32 | {'bytes': 16766431232} |
| 12 | `network_default_route` | PASS | 1.86 | {'routes': ['default via 10.1.0.1 dev eth0 proto dhcp src 10.1.1.133 metric 1... |
| 13 | `serial_handshake` | UNAVAIL | 1.79 | serial error: [Errno 13] could not open port /dev/ttyS0: [Errno 13] Permission denied: '/dev/ttyS0' |
| 14 | `serial_port_present` | PASS | 0.27 | {'path': '/dev/ttyS0'} |
| 15 | `service_unit_active` | SKIP | 0.17 | no service units configured |
| 16 | `swap_disabled` | SKIP | 0.15 | swap-disabled requirement not enforced by config |
| 17 | `thermal_max` | UNAVAIL | 0.28 | no thermal zones in /sys/class/thermal |
| 18 | `time_sync` | PASS | 73.93 | {'ntp_synchronized': 'yes'} |

## Failures and unavailable

### `gpio_chips` — unavailable

- reason: no gpiochips exposed
- expected: `{'min_chips': 0}`
- measured: `{'chip_count': 0, 'chips': []}`

### `i2c_bus_present` — unavailable

- reason: no /dev/i2c-* nodes (no I2C buses on host)
- expected: `{'min_buses': 0}`
- measured: `{'bus_count': 0, 'buses': []}`

### `kernel_module_loaded` — fail

- reason: none of ['loop'] loaded
- expected: `{'any_of': ['loop']}`
- measured: `{'found': [], 'loaded_count': 57}`

### `serial_handshake` — unavailable

- reason: serial error: [Errno 13] could not open port /dev/ttyS0: [Errno 13] Permission denied: '/dev/ttyS0'
- expected: `{'baud': 115200, 'response_regex': '^OK', 'send': 'AT\r\n', 'timeout_seconds': 1.0}`
- measured: `{'error': "serial error: [Errno 13] could not open port /dev/ttyS0: [Errno 13] Permission denied: '/dev/ttyS0'", 'path': '/dev/ttyS0'}`

### `thermal_max` — unavailable

- reason: no thermal zones in /sys/class/thermal
- expected: `{'max_milli_celsius': 80000}`

