"""Linear elastic modal response-history analysis for base excitation."""

from __future__ import annotations

from typing import Any

import numpy as np

from postprocessing.drift_results import group_nodes_by_floor, get_roof_nodes


def run_modal_rha(
    modal_result: dict[str, Any],
    ground_motion: dict[str, Any],
    damping_ratio: float | list[float] | np.ndarray = 0.05,
    num_modes: int | None = None,
    direction: str = "ux",
) -> dict[str, Any]:
    """Run linear elastic modal RHA using existing modal-analysis results."""
    if direction != "ux":
        raise ValueError("First-version modal RHA supports direction='ux' only.")
    time = np.asarray(ground_motion["time"], dtype=float)
    ag = np.asarray(ground_motion["acceleration"], dtype=float)
    if time.shape != ag.shape:
        raise ValueError("Ground-motion time and acceleration arrays must have the same shape.")
    if time.size < 2:
        raise ValueError("Ground motion must contain at least two points.")
    dt = float(ground_motion.get("dt", time[1] - time[0]))
    if dt <= 0.0:
        raise ValueError("Ground-motion dt must be positive.")

    omegas = np.asarray(modal_result.get("omega", modal_result.get("omega_rad_per_s", [])), dtype=float)
    if omegas.size == 0:
        raise ValueError("Modal result must contain circular frequencies.")
    n_available = min(omegas.size, len(modal_result.get("node_mode_shapes", [])))
    if n_available <= 0:
        raise ValueError("Modal result must contain node-keyed mode shapes.")
    n_modes = n_available if num_modes is None else int(num_modes)
    if n_modes <= 0:
        raise ValueError("num_modes must be positive.")
    if n_modes > n_available:
        raise ValueError(f"num_modes cannot exceed available modes ({n_available}).")
    if np.any(omegas[:n_modes] <= 0.0):
        raise ValueError("Modal RHA requires positive circular frequencies.")

    gammas = _participation_factors(modal_result, n_modes)
    xis = _damping_ratios(damping_ratio, n_modes)
    q = np.zeros((n_modes, time.size), dtype=float)
    qdot = np.zeros_like(q)
    qddot = np.zeros_like(q)
    warnings: list[str] = []

    for mode_idx in range(n_modes):
        response = solve_modal_sdof_history(omegas[mode_idx], gammas[mode_idx], ag, dt, xi=xis[mode_idx])
        q[mode_idx, :] = response["displacement"]
        qdot[mode_idx, :] = response["velocity"]
        qddot[mode_idx, :] = response["relative_acceleration"]

    node_histories = reconstruct_displacement_history(modal_result, q, direction=direction, num_modes=n_modes)
    floor_histories = compute_floor_displacement_histories(modal_result, node_histories)
    story_histories = compute_story_drift_histories(floor_histories)
    peak_floor = peak_floor_responses(floor_histories, time)
    peak_story = peak_story_drifts(story_histories, time)
    roof = peak_roof_displacement(modal_result, node_histories, time)

    record_name = str(ground_motion.get("path", ground_motion.get("name", "ground motion")))
    return {
        "time": time,
        "ground_acceleration": ag,
        "dt": dt,
        "duration": float(time[-1] - time[0]),
        "n_points": int(time.size),
        "pga_mps2": float(np.max(np.abs(ag))),
        "pga_g": float(np.max(np.abs(ag))) / 9.80665,
        "record_name": record_name,
        "input_unit": ground_motion.get("input_unit", ""),
        "damping_ratio": float(xis[0]) if np.allclose(xis, xis[0]) else xis,
        "modal_damping_ratios": xis,
        "modes_used": n_modes,
        "direction": direction,
        "omega": omegas[:n_modes],
        "participation_factors": gammas,
        "modal_coordinate_histories": q,
        "modal_velocity_histories": qdot,
        "modal_acceleration_histories": qddot,
        "node_displacement_histories": node_histories,
        "floor_displacement_histories": floor_histories,
        "story_drift_histories": story_histories,
        "peak_roof_displacement": roof,
        "peak_floor_responses": peak_floor,
        "peak_story_drifts": peak_story,
        "warnings": warnings,
    }


def solve_modal_sdof_history(
    omega: float,
    gamma: float,
    ag: Any,
    dt: float,
    xi: float = 0.05,
) -> dict[str, np.ndarray]:
    """Solve ``qddot + 2 xi omega qdot + omega^2 q = -Gamma ag``."""
    if omega <= 0.0:
        raise ValueError("omega must be positive.")
    if xi < 0.0:
        raise ValueError("damping ratio cannot be negative.")
    if dt <= 0.0:
        raise ValueError("dt must be positive.")

    ag_values = np.asarray(ag, dtype=float)
    beta = 0.25
    newmark_gamma = 0.5
    mass = 1.0
    stiffness = omega * omega
    damping = 2.0 * xi * omega
    force = -float(gamma) * ag_values

    n = ag_values.size
    q = np.zeros(n, dtype=float)
    qdot = np.zeros(n, dtype=float)
    qddot = np.zeros(n, dtype=float)
    qddot[0] = (force[0] - damping * qdot[0] - stiffness * q[0]) / mass

    a0 = 1.0 / (beta * dt * dt)
    a1 = newmark_gamma / (beta * dt)
    a2 = 1.0 / (beta * dt)
    a3 = 1.0 / (2.0 * beta) - 1.0
    a4 = newmark_gamma / beta - 1.0
    a5 = dt * (newmark_gamma / (2.0 * beta) - 1.0)
    k_eff = stiffness + a0 * mass + a1 * damping

    for idx in range(n - 1):
        p_eff = (
            force[idx + 1]
            + mass * (a0 * q[idx] + a2 * qdot[idx] + a3 * qddot[idx])
            + damping * (a1 * q[idx] + a4 * qdot[idx] + a5 * qddot[idx])
        )
        q[idx + 1] = p_eff / k_eff
        qddot[idx + 1] = a0 * (q[idx + 1] - q[idx]) - a2 * qdot[idx] - a3 * qddot[idx]
        qdot[idx + 1] = qdot[idx] + dt * ((1.0 - newmark_gamma) * qddot[idx] + newmark_gamma * qddot[idx + 1])

    return {"displacement": q, "velocity": qdot, "relative_acceleration": qddot}


def reconstruct_displacement_history(
    modal_result: dict[str, Any],
    modal_coordinate_histories: Any,
    direction: str = "ux",
    num_modes: int | None = None,
) -> dict[int, np.ndarray]:
    """Reconstruct node displacement histories from modal coordinates."""
    q = np.asarray(modal_coordinate_histories, dtype=float)
    if q.ndim != 2:
        raise ValueError("modal_coordinate_histories must be a 2D array.")
    n_modes = q.shape[0] if num_modes is None else int(num_modes)
    node_modes = modal_result.get("node_mode_shapes", [])
    nodes = {int(node_id): np.zeros(q.shape[1], dtype=float) for node_id in modal_result.get("nodes", {})}
    for mode_idx in range(n_modes):
        mode = node_modes[mode_idx]
        for node_id, components in mode.items():
            nodes.setdefault(int(node_id), np.zeros(q.shape[1], dtype=float))
            nodes[int(node_id)] += float(components.get(direction, 0.0)) * q[mode_idx, :]
    return nodes


def compute_floor_displacement_histories(
    modal_result: dict[str, Any],
    node_displacement_histories: dict[int, np.ndarray],
) -> list[dict[str, Any]]:
    """Return mean lateral displacement history per floor elevation."""
    grouped = group_nodes_by_floor(modal_result.get("nodes", {}))
    floors = []
    for floor_index, (elevation, node_ids) in enumerate(grouped.items()):
        values = [node_displacement_histories.get(int(node_id)) for node_id in node_ids]
        values = [value for value in values if value is not None]
        if values:
            history = np.mean(np.vstack(values), axis=0)
        else:
            history = np.array([], dtype=float)
        floors.append(
            {
                "floor": floor_index,
                "elevation": float(elevation),
                "node_ids": [int(node_id) for node_id in node_ids],
                "history": history,
            }
        )
    return floors


def compute_story_drift_histories(floor_displacement_histories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return interstory drift histories from floor displacement histories."""
    stories = []
    for idx in range(1, len(floor_displacement_histories)):
        lower = floor_displacement_histories[idx - 1]
        upper = floor_displacement_histories[idx]
        height = float(upper["elevation"]) - float(lower["elevation"])
        if height <= 0.0:
            raise ValueError("Floor elevations must be strictly increasing.")
        history = np.asarray(upper["history"], dtype=float) - np.asarray(lower["history"], dtype=float)
        stories.append(
            {
                "story": idx,
                "lower_elevation": lower["elevation"],
                "upper_elevation": upper["elevation"],
                "story_height": height,
                "history": history,
                "drift_ratio_history": history / height,
            }
        )
    return stories


def peak_roof_displacement(
    modal_result: dict[str, Any],
    node_displacement_histories: dict[int, np.ndarray],
    time: np.ndarray,
) -> dict[str, Any]:
    """Return peak roof displacement summary."""
    roof_nodes = get_roof_nodes(modal_result.get("nodes", {}))
    if not roof_nodes:
        return {"value": 0.0, "time": 0.0, "node": None, "history": np.array([], dtype=float)}
    roof_histories = {node_id: node_displacement_histories[int(node_id)] for node_id in roof_nodes}
    controlling_node, history = max(roof_histories.items(), key=lambda item: float(np.max(np.abs(item[1]))))
    idx = int(np.argmax(np.abs(history)))
    mean_history = np.mean(np.vstack(list(roof_histories.values())), axis=0)
    return {
        "value": float(history[idx]),
        "abs_value": float(abs(history[idx])),
        "time": float(time[idx]),
        "node": int(controlling_node),
        "roof_node_ids": roof_nodes,
        "history": mean_history,
    }


def peak_floor_responses(floor_displacement_histories: list[dict[str, Any]], time: np.ndarray) -> list[dict[str, Any]]:
    """Return positive, negative, and absolute peak floor responses."""
    rows = []
    for floor in floor_displacement_histories:
        history = np.asarray(floor["history"], dtype=float)
        pos_idx = int(np.argmax(history)) if history.size else 0
        neg_idx = int(np.argmin(history)) if history.size else 0
        abs_idx = int(np.argmax(np.abs(history))) if history.size else 0
        rows.append(
            {
                "floor": int(floor["floor"]),
                "elevation": float(floor["elevation"]),
                "peak_positive": float(history[pos_idx]) if history.size else 0.0,
                "peak_negative": float(history[neg_idx]) if history.size else 0.0,
                "peak_absolute": float(abs(history[abs_idx])) if history.size else 0.0,
                "controlling_time": float(time[abs_idx]) if history.size else 0.0,
            }
        )
    return rows


def peak_story_drifts(story_drift_histories: list[dict[str, Any]], time: np.ndarray) -> list[dict[str, Any]]:
    """Return positive, negative, and absolute peak story drift responses."""
    rows = []
    for story in story_drift_histories:
        history = np.asarray(story["history"], dtype=float)
        ratio = np.asarray(story["drift_ratio_history"], dtype=float)
        pos_idx = int(np.argmax(history)) if history.size else 0
        neg_idx = int(np.argmin(history)) if history.size else 0
        abs_idx = int(np.argmax(np.abs(history))) if history.size else 0
        rows.append(
            {
                "story": int(story["story"]),
                "lower_elevation": float(story["lower_elevation"]),
                "upper_elevation": float(story["upper_elevation"]),
                "peak_positive": float(history[pos_idx]) if history.size else 0.0,
                "peak_negative": float(history[neg_idx]) if history.size else 0.0,
                "peak_absolute": float(abs(history[abs_idx])) if history.size else 0.0,
                "peak_drift_ratio": float(abs(ratio[abs_idx])) if ratio.size else 0.0,
                "controlling_time": float(time[abs_idx]) if history.size else 0.0,
            }
        )
    return rows


def _participation_factors(modal_result: dict[str, Any], n_modes: int) -> np.ndarray:
    rows = modal_result.get("participation", []) or []
    if len(rows) < n_modes:
        raise ValueError("Modal participation factors are required for modal RHA.")
    return np.asarray([float(rows[idx].get("gamma", 0.0)) for idx in range(n_modes)], dtype=float)


def _damping_ratios(values: float | list[float] | np.ndarray, n_modes: int) -> np.ndarray:
    if np.isscalar(values):
        xi = np.full(n_modes, float(values), dtype=float)
    else:
        xi = np.asarray(values, dtype=float).reshape(-1)
        if xi.size < n_modes:
            raise ValueError("Not enough modal damping ratios were provided.")
        xi = xi[:n_modes]
    if np.any(xi < 0.0):
        raise ValueError("damping ratio cannot be negative.")
    return xi
