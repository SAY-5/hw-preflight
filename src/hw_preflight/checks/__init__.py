"""Auto-imported check modules.

Importing this package side-effect-registers every check via ``@register_check``.
"""

from __future__ import annotations

# Register order is irrelevant; runner sorts by name.
from . import (  # noqa: F401
    cpu,
    disk,
    gpio,
    memory,
    network,
    serial,
    service,
    system,
    thermal,
)
