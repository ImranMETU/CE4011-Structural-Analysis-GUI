"""CE586/Chopra-style generalized modal response parameters."""

from __future__ import annotations

from typing import Any

import numpy as np


def compute_modal_generalized_parameters(
    modes,
    masses,
    omegas,
    floor_heights,
    influence_vector=None,
    normalization: str = "display",
) -> dict[str, Any]:
    """Compute generalized quantities using the supplied displayed floor modes."""
    phi = np.asarray(modes, dtype=float)
    mass = np.asarray(masses, dtype=float).reshape(-1)
    omega = np.asarray(omegas, dtype=float).reshape(-1)
    heights = np.asarray(floor_heights, dtype=float).reshape(-1)
    if phi.ndim != 2 or phi.shape[0] != mass.size:
        raise ValueError("modes must have shape (n_floor_dof, n_modes) matching masses.")
    if heights.size != mass.size or omega.size < phi.shape[1]:
        raise ValueError("floor_heights and omegas must match the modal dimensions.")
    influence = np.ones(mass.size) if influence_vector is None else np.asarray(influence_vector, dtype=float).reshape(-1)
    if influence.size != mass.size:
        raise ValueError("influence_vector must match masses.")

    total_mass = float(np.sum(mass * influence * influence))
    cumulative = 0.0
    rows = []
    for mode_idx in range(phi.shape[1]):
        vector = phi[:, mode_idx]
        modal_mass = float(np.sum(mass * vector * vector))
        if modal_mass <= 0.0:
            raise ValueError(f"Mode {mode_idx + 1} has non-positive generalized mass.")
        lnh = float(np.sum(mass * vector * influence))
        gamma = lnh / modal_mass
        ln_theta = float(np.sum(mass * vector * heights))
        h_star = ln_theta / lnh if abs(lnh) > 1.0e-14 else float("nan")
        effective_mass = lnh * lnh / modal_mass
        ratio = effective_mass / total_mass if total_mass > 0.0 else 0.0
        cumulative += ratio
        sn = gamma * mass * vector
        u_coeff = gamma * vector / (omega[mode_idx] ** 2)
        rows.append(
            {
                "mode": mode_idx + 1,
                "phi": vector.copy(),
                "omega": float(omega[mode_idx]),
                "omega_rad_per_s": float(omega[mode_idx]),
                "frequency_hz": float(omega[mode_idx] / (2.0 * np.pi)),
                "frequency_Hz": float(omega[mode_idx] / (2.0 * np.pi)),
                "period_s": float(2.0 * np.pi / omega[mode_idx]),
                "Mn": modal_mass,
                "Lnh": lnh,
                "Gamma": gamma,
                "Ln_theta": ln_theta,
                "h_star": h_star,
                "M_eff": effective_mass,
                "M_eff_ratio": ratio,
                "cumulative_M_eff_ratio": cumulative,
                "sn": sn,
                "base_shear_coefficient": float(np.sum(sn)),
                "base_moment_coefficient": float(np.sum(sn * heights)),
                "Vb_coeff": float(np.sum(sn)),
                "Mb_coeff": float(np.sum(sn * heights)),
                "u_coeff": u_coeff,
                "normalization": normalization,
            }
        )
    return {
        "modes": phi,
        "masses": mass,
        "omegas": omega[: phi.shape[1]],
        "floor_heights": heights,
        "influence_vector": influence,
        "total_mass": total_mass,
        "normalization": normalization,
        "floor_labels": list(range(1, mass.size + 1)),
        "rows": rows,
    }


def modal_response_parameters_from_result(
    modal_result: dict[str, Any],
    normalization: str = "display",
) -> dict[str, Any]:
    """Extract lateral floor modes/masses and compute textbook parameters."""
    raw_modes = np.asarray(modal_result["full_free_mode_shapes"], dtype=float)
    mass_matrix = np.asarray(modal_result["active_mass_matrix"], dtype=float)
    dof_map = modal_result.get("free_dof_map", [])
    nodes = modal_result.get("nodes", {})
    by_height: dict[float, list[int]] = {}
    for item in dof_map:
        idx = int(item["index"])
        if item.get("dof") != "ux" or mass_matrix[idx, idx] <= 0.0:
            continue
        height = float(nodes[int(item["node"])]["y"])
        by_height.setdefault(height, []).append(idx)
    heights = sorted(by_height)
    if not heights:
        raise ValueError("No massive ux floor DOFs are available for modal response parameters.")

    floor_masses = []
    floor_modes = []
    for height in heights:
        indices = by_height[height]
        weights = np.asarray([mass_matrix[idx, idx] for idx in indices], dtype=float)
        floor_masses.append(float(np.sum(weights)))
        floor_modes.append(np.average(raw_modes[indices, :], axis=0, weights=weights))
    modes = np.vstack(floor_modes)

    normalized = str(normalization).strip().lower()
    if normalized in {"display", "lecture", "roof", "roof-normalized"}:
        for mode_idx in range(modes.shape[1]):
            roof_value = modes[-1, mode_idx]
            if abs(roof_value) > 1.0e-14:
                modes[:, mode_idx] /= roof_value
        label = "roof-normalized, roof ux positive"
    elif normalized in {"mass", "mass-normalized"}:
        for mode_idx in range(modes.shape[1]):
            mn = float(np.sum(np.asarray(floor_masses) * modes[:, mode_idx] ** 2))
            modes[:, mode_idx] /= np.sqrt(mn)
        label = "mass-normalized"
    elif normalized == "raw":
        label = "raw solver normalization"
    else:
        raise ValueError("normalization must be display, roof, mass, or raw.")

    result = compute_modal_generalized_parameters(
        modes,
        floor_masses,
        modal_result["omega"],
        heights,
        normalization=label,
    )
    result["floor_labels"] = list(range(1, len(heights) + 1))
    return result
