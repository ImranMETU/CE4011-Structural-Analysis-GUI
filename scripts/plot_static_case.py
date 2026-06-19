"""Smoke script for generating static post-processing plots."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
IO_ROOT = SRC_ROOT / "io"

for path in (SRC_ROOT, IO_ROOT, PROJECT_ROOT):
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


def main() -> None:
    case_path = PROJECT_ROOT / "inputs" / "regression" / "xml" / "regression_thermal_combined_frame.xml"
    output_dir = PROJECT_ROOT / "results" / "plots"
    output_dir.mkdir(parents=True, exist_ok=True)

    data = load_structure_from_xml(case_path)
    result = run_static_analysis(data)

    plots = [
        ("geometry.png", plot_geometry, {}),
        ("deformed_shape.png", plot_deformed_shape, {"scale": 1.0}),
        ("axial_force.png", plot_axial_force_diagram, {"scale": 1.0}),
        ("shear_force.png", plot_shear_force_diagram, {"scale": 1.0}),
        ("bending_moment.png", plot_bending_moment_diagram, {"scale": 1.0}),
    ]

    for filename, plot_func, kwargs in plots:
        fig, _ = plot_func(result, **kwargs)
        fig.tight_layout()
        fig.savefig(output_dir / filename, dpi=150)
        plt.close(fig)

    print(f"Saved static plots to: {output_dir}")


if __name__ == "__main__":
    main()
