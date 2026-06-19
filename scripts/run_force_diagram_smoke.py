"""Smoke script for geometry-attached static force diagrams."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
IO_ROOT = SRC_ROOT / "io"
for path in (SRC_ROOT, IO_ROOT, ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from postprocessing.static_results import run_static_analysis  # noqa: E402
from text_loader import load_text_model  # noqa: E402
from visualization.static_plots import (  # noqa: E402
    build_structural_force_diagram_coordinates,
    plot_axial_force_diagram,
    plot_bending_moment_diagram,
    plot_shear_force_diagram,
)


def main() -> None:
    input_path = ROOT / "inputs" / "examples" / "basic_cantilever_beam.txt"
    if not input_path.exists():
        raise FileNotFoundError(f"Example input not found: {input_path}")
    output_dir = ROOT / "results" / "force_diagram_smoke"
    output_dir.mkdir(parents=True, exist_ok=True)

    data, _masses = load_text_model(input_path)
    result = run_static_analysis(data)
    for filename, plot_func in (
        ("axial_force_diagram.png", plot_axial_force_diagram),
        ("shear_force_diagram.png", plot_shear_force_diagram),
        ("bending_moment_diagram.png", plot_bending_moment_diagram),
    ):
        fig, _ax = plot_func(result)
        fig.savefig(output_dir / filename, dpi=150)
        plt.close(fig)

    axial = build_structural_force_diagram_coordinates(result, 1, "N", scale=1.0)
    shear = build_structural_force_diagram_coordinates(result, 1, "V", scale=1.0)
    moment = build_structural_force_diagram_coordinates(result, 1, "M", scale=1.0)
    print(f"Case: {input_path.name}")
    print(f"Max |N|: {axial['max_abs_value']:.6e}")
    print(f"Max |V|: {shear['max_abs_value']:.6e}")
    print(f"Max |M|: {moment['max_abs_value']:.6e}")
    print(f"BMD fixed-end moment: {moment['values'][0]:.6e}")
    print(f"BMD free-end moment: {moment['values'][-1]:.6e}")
    print(f"Force diagram smoke plots written to {output_dir}")


if __name__ == "__main__":
    main()
