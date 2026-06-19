"""Built-in educational material presets for GUI model entry."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


_MATERIAL_PRESETS: dict[str, dict[str, Any]] = {
    "Steel S235": {
        "name": "Steel S235",
        "E": 200.0e9,
        "alpha": 1.2e-5,
        "density": 7850.0,
        "notes": "Typical structural steel preset. Density is metadata only.",
    },
    "Steel S355": {
        "name": "Steel S355",
        "E": 210.0e9,
        "alpha": 1.2e-5,
        "density": 7850.0,
        "notes": "Typical structural steel preset. Density is metadata only.",
    },
    "Concrete C25/30": {
        "name": "Concrete C25/30",
        "E": 31.0e9,
        "alpha": 1.0e-5,
        "density": 2500.0,
        "notes": "Educational concrete preset. Density is metadata only.",
    },
    "Concrete C30/37": {
        "name": "Concrete C30/37",
        "E": 33.0e9,
        "alpha": 1.0e-5,
        "density": 2500.0,
        "notes": "Educational concrete preset. Density is metadata only.",
    },
    "Aluminum": {
        "name": "Aluminum",
        "E": 70.0e9,
        "alpha": 2.3e-5,
        "density": 2700.0,
        "notes": "Generic aluminum preset. Density is metadata only.",
    },
}


def get_material_presets() -> dict[str, dict[str, Any]]:
    """Return a copy of all material presets keyed by preset name."""
    return deepcopy(_MATERIAL_PRESETS)


def get_material_preset_names() -> list[str]:
    """Return material preset names in display order."""
    return list(_MATERIAL_PRESETS)


def get_material_preset(name: str) -> dict[str, Any]:
    """Return one material preset by name.

    Matching is case-insensitive and ignores leading/trailing whitespace.
    """
    normalized = _normalize_name(name)
    for preset_name, preset in _MATERIAL_PRESETS.items():
        if _normalize_name(preset_name) == normalized:
            return deepcopy(preset)
    raise KeyError(f"Unknown material preset: {name}")


def _normalize_name(name: str) -> str:
    return str(name).strip().lower()

