from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"

for path in (SRC_ROOT, ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from generators.frame_generator import generate_frame_model  # noqa: E402
from postprocessing.drift_results import (  # noqa: E402
    compute_floor_displacements,
    compute_modal_roof_displacement,
    compute_modal_story_drift,
    compute_roof_displacement,
    compute_story_drift,
    format_roof_displacement_rows,
    format_story_drift_rows,
    get_floor_levels,
    get_roof_level,
    get_roof_nodes,
    group_nodes_by_floor,
)
from postprocessing.static_results import run_static_analysis  # noqa: E402


def _static_result():
    return {
        "nodes": {
            1: {"x": 0.0, "y": 0.0},
            2: {"x": 4.0, "y": 1.0e-10},
            3: {"x": 0.0, "y": 3.0},
            4: {"x": 4.0, "y": 3.0 + 1.0e-10},
            5: {"x": 0.0, "y": 6.0},
            6: {"x": 4.0, "y": 6.0},
        },
        "displacements": {
            1: {"ux": 0.0, "uy": 0.0, "rz": 0.0},
            2: {"ux": 0.0, "uy": 0.0, "rz": 0.0},
            3: {"ux": 0.030, "uy": 0.0, "rz": 0.0},
            4: {"ux": 0.033, "uy": 0.0, "rz": 0.0},
            5: {"ux": 0.090, "uy": 0.0, "rz": 0.0},
            6: {"ux": 0.087, "uy": 0.0, "rz": 0.0},
        },
    }


def _modal_result():
    return {
        "nodes": _static_result()["nodes"],
        "node_mode_shapes": [
            _static_result()["displacements"],
        ],
    }


def test_floor_grouping_and_roof_detection():
    nodes = _static_result()["nodes"]

    grouped = group_nodes_by_floor(nodes)

    assert len(grouped) == 3
    assert get_floor_levels(nodes) == pytest.approx([0.0, 3.0, 6.0], abs=1e-8)
    assert get_roof_level(nodes) == pytest.approx(6.0)
    assert get_roof_nodes(nodes) == [5, 6]


def test_static_floor_displacement_calculation_mean():
    floors = compute_floor_displacements(_static_result(), direction="ux", method="mean")

    assert len(floors["floors"]) == 3
    assert floors["floors"][0]["displacement"] == pytest.approx(0.0)
    assert floors["floors"][1]["displacement"] == pytest.approx(0.0315)
    assert floors["floors"][2]["displacement"] == pytest.approx(0.0885)


def test_story_drift_and_drift_ratio_calculation():
    drift = compute_story_drift(_static_result(), direction="ux", method="mean")

    assert len(drift["stories"]) == 2
    assert drift["stories"][0]["story_drift"] == pytest.approx(0.0315)
    assert drift["stories"][0]["drift_ratio"] == pytest.approx(0.0315 / 3.0)
    assert drift["stories"][1]["story_drift"] == pytest.approx(0.057)
    assert drift["stories"][1]["abs_drift_ratio"] == pytest.approx(0.057 / 3.0)


def test_roof_displacement_max_abs_with_controlling_node():
    roof = compute_roof_displacement(_static_result(), direction="ux", method="max_abs")

    assert roof["roof_elevation"] == pytest.approx(6.0)
    assert roof["roof_node_ids"] == [5, 6]
    assert roof["roof_displacement"] == pytest.approx(0.090)
    assert roof["controlling_node_id"] == 5


def test_modal_story_drift_and_roof_displacement():
    drift = compute_modal_story_drift(_modal_result(), mode_index=0, direction="ux", method="mean")
    roof = compute_modal_roof_displacement(_modal_result(), mode_index=0, direction="ux", method="max_abs")

    assert drift["type"] == "modal"
    assert drift["stories"][1]["story_drift"] == pytest.approx(0.057)
    assert roof["roof_displacement"] == pytest.approx(0.090)


def test_generated_frame_can_solve_and_compute_drift():
    data = generate_frame_model(n_stories=3, n_bays=1, story_height=3.0, bay_width=6.0)
    result = run_static_analysis(data)

    drift = compute_story_drift(result)
    roof = compute_roof_displacement(result)

    assert len(drift["stories"]) == 3
    assert roof["roof_elevation"] == pytest.approx(9.0)


def test_format_table_rows_have_expected_columns():
    drift = compute_story_drift(_static_result())
    roof = compute_roof_displacement(_static_result())

    drift_headers, drift_rows = format_story_drift_rows(drift)
    roof_headers, roof_rows = format_roof_displacement_rows(roof)

    assert drift_headers[0] == "Story"
    assert drift_headers[-1] == "Abs Drift Ratio"
    assert len(drift_rows[0]) == len(drift_headers)
    assert roof_headers == ["Roof Elevation", "Roof Nodes", "Roof Displacement", "Controlling Node"]
    assert roof_rows[0][3] == "5"
