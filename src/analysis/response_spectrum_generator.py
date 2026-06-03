"""Elastic SDOF response spectrum generation using Newmark integration."""

from __future__ import annotations

from typing import Any

import numpy as np


def generate_elastic_response_spectrum(
    time,
    ground_acceleration,
    periods,
    damping_ratio: float = 0.05,
) -> dict[str, Any]:
    """Generate elastic response spectra for an acceleration input in m/s^2.

    The SDOF equation is solved in relative coordinates:
        u_ddot + 2*zeta*omega*u_dot + omega^2*u = -a_g(t)

    ``Sa`` is the maximum absolute total acceleration response. ``Sv`` is the
    maximum relative velocity response and ``Sd`` is the maximum relative
    displacement response.
    """
    time = np.asarray(time, dtype=float)
    ag = np.asarray(ground_acceleration, dtype=float)
    periods = np.asarray(periods, dtype=float)

    if time.shape != ag.shape:
        raise ValueError("time and ground_acceleration must have the same shape.")
    if damping_ratio < 0.0:
        raise ValueError("damping_ratio cannot be negative.")
    if np.any(periods <= 0.0):
        raise ValueError("All periods must be positive.")

    dt = _validate_constant_dt(time)
    sd = np.zeros_like(periods, dtype=float)
    sv = np.zeros_like(periods, dtype=float)
    sa = np.zeros_like(periods, dtype=float)

    for idx, period in enumerate(periods):
        response = _newmark_average_acceleration(ag, dt, float(period), damping_ratio)
        sd[idx] = float(np.max(np.abs(response["displacement"])))
        sv[idx] = float(np.max(np.abs(response["velocity"])))
        sa[idx] = float(np.max(np.abs(response["absolute_acceleration"])))

    return {
        "periods": periods,
        "damping_ratio": damping_ratio,
        "Sa": sa,
        "Sv": sv,
        "Sd": sd,
    }


def _newmark_average_acceleration(ag: np.ndarray, dt: float, period: float, damping_ratio: float) -> dict[str, np.ndarray]:
    beta = 0.25
    gamma = 0.5
    mass = 1.0
    omega = 2.0 * np.pi / period
    stiffness = omega * omega * mass
    damping = 2.0 * damping_ratio * omega * mass
    force = -mass * ag

    n = ag.size
    u = np.zeros(n, dtype=float)
    v = np.zeros(n, dtype=float)
    a_rel = np.zeros(n, dtype=float)
    a_abs = np.zeros(n, dtype=float)

    a_rel[0] = (force[0] - damping * v[0] - stiffness * u[0]) / mass
    a_abs[0] = a_rel[0] + ag[0]

    a0 = 1.0 / (beta * dt * dt)
    a1 = gamma / (beta * dt)
    a2 = 1.0 / (beta * dt)
    a3 = 1.0 / (2.0 * beta) - 1.0
    a4 = gamma / beta - 1.0
    a5 = dt * (gamma / (2.0 * beta) - 1.0)
    k_eff = stiffness + a0 * mass + a1 * damping

    for i in range(n - 1):
        p_eff = (
            force[i + 1]
            + mass * (a0 * u[i] + a2 * v[i] + a3 * a_rel[i])
            + damping * (a1 * u[i] + a4 * v[i] + a5 * a_rel[i])
        )
        u[i + 1] = p_eff / k_eff
        a_rel[i + 1] = a0 * (u[i + 1] - u[i]) - a2 * v[i] - a3 * a_rel[i]
        v[i + 1] = v[i] + dt * ((1.0 - gamma) * a_rel[i] + gamma * a_rel[i + 1])
        a_abs[i + 1] = a_rel[i + 1] + ag[i + 1]

    return {
        "displacement": u,
        "velocity": v,
        "relative_acceleration": a_rel,
        "absolute_acceleration": a_abs,
    }


def _validate_constant_dt(time: np.ndarray, dt_tol: float = 1e-8) -> float:
    if time.size < 2:
        raise ValueError("At least two time points are required.")
    increments = np.diff(time)
    if np.any(increments <= 0.0):
        raise ValueError("time values must be strictly increasing.")
    dt = float(increments[0])
    if not np.allclose(increments, dt, atol=dt_tol, rtol=0.0):
        raise ValueError("time step is not constant within tolerance.")
    return dt
