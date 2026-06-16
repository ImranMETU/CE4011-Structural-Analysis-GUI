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

from analysis.modal_rsa import run_modal_rsa  # noqa: E402
from gui.result_tables import format_rsa_combined_response_rows  # noqa: E402
from postprocessing.rsa_results import rsa_combined_response_rows  # noqa: E402
from visualization.rsa_plots import (  # noqa: E402
    plot_rsa_combined_roof_response,
    plot_rsa_combined_story_drift_envelope,
)


def _modal_result() -> dict:
    return {
        "eigenvalues": np.array([4.0, 9.0]),
        "omega": np.array([2.0, 3.0]),
        "frequencies_hz": np.array([2.0 / (2.0 * np.pi), 3.0 / (2.0 * np.pi)]),
        "periods": np.array([1.0, 2.0]),
        "participation": [{"mode": 1, "gamma": 1.0}, {"mode": 2, "gamma": 1.0}],
        "node_mode_shapes": [
            {1: {"ux": 0.0}, 2: {"ux": 1.0}, 3: {"ux": 2.0}},
            {1: {"ux": 0.0}, 2: {"ux": -0.5}, 3: {"ux": 1.0}},
        ],
        "nodes": {
            1: {"x": 0.0, "y": 0.0},
            2: {"x": 0.0, "y": 3.0},
            3: {"x": 0.0, "y": 6.0},
        },
    }


def _spectrum() -> dict:
    return {
        "periods": np.array([0.5, 1.0, 2.0]),
        "Sa": np.array([1.0, 1.0, 1.0]),
        "Sd": np.array([0.1, 0.2, 0.3]),
        "damping_ratio": 0.05,
    }


def test_combined_result_dictionary_contains_methods_and_roof_response():
    rsa = run_modal_rsa(_modal_result(), _spectrum(), num_modes=2)

    assert rsa["combined"]["method_names"] == ["ABSSUM", "SRSS", "CQC"]
    assert {"ABSSUM", "SRSS", "CQC"} <= set(rsa["combined"]["roof_response"])
    assert rsa["combined"]["story_drifts"]


def test_combined_rows_and_gui_table_have_expected_columns():
    rsa = run_modal_rsa(_modal_result(), _spectrum(), num_modes=2)
    rows = rsa_combined_response_rows(rsa)
    headers, table = format_rsa_combined_response_rows(rsa)

    assert rows
    assert headers == ["Quantity", "Location", "ABSSUM", "SRSS", "CQC"]
    assert table
    assert any(row[0] == "Story drift" for row in table)


def test_combined_rsa_plots_return_figure_and_axes_and_save(tmp_path):
    rsa = run_modal_rsa(_modal_result(), _spectrum(), num_modes=2)
    for filename, plot_func in (
        ("combined_roof.png", plot_rsa_combined_roof_response),
        ("combined_story.png", plot_rsa_combined_story_drift_envelope),
    ):
        fig, ax = plot_func(rsa)
        assert isinstance(fig, Figure)
        assert isinstance(ax, Axes)
        output = tmp_path / filename
        fig.savefig(output)
        assert output.exists()
        assert output.stat().st_size > 0
        plt.close(fig)
