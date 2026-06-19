from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure

matplotlib.use("Agg")

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from postprocessing.modal_response_parameters import compute_modal_generalized_parameters  # noqa: E402
from visualization.rha_modal_force_plots import plot_modal_story_forces  # noqa: E402


def test_modal_story_force_view_returns_figure_and_axes():
    parameters = compute_modal_generalized_parameters(
        np.array([[0.5], [1.0]]), np.array([10.0, 5.0]), np.array([2.0]), np.array([3.0, 6.0])
    )
    gamma = parameters["rows"][0]["Gamma"]
    acceleration = np.array([0.0, 1.0, -2.0])
    rha = {
        "time": np.array([0.0, 0.1, 0.2]),
        "omega": np.array([2.0]),
        "participation_factors": np.array([gamma]),
        "modal_coordinate_histories": np.array([gamma * acceleration / 4.0]),
    }

    fig, ax = plot_modal_story_forces(rha, parameters)

    assert isinstance(fig, Figure)
    assert isinstance(ax, Axes)
    assert "modal force state" in ax.get_title().lower()
