from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"

for path in (SRC_ROOT, ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from postprocessing.modal_results import (
    apply_mode_shape_sign_convention,
    calculate_modal_participation,
    frequency_table,
    mode_shape_component_labels,
    normalize_modes_by_max_translation,
    package_modal_results,
    period_table,
)


def _artificial_modal_result():
    omega = np.array([2.0, 3.0])
    return {
        "eigenvalues": omega**2,
        "omega": omega,
        "frequencies_hz": omega / (2.0 * math.pi),
        "periods": 2.0 * math.pi / omega,
        "full_free_mode_shapes": np.array(
            [
                [2.0, 0.0],
                [0.0, 3.0],
                [0.0, 0.5],
            ]
        ),
        "active_mass_matrix": np.diag([10.0, 20.0, 0.0]),
        "free_dof_map": [
            {"index": 0, "node": 1, "dof": "ux"},
            {"index": 1, "node": 2, "dof": "ux"},
            {"index": 2, "node": 2, "dof": "rz"},
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


def test_modal_result_packaging_generates_tables_and_node_shapes():
    packaged = package_modal_results(_artificial_modal_result())

    assert len(packaged["frequency_table"]) == 2
    assert len(packaged["period_table"]) == 2
    assert packaged["frequency_table"][0]["mode"] == 1
    assert packaged["frequency_table"][0]["omega"] == pytest.approx(2.0)
    assert packaged["period_table"][1]["period"] == pytest.approx(2.0 * math.pi / 3.0)
    assert packaged["node_mode_shapes"][0][1]["ux"] == pytest.approx(2.0)
    assert packaged["node_mode_shapes"][1][2]["rz"] == pytest.approx(0.5)
    assert packaged["max_modal_displacements"] == pytest.approx([2.0, 3.0])


def test_frequency_and_period_table_helpers():
    modal = _artificial_modal_result()

    freq_rows = frequency_table(modal)
    period_rows = period_table(modal)

    assert freq_rows[1]["frequency_hz"] == pytest.approx(3.0 / (2.0 * math.pi))
    assert period_rows[0]["period"] == pytest.approx(math.pi)


def test_max_translation_normalization_has_expected_amplitude():
    modal = _artificial_modal_result()
    normalized = normalize_modes_by_max_translation(
        modal["full_free_mode_shapes"],
        modal["free_dof_map"],
    )

    assert np.max(np.abs(normalized[[0, 1], 0])) == pytest.approx(1.0)
    assert np.max(np.abs(normalized[[0, 1], 1])) == pytest.approx(1.0)
    assert normalized[2, 1] == pytest.approx(0.5 / 3.0)


def test_lateral_participation_calculations():
    participation = calculate_modal_participation(_artificial_modal_result(), excitation_dof="ux")

    assert participation[0]["gamma"] == pytest.approx(0.5)
    assert participation[0]["effective_modal_mass"] == pytest.approx(10.0)
    assert participation[0]["effective_modal_mass_ratio"] == pytest.approx(1.0 / 3.0)
    assert participation[1]["gamma"] == pytest.approx(1.0 / 3.0)
    assert participation[1]["effective_modal_mass"] == pytest.approx(20.0)
    assert participation[1]["effective_modal_mass_ratio"] == pytest.approx(2.0 / 3.0)


def test_roof_ux_sign_convention_flips_negative_roof_mode():
    modal = _artificial_modal_result()
    modal["full_free_mode_shapes"] = np.array(
        [
            [-0.5, 0.0],
            [-2.0, 3.0],
            [0.0, 0.5],
        ]
    )
    modal["nodes"] = {
        1: {"x": 0.0, "y": 0.0},
        2: {"x": 3.0, "y": 4.0},
    }
    packaged = package_modal_results(modal)

    display = apply_mode_shape_sign_convention(packaged, "roof ux positive")

    assert packaged["node_mode_shapes"][0][2]["ux"] == pytest.approx(-2.0)
    assert display["node_mode_shapes"][0][2]["ux"] == pytest.approx(2.0)
    assert display["display_sign_convention"] == "roof ux positive"


def test_sign_convention_leaves_positive_roof_mode_unchanged():
    packaged = package_modal_results(_artificial_modal_result())

    display = apply_mode_shape_sign_convention(packaged, "roof ux positive")

    assert display["node_mode_shapes"][0][1]["ux"] == pytest.approx(2.0)


def test_largest_component_sign_convention_and_mode_labels():
    modal = _artificial_modal_result()
    modal["full_free_mode_shapes"] = np.array(
        [
            [-0.5, 0.0],
            [-2.0, 3.0],
            [0.0, -0.5],
        ]
    )
    packaged = package_modal_results(modal)

    display = apply_mode_shape_sign_convention(packaged, "largest component positive")
    labels = mode_shape_component_labels(display, mode_index=0, normalized=True)

    assert display["full_free_mode_shapes"][1, 0] == pytest.approx(2.0)
    assert labels[1].startswith("N1: phi_x=")
    assert "phi_y=" in labels[1]
    assert "phi_r=" in labels[1]
