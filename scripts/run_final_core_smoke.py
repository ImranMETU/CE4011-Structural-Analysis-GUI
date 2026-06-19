"""Final-submission core smoke test for CE4011 static/modal GUI workflow.

This script intentionally covers only the stable core scope: generated model
loading, static results, structural force diagrams, modal frequencies/mode
shape, participation data, and drift/roof post-processing.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

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

from analysis.modal_solver import solve_modal_analysis  # noqa: E402
from gui.static_app import _load_companion_masses, load_model_data  # noqa: E402
from model.structure import Structure  # noqa: E402
from postprocessing.drift_results import compute_roof_displacement, compute_story_drift  # noqa: E402
from postprocessing.modal_results import package_modal_results  # noqa: E402
from postprocessing.static_results import collect_static_results  # noqa: E402
from visualization.drift_plots import plot_roof_displacement_marker, plot_story_drift_profile  # noqa: E402
from visualization.model_view import plot_model_view  # noqa: E402
from visualization.modal_plots import plot_modal_frequencies, plot_mode_shape  # noqa: E402
from visualization.static_plots import (  # noqa: E402
    plot_axial_force_diagram,
    plot_bending_moment_diagram,
    plot_deformed_shape,
    plot_shear_force_diagram,
)


CASE_PATH = PROJECT_ROOT / "inputs" / "generated" / "model_a_5story_unbraced.json"
OUTPUT_DIR = PROJECT_ROOT / "results" / "final_core_smoke"


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    checks: list[tuple[str, bool, str]] = []

    try:
        data = load_model_data(CASE_PATH)
        structure = Structure.from_dict(data)
        static_result = collect_static_results(structure, solve=True)
        checks.append(("load generated model", True, CASE_PATH.name))
    except Exception as exc:
        _print_summary([("load generated model", False, f"{type(exc).__name__}: {exc}")])
        return 1

    checks.extend(
        [
            ("static nodal displacements", bool(static_result.get("displacements")), ""),
            ("static support reactions", bool(static_result.get("reactions")), ""),
            ("static member-end forces", bool(static_result.get("member_end_forces")), ""),
        ]
    )

    _save_plot("model_view.png", lambda: plot_model_view(data, options={"show_legend": True}))
    _save_plot("deformed_shape.png", lambda: plot_deformed_shape(static_result, scale=1.0))
    _save_plot("axial_force_diagram.png", lambda: plot_axial_force_diagram(static_result))
    _save_plot("shear_force_diagram.png", lambda: plot_shear_force_diagram(static_result))
    _save_plot("bending_moment_diagram.png", lambda: plot_bending_moment_diagram(static_result))
    checks.append(("static/core plots saved", True, str(OUTPUT_DIR)))

    try:
        masses = _load_companion_masses(CASE_PATH)
        if not masses:
            raise ValueError(f"No companion modal mass mapping found for {CASE_PATH.name}.")
        modal_structure = Structure.from_dict(data)
        raw_modal = solve_modal_analysis(modal_structure, masses, n_modes=4)
        modal_result = package_modal_results(raw_modal, structure=modal_structure)
        checks.extend(
            [
                ("modal frequencies", len(modal_result.get("frequencies_hz", [])) > 0, ""),
                ("modal periods", len(modal_result.get("periods", [])) > 0, ""),
                ("mode-shape data", bool(modal_result.get("node_mode_shapes")), ""),
                ("modal participation", bool(modal_result.get("participation")), ""),
            ]
        )
        _save_plot("mode_1.png", lambda: plot_mode_shape(modal_result, mode_index=0, scale=1.0))
        _save_plot("modal_frequencies.png", lambda: plot_modal_frequencies(modal_result))
        checks.append(("modal plots saved", True, str(OUTPUT_DIR)))
    except Exception as exc:
        checks.append(("modal workflow", False, f"{type(exc).__name__}: {exc}"))

    try:
        drift = compute_story_drift(static_result, direction="ux", method="mean")
        roof = compute_roof_displacement(static_result, direction="ux", method="max_abs")
        checks.extend(
            [
                ("story drift rows", bool(drift.get("stories")), ""),
                ("roof displacement", "roof_displacement" in roof, ""),
            ]
        )
        _save_plot("story_drift_profile.png", lambda: plot_story_drift_profile(drift))
        _save_plot("roof_displacement.png", lambda: plot_roof_displacement_marker(roof))
    except Exception as exc:
        checks.append(("drift/roof postprocessing", False, f"{type(exc).__name__}: {exc}"))

    _print_summary(checks)
    return 0 if all(status for _name, status, _message in checks) else 1


def _save_plot(filename: str, plotter: Callable):
    fig, _ax = plotter()
    fig.savefig(OUTPUT_DIR / filename, dpi=150)
    plt.close(fig)


def _print_summary(checks: list[tuple[str, bool, str]]) -> None:
    print("Final core smoke summary")
    print("-" * 88)
    print(f"{'Check':36} {'Status':8} Message")
    print("-" * 88)
    for name, status, message in checks:
        print(f"{name:36} {'PASS' if status else 'FAIL':8} {message}")
    print("-" * 88)
    print(f"Output directory: {OUTPUT_DIR}")


if __name__ == "__main__":
    raise SystemExit(main())
