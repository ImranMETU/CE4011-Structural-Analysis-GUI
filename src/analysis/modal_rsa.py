"""Per-mode response-spectrum postprocessing for existing modal results."""

from __future__ import annotations

from typing import Any

import numpy as np

from postprocessing.drift_results import group_nodes_by_floor, get_roof_nodes


def run_modal_rsa(
    modal_result: dict[str, Any],
    spectrum_result: dict[str, Any],
    static_or_model_data: dict[str, Any] | None = None,
    num_modes: int | None = None,
    direction: str = "ux",
) -> dict[str, Any]:
    """Compute per-mode peak response estimates from a response spectrum.

    This intentionally does not combine modes. Each row is the peak contribution
    of one retained mode using ``qmax_n = Gamma_n * Sd(T_n)``.
    """
    if direction not in {"ux", "uy", "rz"}:
        raise ValueError("direction must be ux, uy, or rz.")

    periods = np.asarray(modal_result.get("periods", []), dtype=float)
    omegas = np.asarray(modal_result.get("omega", modal_result.get("omega_rad_per_s", [])), dtype=float)
    frequencies = np.asarray(modal_result.get("frequencies_hz", []), dtype=float)
    eigenvalues = np.asarray(modal_result.get("eigenvalues", omegas * omegas), dtype=float)
    node_modes = modal_result.get("node_mode_shapes", [])
    if periods.size == 0 or omegas.size == 0 or not node_modes:
        raise ValueError("Modal RSA requires periods, circular frequencies, and node mode shapes.")

    participation = modal_result.get("participation", []) or []
    if len(participation) == 0:
        raise ValueError("Modal RSA requires modal participation factors.")

    n_available = min(periods.size, omegas.size, len(node_modes), len(participation))
    n_modes = n_available if num_modes is None else min(int(num_modes), n_available)
    if n_modes <= 0:
        raise ValueError("num_modes must be positive.")

    nodes = _node_coordinates(modal_result, static_or_model_data)
    spectrum_periods = np.asarray(spectrum_result.get("periods", spectrum_result.get("T", [])), dtype=float)
    sa_values = np.asarray(spectrum_result.get("Sa", []), dtype=float)
    sd_values = np.asarray(spectrum_result.get("Sd", []), dtype=float)
    if spectrum_periods.size == 0 or sa_values.size == 0:
        raise ValueError("Spectrum result must contain periods and Sa arrays.")
    if sd_values.size == 0:
        sd_values = np.array([sa / (omega * omega) if omega > 0.0 else 0.0 for sa, omega in zip(sa_values, 2.0 * np.pi / spectrum_periods)])

    warnings: list[str] = []
    modal_peak_rows = []
    roof_peak_by_mode = []
    floor_peak_by_mode = []
    story_drift_peak_by_mode = []

    for mode_index in range(n_modes):
        mode_number = mode_index + 1
        period = float(periods[mode_index])
        omega = float(omegas[mode_index])
        sa = _interpolate_spectrum_value(spectrum_periods, sa_values, period, "Sa", warnings)
        sd = _interpolate_spectrum_value(spectrum_periods, sd_values, period, "Sd", warnings)
        gamma = float(participation[mode_index].get("gamma", 0.0))
        qmax = gamma * sd
        node_contrib = _node_contribution(node_modes[mode_index], qmax)
        roof_row = _roof_peak_row(mode_number, nodes, node_contrib, direction)
        floor_rows = _floor_peak_rows(mode_number, nodes, node_contrib, direction)
        story_rows = _story_peak_rows(mode_number, floor_rows)

        modal_peak_rows.append(
            {
                "mode": mode_number,
                "eigenvalue": float(eigenvalues[mode_index]) if mode_index < eigenvalues.size else omega * omega,
                "omega_rad_per_s": omega,
                "frequency_hz": float(frequencies[mode_index]) if mode_index < frequencies.size else omega / (2.0 * np.pi),
                "period_s": period,
                "gamma": gamma,
                "Sa_at_Tn": sa,
                "Sd_at_Tn": sd,
                "qmax": qmax,
                "peak_roof_ux": roof_row.get("peak_roof_response", 0.0),
                "controlling_roof_node": roof_row.get("controlling_roof_node"),
                "node_displacement_contribution": node_contrib,
            }
        )
        roof_peak_by_mode.append(roof_row)
        floor_peak_by_mode.extend(floor_rows)
        story_drift_peak_by_mode.extend(story_rows)

    combined = _combined_rsa_results(
        roof_peak_by_mode,
        floor_peak_by_mode,
        story_drift_peak_by_mode,
        omegas[:n_modes],
        spectrum_result.get("damping_ratio", 0.05),
    )
    combined["warnings"].extend(warnings)

    return {
        "modes_used": n_modes,
        "direction": direction,
        "modal_peak_rows": modal_peak_rows,
        "roof_peak_by_mode": roof_peak_by_mode,
        "floor_peak_by_mode": floor_peak_by_mode,
        "story_drift_peak_by_mode": story_drift_peak_by_mode,
        "combined": combined,
        "spectrum_metadata": {
            "period_min": float(np.min(spectrum_periods)),
            "period_max": float(np.max(spectrum_periods)),
            "damping_ratio": spectrum_result.get("damping_ratio", ""),
        },
        "warnings": warnings,
    }


def _combined_rsa_results(
    roof_peak_by_mode: list[dict[str, Any]],
    floor_peak_by_mode: list[dict[str, Any]],
    story_drift_peak_by_mode: list[dict[str, Any]],
    omegas: np.ndarray,
    damping_ratio: Any,
) -> dict[str, Any]:
    from analysis.modal_combination import combine_all_methods

    xi = _float_or_default(damping_ratio, 0.05)
    warnings: list[str] = []
    roof_values = [float(row.get("peak_roof_response", row.get("peak_roof_ux", 0.0))) for row in roof_peak_by_mode]
    roof = combine_all_methods(roof_values, omegas, damping_ratio=xi) if roof_values else {"ABSSUM": 0.0, "SRSS": 0.0, "CQC": 0.0}

    floor_rows = []
    floors = sorted({int(row.get("floor", 0)) for row in floor_peak_by_mode})
    for floor in floors:
        rows = [row for row in floor_peak_by_mode if int(row.get("floor", 0)) == floor]
        values = [float(row.get("peak_floor_displacement", 0.0)) for row in rows]
        row_omegas = _omegas_for_rows(rows, omegas)
        floor_rows.append(
            {
                "floor": floor,
                "elevation": float(rows[0].get("elevation", 0.0)) if rows else 0.0,
                "quantity": "Floor ux",
                **combine_all_methods(values, row_omegas, damping_ratio=xi),
            }
        )
    if not floor_rows:
        warnings.append("RSA floor response combination unavailable: no floor rows were generated.")

    story_rows = []
    stories = sorted({int(row.get("story", 0)) for row in story_drift_peak_by_mode})
    for story in stories:
        rows = [row for row in story_drift_peak_by_mode if int(row.get("story", 0)) == story]
        row_omegas = _omegas_for_rows(rows, omegas)
        drift_values = [float(row.get("peak_story_drift", 0.0)) for row in rows]
        ratio_values = [float(row.get("peak_drift_ratio", 0.0)) for row in rows]
        story_rows.append(
            {
                "story": story,
                "lower_elevation": float(rows[0].get("lower_elevation", 0.0)) if rows else 0.0,
                "upper_elevation": float(rows[0].get("upper_elevation", 0.0)) if rows else 0.0,
                "quantity": "Story drift",
                **combine_all_methods(drift_values, row_omegas, damping_ratio=xi),
                "drift_ratio": combine_all_methods(ratio_values, row_omegas, damping_ratio=xi),
            }
        )
    if not story_rows:
        warnings.append("RSA story drift combination unavailable: no story rows were generated.")

    return {
        "method_names": ["ABSSUM", "SRSS", "CQC"],
        "roof_response": roof,
        "floor_responses": floor_rows,
        "story_drifts": story_rows,
        "damping_ratio": xi,
        "warnings": warnings,
    }


def _omegas_for_rows(rows: list[dict[str, Any]], omegas: np.ndarray) -> np.ndarray:
    return np.asarray([omegas[int(row.get("mode", 1)) - 1] for row in rows], dtype=float)


def _float_or_default(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def interpolate_spectrum_at_period(
    spectrum_result: dict[str, Any],
    period: float,
    quantity: str = "Sa",
) -> tuple[float, list[str]]:
    """Return an interpolated spectrum ordinate and any clamp warning."""
    warnings: list[str] = []
    spectrum_periods = np.asarray(spectrum_result.get("periods", []), dtype=float)
    values = np.asarray(spectrum_result.get(quantity, []), dtype=float)
    if spectrum_periods.size == 0 or values.size == 0:
        raise ValueError(f"Spectrum result must contain periods and {quantity}.")
    value = _interpolate_spectrum_value(spectrum_periods, values, float(period), quantity, warnings)
    return value, warnings


def _interpolate_spectrum_value(
    periods: np.ndarray,
    values: np.ndarray,
    target_period: float,
    label: str,
    warnings: list[str],
) -> float:
    if periods.size != values.size:
        raise ValueError(f"Spectrum periods and {label} arrays must have the same length.")
    order = np.argsort(periods)
    periods = periods[order]
    values = values[order]
    if target_period < periods[0]:
        warnings.append(f"Mode period {target_period:.6g} s is below spectrum range; {label} clamped to T={periods[0]:.6g}.")
        return float(values[0])
    if target_period > periods[-1]:
        warnings.append(f"Mode period {target_period:.6g} s is above spectrum range; {label} clamped to T={periods[-1]:.6g}.")
        return float(values[-1])
    return float(np.interp(target_period, periods, values))


def _node_coordinates(modal_result: dict[str, Any], model_data: dict[str, Any] | None) -> dict[int, dict[str, float]]:
    if modal_result.get("nodes"):
        return {int(node_id): dict(node) for node_id, node in modal_result["nodes"].items()}
    if model_data and model_data.get("nodes"):
        raw_nodes = model_data["nodes"]
        if isinstance(raw_nodes, dict):
            return {int(node_id): dict(node) for node_id, node in raw_nodes.items()}
        return {int(node["id"]): dict(node) for node in raw_nodes}
    return {}


def _node_contribution(mode_shape: dict[int, dict[str, float]], qmax: float) -> dict[int, dict[str, float]]:
    return {
        int(node_id): {
            "ux": float(values.get("ux", 0.0)) * qmax,
            "uy": float(values.get("uy", 0.0)) * qmax,
            "rz": float(values.get("rz", 0.0)) * qmax,
        }
        for node_id, values in mode_shape.items()
    }


def _roof_peak_row(
    mode: int,
    nodes: dict[int, dict[str, float]],
    node_contrib: dict[int, dict[str, float]],
    direction: str,
) -> dict[str, Any]:
    roof_nodes = get_roof_nodes(nodes) if nodes else sorted(node_contrib)
    if not roof_nodes:
        return {"mode": mode, "peak_roof_response": 0.0, "controlling_roof_node": None}
    values = [(int(node_id), float(node_contrib.get(int(node_id), {}).get(direction, 0.0))) for node_id in roof_nodes]
    node_id, value = max(values, key=lambda item: abs(item[1]))
    return {"mode": mode, "peak_roof_response": value, "peak_roof_ux": value, "controlling_roof_node": node_id}


def _floor_peak_rows(
    mode: int,
    nodes: dict[int, dict[str, float]],
    node_contrib: dict[int, dict[str, float]],
    direction: str,
) -> list[dict[str, Any]]:
    if not nodes:
        return []
    rows = []
    for floor_idx, (elevation, node_ids) in enumerate(group_nodes_by_floor(nodes).items()):
        values = [float(node_contrib.get(int(node_id), {}).get(direction, 0.0)) for node_id in node_ids]
        floor_value = float(np.mean(values)) if values else 0.0
        rows.append(
            {
                "mode": mode,
                "floor": floor_idx,
                "elevation": float(elevation),
                "node_ids": [int(node_id) for node_id in node_ids],
                "peak_floor_displacement": floor_value,
            }
        )
    return rows


def _story_peak_rows(mode: int, floor_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    ordered = sorted(floor_rows, key=lambda row: row["elevation"])
    for idx in range(1, len(ordered)):
        lower = ordered[idx - 1]
        upper = ordered[idx]
        height = float(upper["elevation"]) - float(lower["elevation"])
        if height <= 0.0:
            continue
        drift = float(upper["peak_floor_displacement"]) - float(lower["peak_floor_displacement"])
        rows.append(
            {
                "mode": mode,
                "story": idx,
                "lower_elevation": float(lower["elevation"]),
                "upper_elevation": float(upper["elevation"]),
                "story_height": height,
                "peak_story_drift": drift,
                "peak_drift_ratio": drift / height,
            }
        )
    return rows
