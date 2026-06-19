"""Plotting-only sign conventions for structural force diagrams.

These settings affect only the side on which diagram ordinates are drawn.
They do not change internal force recovery, result tables, or solver values.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ForceDiagramConvention:
    convention_name: str = "Ftool-style"
    moment_side: str = "tension"
    shear_positive_side: str = "top"
    axial_positive_side: str = "top"


def default_force_diagram_convention() -> ForceDiagramConvention:
    return ftool_force_diagram_convention()


def ftool_force_diagram_convention() -> ForceDiagramConvention:
    return ForceDiagramConvention(
        convention_name="Ftool-style",
        moment_side="tension",
        shear_positive_side="top",
        axial_positive_side="top",
    )


def internal_force_diagram_convention() -> ForceDiagramConvention:
    return ForceDiagramConvention(
        convention_name="Internal sign convention",
        moment_side="internal",
        shear_positive_side="internal",
        axial_positive_side="internal",
    )


def get_display_sign(quantity: str, convention: ForceDiagramConvention | None = None) -> float:
    """Return the plotting-only ordinate sign multiplier."""
    active = convention or default_force_diagram_convention()
    normalized = str(quantity).strip().lower()
    aliases = {"n": "axial", "v": "shear", "m": "moment"}
    normalized = aliases.get(normalized, normalized)

    if normalized == "moment":
        return _side_sign(active.moment_side, positive_side="compression", negative_side="tension")
    if normalized == "shear":
        return _side_sign(active.shear_positive_side, positive_side="top", negative_side="bottom")
    if normalized == "axial":
        return _side_sign(active.axial_positive_side, positive_side="top", negative_side="bottom")
    raise ValueError("quantity must be axial, shear, or moment.")


def _side_sign(side: str, positive_side: str, negative_side: str) -> float:
    normalized = str(side).strip().lower()
    if normalized in {"internal", positive_side}:
        return 1.0
    if normalized == negative_side:
        return -1.0
    raise ValueError(f"Unsupported diagram side: {side}")

