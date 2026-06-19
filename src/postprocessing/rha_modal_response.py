"""Modal response-history decomposition without altering the RHA solver."""

from __future__ import annotations

from typing import Any

import numpy as np


def compute_modal_pseudo_acceleration_history(rha_result, modal_parameters):
    q = np.asarray(rha_result["modal_coordinate_histories"], dtype=float)
    omega = np.asarray(rha_result.get("omega", modal_parameters["omegas"]), dtype=float)
    gamma = np.asarray(rha_result.get("participation_factors", []), dtype=float)
    if gamma.size < q.shape[0]:
        gamma = np.asarray([row["Gamma"] for row in modal_parameters["rows"]], dtype=float)
    out = np.full_like(q, np.nan)
    for mode_idx in range(q.shape[0]):
        if abs(gamma[mode_idx]) > 1.0e-14:
            out[mode_idx] = omega[mode_idx] ** 2 * q[mode_idx] / gamma[mode_idx]
    return out


def compute_modal_displacement_contributions(rha_result, modal_parameters):
    acceleration = compute_modal_pseudo_acceleration_history(rha_result, modal_parameters)
    coeff = np.vstack([row["u_coeff"] for row in modal_parameters["rows"][: acceleration.shape[0]]])
    return coeff[:, :, None] * acceleration[:, None, :]


def compute_modal_force_contributions(rha_result, modal_parameters):
    acceleration = compute_modal_pseudo_acceleration_history(rha_result, modal_parameters)
    coeff = np.vstack([row["sn"] for row in modal_parameters["rows"][: acceleration.shape[0]]])
    return coeff[:, :, None] * acceleration[:, None, :]


def compute_modal_base_shear_history(rha_result, modal_parameters):
    return np.sum(compute_modal_force_contributions(rha_result, modal_parameters), axis=1)


def compute_modal_base_moment_history(rha_result, modal_parameters):
    forces = compute_modal_force_contributions(rha_result, modal_parameters)
    heights = np.asarray(modal_parameters["floor_heights"], dtype=float)
    return np.sum(forces * heights[None, :, None], axis=1)


def package_modal_rha_response(rha_result, modal_parameters) -> dict[str, Any]:
    acceleration = compute_modal_pseudo_acceleration_history(rha_result, modal_parameters)
    displacements = compute_modal_displacement_contributions(rha_result, modal_parameters)
    forces = compute_modal_force_contributions(rha_result, modal_parameters)
    return {
        "time": np.asarray(rha_result["time"], dtype=float),
        "pseudo_acceleration_histories": acceleration,
        "modal_displacement_contributions": displacements,
        "modal_force_contributions": forces,
        "modal_base_shear_histories": np.sum(forces, axis=1),
        "modal_base_moment_histories": np.sum(
            forces * np.asarray(modal_parameters["floor_heights"])[None, :, None], axis=1
        ),
        "modal_parameters": modal_parameters,
    }
