"""Wrapper around the C++ ``hwprobe`` helper with a pure-Python fallback.

The C++ helper is built via CMake + pybind11 and exposes:

* ``cpu_features()`` - list of CPU feature flags
* ``dmi_fields()``   - dict of /sys/class/dmi/id/* values

If the compiled extension is unavailable (e.g. the user installed the wheel
without building C++, or the platform is non-Linux), this module falls back
to parsing /proc/cpuinfo and reading /sys/class/dmi/id directly. Both paths
read the same underlying kernel data; the C++ binding exists to demonstrate
the integration pattern and to keep CPUID detection runtime-checked rather
than parser-checked when the helper is available.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

_hwprobe_ext: Any
try:  # pragma: no cover - imports depend on build system
    # The compiled extension is built by CMake; at type-check time it does
    # not exist. The runtime fallback below handles ImportError cleanly.
    from hw_preflight import _hwprobe_ext as _ext_mod  # type: ignore[attr-defined]

    _hwprobe_ext = _ext_mod
    _EXT_AVAILABLE = True
except ImportError:  # pragma: no cover
    _hwprobe_ext = None
    _EXT_AVAILABLE = False


def extension_available() -> bool:
    """Return True if the compiled C++ extension is loaded."""
    return _EXT_AVAILABLE


def cpu_features() -> list[str]:
    """Return the list of CPU feature flags reported by the kernel.

    Prefers the C++ helper (which combines ``__builtin_cpu_supports`` with
    /proc/cpuinfo flag parsing). Falls back to /proc/cpuinfo when the
    extension is not loaded.
    """
    if _EXT_AVAILABLE:
        return list(_hwprobe_ext.cpu_features())
    return _features_from_cpuinfo()


def _features_from_cpuinfo(path: str = "/proc/cpuinfo") -> list[str]:
    p = Path(path)
    if not p.exists():
        return []
    text = p.read_text(errors="replace")
    for line in text.splitlines():
        # x86 uses "flags", arm64 uses "Features"
        lower = line.lower()
        if lower.startswith("flags") or lower.startswith("features"):
            _, _, rhs = line.partition(":")
            return [tok for tok in rhs.strip().split() if tok]
    return []


def dmi_fields() -> dict[str, str]:
    """Return DMI fields (vendor, product name, etc.) from /sys/class/dmi/id."""
    if _EXT_AVAILABLE:
        return dict(_hwprobe_ext.dmi_fields())
    return _dmi_from_sysfs()


def _dmi_from_sysfs(root: str = "/sys/class/dmi/id") -> dict[str, str]:
    out: dict[str, str] = {}
    base = Path(root)
    if not base.exists():
        return out
    for entry in sorted(base.iterdir()):
        if not entry.is_file():
            continue
        try:
            value = entry.read_text(errors="replace").strip()
        except OSError:
            continue
        if value:
            out[entry.name] = value
    return out


def info() -> dict[str, Any]:
    """Diagnostic dump used by tests and the CLI."""
    return {
        "extension_available": _EXT_AVAILABLE,
        "cpu_count": os.cpu_count(),
        "feature_count": len(cpu_features()),
    }
