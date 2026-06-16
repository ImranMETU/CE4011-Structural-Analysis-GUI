"""Matrix and solver-efficiency diagnostics for structural models."""

from __future__ import annotations

from typing import Any

import numpy as np


def compute_matrix_sparsity(K: Any, zero_tol: float = 0.0) -> dict[str, Any]:
    """Return size, nonzero count, and density for a stiffness matrix."""
    entries, size = _matrix_entries(K, zero_tol=zero_tol)
    full_nonzero_count = 0
    for i, j, _value in entries:
        full_nonzero_count += 1 if i == j else 2
    density = full_nonzero_count / (size * size) if size > 0 else 0.0
    return {
        "matrix_size": int(size),
        "nonzero_count": int(full_nonzero_count),
        "density": float(density),
    }


def compute_bandwidth(K: Any, zero_tol: float = 0.0) -> dict[str, int]:
    """Return semi- and full-bandwidth using zero-based matrix indices."""
    entries, size = _matrix_entries(K, zero_tol=zero_tol)
    if size == 0 or not entries:
        semi = 0
    else:
        semi = max(abs(i - j) for i, j, _value in entries) + 1
    return {
        "semi_bandwidth": int(semi),
        "full_bandwidth": int(2 * semi - 1 if semi > 0 else 0),
    }


def compute_dof_summary(structure_or_model_data: Any) -> dict[str, int]:
    """Return node, element, and DOF counts from a Structure or model dict."""
    if isinstance(structure_or_model_data, dict):
        nodes = structure_or_model_data.get("nodes", [])
        elements = structure_or_model_data.get("elements", [])
        restrained = 0
        for node in nodes:
            restraints = node.get("restraints", {})
            restrained += sum(1 for dof in ("ux", "uy", "rz") if bool(restraints.get(dof, False)))
        total = 3 * len(nodes)
        return {
            "node_count": len(nodes),
            "element_count": len(elements),
            "frame_element_count": sum(1 for element in elements if str(element.get("type", "")).lower() == "frame"),
            "truss_element_count": sum(1 for element in elements if str(element.get("type", "")).lower() == "truss"),
            "total_dofs": total,
            "free_dofs": total - restrained,
            "restrained_dofs": restrained,
        }

    nodes = getattr(structure_or_model_data, "nodes", {})
    elements = getattr(structure_or_model_data, "elements", [])
    total = 3 * len(nodes)
    free = int(getattr(structure_or_model_data, "n_active_dofs", 0))
    return {
        "node_count": len(nodes),
        "element_count": len(elements),
        "frame_element_count": sum(1 for element in elements if "Frame" in element.__class__.__name__),
        "truss_element_count": sum(1 for element in elements if "Truss" in element.__class__.__name__),
        "total_dofs": total,
        "free_dofs": free,
        "restrained_dofs": total - free,
    }


def compute_solver_diagnostics(structure: Any, K: Any | None = None) -> dict[str, Any]:
    """Compute structural DOF and stiffness matrix diagnostics."""
    warnings: list[str] = []
    matrix = K if K is not None else getattr(structure, "K", None)
    if matrix is None:
        if getattr(structure, "n_active_dofs", 0) <= 0 and hasattr(structure, "assign_dofs"):
            structure.assign_dofs()
        if hasattr(structure, "assemble_global_stiffness"):
            matrix = structure.assemble_global_stiffness()
        else:
            warnings.append("Global stiffness matrix unavailable; matrix diagnostics omitted.")

    diagnostics = compute_dof_summary(structure)
    if matrix is not None:
        diagnostics.update(compute_matrix_sparsity(matrix))
        diagnostics.update(compute_bandwidth(matrix))
        rcm = estimate_rcm_bandwidth(matrix)
        if rcm:
            diagnostics.update(rcm)
        else:
            warnings.append("RCM bandwidth estimate unavailable.")
    else:
        diagnostics.update(
            {
                "matrix_size": 0,
                "nonzero_count": 0,
                "density": 0.0,
                "semi_bandwidth": 0,
                "full_bandwidth": 0,
            }
        )
    diagnostics["warnings"] = warnings
    return diagnostics


def estimate_rcm_bandwidth(K: Any) -> dict[str, int]:
    """Estimate bandwidth after Reverse Cuthill-McKee ordering, if SciPy is available."""
    try:
        from scipy.sparse import coo_matrix
        from scipy.sparse.csgraph import reverse_cuthill_mckee
    except ImportError:
        return {}

    entries, size = _matrix_entries(K)
    if size == 0:
        return {"rcm_semi_bandwidth": 0, "rcm_full_bandwidth": 0}
    rows = []
    cols = []
    data = []
    for i, j, _value in entries:
        rows.append(i)
        cols.append(j)
        data.append(1)
        if i != j:
            rows.append(j)
            cols.append(i)
            data.append(1)
    sparse = coo_matrix((data, (rows, cols)), shape=(size, size)).tocsr()
    permutation = reverse_cuthill_mckee(sparse, symmetric_mode=True)
    dense_pattern = sparse[permutation, :][:, permutation]
    semi = _semi_bandwidth_from_sparse_pattern(dense_pattern)
    return {"rcm_semi_bandwidth": int(semi), "rcm_full_bandwidth": int(2 * semi - 1 if semi > 0 else 0)}


def format_solver_diagnostics_rows(diagnostics: dict[str, Any]) -> tuple[list[str], list[list[str]]]:
    """Return GUI/table rows for solver diagnostics."""
    labels = [
        ("Nodes", "node_count"),
        ("Elements", "element_count"),
        ("Frame elements", "frame_element_count"),
        ("Truss elements", "truss_element_count"),
        ("Total DOFs", "total_dofs"),
        ("Free DOFs", "free_dofs"),
        ("Restrained DOFs", "restrained_dofs"),
        ("K matrix size", "matrix_size"),
        ("Nonzero stiffness entries", "nonzero_count"),
        ("Matrix density", "density"),
        ("Semi-bandwidth", "semi_bandwidth"),
        ("Full bandwidth", "full_bandwidth"),
        ("RCM semi-bandwidth", "rcm_semi_bandwidth"),
        ("RCM full bandwidth", "rcm_full_bandwidth"),
    ]
    rows = []
    for label, key in labels:
        if key in diagnostics:
            rows.append([label, _format_value(diagnostics[key])])
    warnings = diagnostics.get("warnings", [])
    if warnings:
        rows.append(["Warnings", "; ".join(str(item) for item in warnings)])
    return ["Quantity", "Value"], rows


def _matrix_entries(K: Any, zero_tol: float = 0.0) -> tuple[list[tuple[int, int, float]], int]:
    size = int(getattr(K, "size", 0) or 0)
    data = getattr(K, "data", None)
    if isinstance(data, dict):
        entries = [
            (int(i), int(j), float(value))
            for (i, j), value in data.items()
            if abs(float(value)) > zero_tol
        ]
        return entries, size

    matrix = np.asarray(K, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("K must be a square matrix.")
    entries = []
    for i in range(matrix.shape[0]):
        for j in range(i, matrix.shape[1]):
            value = float(matrix[i, j])
            if abs(value) > zero_tol:
                entries.append((i, j, value))
    return entries, int(matrix.shape[0])


def _semi_bandwidth_from_sparse_pattern(matrix: Any) -> int:
    coo = matrix.tocoo()
    if coo.nnz == 0:
        return 0
    return int(np.max(np.abs(coo.row - coo.col)) + 1)


def _format_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.6e}"
    return str(value)
