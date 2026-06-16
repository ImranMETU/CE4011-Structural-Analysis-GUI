"""Modal diagnostics helpers for GUI/debugging tables."""

from __future__ import annotations

from typing import Any

import numpy as np


def modal_properties_rows(modal_result: dict[str, Any]) -> list[dict[str, Any]]:
    """Return per-mode modal properties including participation and controlling DOF."""
    eigenvalues = np.asarray(modal_result.get("eigenvalues", []), dtype=float)
    omega = np.asarray(modal_result.get("omega", []), dtype=float)
    frequencies = np.asarray(modal_result.get("frequencies_hz", []), dtype=float)
    periods = np.asarray(modal_result.get("periods", []), dtype=float)
    modes = np.asarray(modal_result.get("full_free_mode_shapes", []), dtype=float)
    mass = np.asarray(modal_result.get("active_mass_matrix", []), dtype=float)
    stiffness = np.asarray(modal_result.get("free_stiffness_matrix", []), dtype=float)
    free_dof_map = modal_result.get("free_dof_map", [])
    participation = {int(row.get("mode", 0)): row for row in modal_result.get("participation", []) or []}

    cumulative = 0.0
    rows: list[dict[str, Any]] = []
    n_modes = len(frequencies)
    for mode_idx in range(n_modes):
        part = participation.get(mode_idx + 1, {})
        ratio = float(part.get("effective_modal_mass_ratio", 0.0))
        cumulative += ratio
        control = _controlling_component(modes, mode_idx, free_dof_map)
        rows.append(
            {
                "mode": mode_idx + 1,
                "eigenvalue": float(eigenvalues[mode_idx]) if mode_idx < len(eigenvalues) else "",
                "omega": float(omega[mode_idx]) if mode_idx < len(omega) else "",
                "frequency_hz": float(frequencies[mode_idx]),
                "period": float(periods[mode_idx]) if mode_idx < len(periods) else "",
                "gamma": float(part.get("gamma", 0.0)),
                "modal_mass": _modal_quadratic_form(modes, mass, mode_idx),
                "modal_stiffness": _modal_quadratic_form(modes, stiffness, mode_idx),
                "effective_modal_mass": float(part.get("effective_modal_mass", 0.0)),
                "effective_modal_mass_ratio": ratio,
                "cumulative_effective_mass_ratio": cumulative,
                "normalization": modal_result.get("normalization", "max translational displacement for plotting"),
                "max_modal_component": control["value"],
                "controlling_node": control["node"],
                "controlling_dof": control["dof"],
            }
        )
    return rows


def modal_dof_classification_rows(modal_result: dict[str, Any]) -> list[dict[str, Any]]:
    """Return active/free DOF mass classification rows."""
    free_dof_map = modal_result.get("free_dof_map", [])
    mass = np.asarray(modal_result.get("active_mass_matrix", []), dtype=float)
    mass_diag = np.diag(mass) if mass.ndim == 2 and mass.size else np.array([])
    massive = {int(idx) for idx in modal_result.get("massive_dof_indices", [])}
    massless = {int(idx) for idx in modal_result.get("massless_dof_indices", [])}

    rows = []
    for item in sorted(free_dof_map, key=lambda row: int(row["index"])):
        index = int(item["index"])
        mass_value = float(mass_diag[index]) if index < len(mass_diag) else 0.0
        if index in massive:
            classification = "massive"
            note = ""
        elif index in massless:
            classification = "massless condensed"
            note = "zero/near-zero modal mass"
        else:
            classification = "free/unclassified"
            note = ""
        rows.append(
            {
                "free_dof_index": index,
                "node": int(item["node"]),
                "dof": str(item["dof"]),
                "mass": mass_value,
                "classification": classification,
                "note": note,
            }
        )
    return rows


def condensed_matrix_summary(modal_result: dict[str, Any]) -> dict[str, Any]:
    """Return modal condensation matrix diagnostics."""
    diagnostics = dict(modal_result.get("matrix_diagnostics", {}))
    k_condensed = np.asarray(modal_result.get("condensed_stiffness", []), dtype=float)
    m_condensed = np.asarray(modal_result.get("condensed_mass_matrix", []), dtype=float)
    if "condensed_stiffness_symmetry_error" not in diagnostics and k_condensed.size:
        diagnostics["condensed_stiffness_symmetry_error"] = _symmetry_error(k_condensed)
    if "condensed_mass_symmetry_error" not in diagnostics and m_condensed.size:
        diagnostics["condensed_mass_symmetry_error"] = _symmetry_error(m_condensed)
    diagnostics.setdefault("notes", "; ".join(modal_result.get("notes", [])))
    return diagnostics


def full_mode_shape_rows(modal_result: dict[str, Any]) -> list[dict[str, Any]]:
    """Return node-keyed full free-DOF mode shape rows."""
    node_modes = modal_result.get("node_mode_shapes", [])
    rows: list[dict[str, Any]] = []
    for mode_idx, mode in enumerate(node_modes, start=1):
        for node_id in sorted(mode):
            values = mode[node_id]
            rows.append(
                {
                    "mode": mode_idx,
                    "node": int(node_id),
                    "ux": float(values.get("ux", 0.0)),
                    "uy": float(values.get("uy", 0.0)),
                    "rz": float(values.get("rz", 0.0)),
                }
            )
    return rows


def modal_mass_summary(modal_result: dict[str, Any], mass_source: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return assigned/active modal mass summary."""
    mass = np.asarray(modal_result.get("active_mass_matrix", []), dtype=float)
    diag = np.diag(mass) if mass.ndim == 2 and mass.size else np.array([])
    source = mass_source or modal_result.get("mass_source_summary", {}) or {}
    return {
        "source_type": source.get("source_type", "unknown"),
        "nodes_with_assigned_mass": source.get("node_count", ""),
        "total_assigned_ux_mass": source.get("total_ux_mass", ""),
        "total_assigned_uy_mass": source.get("total_uy_mass", ""),
        "total_assigned_rz_mass": source.get("total_rz_mass", ""),
        "active_mass_dof_count": int(np.count_nonzero(diag > 0.0)),
        "active_mass_total": float(np.sum(diag)) if diag.size else 0.0,
        "warnings": "; ".join(modal_result.get("notes", [])),
    }


def _controlling_component(modes: np.ndarray, mode_idx: int, free_dof_map: list[dict[str, Any]]) -> dict[str, Any]:
    if modes.ndim != 2 or mode_idx >= modes.shape[1] or modes.shape[0] == 0:
        return {"value": "", "node": "", "dof": ""}
    amplitudes = np.abs(modes[:, mode_idx])
    index = int(np.argmax(amplitudes))
    item = next((row for row in free_dof_map if int(row["index"]) == index), {})
    return {
        "value": float(modes[index, mode_idx]),
        "node": item.get("node", ""),
        "dof": item.get("dof", ""),
    }


def _symmetry_error(matrix: np.ndarray) -> float:
    return float(np.max(np.abs(matrix - matrix.T))) if matrix.size else 0.0


def _modal_quadratic_form(modes: np.ndarray, matrix: np.ndarray, mode_idx: int) -> float | str:
    if modes.ndim != 2 or matrix.ndim != 2 or mode_idx >= modes.shape[1]:
        return ""
    if matrix.shape != (modes.shape[0], modes.shape[0]):
        return ""
    phi = modes[:, mode_idx]
    return float(phi.T @ matrix @ phi)
