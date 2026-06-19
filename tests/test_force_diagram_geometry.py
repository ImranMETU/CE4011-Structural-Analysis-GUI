from __future__ import annotations

import sys
from pathlib import Path

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

from visualization.static_plots import (  # noqa: E402
    build_structural_force_diagram_coordinates,
    plot_axial_force_diagram,
    plot_bending_moment_diagram,
    plot_shear_force_diagram,
)
from visualization.diagram_conventions import ForceDiagramConvention  # noqa: E402
from gui.result_tables import format_element_station_force_rows  # noqa: E402
from postprocessing.static_results import run_static_analysis  # noqa: E402
from text_loader import load_text_model  # noqa: E402


def _one_element_result(angle_case: str = "horizontal", member_loads=None, forces=None):
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


def test_horizontal_udl_bending_diagram_uses_global_station_coordinates():
    result = _one_element_result(member_loads=[{"type": "udl", "direction": "local_y", "w": -2.0}])

    coords = build_structural_force_diagram_coordinates(result, 1, "M", scale=0.1, n_stations=9)
    fig, ax = plot_bending_moment_diagram(result)

    assert isinstance(fig, Figure)
    assert isinstance(ax, Axes)
    assert len(coords["diagram_x"]) == 9
    assert len(coords["diagram_y"]) == 9
    assert len(set(round(value, 8) for value in coords["diagram_y"])) > 2
    plt.close(fig)


def test_inclined_member_diagram_offsets_perpendicular_to_member():
    result = _one_element_result("inclined")

    coords = build_structural_force_diagram_coordinates(result, 1, "N", scale=0.1, n_stations=3)
    idx = 1
    offset = (
        coords["diagram_x"][idx] - coords["baseline_x"][idx],
        coords["diagram_y"][idx] - coords["baseline_y"][idx],
    )
    tangent = coords["tangent"]

    assert offset[0] * tangent[0] + offset[1] * tangent[1] == pytest.approx(0.0, abs=1.0e-12)


def test_vertical_member_force_diagram_has_no_divide_by_zero():
    result = _one_element_result("vertical")

    coords = build_structural_force_diagram_coordinates(result, 1, "V", scale=0.1, n_stations=3)
    fig, ax = plot_shear_force_diagram(result)

    assert coords["baseline_x"][1] == pytest.approx(0.0)
    assert coords["diagram_x"][1] != pytest.approx(coords["baseline_x"][1])
    assert isinstance(fig, Figure)
    assert isinstance(ax, Axes)
    plt.close(fig)


def test_zero_force_diagrams_do_not_crash_under_agg_backend():
    zero = {
        "node_i": {"nx": 0.0, "vy": 0.0, "mz": 0.0},
        "node_j": {"nx": 0.0, "vy": 0.0, "mz": 0.0},
    }
    result = _one_element_result(forces=zero)

    for plot_func in (plot_axial_force_diagram, plot_shear_force_diagram, plot_bending_moment_diagram):
        fig, ax = plot_func(result)
        assert isinstance(fig, Figure)
        assert isinstance(ax, Axes)
        assert len(ax.lines) >= 1
        plt.close(fig)


def test_cantilever_tip_load_bmd_free_end_returns_to_member_baseline():
    data, _masses = load_text_model(ROOT / "inputs" / "examples" / "basic_cantilever_beam.txt")
    result = run_static_analysis(data)

    coords = build_structural_force_diagram_coordinates(result, 1, "M", scale=1.0, n_stations=11)

    assert coords["values"][0] == pytest.approx(50000.0)
    assert coords["values"][-1] == pytest.approx(0.0, abs=1.0e-8)
    assert coords["diagram_x"][-1] == pytest.approx(coords["baseline_x"][-1])
    assert coords["diagram_y"][-1] == pytest.approx(coords["baseline_y"][-1], abs=1.0e-8)


def test_opposite_moment_display_conventions_mirror_coordinates_only():
    data, _masses = load_text_model(ROOT / "inputs" / "examples" / "basic_cantilever_beam.txt")
    result = run_static_analysis(data)
    tension = ForceDiagramConvention("Custom", "tension", "top", "top")
    compression = ForceDiagramConvention("Custom", "compression", "top", "top")

    tension_coords = build_structural_force_diagram_coordinates(
        result, 1, "M", scale=1.0, n_stations=7, convention=tension
    )
    compression_coords = build_structural_force_diagram_coordinates(
        result, 1, "M", scale=1.0, n_stations=7, convention=compression
    )

    assert tension_coords["values"] == pytest.approx(compression_coords["values"])
    for base, tension_y, compression_y in zip(
        tension_coords["baseline_y"],
        tension_coords["diagram_y"],
        compression_coords["diagram_y"],
    ):
        assert tension_y - base == pytest.approx(-(compression_y - base))


def test_display_convention_does_not_change_station_table_values():
    data, _masses = load_text_model(ROOT / "inputs" / "examples" / "basic_cantilever_beam.txt")
    result = run_static_analysis(data)

    headers_before, rows_before = format_element_station_force_rows(result, n_stations=7)
    fig, _ax = plot_bending_moment_diagram(
        result,
        convention=ForceDiagramConvention("Custom", "compression", "top", "top"),
    )
    headers_after, rows_after = format_element_station_force_rows(result, n_stations=7)

    assert headers_after == headers_before
    assert rows_after == rows_before
    plt.close(fig)
