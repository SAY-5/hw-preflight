# Configuration

`preflight.example.yaml` shows every threshold and toggle the runner accepts.
Pass a copy via `hw-preflight run --config path/to/preflight.yaml`. Anything
omitted falls back to the defaults defined in `src/hw_preflight/config.py`.

## Tiers

A useful pattern is one file per hardware tier — for example
`developer.yaml` (loose thresholds, optional checks disabled) versus
`production.yaml` (strict thresholds, services required active).

## Toggles vs thresholds

| Field | Type | Effect |
|---|---|---|
| `runner.enabled_checks` | list or null | When set, only these checks run |
| `runner.disabled_checks` | list | Always skipped |
| `cpu.required_features` | list | Empty list -> `cpu_features` returns `skip` |
| `memory.require_swap_disabled` | bool | False -> `swap_disabled` returns `skip` |
| `system.required_modules` | list | Empty -> `kernel_module_loaded` returns `skip` |
| `service.units` | list | Empty -> `service_unit_active` returns `skip` |
