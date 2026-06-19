from __future__ import annotations

import inspect
import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.axes import Axes
from matplotlib.figure import Figure

matplotlib.use("Agg")

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "src" / "io", ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from analysis.modal_solver import solve_modal_analysis  # noqa: E402
from gui.static_app import StaticAnalysisApp, _load_companion_masses, load_model_data  # noqa: E402
from model.structure import Structure  # noqa: E402
from postprocessing.modal_response_parameters import modal_response_parameters_from_result  # noqa: E402
from postprocessing.modal_results import package_modal_results  # noqa: E402
from visualization.modal_force_state_plots import plot_modal_force_state  # noqa: E402


def _model():
    return {
        "nodes": [
            {"id": 1, "x": 0.0, "y": 0.0},
            {"id": 2, "x": 0.0, "y": 3.0},
            {"id": 3, "x": 0.0, "y": 6.0},
            {"id": 4, "x": 0.0, "y": 9.0},
        ],
        "elements": [
            {"node_i": 1, "node_j": 2},
            {"node_i": 2, "node_j": 3},
            {"node_i": 3, "node_j": 4},
        ],
    }


def _parameters(sn=None):
    sn = np.asarray(sn if sn is not None else [21.457, 34.530, 35.525], dtype=float)
    heights = np.array([3.0, 6.0, 9.0])
    return {
        "floor_heights": heights,
        "rows": [
            {
                "mode": 1,
                "sn": sn,
                "Vb_coeff": float(np.sum(sn)),
                "Mb_coeff": float(np.sum(sn * heights)),
            }
        ],
    }


def test_modal_force_state_coefficient_mode_matches_response_factors():
    parameters = _parameters()

    fig, ax = plot_modal_force_state(_model(), parameters, mode_number=1, A_value=1.0)
    data = ax._modal_force_state_data

    assert isinstance(fig, Figure)
    assert isinstance(ax, Axes)
    assert data["floor_forces"] == pytest.approx([21.457, 34.530, 35.525])
    assert data["base_shear"] == pytest.approx(91.512)
    assert data["base_moment"] == pytest.approx(21.457 * 3 + 34.530 * 6 + 35.525 * 9)
    assert "A_n = 1" in ax.get_title()
    plt.close(fig)


def test_modal_force_state_scales_with_A_value():
    fig, ax = plot_modal_force_state(_model(), _parameters(), mode_number=1, A_value=2.0)
    data = ax._modal_force_state_data

    assert data["floor_forces"] == pytest.approx(2.0 * np.array([21.457, 34.530, 35.525]))
    assert data["base_shear"] == pytest.approx(2.0 * 91.512)
    assert data["base_moment"] == pytest.approx(2.0 * (21.457 * 3 + 34.530 * 6 + 35.525 * 9))
    plt.close(fig)


def test_modal_force_state_handles_negative_floor_forces():
    fig, ax = plot_modal_force_state(_model(), _parameters([-2.0, 3.0, -4.0]), mode_number=1)

    assert ax._modal_force_state_data["floor_forces"] == pytest.approx([-2.0, 3.0, -4.0])
    assert len(ax._modal_force_state_data["floor_arrows"]) == 3
    plt.close(fig)


def test_ce586_base_coefficients_match_sn_sums():
    path = ROOT / "inputs" / "examples" / "CE586_Examples_6_4_6_6_frame_model.json"
    structure = Structure.from_dict(load_model_data(path))
    modal = package_modal_results(
        solve_modal_analysis(structure, _load_companion_masses(path), n_modes=3),
        structure,
    )
    parameters = modal_response_parameters_from_result(modal, normalization="display")

    for row in parameters["rows"]:
        assert row["Vb_coeff"] == pytest.approx(np.sum(row["sn"]))
        assert row["Mb_coeff"] == pytest.approx(np.sum(row["sn"] * parameters["floor_heights"]))


def test_gui_exposes_modal_force_state_under_modal_display():
    source = inspect.getsource(StaticAnalysisApp._build_menu)

    assert '("Modal Force State", "Modal Force State")' in source
    assert '("Modal Story Forces", "RHA Modal Story Forces")' not in source
