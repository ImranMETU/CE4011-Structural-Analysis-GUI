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
IO_ROOT = SRC_ROOT / "io"

for path in (SRC_ROOT, IO_ROOT, ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from postprocessing.static_results import run_static_analysis  # noqa: E402
from visualization.static_plots import (  # noqa: E402
    plot_axial_force_diagram,
    plot_bending_moment_diagram,
    plot_deformed_shape,
    plot_geometry,
    plot_shear_force_diagram,
)
from xml_loader import load_structure_from_xml  # noqa: E402


def _static_result():
    case_path = ROOT / "inputs" / "regression" / "xml" / "regression_thermal_combined_frame.xml"
    return run_static_analysis(load_structure_from_xml(case_path))


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


def test_static_plot_figures_can_be_saved(tmp_path):
    result = _static_result()
    plot_cases = [
        ("geometry.png", plot_geometry, {}),
        ("deformed_shape.png", plot_deformed_shape, {"scale": 1.0}),
        ("axial_force.png", plot_axial_force_diagram, {"scale": 1.0e-6}),
        ("shear_force.png", plot_shear_force_diagram, {"scale": 1.0e-6}),
        ("bending_moment.png", plot_bending_moment_diagram, {"scale": 1.0e-6}),
    ]

    for filename, plot_func, kwargs in plot_cases:
        fig, _ = plot_func(result, **kwargs)
        output_path = tmp_path / filename
        fig.savefig(output_path)
        plt.close(fig)

        assert output_path.exists()
        assert output_path.stat().st_size > 0
