"""Ground-motion time-history loader and unit conversion helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np


G_ACCEL = 9.80665


def load_ground_motion(
    path: str | Path,
    input_unit: str = "cm/s2",
    output_unit: str = "m/s2",
    dt_tol: float = 1e-8,
) -> dict[str, Any]:
    """Load a two-column ``time acceleration`` ground-motion text file."""
    raw = np.loadtxt(str(path), comments="#", dtype=float)
    if raw.ndim == 1:
        raw = raw.reshape(1, -1)
    if raw.shape[1] != 2:
        raise ValueError("Ground motion file must have exactly two columns: time acceleration.")

    time = np.asarray(raw[:, 0], dtype=float)
    acceleration = convert_acceleration(raw[:, 1], input_unit, output_unit)
    dt = validate_constant_dt(time, dt_tol=dt_tol)

    return {
        "time": time,
        "acceleration": acceleration,
        "dt": dt,
        "duration": float(time[-1] - time[0]) if time.size else 0.0,
        "n_points": int(time.size),
        "pga": float(np.max(np.abs(acceleration))) if acceleration.size else 0.0,
        "input_unit": input_unit,
        "output_unit": output_unit,
    }


def validate_constant_dt(time: np.ndarray, dt_tol: float = 1e-8) -> float:
    """Validate that a time vector is increasing with constant spacing."""
    time = np.asarray(time, dtype=float)
    if time.size < 2:
        raise ValueError("At least two time points are required.")

    increments = np.diff(time)
    if np.any(increments <= 0.0):
        raise ValueError("Ground motion time values must be strictly increasing.")

    dt = float(increments[0])
    if not np.allclose(increments, dt, atol=dt_tol, rtol=0.0):
        raise ValueError("Ground motion time step is not constant within tolerance.")
    return dt


def convert_acceleration(values, input_unit: str, output_unit: str = "m/s2") -> np.ndarray:
    """Convert acceleration values to the requested output unit."""
    values = np.asarray(values, dtype=float)
    values_mps2 = values * _to_mps2_factor(input_unit)
    return values_mps2 / _to_mps2_factor(output_unit)


def _to_mps2_factor(unit: str) -> float:
    normalized = _normalize_unit(unit)
    if normalized == "m/s2":
        return 1.0
    if normalized == "cm/s2":
        return 0.01
    if normalized == "g":
        return G_ACCEL
    raise ValueError(f"Unsupported acceleration unit {unit!r}. Use cm/s2, m/s2, or g.")


def _normalize_unit(unit: str) -> str:
    text = unit.strip().lower().replace("^", "")
    text = text.replace("sec", "s")
    text = text.replace(" ", "")
    if text in {"m/s2", "m/s/s", "mps2"}:
        return "m/s2"
    if text in {"cm/s2", "cm/s/s", "cmps2"}:
        return "cm/s2"
    if text in {"g", "gravity"}:
        return "g"
    return text
