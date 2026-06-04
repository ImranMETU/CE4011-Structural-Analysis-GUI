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

from visualization.drift_plots import (  # noqa: E402
    plot_drift_ratio_profile,
    plot_floor_displacement_profile,
    plot_roof_displacement_marker,
    plot_story_drift_profile,
)


def _floor_result():
    return {
        "direction": "ux",
        "floors": [
            {"elevation": 0.0, "displacement": 0.0},
            {"elevation": 3.0, "displacement": 0.03},
            {"elevation": 6.0, "displacement": 0.09},
        ],
    }


def _drift_result():
    return {
        "direction": "ux",
        "stories": [
            {"upper_elevation": 3.0, "story_drift": 0.03, "drift_ratio": 0.01},
            {"upper_elevation": 6.0, "story_drift": 0.06, "drift_ratio": 0.02},
        ],
    }


def _roof_result():
    return {
        "direction": "ux",
        "roof_elevation": 6.0,
        "roof_displacement": 0.09,
    }


def test_drift_plot_functions_import():
    assert callable(plot_story_drift_profile)
    assert callable(plot_drift_ratio_profile)
    assert callable(plot_floor_displacement_profile)
    assert callable(plot_roof_displacement_marker)


def test_drift_plot_functions_return_figure_and_axes():
    plot_cases = [
        (plot_story_drift_profile, _drift_result()),
        (plot_drift_ratio_profile, _drift_result()),
        (plot_floor_displacement_profile, _floor_result()),
        (plot_roof_displacement_marker, _roof_result()),
    ]

    for plot_func, result in plot_cases:
        fig, ax = plot_func(result)
        assert isinstance(fig, Figure)
        assert isinstance(ax, Axes)
        plt.close(fig)


def test_drift_plot_figures_can_be_saved(tmp_path):
    plot_cases = [
        ("story_drift.png", plot_story_drift_profile, _drift_result()),
        ("drift_ratio.png", plot_drift_ratio_profile, _drift_result()),
        ("floor_displacement.png", plot_floor_displacement_profile, _floor_result()),
        ("roof_marker.png", plot_roof_displacement_marker, _roof_result()),
    ]

    for filename, plot_func, result in plot_cases:
        fig, _ax = plot_func(result)
        path = tmp_path / filename
        fig.savefig(path)
        plt.close(fig)

        assert path.exists()
        assert path.stat().st_size > 0
