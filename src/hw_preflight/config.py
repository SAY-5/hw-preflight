"""Configuration model for hw-preflight thresholds and overrides."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class CpuConfig(BaseModel):
    min_count: int = 2
    required_features: list[str] = Field(default_factory=lambda: ["sse4_2"])


class MemoryConfig(BaseModel):
    min_total_bytes: int = 1 * 1024 * 1024 * 1024  # 1 GiB
    min_available_bytes: int = 256 * 1024 * 1024  # 256 MiB
    require_swap_disabled: bool = False


class DiskConfig(BaseModel):
    path: str = "/"
    min_free_bytes: int = 1 * 1024 * 1024 * 1024  # 1 GiB


class SystemConfig(BaseModel):
    loadavg_factor: float = 1.5
    min_kernel_version: str = "5.10.0"
    required_modules: list[str] = Field(default_factory=lambda: ["loop"])
    allowed_clocksources: list[str] = Field(
        default_factory=lambda: ["tsc", "kvm-clock", "xen", "arch_sys_counter"]
    )


class ThermalConfig(BaseModel):
    max_milli_celsius: int = 80000


class SerialConfig(BaseModel):
    candidate_paths: list[str] = Field(default_factory=lambda: ["/dev/ttyS0", "/dev/ttyUSB0"])
    by_id_glob: str = "/dev/serial/by-id/*"
    baudrate: int = 115200
    handshake_send: str = "AT\r\n"
    handshake_response_regex: str = r"^OK"
    handshake_timeout_seconds: float = 1.0


class GpioConfig(BaseModel):
    min_chips: int = 0
    min_i2c_buses: int = 0


class ServiceConfig(BaseModel):
    units: list[str] = Field(default_factory=list)


class RunnerConfig(BaseModel):
    per_check_timeout_seconds: float = 5.0
    enabled_checks: list[str] | None = None  # None = all
    disabled_checks: list[str] = Field(default_factory=list)
    parallelism: int = 1  # 1 = serial; >1 = thread pool size; <=0 means CPU count.


class PreflightConfig(BaseModel):
    cpu: CpuConfig = Field(default_factory=CpuConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    disk: DiskConfig = Field(default_factory=DiskConfig)
    system: SystemConfig = Field(default_factory=SystemConfig)
    thermal: ThermalConfig = Field(default_factory=ThermalConfig)
    serial: SerialConfig = Field(default_factory=SerialConfig)
    gpio: GpioConfig = Field(default_factory=GpioConfig)
    service: ServiceConfig = Field(default_factory=ServiceConfig)
    runner: RunnerConfig = Field(default_factory=RunnerConfig)


def load_config(path: Path | str | None) -> PreflightConfig:
    """Load configuration from YAML, falling back to defaults."""
    if path is None:
        return PreflightConfig()
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"config file not found: {p}")
    raw: dict[str, Any] = yaml.safe_load(p.read_text()) or {}
    return PreflightConfig.model_validate(raw)
