from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
import numpy as np

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

from visualization.rha_node_plots import plot_node_response_history  # noqa: E402


def test_node_response_plot_returns_figure_and_axes_and_saves(tmp_path):
    rha = {
        "time": np.array([0.0, 1.0, 2.0]),
        "node_displacement_histories": {3: np.array([0.0, 0.1, -0.05])},
    }

    fig, ax = plot_node_response_history(rha, 3, "ux")
    assert isinstance(fig, Figure)
    assert isinstance(ax, Axes)
    output = tmp_path / "node_response.png"
    fig.savefig(output)
    assert output.exists()
    assert output.stat().st_size > 0
    plt.close(fig)
