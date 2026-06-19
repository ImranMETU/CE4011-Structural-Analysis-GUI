from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
import numpy as np
import pytest
from matplotlib.axes import Axes
from matplotlib.figure import Figure

matplotlib.use("Agg")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from postprocessing.modal_response_parameters import compute_modal_generalized_parameters  # noqa: E402
from visualization.modal_force_state_plots import plot_modal_force_state  # noqa: E402


def test_rsa_modal_force_state_uses_spectral_acceleration():
    parameters = compute_modal_generalized_parameters(
        np.array([[0.5], [1.0]]), np.array([10.0, 5.0]), np.array([2.0]), np.array([3.0, 6.0])
    )
    model = {
        "nodes": [{"id": 1, "x": 0.0, "y": 0.0}, {"id": 2, "x": 0.0, "y": 3.0}, {"id": 3, "x": 0.0, "y": 6.0}],
        "elements": [{"node_i": 1, "node_j": 2}, {"node_i": 2, "node_j": 3}],
    }
    sa = 2.5

    fig, ax = plot_modal_force_state(model, parameters, 1, A_value=sa, title="RSA Modal Force State")

    assert isinstance(fig, Figure)
    assert isinstance(ax, Axes)
    assert ax._modal_force_state_data["floor_forces"] == pytest.approx(parameters["rows"][0]["sn"] * sa)
