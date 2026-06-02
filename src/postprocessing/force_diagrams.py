"""Diagram-data helpers built from recovered local member-end forces.

First-version assumptions:
- Samples are based only on recovered local end forces.
- Internal distributed and point member loads are not re-applied here.
- Right-end force signs are flipped so both endpoints are expressed with one
  left-to-right local member diagram convention.
"""

from __future__ import annotations

from typing import Any


def axial_force_diagram(member_force: dict[str, Any], length: float, n_points: int = 2) -> dict[str, list[float]]:
    """Return axial-force sample arrays for one element."""
    return _linear_diagram(
        length,
        member_force["node_i"]["nx"],
        -member_force["node_j"]["nx"],
        n_points,
    )


def shear_force_diagram(member_force: dict[str, Any], length: float, n_points: int = 2) -> dict[str, list[float]]:
    """Return shear-force sample arrays for one frame element."""
    return _linear_diagram(
        length,
        member_force["node_i"]["vy"],
        -member_force["node_j"]["vy"],
        n_points,
    )


def bending_moment_diagram(member_force: dict[str, Any], length: float, n_points: int = 2) -> dict[str, list[float]]:
    """Return bending-moment sample arrays for one frame element."""
    return _linear_diagram(
        length,
        member_force["node_i"]["mz"],
        -member_force["node_j"]["mz"],
        n_points,
    )


def element_force_diagrams(
    static_results: dict[str, Any],
    element_id: int,
    n_points: int = 2,
) -> dict[str, dict[str, list[float]]]:
    """Return available force diagrams for a frame or truss element."""
    element = static_results["elements"][element_id]
    member_force = static_results["member_end_forces"][element_id]
    length = element["length"]
    element_type = element["type"]

    diagrams = {
        "axial": axial_force_diagram(member_force, length, n_points),
    }
    if element_type == "frame":
        diagrams["shear"] = shear_force_diagram(member_force, length, n_points)
        diagrams["moment"] = bending_moment_diagram(member_force, length, n_points)
    return diagrams


def _linear_diagram(length: float, start_value: float, end_value: float, n_points: int) -> dict[str, list[float]]:
    if length <= 0.0:
        raise ValueError(f"Element length must be positive, got {length}.")
    if n_points < 2:
        raise ValueError("n_points must be at least 2.")

    x = [length * i / (n_points - 1) for i in range(n_points)]
    values = [
        start_value + (end_value - start_value) * i / (n_points - 1)
        for i in range(n_points)
    ]
    return {"x": x, "values": values}
