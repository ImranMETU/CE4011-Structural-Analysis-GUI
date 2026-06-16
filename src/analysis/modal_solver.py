"""Core modal-analysis backend with massless DOF condensation."""

from __future__ import annotations

from typing import Any

import numpy as np

from .mass_assembly import DOF_KEYS, assemble_lumped_mass_matrix


class ModalDependencyError(ImportError):
    """Raised when modal eigensolve dependencies are unavailable."""


def solve_modal_analysis(
    structure: Any,
    nodal_masses: dict[int, dict[str, float]],
    n_modes: int | None = None,
    mass_tol: float = 1e-12,
    eigenvalue_tol: float = 1e-10,
) -> dict[str, Any]:
    """Solve modal properties for an existing Structure using external masses."""
    if structure.n_active_dofs <= 0:
        raise ValueError("Modal analysis requires at least one active/free DOF.")

    if structure.K is None:
        structure.assemble_global_stiffness()

    stiffness = matrix_to_dense(structure.K)
    mass = assemble_lumped_mass_matrix(structure, nodal_masses)
    result = solve_modal_from_matrices(
        stiffness,
        mass,
        n_modes=n_modes,
        mass_tol=mass_tol,
        eigenvalue_tol=eigenvalue_tol,
    )
    result["free_dof_map"] = active_dof_map(structure)
    return result


def solve_modal_from_matrices(
    stiffness: Any,
    mass: Any,
    n_modes: int | None = None,
    mass_tol: float = 1e-12,
    eigenvalue_tol: float = 1e-10,
) -> dict[str, Any]:
    """Solve ``K phi = omega^2 M phi`` with massless free-DOF condensation."""
    scipy_linalg = _require_scipy_linalg()

    k = np.asarray(stiffness, dtype=float)
    m = np.asarray(mass, dtype=float)
    _validate_square_pair(k, m)

    notes: list[str] = []
    diag_m = np.diag(m)
    massive = np.array([i for i, value in enumerate(diag_m) if value > mass_tol], dtype=int)
    massless = np.array([i for i, value in enumerate(diag_m) if value <= mass_tol], dtype=int)

    if massive.size == 0:
        raise ValueError("Modal analysis requires at least one massive active DOF.")

    kbb_condition_number = None
    if massless.size > 0:
        k_bb_for_diagnostics = k[np.ix_(massless, massless)]
        try:
            kbb_condition_number = float(np.linalg.cond(k_bb_for_diagnostics))
        except np.linalg.LinAlgError:
            kbb_condition_number = float("inf")
        if not np.isfinite(kbb_condition_number) or kbb_condition_number > 1.0e12:
            notes.append("Massless DOF stiffness block K_bb is ill-conditioned; modal condensation may be sensitive.")

    k_condensed, m_condensed = _condense_massless_dofs(k, m, massive, massless, notes)

    eigenvalues, condensed_modes = scipy_linalg.eigh(k_condensed, m_condensed)
    eigenvalues = np.real_if_close(eigenvalues)

    order = np.argsort(eigenvalues)
    eigenvalues = eigenvalues[order]
    condensed_modes = condensed_modes[:, order]

    positive = eigenvalues > eigenvalue_tol
    if not np.all(positive):
        notes.append("Non-positive or near-zero eigenvalues were omitted from modal results.")
    eigenvalues = eigenvalues[positive]
    condensed_modes = condensed_modes[:, positive]

    if n_modes is not None:
        if n_modes <= 0:
            raise ValueError("n_modes must be positive when provided.")
        eigenvalues = eigenvalues[:n_modes]
        condensed_modes = condensed_modes[:, :n_modes]

    full_modes = recover_full_free_modes(k, massive, massless, condensed_modes)
    omega = np.sqrt(eigenvalues)
    frequencies_hz = omega / (2.0 * np.pi)
    periods = np.array([2.0 * np.pi / w if w > 0.0 else np.inf for w in omega])

    return {
        "eigenvalues": eigenvalues,
        "omega": omega,
        "frequencies_hz": frequencies_hz,
        "periods": periods,
        "condensed_mode_shapes": condensed_modes,
        "full_free_mode_shapes": full_modes,
        "massive_dof_indices": massive.tolist(),
        "massless_dof_indices": massless.tolist(),
        "free_stiffness_matrix": k,
        "condensed_stiffness": k_condensed,
        "condensed_mass_matrix": m_condensed,
        "active_mass_matrix": m,
        "matrix_diagnostics": {
            "free_stiffness_size": int(k.shape[0]),
            "free_mass_size": int(m.shape[0]),
            "massive_dof_count": int(massive.size),
            "massless_dof_count": int(massless.size),
            "condensed_stiffness_size": int(k_condensed.shape[0]),
            "condensed_mass_size": int(m_condensed.shape[0]),
            "condensed_stiffness_symmetry_error": _symmetry_error(k_condensed),
            "condensed_mass_symmetry_error": _symmetry_error(m_condensed),
            "kbb_condition_number": kbb_condition_number,
        },
        "notes": notes,
    }


def recover_full_free_modes(
    stiffness: Any,
    massive_dof_indices: np.ndarray,
    massless_dof_indices: np.ndarray,
    condensed_modes: np.ndarray,
) -> np.ndarray:
    """Recover massless DOF amplitudes and return modes in original free order."""
    k = np.asarray(stiffness, dtype=float)
    massive = np.asarray(massive_dof_indices, dtype=int)
    massless = np.asarray(massless_dof_indices, dtype=int)

    full_modes = np.zeros((k.shape[0], condensed_modes.shape[1]), dtype=float)
    full_modes[massive, :] = condensed_modes

    if massless.size > 0 and condensed_modes.size > 0:
        k_bb = k[np.ix_(massless, massless)]
        k_ba = k[np.ix_(massless, massive)]
        full_modes[massless, :] = -np.linalg.solve(k_bb, k_ba @ condensed_modes)

    return full_modes


def matrix_to_dense(matrix: Any) -> np.ndarray:
    """Convert the project matrix containers or array-like objects to ndarray."""
    if isinstance(matrix, np.ndarray):
        return np.asarray(matrix, dtype=float)

    size = getattr(matrix, "size", None)
    if size is not None and hasattr(matrix, "get"):
        dense = np.zeros((int(size), int(size)), dtype=float)
        for i in range(int(size)):
            for j in range(int(size)):
                dense[i, j] = matrix.get(i, j)
        return dense

    return np.asarray(matrix, dtype=float)


def active_dof_map(structure: Any) -> list[dict[str, Any]]:
    """Return active free DOFs in equation-number order."""
    items: list[dict[str, Any]] = []
    for node_id in sorted(structure.nodes):
        node = structure.nodes[node_id]
        for dof_idx, dof_key in enumerate(DOF_KEYS):
            eq = node.get_global_dof_numbers()[dof_idx]
            if eq != 0:
                items.append({"index": eq - 1, "node": node_id, "dof": dof_key})
    return sorted(items, key=lambda item: item["index"])


def _condense_massless_dofs(
    k: np.ndarray,
    m: np.ndarray,
    massive: np.ndarray,
    massless: np.ndarray,
    notes: list[str],
) -> tuple[np.ndarray, np.ndarray]:
    k_aa = k[np.ix_(massive, massive)]
    m_aa = m[np.ix_(massive, massive)]

    if massless.size == 0:
        return k_aa, m_aa

    k_ab = k[np.ix_(massive, massless)]
    k_ba = k[np.ix_(massless, massive)]
    k_bb = k[np.ix_(massless, massless)]

    try:
        condensed_term = k_ab @ np.linalg.solve(k_bb, k_ba)
    except np.linalg.LinAlgError as exc:
        raise ValueError("Massless DOF stiffness block K_bb is singular and cannot be condensed.") from exc

    notes.append(f"Condensed {massless.size} massless active DOF(s).")
    return k_aa - condensed_term, m_aa


def _validate_square_pair(k: np.ndarray, m: np.ndarray) -> None:
    if k.ndim != 2 or k.shape[0] != k.shape[1]:
        raise ValueError("Stiffness matrix must be square.")
    if m.ndim != 2 or m.shape[0] != m.shape[1]:
        raise ValueError("Mass matrix must be square.")
    if k.shape != m.shape:
        raise ValueError(f"Stiffness and mass shapes must match, got {k.shape} and {m.shape}.")


def _symmetry_error(matrix: np.ndarray) -> float:
    if matrix.size == 0:
        return 0.0
    return float(np.max(np.abs(matrix - matrix.T)))


def _require_scipy_linalg():
    try:
        import scipy.linalg
    except ImportError as exc:
        raise ModalDependencyError(
            "SciPy is required for modal analysis generalized symmetric eigensolve. "
            "Install scipy in the CE4011 environment to enable modal solving."
        ) from exc
    return scipy.linalg
