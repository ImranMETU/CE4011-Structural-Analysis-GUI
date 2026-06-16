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

from gui.result_tables import (  # noqa: E402
    format_element_deformed_slope_rows,
    format_element_station_force_rows,
)
from postprocessing.element_station_results import (  # noqa: E402
    all_frame_station_results,
    frame_station_results,
    hermite_deformed_polyline,
    hermite_shape_values,
    interpolate_frame_displacement,
    section_force_at_x,
    station_xis,
)


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

    assert headers == ["Element", "Type", "Station", "xi", "x_local", "global_x", "global_y", "N", "V", "M"]
    assert slope_headers[-3:] == ["u_local", "v_local", "slope_rad"]
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

    assert after - before == pytest.approx(-3.0)


def test_hermite_deformed_polyline_has_station_coordinates():
    polyline = hermite_deformed_polyline(_static_result(), 1, scale=1.0, n_stations=4)

    assert len(polyline["x_deformed"]) == 4
    assert polyline["x_deformed"][0] == pytest.approx(0.0)
    assert polyline["x_deformed"][-1] == pytest.approx(10.1)
