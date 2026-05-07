"""Tests for the _hwprobe Python wrapper (fallback paths)."""

from __future__ import annotations

from pathlib import Path

import pytest

from hw_preflight import _hwprobe


def test_extension_available_is_bool() -> None:
    assert isinstance(_hwprobe.extension_available(), bool)


def test_info_shape() -> None:
    out = _hwprobe.info()
    assert set(out.keys()) == {"extension_available", "cpu_count", "feature_count"}
    assert isinstance(out["feature_count"], int)
    assert isinstance(out["cpu_count"], int) or out["cpu_count"] is None


def test_features_from_cpuinfo_missing(tmp_path: Path) -> None:
    # Path that does not exist -> empty.
    missing = tmp_path / "no_such_cpuinfo"
    assert _hwprobe._features_from_cpuinfo(str(missing)) == []


def test_features_from_cpuinfo_x86(tmp_path: Path) -> None:
    p = tmp_path / "cpuinfo"
    p.write_text(
        "processor\t: 0\n"
        "vendor_id\t: GenuineIntel\n"
        "flags\t\t: fpu vme sse4_2 avx avx2\n"
        "model\t\t: 158\n"
    )
    out = _hwprobe._features_from_cpuinfo(str(p))
    assert "fpu" in out
    assert "sse4_2" in out
    assert "avx2" in out


def test_features_from_cpuinfo_arm(tmp_path: Path) -> None:
    p = tmp_path / "cpuinfo"
    p.write_text("processor\t: 0\n" "Features\t: fp asimd evtstrm aes pmull\n")
    out = _hwprobe._features_from_cpuinfo(str(p))
    # x86 fallback only reads the literal "flags:" prefix; the case here is
    # that nothing matches and we get an empty list. The C++ helper handles
    # arm64; this branch documents the fallback's narrower scope.
    assert out == [] or "asimd" in out


def test_features_from_cpuinfo_no_match(tmp_path: Path) -> None:
    p = tmp_path / "cpuinfo"
    p.write_text("processor\t: 0\nmodel name\t: tiny\n")
    out = _hwprobe._features_from_cpuinfo(str(p))
    assert out == []


def test_dmi_from_sysfs_missing(tmp_path: Path) -> None:
    out = _hwprobe._dmi_from_sysfs(str(tmp_path / "no_such_dir"))
    assert out == {}


def test_dmi_from_sysfs_reads_files(tmp_path: Path) -> None:
    (tmp_path / "sys_vendor").write_text("ACME Corp\n")
    (tmp_path / "product_name").write_text("Whirligig 9000\n")
    (tmp_path / "ignored").write_text("")  # empty file is skipped
    sub = tmp_path / "subdir"
    sub.mkdir()
    out = _hwprobe._dmi_from_sysfs(str(tmp_path))
    assert out["sys_vendor"] == "ACME Corp"
    assert out["product_name"] == "Whirligig 9000"
    assert "ignored" not in out
    assert "subdir" not in out


def test_dmi_from_sysfs_skips_unreadable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    f = tmp_path / "x"
    f.write_text("ok\n")

    real_read = Path.read_text

    def boom(self: Path, *a: object, **kw: object) -> str:
        if self.name == "x":
            raise OSError("fake EACCES")
        return real_read(self, *a, **kw)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "read_text", boom)
    out = _hwprobe._dmi_from_sysfs(str(tmp_path))
    assert out == {}


def test_cpu_features_returns_list() -> None:
    """Public function must return a list (extension or fallback)."""
    out = _hwprobe.cpu_features()
    assert isinstance(out, list)
    for tok in out:
        assert isinstance(tok, str)


def test_dmi_fields_returns_dict() -> None:
    out = _hwprobe.dmi_fields()
    assert isinstance(out, dict)
    for k, v in out.items():
        assert isinstance(k, str)
        assert isinstance(v, str)
