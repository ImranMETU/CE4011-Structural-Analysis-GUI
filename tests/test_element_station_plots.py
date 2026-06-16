from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.axes import Axes  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"

for path in (SRC_ROOT, ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from visualization.element_station_plots import (  # noqa: E402
    plot_deformed_slope_profile,
    plot_hermite_deformed_shape,
    plot_section_force_stations,
)


def _static_result() -> dict:
    return {
        "nodes": {
            1: {"x": 0.0, "y": 0.0},
            2: {"x": 5.0, "y": 0.0},
        },
        "elements": {
            1: {
                "type": "frame",
                "node_i": 1,
                "node_j": 2,
                "length": 5.0,
                "angle": 0.0,
                "member_loads": [{"type": "udl", "direction": "local_y", "w": -1.0}],
            }
        },
        "displacements": {
            1: {"ux": 0.0, "uy": 0.0, "rz": 0.0},
            2: {"ux": 0.05, "uy": -0.02, "rz": 0.01},
        },
        "member_end_forces": {
            1: {
                "node_i": {"nx": 10.0, "vy": 5.0, "mz": 2.0},
                "node_j": {"nx": -10.0, "vy": -5.0, "mz": -2.0},
            }
        },
    }


def test_station_plot_functions_return_figure_and_axes():
    for plot_func in (plot_hermite_deformed_shape, plot_section_force_stations, plot_deformed_slope_profile):
        fig, ax = plot_func(_static_result())
        assert isinstance(fig, Figure)
        assert isinstance(ax, Axes)
        plt.close(fig)


def test_station_plot_functions_can_save_figures(tmp_path):
    plots = [
        ("hermite.png", plot_hermite_deformed_shape),
        ("stations.png", plot_section_force_stations),
        ("slopes.png", plot_deformed_slope_profile),
    ]
    for filename, plot_func in plots:
        fig, _ax = plot_func(_static_result())
        output = tmp_path / filename
        fig.savefig(output)
        assert output.exists()
        assert output.stat().st_size > 0
        plt.close(fig)
