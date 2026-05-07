"""IOMMU group enumeration (pci_iommu_groups).

Counts entries under ``/sys/kernel/iommu_groups/``; informational by
nature, the check passes when at least one group exists and reports
``unavailable`` when the directory is missing (kernel without IOMMU).
"""

from __future__ import annotations

from pathlib import Path

from hw_preflight.config import PreflightConfig

from ._base import CheckResult, make_result, register_check

_IOMMU_ROOT = "/sys/kernel/iommu_groups"


@register_check("pci_iommu_groups")
def pci_iommu_groups(config: PreflightConfig) -> CheckResult:
    base = Path(_IOMMU_ROOT)
    if not base.exists():
        return make_result(
            "pci_iommu_groups",
            "unavailable",
            reason=f"{_IOMMU_ROOT} not present (IOMMU not enabled)",
        )
    try:
        groups = sorted(p.name for p in base.iterdir() if p.is_dir())
    except OSError as exc:
        return make_result(
            "pci_iommu_groups",
            "unavailable",
            reason=f"could not enumerate iommu groups: {exc}",
        )
    measured = {"group_count": len(groups), "groups_preview": groups[:8]}
    if not groups:
        return make_result(
            "pci_iommu_groups",
            "unavailable",
            measured=measured,
            reason="iommu_groups directory empty (IOMMU enabled but no devices grouped)",
        )
    return make_result("pci_iommu_groups", "pass", measured=measured)


__all__ = ["pci_iommu_groups"]
