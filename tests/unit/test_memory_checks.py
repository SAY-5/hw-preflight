"""Unit tests for memory checks using pyfakefs."""

from __future__ import annotations

from hw_preflight.checks import memory as memmod
from hw_preflight.config import PreflightConfig

MEMINFO_OK = (
    "MemTotal:       16384000 kB\n"
    "MemFree:         8192000 kB\n"
    "MemAvailable:   12000000 kB\n"
    "SwapTotal:             0 kB\n"
)

MEMINFO_LOW = (
    "MemTotal:         500000 kB\n"
    "MemFree:           50000 kB\n"
    "MemAvailable:     100000 kB\n"
    "SwapTotal:        200000 kB\n"
)

MEMINFO_GARBAGE = "this is not /proc/meminfo\n"


def test_read_meminfo_ok(fs) -> None:  # type: ignore[no-untyped-def]
    fs.create_file("/proc/meminfo", contents=MEMINFO_OK)
    info = memmod._read_meminfo()
    assert info["MemTotal"] == 16384000 * 1024
    assert info["MemAvailable"] == 12000000 * 1024
    assert info["SwapTotal"] == 0


def test_read_meminfo_missing(fs) -> None:  # type: ignore[no-untyped-def]
    info = memmod._read_meminfo()
    assert info == {}


def test_memory_total_pass(fs) -> None:  # type: ignore[no-untyped-def]
    fs.create_file("/proc/meminfo", contents=MEMINFO_OK)
    cfg = PreflightConfig()
    r = memmod.memory_total(cfg)
    assert r.status == "pass"


def test_memory_total_fail(fs) -> None:  # type: ignore[no-untyped-def]
    fs.create_file("/proc/meminfo", contents=MEMINFO_LOW)
    cfg = PreflightConfig()
    r = memmod.memory_total(cfg)
    assert r.status == "fail"


def test_memory_total_unavailable(fs) -> None:  # type: ignore[no-untyped-def]
    fs.create_file("/proc/meminfo", contents=MEMINFO_GARBAGE)
    cfg = PreflightConfig()
    r = memmod.memory_total(cfg)
    assert r.status == "unavailable"


def test_memory_available_boundary(fs) -> None:  # type: ignore[no-untyped-def]
    fs.create_file("/proc/meminfo", contents=MEMINFO_OK)
    cfg = PreflightConfig()
    cfg.memory.min_available_bytes = 12_000_000 * 1024  # exact boundary
    r = memmod.memory_available(cfg)
    assert r.status == "pass"


def test_swap_disabled_skip_default(fs) -> None:  # type: ignore[no-untyped-def]
    fs.create_file("/proc/meminfo", contents=MEMINFO_OK)
    r = memmod.swap_disabled(PreflightConfig())
    assert r.status == "skip"


def test_swap_disabled_pass(fs) -> None:  # type: ignore[no-untyped-def]
    fs.create_file("/proc/meminfo", contents=MEMINFO_OK)
    cfg = PreflightConfig()
    cfg.memory.require_swap_disabled = True
    r = memmod.swap_disabled(cfg)
    assert r.status == "pass"


def test_swap_disabled_fail(fs) -> None:  # type: ignore[no-untyped-def]
    fs.create_file("/proc/meminfo", contents=MEMINFO_LOW)
    cfg = PreflightConfig()
    cfg.memory.require_swap_disabled = True
    r = memmod.swap_disabled(cfg)
    assert r.status == "fail"
    assert r.measured is not None
    assert r.measured["swap_total_bytes"] == 200000 * 1024
