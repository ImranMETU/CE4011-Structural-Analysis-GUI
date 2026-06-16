from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"

for path in (ROOT, SRC_ROOT):
    path_str = str(path)
    if path_str in sys.path:
        sys.path.remove(path_str)
sys.path.insert(0, str(SRC_ROOT))
sys.path.insert(1, str(ROOT))

for module_name in ("model.structure", "model.frame_element"):
    sys.modules.pop(module_name, None)

from analysis.axis_transformation import (  # noqa: E402
    build_2d_axis_offset_matrix,
    transform_frame_local_stiffness_for_offsets,
)
from analysis.modal_solver import solve_modal_analysis  # noqa: E402
from model.frame_element import compute_local_stiffness  # noqa: E402
from model.structure import Structure  # noqa: E402
from postprocessing.static_results import run_static_analysis  # noqa: E402


def _offset_frame_model() -> dict:
    return {
        "nodes": [
            {"id": 1, "x": 0.0, "y": 0.0, "restraints": {"ux": True, "uy": True, "rz": True}},
            {"id": 2, "x": 3.0, "y": 0.0, "restraints": {"ux": False, "uy": False, "rz": False}},
        ],
        "materials": [{"id": "steel", "E": 200_000_000.0}],
        "sections": [{"id": "beam", "A": 0.02, "I": 1.0e-4}],
        "elements": [
            {
                "id": 1,
                "type": "frame",
                "node_i": 1,
                "node_j": 2,
                "material": "steel",
                "section": "beam",
                "axis_offset": {"i_local_y": 0.15, "j_local_y": 0.05},
            }
        ],
        "nodal_loads": [{"node": 2, "fx": 1000.0, "fy": -500.0, "mz": 0.0}],
    }


def test_axis_offset_matrix_has_expected_reference_to_neutral_mapping():
    transform = build_2d_axis_offset_matrix(0.2, -0.1)

    assert transform.shape == (6, 6)
    assert transform[0, 2] == pytest.approx(-0.2)
    assert transform[3, 5] == pytest.approx(0.1)
    assert np.allclose(np.diag(transform), np.ones(6))


def test_zero_axis_offsets_leave_local_stiffness_unchanged():
    base = compute_local_stiffness(A=0.02, I=1.0e-4, E=200_000_000.0, L=3.0)
    transformed = transform_frame_local_stiffness_for_offsets(base, 0.0, 0.0)

    assert np.allclose(transformed, base)


def test_nonzero_axis_offsets_keep_stiffness_symmetric_and_change_coupling_terms():
    base = compute_local_stiffness(A=0.02, I=1.0e-4, E=200_000_000.0, L=3.0)
    transformed = np.asarray(transform_frame_local_stiffness_for_offsets(base, 0.2, 0.1))

    assert np.allclose(transformed, transformed.T)
    assert transformed[0, 2] != pytest.approx(base[0][2])
    assert transformed[3, 5] != pytest.approx(base[3][5])


def test_frame_model_with_axis_offset_runs_static_analysis():
    result = run_static_analysis(_offset_frame_model())

    assert result["displacements"]
    assert result["reactions"]
    assert result["member_end_forces"]


def test_frame_model_with_axis_offset_runs_modal_smoke():
    scipy = pytest.importorskip("scipy.linalg", reason="SciPy is required for modal eigensolve tests.")
    assert scipy is not None

    structure = Structure.from_dict(_offset_frame_model())
    result = solve_modal_analysis(structure, {2: {"ux": 1000.0, "uy": 1000.0, "rz": 0.0}}, n_modes=1)

    assert len(result["omega"]) >= 1
    assert math.isfinite(float(result["omega"][0]))
    assert float(result["omega"][0]) > 0.0

