"""Smoke script for generating modal post-processing plots."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

for path in (SRC_ROOT, PROJECT_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from analysis.modal_solver import solve_modal_analysis  # noqa: E402
from model.structure import Structure  # noqa: E402
from postprocessing.modal_results import package_modal_results  # noqa: E402
from visualization.modal_plots import (  # noqa: E402
    plot_modal_frequencies,
    plot_modal_periods,
    plot_mode_shape,
)


def build_smoke_structure() -> Structure:
    """Build a tiny cantilever frame for modal smoke plotting."""
    data = {
        "nodes": [
            {"id": 1, "x": 0.0, "y": 0.0, "restraints": {"ux": True, "uy": True, "rz": True}},
            {"id": 2, "x": 3.0, "y": 0.0, "restraints": {"ux": False, "uy": False, "rz": False}},
        ],
        "materials": [{"id": "steel", "E": 200.0e9}],
        "sections": [{"id": "rect", "A": 0.01, "I": 1.0e-4, "d": 0.3}],
        "elements": [
            {"id": 1, "type": "frame", "node_i": 1, "node_j": 2, "material": "steel", "section": "rect"}
        ],
    }
    return Structure.from_dict(data)


def main() -> None:
    output_dir = PROJECT_ROOT / "results" / "modal_plots"
    output_dir.mkdir(parents=True, exist_ok=True)

    structure = build_smoke_structure()
    modal = solve_modal_analysis(structure, {2: {"ux": 100.0, "uy": 100.0}}, n_modes=2)
    result = package_modal_results(modal, structure)

    plot_cases = [
        ("mode_1.png", plot_mode_shape, {"mode_index": 0, "scale": 0.5}),
        ("frequencies.png", plot_modal_frequencies, {}),
        ("periods.png", plot_modal_periods, {}),
    ]
    if len(result["frequencies_hz"]) > 1:
        plot_cases.insert(1, ("mode_2.png", plot_mode_shape, {"mode_index": 1, "scale": 0.5}))

    for filename, plot_func, kwargs in plot_cases:
        fig, _ = plot_func(result, **kwargs)
        fig.tight_layout()
        fig.savefig(output_dir / filename, dpi=150)
        plt.close(fig)

    print(f"Saved modal plots to: {output_dir}")


if __name__ == "__main__":
    main()
