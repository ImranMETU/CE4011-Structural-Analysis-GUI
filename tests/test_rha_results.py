from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
IO_ROOT = SRC_ROOT / "io"
for path in (SRC_ROOT, IO_ROOT, ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


from analysis.modal_rha import (  # noqa: E402
    compute_floor_displacement_histories,
    compute_story_drift_histories,
    peak_roof_displacement,
    run_modal_rha,
)
from postprocessing.rha_results import (  # noqa: E402
    format_peak_floor_response_rows,
    format_peak_story_drift_rows,
    format_rha_summary_rows,
)


def _modal_result():
    return {
        "omega": np.array([5.0]),
        "participation": [{"mode": 1, "gamma": 1.0}],
        "nodes": {
            1: {"x": 0.0, "y": 0.0},
            2: {"x": 0.0, "y": 3.0},
            3: {"x": 0.0, "y": 6.0},
        },
        "node_mode_shapes": [
            {
                1: {"ux": 0.0, "uy": 0.0, "rz": 0.0},
                2: {"ux": 0.5, "uy": 0.0, "rz": 0.0},
                3: {"ux": 1.0, "uy": 0.0, "rz": 0.0},
            }
        ],
    }


def test_floor_story_and_roof_history_extraction():
    node_histories = {
        1: np.array([0.0, 0.0, 0.0]),
        2: np.array([0.0, 0.1, -0.1]),
        3: np.array([0.0, 0.3, -0.2]),
    }
    time = np.array([0.0, 0.1, 0.2])

    floors = compute_floor_displacement_histories(_modal_result(), node_histories)
    stories = compute_story_drift_histories(floors)
    roof = peak_roof_displacement(_modal_result(), node_histories, time)

    assert len(floors) == 3
    assert len(stories) == 2
    assert roof["node"] == 3
    assert roof["abs_value"] == 0.3
    assert stories[1]["history"][1] == pytest.approx(0.2)


def test_rha_summary_rows_format_correctly():
    time = np.arange(10, dtype=float) * 0.01
    gm = {"time": time, "acceleration": np.sin(time), "dt": 0.01, "path": "synthetic.thf"}
    result = run_modal_rha(_modal_result(), gm, damping_ratio=0.05, num_modes=1)

    summary_headers, summary_rows = format_rha_summary_rows(result)
    floor_headers, floor_rows = format_peak_floor_response_rows(result)
    story_headers, story_rows = format_peak_story_drift_rows(result)

    assert summary_headers[0] == "record name"
    assert summary_rows[0][6] == "1"
    assert floor_headers[0] == "floor"
    assert len(floor_rows) == 3
    assert story_headers[0] == "story"
    assert len(story_rows) == 2
