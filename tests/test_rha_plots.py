from __future__ import annotations

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
IO_ROOT = SRC_ROOT / "io"
for path in (SRC_ROOT, IO_ROOT, ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


from analysis.modal_rha import run_modal_rha  # noqa: E402
from visualization.rha_plots import (  # noqa: E402
    plot_floor_displacement_histories,
    plot_ground_motion_history,
    plot_modal_coordinate_histories,
    plot_peak_story_drift_envelope,
    plot_roof_displacement_history,
    plot_story_drift_histories,
)


def _rha_result():
    modal = {
        "omega": np.array([5.0]),
        "participation": [{"mode": 1, "gamma": 1.0}],
        "nodes": {
            1: {"x": 0.0, "y": 0.0},
            2: {"x": 0.0, "y": 3.0},
        },
        "node_mode_shapes": [
            {
                1: {"ux": 0.0, "uy": 0.0, "rz": 0.0},
                2: {"ux": 1.0, "uy": 0.0, "rz": 0.0},
            }
        ],
    }
    time = np.arange(40, dtype=float) * 0.01
    gm = {"time": time, "acceleration": np.sin(time), "dt": 0.01, "path": "synthetic.thf"}
    return run_modal_rha(modal, gm, damping_ratio=0.05, num_modes=1)


def test_rha_plot_functions_return_figure_and_axes_and_save(tmp_path):
    result = _rha_result()
    plot_funcs = [
        plot_ground_motion_history,
        plot_roof_displacement_history,
        plot_floor_displacement_histories,
        plot_story_drift_histories,
        plot_peak_story_drift_envelope,
        plot_modal_coordinate_histories,
    ]

    for plot_func in plot_funcs:
        fig, ax = plot_func(result)
        assert isinstance(fig, Figure)
        assert isinstance(ax, Axes)
        output = tmp_path / f"{plot_func.__name__}.png"
        fig.savefig(output)
        plt.close(fig)
        assert output.exists()
        assert output.stat().st_size > 0
