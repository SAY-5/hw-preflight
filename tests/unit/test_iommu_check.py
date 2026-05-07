"""Unit tests for pci_iommu_groups."""

from __future__ import annotations

from pathlib import Path

import pytest

from hw_preflight.checks import iommu as imod
from hw_preflight.config import PreflightConfig


def test_iommu_groups_unavailable_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    real_exists = Path.exists

    def fake_exists(self: Path) -> bool:
        if str(self) == imod._IOMMU_ROOT:
            return False
        return real_exists(self)

    monkeypatch.setattr(Path, "exists", fake_exists)
    r = imod.pci_iommu_groups(PreflightConfig())
    assert r.status == "unavailable"


def test_iommu_groups_pass(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake_root = tmp_path / "iommu_groups"
    fake_root.mkdir()
    for n in ("0", "1", "2"):
        (fake_root / n).mkdir()

    real_exists = Path.exists
    real_iterdir = Path.iterdir
    real_is_dir = Path.is_dir

    def fake_exists(self: Path) -> bool:
        if str(self) == imod._IOMMU_ROOT:
            return True
        return real_exists(self)

    def fake_iterdir(self: Path) -> object:
        if str(self) == imod._IOMMU_ROOT:
            return iter(fake_root.iterdir())
        return real_iterdir(self)

    def fake_is_dir(self: Path) -> bool:
        if str(self).startswith(str(fake_root)):
            return real_is_dir(self)
        return real_is_dir(self)

    monkeypatch.setattr(Path, "exists", fake_exists)
    monkeypatch.setattr(Path, "iterdir", fake_iterdir)
    monkeypatch.setattr(Path, "is_dir", fake_is_dir)
    r = imod.pci_iommu_groups(PreflightConfig())
    assert r.status == "pass"
    assert r.measured is not None
    assert r.measured["group_count"] == 3


def test_iommu_groups_empty(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake_root = tmp_path / "iommu_groups"
    fake_root.mkdir()

    real_exists = Path.exists
    real_iterdir = Path.iterdir

    def fake_exists(self: Path) -> bool:
        if str(self) == imod._IOMMU_ROOT:
            return True
        return real_exists(self)

    def fake_iterdir(self: Path) -> object:
        if str(self) == imod._IOMMU_ROOT:
            return iter([])
        return real_iterdir(self)

    monkeypatch.setattr(Path, "exists", fake_exists)
    monkeypatch.setattr(Path, "iterdir", fake_iterdir)
    r = imod.pci_iommu_groups(PreflightConfig())
    assert r.status == "unavailable"


def test_iommu_groups_oserror(monkeypatch: pytest.MonkeyPatch) -> None:
    real_exists = Path.exists

    def fake_exists(self: Path) -> bool:
        if str(self) == imod._IOMMU_ROOT:
            return True
        return real_exists(self)

    def fake_iterdir(self: Path) -> object:
        if str(self) == imod._IOMMU_ROOT:
            raise OSError("EACCES")
        return iter([])

    monkeypatch.setattr(Path, "exists", fake_exists)
    monkeypatch.setattr(Path, "iterdir", fake_iterdir)
    r = imod.pci_iommu_groups(PreflightConfig())
    assert r.status == "unavailable"
