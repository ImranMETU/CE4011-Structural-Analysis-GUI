"""Modal combination helpers for linear response-spectrum postprocessing."""

from __future__ import annotations

from typing import Any

import numpy as np


def combine_abssum(values: Any) -> float:
    """Return absolute-sum modal combination."""
    modal_values = np.asarray(values, dtype=float).reshape(-1)
    return float(np.sum(np.abs(modal_values)))


def combine_srss(values: Any) -> float:
    """Return square-root-of-sum-of-squares modal combination."""
    modal_values = np.asarray(values, dtype=float).reshape(-1)
    return float(np.sqrt(np.sum(modal_values * modal_values)))


def combine_cqc(values: Any, omegas: Any, damping_ratio: float = 0.05) -> float:
    """Return complete-quadratic-combination modal response.

    Uses equal damping for all modes and the correlation coefficient supplied in
    the lecture notes. The result is clamped to zero only for tiny negative
    values caused by floating-point roundoff.
    """
    modal_values = np.asarray(values, dtype=float).reshape(-1)
    omega_values = np.asarray(omegas, dtype=float).reshape(-1)
    if modal_values.size != omega_values.size:
        raise ValueError("values and omegas must have the same length.")
    if np.any(omega_values <= 0.0):
        raise ValueError("CQC requires positive modal circular frequencies.")
    xi = float(damping_ratio)
    if xi < 0.0:
        raise ValueError("damping_ratio cannot be negative.")

    total = 0.0
    for i, ri in enumerate(modal_values):
        for j, rj in enumerate(modal_values):
            rho = cqc_correlation_coefficient(omega_values[i], omega_values[j], xi)
            total += rho * ri * rj
    if total < 0.0 and abs(total) <= 1.0e-10:
        total = 0.0
    return float(np.sqrt(max(total, 0.0)))


def cqc_correlation_coefficient(omega_i: float, omega_j: float, damping_ratio: float = 0.05) -> float:
    """Return equal-damping CQC modal correlation coefficient."""
    omega_i = float(omega_i)
    omega_j = float(omega_j)
    if omega_i <= 0.0 or omega_j <= 0.0:
        raise ValueError("CQC requires positive modal circular frequencies.")
    if omega_i == omega_j:
        return 1.0
    xi = float(damping_ratio)
    beta = min(omega_i, omega_j) / max(omega_i, omega_j)
    numerator = 8.0 * xi * xi * (1.0 + beta) * (beta ** 1.5)
    denominator = ((1.0 - beta * beta) ** 2) + 4.0 * xi * xi * beta * ((1.0 + beta) ** 2)
    if abs(denominator) <= 1.0e-14:
        return 1.0
    return float(numerator / denominator)


def combine_all_methods(values: Any, omegas: Any, damping_ratio: float = 0.05) -> dict[str, float]:
    """Return ABSSUM, SRSS, and CQC for one response vector."""
    return {
        "ABSSUM": combine_abssum(values),
        "SRSS": combine_srss(values),
        "CQC": combine_cqc(values, omegas, damping_ratio=damping_ratio),
    }
