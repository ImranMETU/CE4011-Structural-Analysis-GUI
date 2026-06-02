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

pytest.importorskip("scipy.linalg", reason="SciPy is required for modal eigensolve tests.")

from analysis.mass_assembly import assemble_lumped_mass_matrix
from analysis.modal_solver import solve_modal_analysis, solve_modal_from_matrices
from model.structure import Structure


def test_sdof_frequency_and_period():
    k = np.array([[8000.0]])
    m = np.array([[20.0]])

    result = solve_modal_from_matrices(k, m)

    expected_omega = math.sqrt(8000.0 / 20.0)
    expected_period = 2.0 * math.pi / expected_omega

    assert result["omega"][0] == pytest.approx(expected_omega)
    assert result["periods"][0] == pytest.approx(expected_period)
    assert result["frequencies_hz"][0] == pytest.approx(expected_omega / (2.0 * math.pi))


def test_two_dof_shear_building_positive_frequencies_and_mass_orthogonality():
    k1 = 12000.0
    k2 = 8000.0
    m1 = 30.0
    m2 = 20.0
    k = np.array([[k1 + k2, -k2], [-k2, k2]], dtype=float)
    m = np.diag([m1, m2])

    result = solve_modal_from_matrices(k, m)

    assert len(result["omega"]) == 2
    assert np.all(result["omega"] > 0.0)

    phi = result["condensed_mode_shapes"]
    modal_mass = phi.T @ m @ phi
    assert modal_mass[0, 1] == pytest.approx(0.0, abs=1e-10)
    assert modal_mass[1, 0] == pytest.approx(0.0, abs=1e-10)


def test_massless_dof_condensation_and_full_mode_recovery():
    k = np.array([[1000.0, -100.0], [-100.0, 200.0]], dtype=float)
    m = np.diag([10.0, 0.0])

    result = solve_modal_from_matrices(k, m)

    expected_kc = 1000.0 - ((-100.0) * (-100.0) / 200.0)
    expected_omega = math.sqrt(expected_kc / 10.0)
    full_mode = result["full_free_mode_shapes"][:, 0]

    assert result["massive_dof_indices"] == [0]
    assert result["massless_dof_indices"] == [1]
    assert result["condensed_stiffness"][0, 0] == pytest.approx(expected_kc)
    assert result["omega"][0] == pytest.approx(expected_omega)
    assert full_mode.shape == (2,)
    assert full_mode[1] == pytest.approx(0.5 * full_mode[0])


def test_existing_structure_stiffness_modal_smoke():
    data = {
        "nodes": [
            {"id": 1, "x": 0.0, "y": 0.0, "restraints": {"ux": True, "uy": True, "rz": True}},
            {"id": 2, "x": 3.0, "y": 0.0, "restraints": {"ux": False, "uy": False, "rz": False}},
        ],
        "materials": [{"id": "steel", "E": 200.0e9}],
        "sections": [{"id": "rect", "A": 0.01, "I": 1.0e-4, "d": 0.3}],
        "elements": [
            {"id": 1, "type": "frame", "node_i": 1, "node_j": 2, "material": "steel", "section": "rect"}
        ],
    }
    structure = Structure.from_dict(data)
    masses = {2: {"ux": 100.0, "uy": 100.0}}

    result = solve_modal_analysis(structure, masses, n_modes=1)
    mass_matrix = assemble_lumped_mass_matrix(structure, masses)

    assert mass_matrix.shape == (3, 3)
    assert result["omega"][0] > 0.0
    assert result["frequencies_hz"][0] > 0.0
    assert result["full_free_mode_shapes"].shape == (3, 1)
    assert len(result["free_dof_map"]) == 3
