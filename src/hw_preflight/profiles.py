"""Declarative profile system.

A profile is a YAML config file selected by short name. Built-in profiles
ship under ``config/profiles/<name>.yaml``; users can also pass an
absolute path. Profile contents are validated as a regular
:class:`PreflightConfig` — there is no separate schema.

CLI usage::

    hw-preflight run --profile production-server
    hw-preflight run --profile /etc/hw-preflight/custom.yaml
"""

from __future__ import annotations

from pathlib import Path

from .config import PreflightConfig, load_config

# Resolve the bundled profiles directory by walking up from this module to
# the repo root. Wheels installed via pip ship the profile YAMLs alongside
# the package; resilience is provided by also accepting absolute paths.
_THIS = Path(__file__).resolve()
_BUILTIN_PROFILE_DIRS = [
    _THIS.parent.parent.parent / "config" / "profiles",  # source layout
    _THIS.parent / "_profiles",  # installed-package layout (future)
]

BUILTIN_PROFILES = ("production-server", "edge-device", "ci-runner")


def list_profiles() -> list[str]:
    """Return built-in profile names known to ship with this distribution."""
    found: set[str] = set()
    for d in _BUILTIN_PROFILE_DIRS:
        if d.exists():
            for p in d.glob("*.yaml"):
                found.add(p.stem)
    # If the source tree is unavailable (installed-only), fall back to
    # the curated list so callers always get a deterministic answer.
    return sorted(found) if found else sorted(BUILTIN_PROFILES)


def resolve_profile_path(name: str) -> Path:
    """Resolve a profile name (or path) to an absolute YAML file path.

    Lookup order:

    1. If ``name`` is an existing path, return it verbatim.
    2. Search the built-in profile directories for ``<name>.yaml``.

    Raises :class:`FileNotFoundError` when nothing matches; the message
    enumerates the directories that were searched and the built-in names
    that were available, so a typo's failure mode is informative.
    """
    candidate = Path(name)
    if candidate.exists() and candidate.is_file():
        return candidate.resolve()
    for d in _BUILTIN_PROFILE_DIRS:
        p = d / f"{name}.yaml"
        if p.exists():
            return p.resolve()
    searched = ", ".join(str(d) for d in _BUILTIN_PROFILE_DIRS)
    available = ", ".join(list_profiles())
    raise FileNotFoundError(
        f"profile {name!r} not found; searched {searched}; available: {available}"
    )


def load_profile(name: str) -> PreflightConfig:
    """Load a profile by short name (or path) into a validated config."""
    return load_config(resolve_profile_path(name))


__all__ = ["BUILTIN_PROFILES", "list_profiles", "load_profile", "resolve_profile_path"]
