"""Standalone matrix-based generalized eigenanalysis utilities."""

from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Any

import numpy as np


class EigenCalculatorDependencyError(ImportError):
    """Raised when SciPy is unavailable for the generalized eigensolve."""


def solve_generalized_eigen(K: Any, M: Any, *, normalize: str = "max_abs") -> dict[str, Any]:
    """Solve ``K phi = lambda M phi`` and return modal quantities.

    The solver is intentionally standalone and does not interact with the
    frame/truss ``Structure`` workflow.
    """
    scipy_linalg = _require_scipy_linalg()
    k = _as_square_matrix(K, "K")
    m = _as_square_matrix(M, "M")
    _validate_same_shape(k, m, "K", "M")
    _validate_mass_matrix(m)

    eigenvalues, modes = scipy_linalg.eigh(k, m)
    eigenvalues = np.real_if_close(eigenvalues).astype(float)
    modes = np.real_if_close(modes).astype(float)

    order = np.argsort(eigenvalues)
    eigenvalues = eigenvalues[order]
    modes = modes[:, order]

    warnings: list[str] = []
    positive = eigenvalues > 1.0e-12
    if not np.all(positive):
        warnings.append("Negative or near-zero eigenvalues were omitted from frequency results.")
    eigenvalues = eigenvalues[positive]
    modes = modes[:, positive]
    if eigenvalues.size == 0:
        raise ValueError("No positive eigenvalues were found.")

    modes = normalize_modes(modes, method=normalize, M=m)
    omega = np.sqrt(eigenvalues)
    frequencies = omega / (2.0 * math.pi)
    periods = np.array([2.0 * math.pi / value if value > 0.0 else math.inf for value in omega])

    result = {
        "eigenvalues": eigenvalues,
        "omega_rad_per_s": omega,
        "frequency_Hz": frequencies,
        "period_s": periods,
        "modes": modes,
        "normalization": normalize,
        "warnings": warnings,
    }
    result.update(compute_modal_properties(k, m, modes=modes))
    return result


def compute_modal_properties(
    K: Any,
    M: Any,
    C: Any | None = None,
    modes: Any | None = None,
    influence_vector: Any | None = None,
) -> dict[str, Any]:
    """Compute modal mass, stiffness, damping, and participation properties."""
    k = _as_square_matrix(K, "K")
    m = _as_square_matrix(M, "M")
    _validate_same_shape(k, m, "K", "M")
    _validate_mass_matrix(m)

    c = None
    if C is not None:
        c = _as_square_matrix(C, "C")
        _validate_same_shape(k, c, "K", "C")

    if modes is None:
        base = solve_generalized_eigen(k, m)
        phi_matrix = np.asarray(base["modes"], dtype=float)
    else:
        phi_matrix = np.asarray(modes, dtype=float)
    if phi_matrix.ndim != 2 or phi_matrix.shape[0] != k.shape[0]:
        raise ValueError("modes must be a 2D array with one row per DOF.")

    r = _influence_vector(influence_vector, k.shape[0])
    total_effective_mass = float(r.T @ m @ r)

    modal_mass = []
    modal_stiffness = []
    modal_damping = []
    damping_ratio = []
    participation_factor = []
    effective_modal_mass = []
    effective_modal_mass_ratio = []
    cumulative_effective_mass_ratio = []

    cumulative = 0.0
    for mode_idx in range(phi_matrix.shape[1]):
        phi = phi_matrix[:, mode_idx]
        mn = float(phi.T @ m @ phi)
        kn = float(phi.T @ k @ phi)
        modal_mass.append(mn)
        modal_stiffness.append(kn)

        if c is not None:
            cn = float(phi.T @ c @ phi)
            modal_damping.append(cn)
            omega = math.sqrt(kn / mn) if mn > 0.0 and kn > 0.0 else 0.0
            damping_ratio.append(cn / (2.0 * mn * omega) if mn > 0.0 and omega > 0.0 else math.nan)

        ln = float(phi.T @ m @ r)
        gamma = ln / mn if mn > 0.0 else 0.0
        mstar = (ln * ln / mn) if mn > 0.0 else 0.0
        ratio = mstar / total_effective_mass if total_effective_mass > 0.0 else 0.0
        cumulative += ratio
        participation_factor.append(gamma)
        effective_modal_mass.append(mstar)
        effective_modal_mass_ratio.append(ratio)
        cumulative_effective_mass_ratio.append(cumulative)

    out: dict[str, Any] = {
        "modal_mass": np.asarray(modal_mass, dtype=float),
        "modal_stiffness": np.asarray(modal_stiffness, dtype=float),
        "participation_factor": np.asarray(participation_factor, dtype=float),
        "effective_modal_mass": np.asarray(effective_modal_mass, dtype=float),
        "effective_modal_mass_ratio": np.asarray(effective_modal_mass_ratio, dtype=float),
        "cumulative_effective_mass_ratio": np.asarray(cumulative_effective_mass_ratio, dtype=float),
        "influence_vector": r,
        "total_effective_mass": total_effective_mass,
    }
    if c is not None:
        out["modal_damping"] = np.asarray(modal_damping, dtype=float)
        out["damping_ratio"] = np.asarray(damping_ratio, dtype=float)
        out["damping_note"] = (
            "Damping ratios use phi.T C phi diagnostics and assume classical/modal-compatible "
            "damping when interpreted as uncoupled modal damping."
        )
    return out


def normalize_modes(modes: Any, method: str = "max_abs", M: Any | None = None) -> np.ndarray:
    """Normalize eigenvector columns using the requested display convention."""
    values = np.asarray(modes, dtype=float).copy()
    if values.ndim != 2:
        raise ValueError("modes must be a 2D array.")

    method_key = str(method).strip().lower()
    if method_key in {"last_dof_positive", "roof_or_last_dof_positive"}:
        method_key = "roof_or_last_dof_positive"
    if method_key not in {"max_abs", "mass", "roof_or_last_dof_positive"}:
        raise ValueError("normalize must be one of: max_abs, mass, last_dof_positive.")

    mass = None if M is None else _as_square_matrix(M, "M")
    if method_key == "mass" and mass is None:
        raise ValueError("Mass normalization requires M.")
    if mass is not None and mass.shape[0] != values.shape[0]:
        raise ValueError("M size must match mode vector length.")

    for mode_idx in range(values.shape[1]):
        column = values[:, mode_idx]
        if method_key == "mass":
            modal_mass = float(column.T @ mass @ column)
            if modal_mass <= 0.0:
                raise ValueError("Cannot mass-normalize a mode with non-positive modal mass.")
            column /= modal_mass ** 0.5
            _make_largest_component_positive(column)
        elif method_key == "roof_or_last_dof_positive":
            _scale_by_max_abs(column)
            if abs(column[-1]) > 1.0e-14:
                if column[-1] < 0.0:
                    column *= -1.0
            else:
                _make_largest_component_positive(column)
        else:
            _scale_by_max_abs(column)
            _make_largest_component_positive(column)
        values[:, mode_idx] = column
    return values


def format_eigenvalue_table(result: dict[str, Any]) -> tuple[list[str], list[list[str]]]:
    """Return frequency/eigenvalue rows for GUI tables or CSV export."""
    headers = ["Mode", "Eigenvalue lambda", "omega rad/s", "frequency Hz", "period s"]
    rows = []
    for idx, eigenvalue in enumerate(np.asarray(result["eigenvalues"], dtype=float)):
        rows.append(
            [
                str(idx + 1),
                _format_number(eigenvalue),
                _format_number(result["omega_rad_per_s"][idx]),
                _format_number(result["frequency_Hz"][idx]),
                _format_number(result["period_s"][idx]),
            ]
        )
    return headers, rows


def format_eigenvector_table(result: dict[str, Any]) -> tuple[list[str], list[list[str]]]:
    """Return eigenvectors as one row per DOF."""
    modes = np.asarray(result["modes"], dtype=float)
    headers = ["DOF"] + [f"Mode {idx + 1}" for idx in range(modes.shape[1])]
    rows = []
    for dof_idx in range(modes.shape[0]):
        rows.append([str(dof_idx + 1)] + [_format_number(modes[dof_idx, idx]) for idx in range(modes.shape[1])])
    return headers, rows


def format_modal_property_table(result: dict[str, Any]) -> tuple[list[str], list[list[str]]]:
    """Return modal property rows for GUI tables or CSV export."""
    headers = [
        "Mode",
        "Modal mass",
        "Modal stiffness",
        "Modal damping",
        "Damping ratio",
        "Participation factor Gamma",
        "Effective modal mass",
        "Effective mass ratio",
        "Cumulative effective mass ratio",
    ]
    rows = []
    n_modes = len(result.get("modal_mass", []))
    modal_damping = result.get("modal_damping")
    damping_ratio = result.get("damping_ratio")
    for idx in range(n_modes):
        rows.append(
            [
                str(idx + 1),
                _format_number(result["modal_mass"][idx]),
                _format_number(result["modal_stiffness"][idx]),
                _format_optional(modal_damping, idx),
                _format_optional(damping_ratio, idx),
                _format_number(result["participation_factor"][idx]),
                _format_number(result["effective_modal_mass"][idx]),
                _format_number(result["effective_modal_mass_ratio"][idx]),
                _format_number(result["cumulative_effective_mass_ratio"][idx]),
            ]
        )
    return headers, rows


def write_eigen_results_csv(path: str | Path, result: dict[str, Any]) -> None:
    """Write all calculator result tables to a UTF-8 CSV file."""
    sections = [
        ("Frequencies", format_eigenvalue_table(result)),
        ("Modal Properties", format_modal_property_table(result)),
        ("Eigenvectors", format_eigenvector_table(result)),
    ]
    if result.get("rayleigh_table") is not None:
        sections.append(("Rayleigh Damping", result["rayleigh_table"]))
    with Path(path).open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        for section_name, (headers, rows) in sections:
            writer.writerow([section_name])
            writer.writerow(headers)
            writer.writerows(rows)
            writer.writerow([])


def _as_square_matrix(values: Any, name: str) -> np.ndarray:
    matrix = np.asarray(values, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError(f"{name} must be a square matrix.")
    return matrix


def _validate_same_shape(a: np.ndarray, b: np.ndarray, a_name: str, b_name: str) -> None:
    if a.shape != b.shape:
        raise ValueError(f"{a_name} and {b_name} must have the same shape.")


def _validate_mass_matrix(mass: np.ndarray) -> None:
    if not np.all(np.isfinite(mass)):
        raise ValueError("M must contain finite numeric values.")
    if np.linalg.matrix_rank(mass) < mass.shape[0]:
        raise ValueError("M must be nonsingular.")


def _influence_vector(values: Any | None, n: int) -> np.ndarray:
    if values is None:
        return np.ones(n, dtype=float)
    vector = np.asarray(values, dtype=float).reshape(-1)
    if vector.shape[0] != n:
        raise ValueError("Influence vector length must match matrix size.")
    return vector


def _scale_by_max_abs(column: np.ndarray) -> None:
    scale = float(np.max(np.abs(column))) if column.size else 0.0
    if scale > 0.0:
        column /= scale


def _make_largest_component_positive(column: np.ndarray) -> None:
    if column.size == 0:
        return
    idx = int(np.argmax(np.abs(column)))
    if column[idx] < 0.0:
        column *= -1.0


def _format_optional(values: Any | None, idx: int) -> str:
    if values is None:
        return "n/a"
    return _format_number(values[idx])


def _format_number(value: Any) -> str:
    if value is None or value == "":
        return ""
    return f"{float(value):.6e}"


def _require_scipy_linalg():
    try:
        import scipy.linalg
    except ImportError as exc:
        raise EigenCalculatorDependencyError(
            "SciPy is required for the standalone eigenanalysis calculator."
        ) from exc
    return scipy.linalg
