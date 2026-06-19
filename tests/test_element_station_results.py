from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
IO_ROOT = SRC_ROOT / "io"

for path in (SRC_ROOT, IO_ROOT, ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from gui.result_tables import (  # noqa: E402
    format_element_deformed_slope_rows,
    format_element_station_force_rows,
)
from postprocessing.element_station_results import (  # noqa: E402
    all_frame_station_results,
    frame_internal_end_section_forces,
    frame_station_results,
    hermite_deformed_polyline,
    hermite_shape_values,
    interpolate_frame_displacement,
    section_force_at_x,
    station_xis,
)
from postprocessing.static_results import run_static_analysis  # noqa: E402
from text_loader import load_text_model  # noqa: E402


def _static_result(member_loads=None) -> dict:
    return {
        "nodes": {
            1: {"x": 0.0, "y": 0.0},
            2: {"x": 10.0, "y": 0.0},
            3: {"x": 0.0, "y": 2.0},
            4: {"x": 2.0, "y": 2.0},
        },
        "elements": {
            1: {
                "type": "frame",
                "node_i": 1,
                "node_j": 2,
                "length": 10.0,
                "angle": 0.0,
                "member_loads": member_loads or [],
            },
            2: {"type": "truss", "node_i": 3, "node_j": 4, "length": 2.0, "angle": 0.0},
        },
        "displacements": {
            1: {"ux": 0.0, "uy": 0.0, "rz": 0.0},
            2: {"ux": 0.1, "uy": 0.0, "rz": 0.0},
            3: {"ux": 0.0, "uy": 0.0, "rz": 0.0},
            4: {"ux": 0.0, "uy": 0.0, "rz": 0.0},
        },
        "member_end_forces": {
            1: {
                "node_i": {"nx": 10.0, "vy": 5.0, "mz": 2.0},
                "node_j": {"nx": -10.0, "vy": -5.0, "mz": -2.0},
            },
            2: {
                "node_i": {"nx": 1.0, "vy": 0.0, "mz": 0.0},
                "node_j": {"nx": -1.0, "vy": 0.0, "mz": 0.0},
            },
        },
    }


def test_hermite_shape_functions_recover_nodal_values_at_ends():
    left = interpolate_frame_displacement(10.0, [1.0, 2.0, 0.3, 4.0, 5.0, -0.2], 0.0)
    right = interpolate_frame_displacement(10.0, [1.0, 2.0, 0.3, 4.0, 5.0, -0.2], 1.0)

    assert left["u"] == pytest.approx(1.0)
    assert left["v"] == pytest.approx(2.0)
    assert right["u"] == pytest.approx(4.0)
    assert right["v"] == pytest.approx(5.0)


def test_hermite_slope_formula_at_simple_rotation_state():
    result = interpolate_frame_displacement(10.0, [0.0, 0.0, 1.0, 0.0, 0.0, 0.0], 0.0)

    assert result["slope"] == pytest.approx(1.0)
    assert "dH2_dx" in hermite_shape_values(10.0, 0.0)


def test_zero_displacements_produce_zero_deformed_offsets():
    result = interpolate_frame_displacement(10.0, [0.0] * 6, 0.5)

    assert result["u"] == pytest.approx(0.0)
    assert result["v"] == pytest.approx(0.0)
    assert result["slope"] == pytest.approx(0.0)


def test_station_list_includes_endpoints_and_intermediate_stations():
    xis = station_xis(5)

    assert xis == pytest.approx([0.0, 0.25, 0.5, 0.75, 1.0])


def test_station_result_rows_skip_truss_elements_and_include_expected_keys():
    rows = all_frame_station_results(_static_result(), n_stations=3)

    assert len(rows) == 3
    assert {row["element"] for row in rows} == {1}
    assert {"N", "V", "M", "u_local", "v_local", "slope"} <= set(rows[0])


def test_station_force_table_rows_have_expected_columns():
    headers, force_rows = format_element_station_force_rows(_static_result(), n_stations=2)
    slope_headers, slope_rows = format_element_deformed_slope_rows(_static_result(), n_stations=2)

    assert headers == [
        "Element",
        "Type",
        "Station",
        "xi [-]",
        "x_local [m]",
        "global_x [m]",
        "global_y [m]",
        "N [N]",
        "V [N]",
        "M [N-m]",
    ]
    assert slope_headers[-3:] == ["u_local [m]", "v_local [m]", "slope [rad]"]
    assert len(force_rows) == 2
    assert len(slope_rows) == 2


def test_udl_station_moment_varies_across_stations():
    result = _static_result([{"type": "udl", "direction": "local_y", "w": -2.0}])
    moments = [row["M"] for row in frame_station_results(result, 1, n_stations=5)]

    assert len(set(round(value, 8) for value in moments)) > 1


def test_point_load_station_shear_has_piecewise_jump():
    element = _static_result([{"type": "point", "direction": "local_y", "p": -3.0, "a": 5.0}])["elements"][1]
    member_force = _static_result()["member_end_forces"][1]

    before = section_force_at_x(member_force, element, 4.0)["V"]
    after = section_force_at_x(member_force, element, 6.0)["V"]

    assert after - before == pytest.approx(3.0)


def test_cantilever_tip_load_reconstructs_triangular_bending_moment():
    data, _masses = load_text_model(ROOT / "inputs" / "examples" / "basic_cantilever_beam.txt")
    result = run_static_analysis(data)

    rows = frame_station_results(result, 1, n_stations=5)
    moments = [row["M"] for row in rows]

    assert moments[0] == pytest.approx(10000.0 * 5.0)
    assert moments[-1] == pytest.approx(0.0, abs=1.0e-8)
    assert max(abs(value) for value in moments) == pytest.approx(50000.0)
    first_differences = [moments[i + 1] - moments[i] for i in range(len(moments) - 1)]
    assert first_differences == pytest.approx([first_differences[0]] * len(first_differences))


def test_no_member_load_uses_converted_j_end_section_moment():
    member_force = {
        "node_i": {"nx": 0.0, "vy": 3.0, "mz": 20.0},
        "node_j": {"nx": 0.0, "vy": -3.0, "mz": -5.0},
    }
    element = {"length": 5.0, "member_loads": []}
    ends = frame_internal_end_section_forces(member_force)

    assert ends["i"]["M"] == pytest.approx(20.0)
    assert ends["j"]["M"] == pytest.approx(5.0)
    assert section_force_at_x(member_force, element, 0.0)["M"] == pytest.approx(20.0)
    assert section_force_at_x(member_force, element, 5.0)["M"] == pytest.approx(5.0)


def test_simply_supported_midspan_point_load_has_zero_end_moments_and_midspan_peak():
    data, _masses = load_text_model(ROOT / "inputs" / "examples" / "member_load_point_frame.txt")
    result = run_static_analysis(data)

    rows = frame_station_results(result, 1, n_stations=5)
    moments = [row["M"] for row in rows]

    assert moments[0] == pytest.approx(0.0, abs=1.0e-8)
    assert moments[-1] == pytest.approx(0.0, abs=1.0e-8)
    assert moments[2] == pytest.approx(25000.0)
    assert moments[2] == pytest.approx(max(moments))


def test_simply_supported_udl_has_zero_end_moments_and_parabolic_shape():
    data, _masses = load_text_model(ROOT / "inputs" / "examples" / "member_load_udl_frame.txt")
    result = run_static_analysis(data)

    rows = frame_station_results(result, 1, n_stations=5)
    moments = [row["M"] for row in rows]
    second_differences = [
        moments[i + 2] - 2.0 * moments[i + 1] + moments[i]
        for i in range(len(moments) - 2)
    ]

    assert moments[0] == pytest.approx(0.0, abs=1.0e-8)
    assert moments[-1] == pytest.approx(0.0, abs=1.0e-8)
    assert moments[2] == pytest.approx(31250.0)
    assert any(abs(value) > 1.0e-8 for value in second_differences)


def test_hermite_deformed_polyline_has_station_coordinates():
    polyline = hermite_deformed_polyline(_static_result(), 1, scale=1.0, n_stations=4)

    assert len(polyline["x_deformed"]) == 4
    assert polyline["x_deformed"][0] == pytest.approx(0.0)
    assert polyline["x_deformed"][-1] == pytest.approx(10.1)
