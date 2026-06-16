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


from analysis.modal_rha import run_modal_rha, solve_modal_sdof_history  # noqa: E402


def _modal_result():
    return {
        "omega": np.array([5.0, 12.0]),
        "participation": [{"mode": 1, "gamma": 1.0}, {"mode": 2, "gamma": 0.4}],
        "nodes": {
            1: {"x": 0.0, "y": 0.0},
            2: {"x": 0.0, "y": 3.0},
            3: {"x": 0.0, "y": 6.0},
        },
        "node_mode_shapes": [
            {
                1: {"ux": 0.0, "uy": 0.0, "rz": 0.0},
                2: {"ux": 0.5, "uy": 0.0, "rz": 0.0},
                3: {"ux": 1.0, "uy": 0.0, "rz": 0.0},
            },
            {
                1: {"ux": 0.0, "uy": 0.0, "rz": 0.0},
                2: {"ux": 1.0, "uy": 0.0, "rz": 0.0},
                3: {"ux": -0.5, "uy": 0.0, "rz": 0.0},
            },
        ],
    }


def _ground_motion(values):
    time = np.arange(len(values), dtype=float) * 0.01
    ag = np.asarray(values, dtype=float)
    return {"time": time, "acceleration": ag, "dt": 0.01, "path": "synthetic.thf"}


def test_sdof_modal_rha_zero_ground_motion_gives_zero_response():
    gm = _ground_motion(np.zeros(20))

    result = run_modal_rha(_modal_result(), gm, damping_ratio=0.05, num_modes=1)

    assert np.max(np.abs(result["modal_coordinate_histories"])) == pytest.approx(0.0)
    assert result["peak_roof_displacement"]["abs_value"] == pytest.approx(0.0)


def test_nonzero_ground_motion_gives_finite_response_and_expected_shapes():
    ag = np.sin(np.linspace(0.0, 2.0 * np.pi, 50))
    gm = _ground_motion(ag)

    result = run_modal_rha(_modal_result(), gm, damping_ratio=0.05, num_modes=2)

    assert result["modal_coordinate_histories"].shape == (2, 50)
    assert result["modal_velocity_histories"].shape == (2, 50)
    assert result["modal_acceleration_histories"].shape == (2, 50)
    assert len(result["node_displacement_histories"]) == 3
    assert np.all(np.isfinite(result["modal_coordinate_histories"]))


def test_invalid_damping_ratio_is_rejected():
    with pytest.raises(ValueError, match="damping ratio"):
        solve_modal_sdof_history(5.0, 1.0, np.zeros(5), 0.01, xi=-0.01)


def test_invalid_mode_count_is_rejected():
    gm = _ground_motion(np.zeros(20))

    with pytest.raises(ValueError, match="num_modes"):
        run_modal_rha(_modal_result(), gm, damping_ratio=0.05, num_modes=0)

    with pytest.raises(ValueError, match="available modes"):
        run_modal_rha(_modal_result(), gm, damping_ratio=0.05, num_modes=3)
