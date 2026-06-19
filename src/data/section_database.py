"""Built-in educational section presets for GUI model entry."""

from __future__ import annotations

from copy import deepcopy
from math import pi
from typing import Any


def make_rectangular_section(name: str, b: float, h: float) -> dict[str, Any]:
    """Create a rectangular section dictionary using SI units."""
    width = float(b)
    depth = float(h)
    return {
        "name": name,
        "A": width * depth,
        "I": width * depth**3 / 12.0,
        "d": depth,
        "shape": "rectangular",
        "category": "concrete/rectangular",
        "notes": "Rectangular preset using A=b*h and I=b*h^3/12.",
    }


def make_circular_section(name: str, D: float) -> dict[str, Any]:
    """Create a circular section dictionary using SI units."""
    diameter = float(D)
    return {
        "name": name,
        "A": pi * diameter**2 / 4.0,
        "I": pi * diameter**4 / 64.0,
        "d": diameter,
        "shape": "circular",
        "category": "concrete/circular",
        "notes": "Circular preset using A=pi*D^2/4 and I=pi*D^4/64.",
    }


_SECTION_PRESETS: dict[str, dict[str, Any]] = {
    "RC 300x300": make_rectangular_section("RC 300x300", 0.30, 0.30),
    "RC 400x400": make_rectangular_section("RC 400x400", 0.40, 0.40),
    "RC 500x500": make_rectangular_section("RC 500x500", 0.50, 0.50),
    "Beam 300x500": make_rectangular_section("Beam 300x500", 0.30, 0.50),
    "Beam 300x600": make_rectangular_section("Beam 300x600", 0.30, 0.60),
    "Beam 400x700": make_rectangular_section("Beam 400x700", 0.40, 0.70),
    "Circular D300": make_circular_section("Circular D300", 0.30),
    "Circular D500": make_circular_section("Circular D500", 0.50),
    "Steel IPE200 approx": {
        "name": "Steel IPE200 approx",
        "A": 2.85e-3,
        "I": 1.94e-5,
        "d": 0.20,
        "shape": "steel I",
        "category": "steel/approximate",
        "notes": "Approximate educational preset; verify before design use.",
    },
    "Steel IPE300 approx": {
        "name": "Steel IPE300 approx",
        "A": 5.38e-3,
        "I": 8.36e-5,
        "d": 0.30,
        "shape": "steel I",
        "category": "steel/approximate",
        "notes": "Approximate educational preset; verify before design use.",
    },
    "Steel HEA200 approx": {
        "name": "Steel HEA200 approx",
        "A": 5.38e-3,
        "I": 3.69e-5,
        "d": 0.19,
        "shape": "steel H",
        "category": "steel/approximate",
        "notes": "Approximate educational preset; verify before design use.",
    },
    "Steel HEA300 approx": {
        "name": "Steel HEA300 approx",
        "A": 1.13e-2,
        "I": 1.83e-4,
        "d": 0.29,
        "shape": "steel H",
        "category": "steel/approximate",
        "notes": "Approximate educational preset; verify before design use.",
    },
}


def get_section_presets() -> dict[str, dict[str, Any]]:
    """Return a copy of all section presets keyed by preset name."""
    return deepcopy(_SECTION_PRESETS)


def get_section_preset_names() -> list[str]:
    """Return section preset names in display order."""
    return list(_SECTION_PRESETS)


def get_section_preset(name: str) -> dict[str, Any]:
    """Return one section preset by name.

    Matching is case-insensitive and ignores leading/trailing whitespace.
    """
    normalized = _normalize_name(name)
    for preset_name, preset in _SECTION_PRESETS.items():
        if _normalize_name(preset_name) == normalized:
            return deepcopy(preset)
    raise KeyError(f"Unknown section preset: {name}")


def _normalize_name(name: str) -> str:
    return str(name).strip().lower()

