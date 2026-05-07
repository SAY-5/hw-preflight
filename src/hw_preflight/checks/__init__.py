"""Auto-imported check modules.

Importing this package side-effect-registers every check via ``@register_check``.
"""

from __future__ import annotations

# Register order is irrelevant; runner sorts by name.
from . import (  # noqa: F401
    clocks,
    cpu,
    disk,
    gpio,
    iommu,
    memory,
    network,
    security,
    serial,
    service,
    storage,
    system,
    thermal,
)
