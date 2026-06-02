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
