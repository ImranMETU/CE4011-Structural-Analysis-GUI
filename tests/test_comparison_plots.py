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

from visualization.comparison_plots import (  # noqa: E402
    plot_fundamental_frequency_comparison,
    plot_fundamental_period_comparison,
    plot_max_story_drift_comparison,
    plot_roof_displacement_comparison,
    plot_story_drift_profile_comparison,
)


def _comparison_result():
    drift_u = {
        "stories": [
            {"upper_elevation": 3.0, "abs_story_drift": 0.03},
            {"upper_elevation": 6.0, "abs_story_drift": 0.05},
        ]
    }
    drift_b = {
        "stories": [
            {"upper_elevation": 3.0, "abs_story_drift": 0.02},
            {"upper_elevation": 6.0, "abs_story_drift": 0.03},
        ]
    }
    return {
        "unbraced": {
            "roof_displacement_ux": 0.10,
            "max_story_drift": 0.05,
            "f1_Hz": 2.0,
            "T1_s": 0.5,
            "drift_result": drift_u,
        },
        "braced": {
            "roof_displacement_ux": 0.04,
            "max_story_drift": 0.03,
            "f1_Hz": 3.0,
            "T1_s": 1.0 / 3.0,
            "drift_result": drift_b,
        },
    }


def test_comparison_plot_module_imports():
    import visualization.comparison_plots as plots

    assert callable(plots.plot_roof_displacement_comparison)


def test_comparison_plot_functions_return_fig_and_axes():
    comparison = _comparison_result()
    plot_cases = [
        (plot_roof_displacement_comparison, (comparison,)),
        (plot_max_story_drift_comparison, (comparison,)),
        (plot_fundamental_frequency_comparison, (comparison,)),
        (plot_fundamental_period_comparison, (comparison,)),
        (plot_story_drift_profile_comparison, (comparison["unbraced"]["drift_result"], comparison["braced"]["drift_result"])),
    ]

    for plot_func, args in plot_cases:
        fig, ax = plot_func(*args)
        assert isinstance(fig, Figure)
        assert isinstance(ax, Axes)
        plt.close(fig)


def test_comparison_plot_figures_can_be_saved(tmp_path):
    comparison = _comparison_result()
    plot_cases = [
        ("roof.png", plot_roof_displacement_comparison, (comparison,)),
        ("drift.png", plot_max_story_drift_comparison, (comparison,)),
        ("freq.png", plot_fundamental_frequency_comparison, (comparison,)),
        ("period.png", plot_fundamental_period_comparison, (comparison,)),
        ("profile.png", plot_story_drift_profile_comparison, (comparison["unbraced"]["drift_result"], comparison["braced"]["drift_result"])),
    ]

    for filename, plot_func, args in plot_cases:
        fig, _ax = plot_func(*args)
        path = tmp_path / filename
        fig.savefig(path)
        plt.close(fig)
        assert path.exists()
        assert path.stat().st_size > 0
