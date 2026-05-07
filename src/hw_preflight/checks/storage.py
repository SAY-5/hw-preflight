"""Storage-adjacent checks: nvme_smart, usb_device_count.

Both checks emit ``unavailable`` when the underlying interface is missing
on the host so they integrate cleanly with general-purpose CI.
"""

from __future__ import annotations

import glob
import shutil
import subprocess
from pathlib import Path

from hw_preflight.config import PreflightConfig

from ._base import CheckResult, make_result, register_check

_USB_DEVICES_GLOB = "/sys/bus/usb/devices/*"


@register_check("nvme_smart")
def nvme_smart(config: PreflightConfig) -> CheckResult:
    """Read SMART data via ``nvme smart-log`` if available.

    Pass requires ``critical_warning`` to be ``0``. Without ``nvme-cli`` or
    any ``/dev/nvme*`` device, the result is ``unavailable``.
    """
    expected = {"critical_warning": 0}
    bin_path = shutil.which("nvme")
    if bin_path is None:
        return make_result(
            "nvme_smart",
            "unavailable",
            expected=expected,
            reason="nvme(8) not on PATH",
        )
    devices = sorted(glob.glob("/dev/nvme[0-9]*"))
    primary = next(
        (d for d in devices if d.removeprefix("/dev/").startswith("nvme") and d.endswith("n1")),
        None,
    ) or (devices[0] if devices else None)
    if primary is None:
        return make_result(
            "nvme_smart",
            "unavailable",
            expected=expected,
            reason="no /dev/nvme* devices present",
        )
    try:
        result = subprocess.run(
            [bin_path, "smart-log", primary],
            capture_output=True,
            text=True,
            timeout=3.0,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return make_result(
            "nvme_smart",
            "unavailable",
            expected=expected,
            reason=f"nvme smart-log invocation failed: {exc}",
        )
    if result.returncode != 0:
        return make_result(
            "nvme_smart",
            "unavailable",
            measured={"returncode": result.returncode, "stderr": result.stderr.strip()[:200]},
            expected=expected,
            reason=f"nvme smart-log exited {result.returncode} (likely EACCES without CAP_SYS_RAWIO)",
        )
    critical = _parse_smart_critical_warning(result.stdout)
    measured: dict[str, object] = {"device": primary, "critical_warning": critical}
    if critical is None:
        return make_result(
            "nvme_smart",
            "unavailable",
            measured=measured,
            expected=expected,
            reason="could not parse critical_warning from nvme smart-log output",
        )
    if critical == 0:
        return make_result("nvme_smart", "pass", measured=measured, expected=expected)
    return make_result(
        "nvme_smart",
        "fail",
        measured=measured,
        expected=expected,
        reason=f"critical_warning={critical}, expected 0",
    )


def _parse_smart_critical_warning(stdout: str) -> int | None:
    """Extract the integer critical_warning bitmap from ``nvme smart-log`` text.

    The line typically reads ``critical_warning : 0`` (decimal) or
    ``critical_warning : 0x00`` (hex).
    """
    for line in stdout.splitlines():
        lower = line.strip().lower()
        if not lower.startswith("critical_warning"):
            continue
        _, _, rhs = lower.partition(":")
        token = rhs.strip().split()[0] if rhs.strip() else ""
        if not token:
            return None
        try:
            return int(token, 16) if token.startswith("0x") else int(token)
        except ValueError:
            return None
    return None


@register_check("usb_device_count")
def usb_device_count(config: PreflightConfig) -> CheckResult:
    """Count entries under ``/sys/bus/usb/devices/``.

    Reports ``unavailable`` if the path is missing (kernel built without
    USB), and ``pass`` whenever a count is obtainable. The check is
    informational — there is no minimum threshold because most hosts have
    legitimate zero-device configurations (cloud VMs).
    """
    base_dir = Path("/sys/bus/usb/devices")
    if not base_dir.exists():
        return make_result(
            "usb_device_count",
            "unavailable",
            reason="/sys/bus/usb/devices not present",
        )
    entries = sorted(p.name for p in base_dir.iterdir())
    measured = {"count": len(entries), "entries": entries[:32]}
    return make_result(
        "usb_device_count",
        "pass",
        measured=measured,
    )


__all__ = ["_parse_smart_critical_warning", "nvme_smart", "usb_device_count"]
