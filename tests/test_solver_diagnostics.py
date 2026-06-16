from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
IO_ROOT = SRC_ROOT / "io"
for path in (SRC_ROOT, IO_ROOT, ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


from model.structure import Structure  # noqa: E402
from postprocessing.solver_diagnostics import (  # noqa: E402
    compute_bandwidth,
    compute_dof_summary,
    compute_matrix_sparsity,
    compute_solver_diagnostics,
    estimate_rcm_bandwidth,
    format_solver_diagnostics_rows,
)


def _simple_model():
    return {
        "materials": [{"id": "steel", "E": 200000000.0}],
        "sections": [{"id": "sec", "A": 0.01, "I": 1.0e-4}],
        "nodes": [
            {"id": 1, "x": 0.0, "y": 0.0, "restraints": {"ux": True, "uy": True, "rz": True}},
            {"id": 2, "x": 3.0, "y": 0.0, "restraints": {"ux": False, "uy": False, "rz": False}},
        ],
        "elements": [{"id": 1, "type": "frame", "node_i": 1, "node_j": 2, "material": "steel", "section": "sec"}],
        "nodal_loads": [],
    }


def test_bandwidth_calculation_on_dense_and_sparse_matrices():
    dense = np.array([[1.0, 2.0, 0.0], [2.0, 3.0, 4.0], [0.0, 4.0, 5.0]])
    diagonal = np.diag([1.0, 2.0, 3.0])

    assert compute_bandwidth(dense) == {"semi_bandwidth": 2, "full_bandwidth": 3}
    assert compute_bandwidth(diagonal) == {"semi_bandwidth": 1, "full_bandwidth": 1}


def test_sparsity_and_density_calculation_expands_symmetric_entries():
    matrix = np.array([[1.0, 2.0, 0.0], [2.0, 3.0, 4.0], [0.0, 4.0, 5.0]])

    sparsity = compute_matrix_sparsity(matrix)

    assert sparsity["matrix_size"] == 3
    assert sparsity["nonzero_count"] == 7
    assert sparsity["density"] == pytest.approx(7.0 / 9.0)


def test_dof_summary_from_model_data():
    summary = compute_dof_summary(_simple_model())

    assert summary["node_count"] == 2
    assert summary["element_count"] == 1
    assert summary["frame_element_count"] == 1
    assert summary["truss_element_count"] == 0
    assert summary["total_dofs"] == 6
    assert summary["restrained_dofs"] == 3


def test_solver_diagnostics_dictionary_contains_expected_keys():
    structure = Structure.from_dict(_simple_model())

    diagnostics = compute_solver_diagnostics(structure)

    for key in (
        "node_count",
        "element_count",
        "total_dofs",
        "free_dofs",
        "matrix_size",
        "nonzero_count",
        "density",
        "semi_bandwidth",
        "full_bandwidth",
        "warnings",
    ):
        assert key in diagnostics
    assert diagnostics["matrix_size"] == structure.n_active_dofs
    assert diagnostics["free_dofs"] == structure.n_active_dofs


def test_rcm_estimate_gracefully_returns_dict_or_empty_result():
    result = estimate_rcm_bandwidth(np.eye(3))

    assert isinstance(result, dict)
    assert set(result).issubset({"rcm_semi_bandwidth", "rcm_full_bandwidth"})


def test_solver_diagnostics_table_formatting():
    diagnostics = {
        "node_count": 2,
        "element_count": 1,
        "frame_element_count": 1,
        "truss_element_count": 0,
        "total_dofs": 6,
        "free_dofs": 3,
        "restrained_dofs": 3,
        "matrix_size": 3,
        "nonzero_count": 9,
        "density": 1.0,
        "semi_bandwidth": 3,
        "full_bandwidth": 5,
        "warnings": ["demo warning"],
    }

    headers, rows = format_solver_diagnostics_rows(diagnostics)

    assert headers == ["Quantity", "Value"]
    assert ["Nodes", "2"] in rows
    assert ["Matrix density", "1.000000e+00"] in rows
    assert rows[-1][0] == "Warnings"
