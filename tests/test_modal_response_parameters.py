from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "src" / "io", ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from analysis.modal_solver import solve_modal_analysis  # noqa: E402
from gui.static_app import _load_companion_masses, load_model_data  # noqa: E402
from model.structure import Structure  # noqa: E402
from postprocessing.modal_response_parameters import (  # noqa: E402
    compute_modal_generalized_parameters,
    modal_response_parameters_from_result,
)
from postprocessing.modal_results import package_modal_results  # noqa: E402


def _ce586_parameters(normalization="display"):
    path = ROOT / "inputs" / "examples" / "CE586_Examples_6_4_6_6_frame_model.json"
    structure = Structure.from_dict(load_model_data(path))
    modal = solve_modal_analysis(structure, _load_companion_masses(path), n_modes=3)
    return modal_response_parameters_from_result(package_modal_results(modal, structure), normalization)


def test_ce586_display_normalized_parameters_match_lecture_values():
    rows = _ce586_parameters()["rows"]

    assert [row["Mn"] for row in rows] == pytest.approx([45.307, 61.823, 564.265], rel=0.015)
    assert [row["Lnh"] for row in rows] == pytest.approx([64.4, -31.675, 51.525], rel=0.02)
    # The lecture target 0.913 for mode 3 is a decimal-place typo:
    # 51.525 / 564.265 = 0.0913, and Gamma must equal Lnh / Mn.
    assert [row["Gamma"] for row in rows] == pytest.approx([1.421, -0.512, 0.0913], rel=0.02)
    assert [row["Ln_theta"] for row in rows] == pytest.approx([416.1, -13.2, 18.6], rel=0.04)
    assert [row["h_star"] for row in rows] == pytest.approx([6.461, 0.417, 0.361], rel=0.04)


def test_mass_normalized_and_display_normalized_modal_masses_differ():
    mass_rows = _ce586_parameters("mass")["rows"]
    display_rows = _ce586_parameters("display")["rows"]

    assert [row["Mn"] for row in mass_rows] == pytest.approx([1.0, 1.0, 1.0])
    assert display_rows[0]["Mn"] != pytest.approx(1.0)


def test_generalized_parameter_identities_and_sign_change():
    modes = np.array([[0.3, -0.7], [0.65, -0.6], [1.0, 1.0]])
    masses = np.array([50.0, 37.5, 25.0])
    heights = np.array([3.0, 6.0, 9.0])
    omega = np.array([4.1, 8.8])
    result = compute_modal_generalized_parameters(modes, masses, omega, heights)

    for row in result["rows"]:
        assert row["Gamma"] == pytest.approx(row["Lnh"] / row["Mn"])
        assert row["h_star"] == pytest.approx(row["Ln_theta"] / row["Lnh"])
        assert row["M_eff"] == pytest.approx(row["Lnh"] ** 2 / row["Mn"])
        assert row["sn"] == pytest.approx(row["Gamma"] * masses * row["phi"])
        assert row["base_shear_coefficient"] == pytest.approx(np.sum(row["sn"]))
        assert row["base_moment_coefficient"] == pytest.approx(np.sum(row["sn"] * heights))
        assert row["u_coeff"] == pytest.approx(row["Gamma"] * row["phi"] / row["omega"] ** 2)

    flipped = compute_modal_generalized_parameters(-modes[:, :1], masses, omega[:1], heights)["rows"][0]
    original = result["rows"][0]
    assert flipped["Mn"] == pytest.approx(original["Mn"])
    assert flipped["M_eff"] == pytest.approx(original["M_eff"])
    assert flipped["h_star"] == pytest.approx(original["h_star"])
    assert flipped["Lnh"] == pytest.approx(-original["Lnh"])
    assert flipped["Gamma"] == pytest.approx(-original["Gamma"])
