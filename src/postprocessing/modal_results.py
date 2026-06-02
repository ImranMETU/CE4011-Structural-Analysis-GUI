"""Modal result packaging helpers for GUI and plotting layers."""

from __future__ import annotations

from typing import Any

import numpy as np


TRANSLATIONAL_DOFS = {"ux", "uy"}


def package_modal_results(
    modal_result: dict[str, Any],
    structure: Any | None = None,
    excitation_dof: str = "ux",
) -> dict[str, Any]:
    """Package modal solver output into table, node, and plotting data."""
    full_modes = np.asarray(modal_result["full_free_mode_shapes"], dtype=float)
    free_dof_map = modal_result.get("free_dof_map", [])
    normalized_modes = normalize_modes_by_max_translation(full_modes, free_dof_map)
    raw_node_modes = node_keyed_mode_shapes(modal_result, full_modes, structure)
    normalized_node_modes = node_keyed_mode_shapes(modal_result, normalized_modes, structure)

    packaged = {
        "eigenvalues": np.asarray(modal_result["eigenvalues"], dtype=float),
        "omega": np.asarray(modal_result["omega"], dtype=float),
        "frequencies_hz": np.asarray(modal_result["frequencies_hz"], dtype=float),
        "periods": np.asarray(modal_result["periods"], dtype=float),
        "full_free_mode_shapes": full_modes,
        "normalized_full_free_mode_shapes": normalized_modes,
        "node_mode_shapes": raw_node_modes,
        "normalized_node_mode_shapes": normalized_node_modes,
        "max_modal_displacements": maximum_modal_displacements(raw_node_modes),
        "frequency_table": frequency_table(modal_result),
        "period_table": period_table(modal_result),
        "participation": calculate_modal_participation(modal_result, excitation_dof),
        "free_dof_map": free_dof_map,
        "nodes": _node_coordinates(structure, modal_result),
        "elements": _element_connectivity(structure, modal_result),
        "notes": list(modal_result.get("notes", [])),
    }
    return packaged


def frequency_table(modal_result: dict[str, Any]) -> list[dict[str, float]]:
    """Return per-mode frequency table rows."""
    omega = np.asarray(modal_result["omega"], dtype=float)
    frequencies = np.asarray(modal_result["frequencies_hz"], dtype=float)
    periods = np.asarray(modal_result["periods"], dtype=float)
    return [
        {
            "mode": mode + 1,
            "omega": float(omega[mode]),
            "frequency_hz": float(frequencies[mode]),
            "period": float(periods[mode]),
        }
        for mode in range(len(frequencies))
    ]


def period_table(modal_result: dict[str, Any]) -> list[dict[str, float]]:
    """Return per-mode period table rows."""
    return [
        {"mode": row["mode"], "period": row["period"], "frequency_hz": row["frequency_hz"]}
        for row in frequency_table(modal_result)
    ]


def normalize_modes_by_max_translation(
    mode_shapes: Any,
    free_dof_map: list[dict[str, Any]] | None = None,
) -> np.ndarray:
    """Normalize each mode by its maximum translational displacement amplitude."""
    modes = np.asarray(mode_shapes, dtype=float).copy()
    if modes.ndim != 2:
        raise ValueError("Mode shapes must be a 2D array with shape (n_dof, n_modes).")

    indices = _translational_indices(free_dof_map)
    if not indices:
        indices = list(range(modes.shape[0]))

    for mode_idx in range(modes.shape[1]):
        max_amp = float(np.max(np.abs(modes[indices, mode_idx]))) if indices else 0.0
        if max_amp > 0.0:
            modes[:, mode_idx] /= max_amp
    return modes


def mass_normalize_modes(mode_shapes: Any, mass_matrix: Any) -> np.ndarray:
    """Normalize each mode so ``phi.T @ M @ phi == 1`` when possible."""
    modes = np.asarray(mode_shapes, dtype=float).copy()
    mass = np.asarray(mass_matrix, dtype=float)
    for mode_idx in range(modes.shape[1]):
        phi = modes[:, mode_idx]
        modal_mass = float(phi.T @ mass @ phi)
        if modal_mass > 0.0:
            modes[:, mode_idx] /= modal_mass ** 0.5
    return modes


def node_keyed_mode_shapes(
    modal_result: dict[str, Any],
    mode_shapes: Any | None = None,
    structure: Any | None = None,
) -> list[dict[int, dict[str, float]]]:
    """Convert free-DOF mode vectors to node-keyed displacement dictionaries."""
    modes = np.asarray(
        modal_result["full_free_mode_shapes"] if mode_shapes is None else mode_shapes,
        dtype=float,
    )
    free_dof_map = modal_result.get("free_dof_map", [])
    node_ids = _node_ids(structure, modal_result, free_dof_map)

    out: list[dict[int, dict[str, float]]] = []
    for mode_idx in range(modes.shape[1]):
        node_values = {
            node_id: {"ux": 0.0, "uy": 0.0, "rz": 0.0}
            for node_id in node_ids
        }
        for item in free_dof_map:
            idx = int(item["index"])
            node_id = int(item["node"])
            dof = str(item["dof"])
            node_values.setdefault(node_id, {"ux": 0.0, "uy": 0.0, "rz": 0.0})
            node_values[node_id][dof] = float(modes[idx, mode_idx])
        out.append(node_values)
    return out


def maximum_modal_displacements(
    node_mode_shapes: list[dict[int, dict[str, float]]],
) -> list[float]:
    """Return maximum translational displacement magnitude for each mode."""
    max_values = []
    for mode in node_mode_shapes:
        max_mag = 0.0
        for values in mode.values():
            mag = (values.get("ux", 0.0) ** 2 + values.get("uy", 0.0) ** 2) ** 0.5
            max_mag = max(max_mag, mag)
        max_values.append(max_mag)
    return max_values


def calculate_modal_participation(
    modal_result: dict[str, Any],
    excitation_dof: str = "ux",
) -> list[dict[str, float]]:
    """Calculate participation factors for a unit influence vector."""
    free_dof_map = modal_result.get("free_dof_map", [])
    if not free_dof_map:
        return []

    modes = np.asarray(modal_result["full_free_mode_shapes"], dtype=float)
    mass = np.asarray(modal_result["active_mass_matrix"], dtype=float)
    influence = np.zeros(modes.shape[0], dtype=float)
    for item in free_dof_map:
        if item["dof"] == excitation_dof:
            influence[int(item["index"])] = 1.0

    total_mass = float(influence.T @ mass @ influence)
    rows = []
    for mode_idx in range(modes.shape[1]):
        phi = modes[:, mode_idx]
        numerator = float(phi.T @ mass @ influence)
        denominator = float(phi.T @ mass @ phi)
        gamma = numerator / denominator if denominator > 0.0 else 0.0
        effective_mass = (numerator * numerator / denominator) if denominator > 0.0 else 0.0
        ratio = effective_mass / total_mass if total_mass > 0.0 else 0.0
        rows.append(
            {
                "mode": mode_idx + 1,
                "excitation_dof": excitation_dof,
                "gamma": gamma,
                "effective_modal_mass": effective_mass,
                "effective_modal_mass_ratio": ratio,
            }
        )
    return rows


def _translational_indices(free_dof_map: list[dict[str, Any]] | None) -> list[int]:
    if not free_dof_map:
        return []
    return [
        int(item["index"])
        for item in free_dof_map
        if item.get("dof") in TRANSLATIONAL_DOFS
    ]


def _node_coordinates(structure: Any | None, modal_result: dict[str, Any]) -> dict[int, dict[str, float]]:
    if structure is not None:
        return {
            int(node_id): {"x": node.x, "y": node.y}
            for node_id, node in sorted(structure.nodes.items())
        }
    return modal_result.get("nodes", {})


def _element_connectivity(structure: Any | None, modal_result: dict[str, Any]) -> dict[int, dict[str, Any]]:
    if structure is None:
        return modal_result.get("elements", {})

    elements: dict[int, dict[str, Any]] = {}
    for element in structure.elements:
        elements[element.id] = {
            "type": element.__class__.__name__.replace("Element", "").lower(),
            "node_i": element.node_i.id,
            "node_j": element.node_j.id,
            "length": element.length(),
            "angle": element.angle(),
        }
    return elements


def _node_ids(
    structure: Any | None,
    modal_result: dict[str, Any],
    free_dof_map: list[dict[str, Any]],
) -> list[int]:
    if structure is not None:
        return [int(node_id) for node_id in sorted(structure.nodes)]
    if "nodes" in modal_result:
        return [int(node_id) for node_id in sorted(modal_result["nodes"])]
    return sorted({int(item["node"]) for item in free_dof_map})
