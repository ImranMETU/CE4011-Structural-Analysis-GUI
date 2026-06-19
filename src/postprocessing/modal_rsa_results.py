"""Response-spectrum postprocessing using CE586 modal response factors."""

from __future__ import annotations

from typing import Any

import numpy as np

from analysis.modal_combination import combine_all_methods, cqc_correlation_coefficient


def interpolate_spectrum_at_periods(periods, spectrum_periods, spectrum_Sa):
    """Linearly interpolate Sa at modal periods, clamping outside the spectrum."""
    targets = np.asarray(periods, dtype=float)
    source_periods = np.asarray(spectrum_periods, dtype=float)
    source_sa = np.asarray(spectrum_Sa, dtype=float)
    if source_periods.size == 0 or source_periods.size != source_sa.size:
        raise ValueError("Spectrum periods and Sa must be non-empty arrays of equal length.")
    order = np.argsort(source_periods)
    source_periods = source_periods[order]
    source_sa = source_sa[order]
    warnings = []
    for period in targets:
        if period < source_periods[0]:
            warnings.append(f"Mode period {period:.6g} s is below spectrum range; Sa clamped.")
        elif period > source_periods[-1]:
            warnings.append(f"Mode period {period:.6g} s is above spectrum range; Sa clamped.")
    values = np.interp(targets, source_periods, source_sa, left=source_sa[0], right=source_sa[-1])
    return values, warnings


def compute_modal_rsa_responses(modal_response_parameters, spectrum):
    """Compute peak modal vectors from Sa sampled at every modal period."""
    rows = modal_response_parameters["rows"]
    periods = np.asarray([row["period_s"] for row in rows], dtype=float)
    spectrum_periods = spectrum.get("periods", spectrum.get("T", []))
    sa, warnings = interpolate_spectrum_at_periods(periods, spectrum_periods, spectrum.get("Sa", []))
    damping = spectrum.get("modal_damping_ratios", spectrum.get("damping_ratio", 0.05))
    if np.isscalar(damping):
        damping_values = np.full(len(rows), float(damping))
    else:
        damping_values = np.asarray(damping, dtype=float)[: len(rows)]

    displacements = np.vstack([row["u_coeff"] * sa[idx] for idx, row in enumerate(rows)])
    forces = np.vstack([row["sn"] * sa[idx] for idx, row in enumerate(rows)])
    base_shear = np.asarray([row["Vb_coeff"] * sa[idx] for idx, row in enumerate(rows)])
    base_moment = np.asarray([row["Mb_coeff"] * sa[idx] for idx, row in enumerate(rows)])
    return {
        "modal_response_parameters": modal_response_parameters,
        "modal_spectrum_values": sa,
        "modal_damping_ratios": damping_values,
        "modal_displacements": displacements,
        "modal_forces": forces,
        "modal_base_shear": base_shear,
        "modal_base_moment": base_moment,
        "spectrum_source": spectrum.get("record_path", spectrum.get("source", "response spectrum")),
        "spectrum_unit": spectrum.get("acceleration_unit", spectrum.get("Sa_unit", "m/s^2")),
        "warnings": warnings,
    }


def compute_rsa_combinations(modal_responses, omegas=None, damping_ratios=None, methods=None):
    """Combine floor and base modal responses using ABSSUM, SRSS, and CQC."""
    methods = methods or ("ABSSUM", "SRSS", "CQC")
    parameters = modal_responses["modal_response_parameters"]
    omega = np.asarray(omegas if omegas is not None else parameters["omegas"], dtype=float)
    damping = damping_ratios if damping_ratios is not None else modal_responses["modal_damping_ratios"]
    damping_array = np.asarray(damping, dtype=float).reshape(-1)
    xi = float(damping_array[0]) if damping_array.size else 0.05

    def combine_components(values):
        values = np.asarray(values, dtype=float)
        if values.ndim == 1:
            return _selected_methods(combine_all_methods(values, omega, damping_ratio=xi), methods)
        return [
            _selected_methods(combine_all_methods(values[:, idx], omega, damping_ratio=xi), methods)
            for idx in range(values.shape[1])
        ]

    rho = np.array(
        [[cqc_correlation_coefficient(wi, wj, xi) for wj in omega] for wi in omega],
        dtype=float,
    )
    return {
        "methods": list(methods),
        "floor_displacements": combine_components(modal_responses["modal_displacements"]),
        "floor_forces": combine_components(modal_responses["modal_forces"]),
        "base_shear": combine_components(modal_responses["modal_base_shear"]),
        "base_moment": combine_components(modal_responses["modal_base_moment"]),
        "cqc_correlation_matrix": rho,
        "damping_ratio": xi,
    }


def _selected_methods(values: dict[str, float], methods) -> dict[str, float]:
    return {method: float(values[method]) for method in methods}
