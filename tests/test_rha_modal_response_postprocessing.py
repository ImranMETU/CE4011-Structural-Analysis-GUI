from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from postprocessing.modal_response_parameters import compute_modal_generalized_parameters  # noqa: E402
from postprocessing.rha_modal_response import (  # noqa: E402
    compute_modal_base_moment_history,
    compute_modal_base_shear_history,
    compute_modal_displacement_contributions,
    compute_modal_force_contributions,
    compute_modal_pseudo_acceleration_history,
)


def _case():
    parameters = compute_modal_generalized_parameters(
        np.array([[0.5, -0.25], [1.0, 1.0]]),
        np.array([10.0, 5.0]),
        np.array([2.0, 4.0]),
        np.array([3.0, 6.0]),
    )
    acceleration = np.array([[0.0, 1.0, -2.0], [0.0, -0.5, 1.5]])
    gamma = np.array([row["Gamma"] for row in parameters["rows"]])
    omega = parameters["omegas"]
    q = gamma[:, None] * acceleration / omega[:, None] ** 2
    rha = {
        "time": np.array([0.0, 0.1, 0.2]),
        "omega": omega,
        "participation_factors": gamma,
        "modal_coordinate_histories": q,
    }
    return parameters, acceleration, rha


def test_modal_rha_histories_follow_ce586_decomposition():
    parameters, acceleration, rha = _case()
    recovered = compute_modal_pseudo_acceleration_history(rha, parameters)
    displacement = compute_modal_displacement_contributions(rha, parameters)
    forces = compute_modal_force_contributions(rha, parameters)

    assert recovered == pytest.approx(acceleration)
    for mode_idx, row in enumerate(parameters["rows"]):
        assert displacement[mode_idx] == pytest.approx(row["u_coeff"][:, None] * acceleration[mode_idx])
        assert forces[mode_idx] == pytest.approx(row["sn"][:, None] * acceleration[mode_idx])
    assert compute_modal_base_shear_history(rha, parameters) == pytest.approx(np.sum(forces, axis=1))
    assert compute_modal_base_moment_history(rha, parameters) == pytest.approx(
        np.sum(forces * parameters["floor_heights"][None, :, None], axis=1)
    )
