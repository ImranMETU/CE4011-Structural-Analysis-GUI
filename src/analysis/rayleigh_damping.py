"""Rayleigh damping diagnostics for modal/eigenanalysis results."""

from __future__ import annotations

from typing import Any

import numpy as np


def rayleigh_coefficients(
    omega_i: float,
    xi_i: float,
    omega_j: float,
    xi_j: float,
) -> tuple[float, float]:
    """Return Rayleigh coefficients ``a0`` and ``a1`` from two target modes."""
    wi = _positive_float(omega_i, "omega_i")
    wj = _positive_float(omega_j, "omega_j")
    xi_i_value = _nonnegative_float(xi_i, "xi_i")
    xi_j_value = _nonnegative_float(xi_j, "xi_j")
    if abs(wi - wj) <= 1.0e-12:
        raise ValueError("Target modes must have distinct positive circular frequencies.")

    matrix = np.array([[1.0 / (2.0 * wi), wi / 2.0], [1.0 / (2.0 * wj), wj / 2.0]], dtype=float)
    targets = np.array([xi_i_value, xi_j_value], dtype=float)
    a0, a1 = np.linalg.solve(matrix, targets)
    return float(a0), float(a1)


def rayleigh_damping_ratios(omegas: Any, a0: float, a1: float) -> np.ndarray:
    """Return Rayleigh damping ratios for every circular frequency."""
    omega = np.asarray(omegas, dtype=float).reshape(-1)
    if omega.size == 0:
        raise ValueError("At least one circular frequency is required.")
    if np.any(omega <= 0.0):
        raise ValueError("Rayleigh damping ratios require positive circular frequencies.")
    return float(a0) / (2.0 * omega) + float(a1) * omega / 2.0


def build_rayleigh_damping_matrix(M: Any, K: Any, a0: float, a1: float) -> np.ndarray:
    """Return ``C = a0 M + a1 K``."""
    mass = np.asarray(M, dtype=float)
    stiffness = np.asarray(K, dtype=float)
    if mass.ndim != 2 or mass.shape[0] != mass.shape[1]:
        raise ValueError("M must be a square matrix.")
    if stiffness.ndim != 2 or stiffness.shape[0] != stiffness.shape[1]:
        raise ValueError("K must be a square matrix.")
    if mass.shape != stiffness.shape:
        raise ValueError("M and K must have the same shape.")
    return float(a0) * mass + float(a1) * stiffness


def format_rayleigh_table(
    omegas: Any,
    frequencies: Any,
    periods: Any,
    xis: Any,
) -> tuple[list[str], list[list[str]]]:
    """Return formatted Rayleigh damping rows."""
    omega = np.asarray(omegas, dtype=float).reshape(-1)
    hz = np.asarray(frequencies, dtype=float).reshape(-1)
    period = np.asarray(periods, dtype=float).reshape(-1)
    xi = np.asarray(xis, dtype=float).reshape(-1)
    if not (omega.size == hz.size == period.size == xi.size):
        raise ValueError("Rayleigh table arrays must have the same length.")

    headers = ["Mode", "omega rad/s", "frequency Hz", "period s", "Rayleigh xi"]
    rows = []
    for idx in range(omega.size):
        rows.append(
            [
                str(idx + 1),
                _format_number(omega[idx]),
                _format_number(hz[idx]),
                _format_number(period[idx]),
                _format_number(xi[idx]),
            ]
        )
    return headers, rows


def _positive_float(value: Any, label: str) -> float:
    number = float(value)
    if number <= 0.0:
        raise ValueError(f"{label} must be positive.")
    return number


def _nonnegative_float(value: Any, label: str) -> float:
    number = float(value)
    if number < 0.0:
        raise ValueError(f"{label} must be nonnegative.")
    return number


def _format_number(value: Any) -> str:
    return f"{float(value):.6e}"
