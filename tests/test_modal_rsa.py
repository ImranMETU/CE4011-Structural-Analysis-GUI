from __future__ import annotations

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

from analysis.modal_rsa import interpolate_spectrum_at_period, run_modal_rsa  # noqa: E402


def _modal_result() -> dict:
    return {
        "eigenvalues": np.array([4.0, 9.0]),
        "omega": np.array([2.0, 3.0]),
        "frequencies_hz": np.array([2.0 / (2.0 * np.pi), 3.0 / (2.0 * np.pi)]),
        "periods": np.array([1.0, 2.0]),
        "participation": [{"mode": 1, "gamma": 1.5}, {"mode": 2, "gamma": 0.5}],
        "node_mode_shapes": [
            {1: {"ux": 0.0, "uy": 0.0, "rz": 0.0}, 2: {"ux": 2.0, "uy": 0.0, "rz": 0.0}},
            {1: {"ux": 0.0, "uy": 0.0, "rz": 0.0}, 2: {"ux": -1.0, "uy": 0.0, "rz": 0.0}},
        ],
        "nodes": {1: {"x": 0.0, "y": 0.0}, 2: {"x": 0.0, "y": 3.0}},
    }


def _spectrum() -> dict:
    return {
        "periods": np.array([0.5, 1.0, 2.0, 3.0]),
        "Sa": np.array([4.0, 3.0, 2.0, 1.0]),
        "Sd": np.array([0.1, 0.2, 0.4, 0.8]),
        "damping_ratio": 0.05,
    }


def test_interpolation_of_sa_sd_at_modal_period():
    sa, warnings = interpolate_spectrum_at_period(_spectrum(), 1.5, "Sa")
    sd, _warnings = interpolate_spectrum_at_period(_spectrum(), 1.5, "Sd")

    assert sa == pytest.approx(2.5)
    assert sd == pytest.approx(0.3)
    assert warnings == []


def test_modal_rsa_qmax_and_modal_displacement_contribution_shape():
    result = run_modal_rsa(_modal_result(), _spectrum(), num_modes=1)
    row = result["modal_peak_rows"][0]

    assert row["qmax"] == pytest.approx(1.5 * 0.2)
    assert row["node_displacement_contribution"][2]["ux"] == pytest.approx(2.0 * row["qmax"])
    assert row["peak_roof_ux"] == pytest.approx(0.6)


def test_out_of_range_period_warning():
    modal = _modal_result()
    modal["periods"] = np.array([10.0, 2.0])

    result = run_modal_rsa(modal, _spectrum(), num_modes=1)

    assert result["warnings"]
    assert "above spectrum range" in result["warnings"][0]


def test_story_drift_rows_are_generated_when_floor_data_exists():
    result = run_modal_rsa(_modal_result(), _spectrum(), num_modes=1)

    assert result["floor_peak_by_mode"]
    assert result["story_drift_peak_by_mode"]
    assert result["story_drift_peak_by_mode"][0]["peak_drift_ratio"] == pytest.approx(0.6 / 3.0)
