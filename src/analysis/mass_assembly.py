"""Lumped mass assembly helpers for modal analysis."""

from __future__ import annotations

from typing import Any

import numpy as np


DOF_KEYS = ("ux", "uy", "rz")


def assemble_lumped_mass_vector(structure: Any, nodal_masses: dict[int, dict[str, float]]) -> np.ndarray:
    """Assemble active-DOF lumped masses from an external node/DOF mapping.

    ``nodal_masses`` format:
        ``{node_id: {"ux": mass_x, "uy": mass_y, "rz": mass_rz}}``

    Restrained DOFs are skipped because they do not appear in the active modal
    system. Missing DOF masses default to zero; rotational mass therefore
    defaults to zero in the first backend version.
    """
    mass = np.zeros(int(structure.n_active_dofs), dtype=float)

    for node_id, dof_masses in nodal_masses.items():
        if node_id not in structure.nodes:
            raise ValueError(f"Mass references unknown node id {node_id}.")

        node = structure.nodes[node_id]
        eqs = node.get_global_dof_numbers()
        for local_idx, dof_key in enumerate(DOF_KEYS):
            value = float(dof_masses.get(dof_key, 0.0))
            if value < 0.0:
                raise ValueError(f"Mass for node {node_id} DOF {dof_key} cannot be negative.")

            eq = eqs[local_idx]
            if eq != 0:
                mass[eq - 1] += value

    return mass


def assemble_lumped_mass_matrix(structure: Any, nodal_masses: dict[int, dict[str, float]]) -> np.ndarray:
    """Assemble a diagonal active-DOF lumped mass matrix."""
    return np.diag(assemble_lumped_mass_vector(structure, nodal_masses))


def build_lateral_floor_mass_mapping(
    structure: Any,
    floor_masses: dict[float, float],
    direction: str = "ux",
    y_tol: float = 1e-6,
) -> dict[int, dict[str, float]]:
    """Assign one lateral mass value to nodes whose y-coordinate matches a floor.

    This helper keeps modal mass input external to existing XML/JSON formats.
    It is intended for simple shear-building style models where floor levels
    are identified by node y-coordinates.
    """
    if direction not in DOF_KEYS:
        raise ValueError(f"Unknown DOF direction {direction!r}. Expected one of {DOF_KEYS}.")
    if y_tol < 0.0:
        raise ValueError("y_tol cannot be negative.")

    mapping: dict[int, dict[str, float]] = {}
    for node_id, node in structure.nodes.items():
        for floor_y, mass in floor_masses.items():
            if abs(node.y - float(floor_y)) <= y_tol:
                if mass < 0.0:
                    raise ValueError(f"Floor mass at y={floor_y} cannot be negative.")
                mapping.setdefault(node_id, {})[direction] = float(mass)
                break
    return mapping


def merge_mass_mappings(
    base: dict[int, dict[str, float]] | None,
    added: dict[int, dict[str, float]],
    overwrite: bool = False,
) -> dict[int, dict[str, float]]:
    """Merge two nodal mass mappings."""
    merged = {
        int(node_id): {dof: float(values.get(dof, 0.0)) for dof in DOF_KEYS}
        for node_id, values in (base or {}).items()
    }
    for node_id, values in added.items():
        target = merged.setdefault(int(node_id), {dof: 0.0 for dof in DOF_KEYS})
        for dof in DOF_KEYS:
            value = float(values.get(dof, 0.0))
            if overwrite:
                target[dof] = value
            else:
                target[dof] = float(target.get(dof, 0.0)) + value
    return merged


def distribute_floor_mass_to_nodes(
    model_data: dict[str, Any],
    floor_y: float,
    total_mass: float,
    direction: str = "ux",
    y_tol: float = 1e-6,
) -> dict[int, dict[str, float]]:
    """Distribute total floor mass equally to nodes at a floor elevation."""
    direction = _normalize_dof(direction)
    if total_mass < 0.0:
        raise ValueError("Floor mass cannot be negative.")
    if y_tol < 0.0:
        raise ValueError("y_tol cannot be negative.")

    matching_nodes = [
        int(node["id"])
        for node in model_data.get("nodes", [])
        if abs(float(node["y"]) - float(floor_y)) <= y_tol
    ]
    if not matching_nodes:
        raise ValueError(f"No nodes found at floor elevation y={floor_y}.")

    share = float(total_mass) / len(matching_nodes)
    return {node_id: {direction: share} for node_id in matching_nodes}


def lump_element_distributed_mass_to_nodes(
    model_data: dict[str, Any],
    element_id: int,
    mass_per_length: float,
    direction: str = "ux",
    include_uy: bool = False,
) -> dict[int, dict[str, float]]:
    """Convert element distributed mass to nodal lumped masses at its end nodes."""
    primary = _normalize_dof(direction)
    if mass_per_length < 0.0:
        raise ValueError("Element mass per length cannot be negative.")

    element = _find_model_element(model_data, element_id)
    if element is None:
        raise ValueError(f"Unknown element id {element_id}.")

    nodes = {int(node["id"]): node for node in model_data.get("nodes", [])}
    node_i = nodes.get(int(element["node_i"]))
    node_j = nodes.get(int(element["node_j"]))
    if node_i is None or node_j is None:
        raise ValueError(f"Element {element_id} references unknown node(s).")

    dx = float(node_j["x"]) - float(node_i["x"])
    dy = float(node_j["y"]) - float(node_i["y"])
    length = float((dx * dx + dy * dy) ** 0.5)
    if length <= 0.0:
        raise ValueError(f"Element {element_id} has zero length.")

    half_mass = 0.5 * float(mass_per_length) * length
    dofs = {"uy"} if primary == "uy" else {"ux"}
    if include_uy:
        dofs.add("uy")
    if primary == "rz":
        dofs = {"rz"}

    mapping: dict[int, dict[str, float]] = {}
    for node_id in (int(element["node_i"]), int(element["node_j"])):
        mapping[node_id] = {dof: half_mass for dof in dofs}
    return mapping


def mass_mapping_summary(mass_mapping: dict[int, dict[str, float]] | None, source_type: str = "unknown") -> dict[str, Any]:
    """Return mass totals for GUI summaries and diagnostics."""
    mapping = mass_mapping or {}
    return {
        "source_type": source_type,
        "node_count": len(mapping),
        "total_ux_mass": sum(float(values.get("ux", 0.0)) for values in mapping.values()),
        "total_uy_mass": sum(float(values.get("uy", 0.0)) for values in mapping.values()),
        "total_rz_mass": sum(float(values.get("rz", 0.0)) for values in mapping.values()),
    }


def _normalize_dof(direction: str) -> str:
    dof = str(direction).strip().lower()
    if dof in {"x", "local_x"}:
        dof = "ux"
    if dof in {"y", "local_y"}:
        dof = "uy"
    if dof not in DOF_KEYS:
        raise ValueError(f"Unknown mass direction {direction!r}. Expected one of {DOF_KEYS}.")
    return dof


def _find_model_element(model_data: dict[str, Any], element_id: int) -> dict[str, Any] | None:
    for element in model_data.get("elements", []):
        if int(element["id"]) == int(element_id):
            return element
    return None
