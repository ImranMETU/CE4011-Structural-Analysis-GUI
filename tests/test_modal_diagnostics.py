from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"

for path in (SRC_ROOT, ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from postprocessing.modal_diagnostics import (  # noqa: E402
    condensed_matrix_summary,
    full_mode_shape_rows,
    modal_dof_classification_rows,
    modal_mass_summary,
    modal_properties_rows,
)
from postprocessing.modal_results import package_modal_results  # noqa: E402


def _modal_result():
    omega = np.array([2.0, 4.0])
    raw = {
        "eigenvalues": omega**2,
        "omega": omega,
        "frequencies_hz": omega / (2.0 * math.pi),
        "periods": 2.0 * math.pi / omega,
        "full_free_mode_shapes": np.array([[2.0, 0.0], [0.0, 3.0], [0.1, 0.2]]),
        "active_mass_matrix": np.diag([10.0, 20.0, 0.0]),
        "condensed_stiffness": np.diag([40.0, 80.0]),
        "condensed_mass_matrix": np.diag([10.0, 20.0]),
        "massive_dof_indices": [0, 1],
        "massless_dof_indices": [2],
        "matrix_diagnostics": {
            "free_stiffness_size": 3,
            "free_mass_size": 3,
            "massive_dof_count": 2,
            "massless_dof_count": 1,
            "condensed_stiffness_size": 2,
            "condensed_mass_size": 2,
            "condensed_stiffness_symmetry_error": 0.0,
            "condensed_mass_symmetry_error": 0.0,
            "kbb_condition_number": 3.0,
        },
        "free_dof_map": [
            {"index": 0, "node": 1, "dof": "ux"},
            {"index": 1, "node": 2, "dof": "ux"},
            {"index": 2, "node": 2, "dof": "rz"},
        ],
        "nodes": {1: {"x": 0.0, "y": 0.0}, 2: {"x": 0.0, "y": 3.0}},
        "notes": ["diagnostic note"],
    }
    packaged = package_modal_results(raw)
    packaged["mass_source_summary"] = {
        "source_type": "floor lumped",
        "node_count": 2,
        "total_ux_mass": 30.0,
        "total_uy_mass": 0.0,
        "total_rz_mass": 0.0,
    }
    return packaged


def test_modal_properties_include_cumulative_effective_mass_ratio():
    rows = modal_properties_rows(_modal_result())

    assert rows[0]["mode"] == 1
    assert rows[1]["cumulative_effective_mass_ratio"] == pytest.approx(1.0)
    assert rows[1]["controlling_node"] == 2


def test_dof_classification_rows_identify_massless_condensed_dofs():
    rows = modal_dof_classification_rows(_modal_result())

    assert rows[0]["classification"] == "massive"
    assert rows[2]["classification"] == "massless condensed"
    assert "zero" in rows[2]["note"]


def test_condensed_matrix_summary_and_mode_shape_rows():
    summary = condensed_matrix_summary(_modal_result())
    mode_rows = full_mode_shape_rows(_modal_result())

    assert summary["massless_dof_count"] == 1
    assert summary["kbb_condition_number"] == pytest.approx(3.0)
    assert mode_rows[0] == {"mode": 1, "node": 1, "ux": 2.0, "uy": 0.0, "rz": 0.0}


def test_modal_mass_summary_reports_source_and_active_mass():
    summary = modal_mass_summary(_modal_result())

    assert summary["source_type"] == "floor lumped"
    assert summary["active_mass_dof_count"] == 2
    assert summary["active_mass_total"] == pytest.approx(30.0)
