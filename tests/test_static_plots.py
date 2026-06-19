from __future__ import annotations

import sys
from pathlib import Path
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pytest  # noqa: E402
from matplotlib.axes import Axes  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
IO_ROOT = SRC_ROOT / "io"

for path in (SRC_ROOT, IO_ROOT, ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from postprocessing.static_results import run_static_analysis  # noqa: E402
from visualization.static_plots import (  # noqa: E402
    build_structural_force_diagram_coordinates,
    compute_deformed_shape_auto_scale,
    compute_force_diagram_ordinates,
    compute_force_diagram_scale,
    plot_axial_force_diagram,
    plot_bending_moment_diagram,
    plot_deformed_shape,
    plot_geometry,
    plot_shear_force_diagram,
)
from text_loader import load_text_model  # noqa: E402
from xml_loader import load_structure_from_xml  # noqa: E402


def _static_result():
    case_path = ROOT / "inputs" / "regression" / "xml" / "regression_thermal_combined_frame.xml"
    return run_static_analysis(load_structure_from_xml(case_path))


def _diagram_result(angle_case: str = "horizontal", member_loads=None, forces=None):
    if angle_case == "vertical":
        node_j = {"x": 0.0, "y": 5.0}
        angle = 1.5707963267948966
    elif angle_case == "inclined":
        node_j = {"x": 3.0, "y": 4.0}
        angle = 0.9272952180016122
    else:
        node_j = {"x": 5.0, "y": 0.0}
        angle = 0.0
    return {
        "nodes": {
            1: {"x": 0.0, "y": 0.0},
            2: node_j,
        },
        "elements": {
            1: {
                "type": "frame",
                "node_i": 1,
                "node_j": 2,
                "length": 5.0,
                "angle": angle,
                "member_loads": member_loads or [],
            }
        },
        "displacements": {
            1: {"ux": 0.0, "uy": 0.0, "rz": 0.0},
            2: {"ux": 0.0, "uy": 0.0, "rz": 0.0},
        },
        "member_end_forces": {
            1: forces
            or {
                "node_i": {"nx": 10.0, "vy": 5.0, "mz": 2.0},
                "node_j": {"nx": -10.0, "vy": -5.0, "mz": -2.0},
            }
        },
    }


def test_static_plot_functions_return_figure_and_axes():
    result = _static_result()

    for plot_func in (
        plot_geometry,
        plot_deformed_shape,
        plot_axial_force_diagram,
        plot_shear_force_diagram,
        plot_bending_moment_diagram,
    ):
        fig, ax = plot_func(result)
        assert isinstance(fig, Figure)
        assert isinstance(ax, Axes)
        plt.close(fig)


def test_static_plot_functions_accept_existing_axes():
    result = _static_result()

    fig, ax = plt.subplots()
    returned_fig, returned_ax = plot_geometry(result, ax=ax)

    assert returned_fig is fig
    assert returned_ax is ax
    plt.close(fig)


def test_deformed_shape_auto_scale_maps_small_displacement_to_visible_size():
    nodes = {
        1: {"x": 0.0, "y": 0.0},
        2: {"x": 0.0, "y": 15.0},
    }
    displacements = {
        1: {"ux": 0.0, "uy": 0.0},
        2: {"ux": 2.3e-3, "uy": 0.0},
    }

    scale = compute_deformed_shape_auto_scale(nodes, displacements)

    assert scale == pytest.approx(0.10 * 15.0 / 2.3e-3)
    assert 100.0 < scale < 1000.0


def test_deformed_shape_auto_scale_handles_zero_displacement():
    nodes = {1: {"x": 0.0, "y": 0.0}, 2: {"x": 5.0, "y": 0.0}}
    displacements = {
        1: {"ux": 0.0, "uy": 0.0},
        2: {"ux": 0.0, "uy": 0.0},
    }

    assert compute_deformed_shape_auto_scale(nodes, displacements) == pytest.approx(1.0)


def test_deformed_shape_explicit_scale_is_respected():
    result = _diagram_result()
    result["displacements"][2]["ux"] = 0.01

    fig, ax = plot_deformed_shape(result, scale=500)

    deformed_line = ax.lines[-1]
    assert deformed_line.get_xdata()[-1] == pytest.approx(10.0)
    assert ax.get_title() == "Deformed Shape (scale=500)"
    plt.close(fig)


def test_deformed_shape_auto_plot_returns_figure_and_axes():
    result = _diagram_result()
    result["displacements"][2]["ux"] = 0.01

    fig, ax = plot_deformed_shape(result, scale="auto")

    assert isinstance(fig, Figure)
    assert isinstance(ax, Axes)
    assert "auto scale=" in ax.get_title()
    plt.close(fig)


def test_static_plot_figures_can_be_saved(tmp_path):
    result = _static_result()
    plot_cases = [
        ("geometry.png", plot_geometry, {}),
        ("deformed_shape.png", plot_deformed_shape, {"scale": 1.0}),
        ("axial_force.png", plot_axial_force_diagram, {"scale": 1.0}),
        ("shear_force.png", plot_shear_force_diagram, {"scale": 1.0}),
        ("bending_moment.png", plot_bending_moment_diagram, {"scale": 1.0}),
    ]

    for filename, plot_func, kwargs in plot_cases:
        fig, _ = plot_func(result, **kwargs)
        output_path = tmp_path / filename
        fig.savefig(output_path)
        plt.close(fig)

        assert output_path.exists()
        assert output_path.stat().st_size > 0


def test_udl_shear_and_bending_diagram_use_multiple_station_values():
    result = _diagram_result(member_loads=[{"type": "udl", "direction": "local_y", "w": -2.0}])

    shear = build_structural_force_diagram_coordinates(result, 1, "V", scale=0.1, n_stations=6)
    moment = build_structural_force_diagram_coordinates(result, 1, "M", scale=0.1, n_stations=6)

    assert len(shear["values"]) == 6
    assert len(set(round(value, 8) for value in shear["values"])) > 1
    second_differences = [
        moment["values"][i + 2] - 2.0 * moment["values"][i + 1] + moment["values"][i]
        for i in range(len(moment["values"]) - 2)
    ]
    assert any(abs(value) > 1.0e-8 for value in second_differences)


def test_inclined_member_diagram_offset_follows_local_normal():
    result = _diagram_result("inclined")
    coords = build_structural_force_diagram_coordinates(result, 1, "N", scale=0.1, n_stations=3)
    idx = 1
    offset = (
        coords["diagram_x"][idx] - coords["baseline_x"][idx],
        coords["diagram_y"][idx] - coords["baseline_y"][idx],
    )
    tangent = coords["tangent"]

    assert offset[0] != pytest.approx(0.0)
    assert offset[1] != pytest.approx(0.0)
    assert offset[0] * tangent[0] + offset[1] * tangent[1] == pytest.approx(0.0, abs=1.0e-12)


def test_vertical_member_diagram_has_no_divide_by_zero_and_offsets_horizontally():
    result = _diagram_result("vertical")
    coords = build_structural_force_diagram_coordinates(result, 1, "V", scale=0.1, n_stations=3)
    idx = 1

    assert coords["baseline_x"][idx] == pytest.approx(0.0)
    assert coords["diagram_x"][idx] != pytest.approx(coords["baseline_x"][idx])


def test_zero_force_diagram_plots_baseline_without_crashing():
    zero_forces = {
        "node_i": {"nx": 0.0, "vy": 0.0, "mz": 0.0},
        "node_j": {"nx": 0.0, "vy": 0.0, "mz": 0.0},
    }
    result = _diagram_result(forces=zero_forces)

    fig, ax = plot_bending_moment_diagram(result)

    assert isinstance(fig, Figure)
    assert isinstance(ax, Axes)
    assert len(ax.lines) >= 1
    plt.close(fig)


def test_compute_force_diagram_scale_maps_max_value_to_target_ordinate():
    values = [0.0, 10.0, -20.0]

    scale = compute_force_diagram_scale(values, model_extent=10.0, auto_scale_fraction=0.12)

    assert max(abs(value * scale) for value in values) == pytest.approx(1.2)


def test_compute_force_diagram_ordinates_maps_max_value_to_target_ordinate():
    ordinates = compute_force_diagram_ordinates([0.0, 10.0, -20.0], model_extent=10.0, auto_fraction=0.12)

    assert max(abs(value) for value in ordinates) == pytest.approx(1.2)


def test_compute_force_diagram_ordinates_respects_user_scale():
    ordinates = compute_force_diagram_ordinates([0.0, 10.0, -20.0], model_extent=10.0, auto_fraction=0.12, user_scale=2.0)

    assert max(abs(value) for value in ordinates) == pytest.approx(2.4)


def test_compute_force_diagram_ordinates_handles_zero_values():
    ordinates = compute_force_diagram_ordinates([0.0, 0.0], model_extent=10.0)

    assert ordinates == [0.0, 0.0]


def test_compute_force_diagram_scale_handles_zero_values_without_division_by_zero():
    scale = compute_force_diagram_scale([0.0, 0.0], model_extent=10.0)

    assert scale == pytest.approx(0.0)


def test_compute_force_diagram_scale_uses_safe_extent_fallback_and_user_scale():
    values = [2.0]

    base = compute_force_diagram_scale(values, model_extent=0.0, auto_scale_fraction=0.12)
    doubled = compute_force_diagram_scale(values, model_extent=0.0, auto_scale_fraction=0.12, user_scale_factor=2.0)

    assert abs(values[0] * base) == pytest.approx(0.12)
    assert abs(values[0] * doubled) == pytest.approx(0.24)


def test_force_diagram_quantities_are_scaled_independently():
    n_scale = compute_force_diagram_scale([100.0], model_extent=10.0, auto_scale_fraction=0.12)
    v_scale = compute_force_diagram_scale([10.0], model_extent=10.0, auto_scale_fraction=0.12)
    m_scale = compute_force_diagram_scale([1000.0], model_extent=10.0, auto_scale_fraction=0.12)

    assert abs(100.0 * n_scale) == pytest.approx(1.2)
    assert abs(10.0 * v_scale) == pytest.approx(1.2)
    assert abs(1000.0 * m_scale) == pytest.approx(1.2)


def test_basic_udl_beam_bending_plot_limits_include_drawn_lines():
    data, _masses = load_text_model(ROOT / "inputs" / "examples" / "basic_simply_supported_beam.txt")
    result = run_static_analysis(data)

    fig, ax = plot_bending_moment_diagram(result)

    _assert_lines_inside_axis_limits(ax)
    assert "max |M|" in ax.get_title()
    plt.close(fig)


def test_member_point_load_shear_plot_limits_include_drawn_lines():
    data, _masses = load_text_model(ROOT / "inputs" / "examples" / "member_load_point_frame.txt")
    result = run_static_analysis(data)

    fig, ax = plot_shear_force_diagram(result)

    _assert_lines_inside_axis_limits(ax)
    assert "max |V|" in ax.get_title()
    assert "1e-06" not in ax.get_title()
    plt.close(fig)


def test_member_point_load_zero_axial_plot_has_readable_axis_limits():
    data, _masses = load_text_model(ROOT / "inputs" / "examples" / "member_load_point_frame.txt")
    result = run_static_analysis(data)

    fig, ax = plot_axial_force_diagram(result)
    y0, y1 = ax.get_ylim()

    assert "max |N| = 0.000e+00" in ax.get_title()
    assert "1e-06" not in ax.get_title()
    assert y1 - y0 >= 2.0
    _assert_lines_inside_axis_limits(ax)
    plt.close(fig)


def test_generated_frame_force_diagrams_plot_without_exception():
    data = json.loads((ROOT / "inputs" / "generated" / "model_a_5story_unbraced.json").read_text())
    result = run_static_analysis(data)

    for plot_func in (plot_axial_force_diagram, plot_shear_force_diagram, plot_bending_moment_diagram):
        fig, ax = plot_func(result)
        _assert_lines_inside_axis_limits(ax)
        plt.close(fig)


def _assert_lines_inside_axis_limits(ax):
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    tolerance = 1.0e-9
    for line in ax.lines:
        xs = line.get_xdata()
        ys = line.get_ydata()
        assert min(xs) >= x0 - tolerance
        assert max(xs) <= x1 + tolerance
        assert min(ys) >= y0 - tolerance
        assert max(ys) <= y1 + tolerance
