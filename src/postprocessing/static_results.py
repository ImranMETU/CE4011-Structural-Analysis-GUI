"""Adapter API for static-analysis post-processing results.

This module intentionally calls the existing Structure workflow instead of
changing solver internals. The returned dictionaries are shaped for plotting
and GUI consumption.
"""

from __future__ import annotations

from typing import Any

from model.frame_element import FrameElement
from model.structure import Structure
from model.truss_element import TrussElement
from units.unit_system import default_unit_system, normalize_unit_system


def run_static_analysis(data: dict[str, Any], tol: float = 1e-8, max_iter: int = 2000) -> dict[str, Any]:
    """Build, solve, and package a static analysis case from input data."""
    structure = Structure.from_dict(data)
    result = collect_static_results(structure, solve=True, tol=tol, max_iter=max_iter)
    result["units"] = normalize_unit_system(data.get("units")).to_dict()
    result["units_defaulted"] = bool(data.get("units_defaulted", "units" not in data))
    return result


def collect_static_results(
    structure: Structure,
    solve: bool = True,
    tol: float = 1e-8,
    max_iter: int = 2000,
) -> dict[str, Any]:
    """Return solver outputs and plotting metadata from a Structure instance.

    Args:
        structure: Existing structural model.
        solve: If true, solve the structure when no displacement solution exists.
        tol: Solver tolerance passed through to ``Structure.solve``.
        max_iter: Solver iteration limit passed through to ``Structure.solve``.
    """
    if solve and structure.D is None:
        if structure.n_active_dofs > 0:
            if structure.K is None:
                structure.assemble_global_stiffness()
            if structure.F is None:
                structure.assemble_global_load_vector()
        structure.solve(tol=tol, max_iter=max_iter)

    displacement_vector = structure.full_displacement_vector()
    return {
        "units": default_unit_system().to_dict(),
        "units_defaulted": True,
        "displacement_vector": displacement_vector,
        "displacements": _node_displacements(structure, displacement_vector),
        "reactions": structure.compute_reactions(),
        "member_end_forces": structure.compute_member_end_forces(),
        "nodes": _node_coordinates(structure),
        "elements": _element_connectivity(structure),
    }


def _node_coordinates(structure: Structure) -> dict[int, dict[str, float]]:
    return {
        node_id: {"x": node.x, "y": node.y}
        for node_id, node in sorted(structure.nodes.items())
    }


def _node_displacements(
    structure: Structure,
    displacement_vector: list[float],
) -> dict[int, dict[str, float]]:
    displacements: dict[int, dict[str, float]] = {}
    for node_id in sorted(structure.nodes):
        node_pos = structure.node_index[node_id]
        base = node_pos * 3
        displacements[node_id] = {
            "ux": displacement_vector[base],
            "uy": displacement_vector[base + 1],
            "rz": displacement_vector[base + 2],
        }
    return displacements


def _element_connectivity(structure: Structure) -> dict[int, dict[str, Any]]:
    elements: dict[int, dict[str, Any]] = {}
    for element in structure.elements:
        elements[element.id] = {
            "type": _element_type(element),
            "node_i": element.node_i.id,
            "node_j": element.node_j.id,
            "length": element.length(),
            "angle": element.angle(),
            "member_loads": [dict(load) for load in getattr(element, "member_loads", [])],
        }
        if hasattr(element, "axis_offset_i") or hasattr(element, "axis_offset_j"):
            elements[element.id]["axis_offset"] = {
                "i_local_y": float(getattr(element, "axis_offset_i", 0.0)),
                "j_local_y": float(getattr(element, "axis_offset_j", 0.0)),
            }
    return elements


def _element_type(element: Any) -> str:
    if isinstance(element, FrameElement):
        return "frame"
    if isinstance(element, TrussElement):
        return "truss"
    return element.__class__.__name__.lower()
