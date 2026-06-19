"""Unit-system metadata for labels and saved models.

This module intentionally performs no numerical conversion.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class UnitSystem:
    name: str = "N-m-C-kg"
    force: str = "N"
    length: str = "m"
    mass: str = "kg"
    temperature: str = "C"
    time: str = "s"
    rotation: str = "rad"

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


_PRESETS = {
    "N-m-C-kg": UnitSystem(),
    "kN-m-C-tonne": UnitSystem("kN-m-C-tonne", "kN", "m", "tonne", "C", "s", "rad"),
    "N-mm-C-kg": UnitSystem("N-mm-C-kg", "N", "mm", "kg", "C", "s", "rad"),
    "kip-ft-F-slug": UnitSystem("kip-ft-F-slug", "kip", "ft", "slug", "F", "s", "rad"),
    "kip-in-F-slug": UnitSystem("kip-in-F-slug", "kip", "in", "slug", "F", "s", "rad"),
}


def default_unit_system() -> UnitSystem:
    return UnitSystem()


def get_unit_preset_names() -> list[str]:
    return list(_PRESETS)


def get_unit_preset(name: str) -> UnitSystem:
    normalized = str(name).strip().lower()
    for preset_name, preset in _PRESETS.items():
        if preset_name.lower() == normalized:
            return preset
    raise KeyError(f"Unknown unit preset: {name}")


def normalize_unit_system(units: UnitSystem | dict[str, Any] | None) -> UnitSystem:
    if isinstance(units, UnitSystem):
        return units
    if not units:
        return default_unit_system()
    default = default_unit_system()
    return UnitSystem(
        name=str(units.get("name", default.name)),
        force=str(units.get("force", default.force)),
        length=str(units.get("length", default.length)),
        mass=str(units.get("mass", default.mass)),
        temperature=str(units.get("temperature", default.temperature)),
        time=str(units.get("time", default.time)),
        rotation=str(units.get("rotation", default.rotation)),
    )


def unit_label(quantity: str, units: UnitSystem | dict[str, Any] | None = None) -> str:
    system = normalize_unit_system(units)
    labels = {
        "displacement": system.length,
        "length": system.length,
        "rotation": system.rotation,
        "force": system.force,
        "moment": f"{system.force}-{system.length}",
        "stiffness_translational": f"{system.force}/{system.length}",
        "stiffness_rotational": f"{system.force}-{system.length}/{system.rotation}",
        "mass": system.mass,
        "temperature": system.temperature,
        "time": system.time,
        "period": system.time,
        "frequency": "Hz",
        "angular_frequency": f"{system.rotation}/{system.time}",
        "acceleration": f"{system.length}/{system.time}^2",
        "dimensionless": "-",
    }
    key = str(quantity).strip().lower()
    if key not in labels:
        raise KeyError(f"Unknown unit quantity: {quantity}")
    return labels[key]


def result_column_label(
    base_name: str,
    quantity: str,
    units: UnitSystem | dict[str, Any] | None = None,
) -> str:
    return f"{base_name} [{unit_label(quantity, units)}]"

