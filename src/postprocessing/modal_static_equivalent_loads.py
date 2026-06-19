"""Generate physical static load cases from modal inertia-force coefficients."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import numpy as np


def create_static_equivalent_modal_loads(
    model_data: dict[str, Any],
    modal_result: dict[str, Any],
    modal_response_parameters: dict[str, Any],
    mode_number: int = 1,
    A_value: float = 1.0,
    direction: str = "ux",
) -> dict[str, Any]:
    """Return a copied model with ``s_n A_n`` distributed to massive nodes."""
    load_key = {"ux": "fx", "uy": "fy", "rz": "mz"}.get(direction)
    if load_key is None:
        raise ValueError("direction must be ux, uy, or rz.")
    mode_index = int(mode_number) - 1
    rows = modal_response_parameters.get("rows", [])
    if mode_index < 0 or mode_index >= len(rows):
        raise IndexError(f"mode_number {mode_number} is outside the available modes.")

    heights = np.asarray(modal_response_parameters["floor_heights"], dtype=float)
    floor_forces = np.asarray(rows[mode_index]["sn"], dtype=float) * float(A_value)
    if heights.size != floor_forces.size:
        raise ValueError("Modal floor heights and force coefficients must have the same length.")

    nodes = _node_mapping(model_data)
    mass_nodes = _massive_direction_nodes(modal_result, nodes, direction)
    generated: list[dict[str, float | int]] = []
    for height, floor_force in zip(heights, floor_forces):
        candidates = [
            (node_id, mass)
            for node_id, mass in mass_nodes.items()
            if abs(float(nodes[node_id]["y"]) - float(height)) <= 1.0e-8
        ]
        if not candidates:
            raise ValueError(f"No explicit modal mass nodes found at floor height {height:g}.")
        total_mass = sum(mass for _node_id, mass in candidates)
        if total_mass <= 0.0:
            raise ValueError(f"Floor height {height:g} has non-positive explicit modal mass.")
        for node_id, mass in candidates:
            load = {"node": int(node_id), "fx": 0.0, "fy": 0.0, "mz": 0.0}
            load[load_key] = float(floor_force * mass / total_mass)
            generated.append(load)

    out = deepcopy(model_data)
    existing = {
        int(load["node"]): {
            "node": int(load["node"]),
            "fx": float(load.get("fx", 0.0)),
            "fy": float(load.get("fy", 0.0)),
            "mz": float(load.get("mz", 0.0)),
        }
        for load in out.get("nodal_loads", [])
    }
    for load in generated:
        node_id = int(load["node"])
        target = existing.setdefault(node_id, {"node": node_id, "fx": 0.0, "fy": 0.0, "mz": 0.0})
        target[load_key] += float(load[load_key])
    out["nodal_loads"] = [existing[node_id] for node_id in sorted(existing)]

    note = (
        f"Static-equivalent modal inertia load case generated from mode {mode_number} "
        f"with A_n = {float(A_value):g} in direction {direction}."
    )
    original_description = str(out.get("description", "")).strip()
    out["description"] = f"{original_description} {note}".strip()
    out["static_equivalent_modal_load"] = {
        "mode": int(mode_number),
        "A_value": float(A_value),
        "direction": direction,
        "total_applied_load": float(np.sum(floor_forces)),
        "source": "s_n = Gamma M phi; f_n = s_n A_n",
    }
    return out


def _node_mapping(model_data):
    nodes = model_data.get("nodes", {})
    if isinstance(nodes, dict):
        return {int(node_id): node for node_id, node in nodes.items()}
    return {int(node["id"]): node for node in nodes}


def _massive_direction_nodes(modal_result, nodes, direction):
    matrix = np.asarray(modal_result.get("active_mass_matrix", []), dtype=float)
    mapping = modal_result.get("free_dof_map", [])
    if matrix.ndim != 2:
        raise ValueError("Modal result does not contain an active mass matrix.")
    masses = {}
    for item in mapping:
        index = int(item["index"])
        node_id = int(item["node"])
        if item.get("dof") == direction and node_id in nodes and matrix[index, index] > 0.0:
            masses[node_id] = float(matrix[index, index])
    return masses
