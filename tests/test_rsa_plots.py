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

from visualization.rsa_plots import plot_rsa_modal_peak_roof_response, plot_rsa_modal_peak_story_drift  # noqa: E402


def _rsa_result() -> dict:
    return {
        "roof_peak_by_mode": [
            {"mode": 1, "peak_roof_response": 0.1},
            {"mode": 2, "peak_roof_response": -0.05},
        ],
        "story_drift_peak_by_mode": [
            {"mode": 1, "story": 1, "peak_story_drift": 0.02},
            {"mode": 2, "story": 1, "peak_story_drift": -0.01},
        ],
    }


def test_rsa_plot_functions_return_figure_and_axes(tmp_path):
    for filename, plot_func in (
        ("roof.png", plot_rsa_modal_peak_roof_response),
        ("drift.png", plot_rsa_modal_peak_story_drift),
    ):
        fig, ax = plot_func(_rsa_result())
        assert isinstance(fig, Figure)
        assert isinstance(ax, Axes)
        output = tmp_path / filename
        fig.savefig(output)
        assert output.exists()
        assert output.stat().st_size > 0
        plt.close(fig)
