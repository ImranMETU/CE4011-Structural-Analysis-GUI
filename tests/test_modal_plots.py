from __future__ import annotations

import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.axes import Axes  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"

for path in (SRC_ROOT, ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from postprocessing.modal_results import package_modal_results  # noqa: E402
from visualization.modal_plots import (  # noqa: E402
    plot_modal_frequencies,
    plot_modal_periods,
    plot_mode_shape,
)


def _packaged_modal_result():
    omega = np.array([2.0, 3.0])
    modal = {
        "eigenvalues": omega**2,
        "omega": omega,
        "frequencies_hz": omega / (2.0 * math.pi),
        "periods": 2.0 * math.pi / omega,
        "full_free_mode_shapes": np.array([[1.0, 0.0], [0.0, 1.0]]),
        "active_mass_matrix": np.diag([10.0, 20.0]),
        "free_dof_map": [
            {"index": 0, "node": 1, "dof": "ux"},
            {"index": 1, "node": 2, "dof": "ux"},
        ],
        "nodes": {
            1: {"x": 0.0, "y": 0.0},
            2: {"x": 3.0, "y": 0.0},
        },
        "elements": {
            1: {"type": "frame", "node_i": 1, "node_j": 2, "length": 3.0, "angle": 0.0},
        },
        "notes": [],
    }
    return package_modal_results(modal)


def test_modal_plot_functions_return_figure_and_axes():
    result = _packaged_modal_result()

    for plot_func in (plot_mode_shape, plot_modal_frequencies, plot_modal_periods):
        fig, ax = plot_func(result)
        assert isinstance(fig, Figure)
        assert isinstance(ax, Axes)
        plt.close(fig)


def test_modal_plot_functions_accept_existing_axes():
    result = _packaged_modal_result()

    fig, ax = plt.subplots()
    returned_fig, returned_ax = plot_mode_shape(result, mode_index=0, ax=ax)

    assert returned_fig is fig
    assert returned_ax is ax
    plt.close(fig)


def test_modal_plot_figures_can_be_saved(tmp_path):
    result = _packaged_modal_result()
    plot_cases = [
        ("mode_1.png", plot_mode_shape, {"mode_index": 0, "scale": 0.5}),
        ("frequencies.png", plot_modal_frequencies, {}),
        ("periods.png", plot_modal_periods, {}),
    ]

    for filename, plot_func, kwargs in plot_cases:
        fig, _ = plot_func(result, **kwargs)
        output_path = tmp_path / filename
        fig.savefig(output_path)
        plt.close(fig)

        assert output_path.exists()
        assert output_path.stat().st_size > 0
