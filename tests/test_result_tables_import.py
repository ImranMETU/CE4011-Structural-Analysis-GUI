from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
IO_ROOT = SRC_ROOT / "io"

for path in (SRC_ROOT, IO_ROOT, ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


def _static_result():
    return {
        "displacements": {
            1: {"ux": 0.0, "uy": 0.0, "rz": 0.0},
            2: {"ux": 0.001, "uy": -0.002, "rz": 0.003},
        },
        "reactions": {
            1: {"rx": 10.0, "ry": -20.0, "mz": 30.0},
        },
        "elements": {
            1: {"type": "frame"},
            2: {"type": "truss"},
        },
        "member_end_forces": {
            1: {
                "node_i": {"nx": 1.0, "vy": 2.0, "mz": 3.0},
                "node_j": {"nx": 4.0, "vy": 5.0, "mz": 6.0},
            },
            2: {
                "node_i": {"nx": 7.0},
                "node_j": {"nx": -7.0},
            },
        },
    }


def _modal_result():
    return {
        "eigenvalues": [4.0, 25.0],
        "omega": [2.0, 5.0],
        "frequencies_hz": [0.318309886, 0.795774715],
        "periods": [3.141592654, 1.256637061],
        "full_free_mode_shapes": [[1.0, 0.0], [0.0, 1.0]],
        "free_stiffness_matrix": [[40.0, 0.0], [0.0, 50.0]],
        "active_mass_matrix": [[10.0, 0.0], [0.0, 5.0]],
        "condensed_stiffness": [[4.0, 0.0], [0.0, 25.0]],
        "condensed_mass_matrix": [[10.0, 0.0], [0.0, 5.0]],
        "massive_dof_indices": [0, 1],
        "massless_dof_indices": [],
        "matrix_diagnostics": {
            "free_stiffness_size": 2,
            "free_mass_size": 2,
            "massive_dof_count": 1,
            "massless_dof_count": 1,
            "condensed_stiffness_size": 1,
            "condensed_mass_size": 1,
            "condensed_stiffness_symmetry_error": 0.0,
            "condensed_mass_symmetry_error": 0.0,
            "kbb_condition_number": 1.0,
        },
        "free_dof_map": [
            {"index": 0, "node": 1, "dof": "ux"},
            {"index": 1, "node": 2, "dof": "ux"},
        ],
        "nodes": {
            1: {"x": 0.0, "y": 3.0},
            2: {"x": 0.0, "y": 6.0},
        },
        "node_mode_shapes": [
            {1: {"ux": 1.0, "uy": 0.0, "rz": 0.0}, 2: {"ux": 0.0, "uy": 0.0, "rz": 0.0}},
            {1: {"ux": 0.0, "uy": 0.0, "rz": 0.0}, 2: {"ux": 1.0, "uy": 0.0, "rz": 0.0}},
        ],
        "frequency_table": [
            {"mode": 1, "omega": 2.0, "frequency_hz": 0.318309886, "period": 3.141592654},
            {"mode": 2, "omega": 5.0, "frequency_hz": 0.795774715, "period": 1.256637061},
        ],
        "participation": [
            {
                "mode": 1,
                "gamma": 1.25,
                "effective_modal_mass": 50.0,
                "effective_modal_mass_ratio": 0.5,
            }
        ],
        "mass_source_summary": {
            "source_type": "manual",
            "node_count": 1,
            "total_ux_mass": 10.0,
            "total_uy_mass": 0.0,
            "total_rz_mass": 0.0,
        },
    }


def _drift_static_result():
    return {
        "nodes": {
            1: {"x": 0.0, "y": 0.0},
            2: {"x": 4.0, "y": 0.0},
            3: {"x": 0.0, "y": 3.0},
            4: {"x": 4.0, "y": 3.0},
        },
        "displacements": {
            1: {"ux": 0.0, "uy": 0.0, "rz": 0.0},
            2: {"ux": 0.0, "uy": 0.0, "rz": 0.0},
            3: {"ux": 0.03, "uy": 0.0, "rz": 0.0},
            4: {"ux": 0.036, "uy": 0.0, "rz": 0.0},
        },
    }


def test_result_table_helper_module_imports_successfully():
    import gui.result_tables as tables

    assert callable(tables.format_nodal_displacement_rows)
    assert callable(tables.write_table_csv)


def test_static_result_formatters_return_expected_headers_and_rows():
    from gui.result_tables import (
        format_member_force_rows,
        format_nodal_displacement_rows,
        format_reaction_rows,
    )

    disp_headers, disp_rows = format_nodal_displacement_rows(_static_result())
    reaction_headers, reaction_rows = format_reaction_rows(_static_result())
    force_headers, force_rows = format_member_force_rows(_static_result())

    assert disp_headers == ["Node", "ux [m]", "uy [m]", "rz [rad]"]
    assert disp_rows[1] == ["2", "1.000000e-03", "-2.000000e-03", "3.000000e-03"]
    assert reaction_headers == ["Node", "Rx [N]", "Ry [N]", "Mz [N-m]"]
    assert reaction_rows[0] == ["1", "1.000000e+01", "-2.000000e+01", "3.000000e+01"]
    assert force_headers[0:2] == ["Element", "Type"]
    assert force_rows[1][0:2] == ["2", "truss"]
    assert force_rows[1][3] == "0.000000e+00"


def test_modal_result_formatters_return_expected_headers_and_rows():
    from gui.result_tables import (
        format_condensed_modal_matrix_rows,
        format_full_mode_shape_rows,
        format_modal_dof_classification_rows,
        format_modal_frequency_rows,
        format_modal_mass_summary_rows,
        format_modal_participation_rows,
        format_modal_properties_rows,
    )

    freq_headers, freq_rows = format_modal_frequency_rows(_modal_result())
    part_headers, part_rows = format_modal_participation_rows(_modal_result())
    prop_headers, prop_rows = format_modal_properties_rows(_modal_result())
    dof_headers, dof_rows = format_modal_dof_classification_rows(_modal_result())
    matrix_headers, matrix_rows = format_condensed_modal_matrix_rows(_modal_result())
    shape_headers, shape_rows = format_full_mode_shape_rows(_modal_result())
    mass_headers, mass_rows = format_modal_mass_summary_rows(_modal_result())

    assert freq_headers == ["Mode", "omega [rad/s]", "frequency [Hz]", "period [s]"]
    assert freq_rows[0] == ["1", "2.000000e+00", "3.183099e-01", "3.141593e+00"]
    assert part_headers[0:4] == ["Mode", "Mn", "Lnh", "Gamma = Lnh/Mn"]
    assert part_rows[0][0:4] == ["1", "1.000000e+01", "1.000000e+01", "1.000000e+00"]
    assert prop_headers[0] == "Mode"
    assert "eigenvalue lambda = omega^2" in prop_headers
    assert "Normalization" in prop_headers
    assert prop_rows[0][0] == "1"
    assert prop_rows[0][prop_headers.index("eigenvalue lambda = omega^2")] == "4.000000e+00"
    assert dof_headers == ["Free DOF Index", "Node", "DOF", "Mass", "Classification", "Note"]
    assert dof_rows[1][4] == "massive"
    assert matrix_headers == ["Property", "Value"]
    assert matrix_rows[0][0] == "free_stiffness_size"
    assert shape_headers == ["Mode", "Node", "ux", "uy", "rz"]
    assert mass_headers == ["Property", "Value"]
    assert any(row[0] == "source_type" and row[1] == "manual" for row in mass_rows)


def test_drift_result_formatters_return_expected_headers_and_rows():
    from gui.result_tables import format_static_roof_displacement_rows, format_static_story_drift_rows

    drift_headers, drift_rows = format_static_story_drift_rows(_drift_static_result())
    roof_headers, roof_rows = format_static_roof_displacement_rows(_drift_static_result())

    assert drift_headers == [
        "Story",
        "Lower Elevation [m]",
        "Upper Elevation [m]",
        "Story Height [m]",
        "Lower Floor ux [m]",
        "Upper Floor ux [m]",
        "Story Drift [m]",
        "Abs Story Drift [m]",
        "Drift Ratio [-]",
        "Abs Drift Ratio [-]",
    ]
    assert drift_rows[0][0] == "1"
    assert drift_rows[0][6] == "3.300000e-02"
    assert roof_headers == ["Roof Elevation [m]", "Roof Nodes", "Direction", "Roof Displacement [m]", "Controlling Node"]
    assert roof_rows[0][2] == "ux"
    assert roof_rows[0][3] == "3.600000e-02"


def test_table_csv_writer_writes_headers_and_rows(tmp_path):
    from gui.result_tables import write_table_csv

    path = tmp_path / "table.csv"
    write_table_csv(path, ["A", "B"], [["1", "2"], ["3", "4"]])

    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))

    assert rows == [["A", "B"], ["1", "2"], ["3", "4"]]


def test_static_gui_launcher_import_remains_safe_with_tables_menu():
    launcher_path = ROOT / "scripts" / "run_static_gui.py"
    spec = importlib.util.spec_from_file_location("run_static_gui_tables_import_test", launcher_path)
    module = importlib.util.module_from_spec(spec)

    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)

    assert hasattr(module, "main")
