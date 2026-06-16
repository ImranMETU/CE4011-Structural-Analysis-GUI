"""Compare generated 10-story unbraced and braced frame models."""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

for path in (SRC_ROOT, PROJECT_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from postprocessing.comparison_results import compare_two_models, compute_model_summary  # noqa: E402
from visualization.comparison_plots import (  # noqa: E402
    plot_fundamental_frequency_comparison,
    plot_fundamental_period_comparison,
    plot_max_story_drift_comparison,
    plot_roof_displacement_comparison,
    plot_story_drift_profile_comparison,
)


GENERATED = PROJECT_ROOT / "inputs" / "generated"
UNBRACED_MODEL = GENERATED / "model_b_10story_unbraced.json"
BRACED_MODEL = GENERATED / "model_c_10story_braced.json"
UNBRACED_MASSES = GENERATED / "model_b_10story_unbraced_masses.json"
BRACED_MASSES = GENERATED / "model_c_10story_braced_masses.json"
OUTPUT_DIR = PROJECT_ROOT / "results" / "comparisons"


def main() -> int:
    missing = [path for path in (UNBRACED_MODEL, BRACED_MODEL) if not path.exists()]
    if missing:
        print("Missing generated proposal model files:")
        for path in missing:
            print(f"  {path}")
        print("Run: C:\\Users\\Imran\\anaconda3\\envs\\CE4011\\python.exe scripts\\generate_proposal_models.py")
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    unbraced = compute_model_summary("unbraced", UNBRACED_MODEL, UNBRACED_MASSES if UNBRACED_MASSES.exists() else None)
    braced = compute_model_summary("braced", BRACED_MODEL, BRACED_MASSES if BRACED_MASSES.exists() else None)
    comparison = compare_two_models(unbraced, braced)

    _write_summary_csv(OUTPUT_DIR / "braced_unbraced_summary.csv", comparison)
    _write_plots(comparison)
    _print_summary(comparison)
    return 0


def _write_summary_csv(path: Path, comparison: dict[str, Any]) -> None:
    rows = [
        ("node_count", "node_count"),
        ("element_count", "element_count"),
        ("frame_element_count", "frame_element_count"),
        ("truss_element_count", "truss_element_count"),
        ("active_dofs", "active_dofs"),
        ("roof_displacement_ux", "roof_displacement_ux"),
        ("max_story_drift", "max_story_drift"),
        ("max_drift_ratio", "max_drift_ratio"),
        ("f1_Hz", "f1_Hz"),
        ("T1_s", "T1_s"),
        ("mode_1_effective_mass_ratio", "mode_1_effective_mass_ratio"),
    ]
    metric_rows = [
        "roof_displacement_reduction_percent",
        "max_story_drift_reduction_percent",
        "max_drift_ratio_reduction_percent",
        "fundamental_frequency_increase_percent",
        "fundamental_period_reduction_percent",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["quantity", "unbraced", "braced", "comparison"])
        for label, key in rows:
            writer.writerow([label, _fmt(comparison["unbraced"].get(key)), _fmt(comparison["braced"].get(key)), ""])
        for key in metric_rows:
            writer.writerow([key, "", "", _fmt(comparison["metrics"].get(key))])
        for warning in comparison.get("warnings", []):
            writer.writerow(["warning", "", "", warning])


def _write_plots(comparison: dict[str, Any]) -> None:
    plot_specs = [
        ("roof_displacement_comparison.png", plot_roof_displacement_comparison, (comparison,)),
        ("max_story_drift_comparison.png", plot_max_story_drift_comparison, (comparison,)),
        ("fundamental_frequency_comparison.png", plot_fundamental_frequency_comparison, (comparison,)),
        ("fundamental_period_comparison.png", plot_fundamental_period_comparison, (comparison,)),
        (
            "story_drift_profile_comparison.png",
            plot_story_drift_profile_comparison,
            (comparison["unbraced"]["drift_result"], comparison["braced"]["drift_result"]),
        ),
    ]
    for filename, plot_func, args in plot_specs:
        fig, _ax = plot_func(*args)
        fig.tight_layout()
        fig.savefig(OUTPUT_DIR / filename, dpi=150)
        plt.close(fig)


def _print_summary(comparison: dict[str, Any]) -> None:
    u = comparison["unbraced"]
    b = comparison["braced"]
    m = comparison["metrics"]
    print("Braced vs unbraced comparison")
    print("-" * 72)
    print(f"Unbraced roof ux: {u['roof_displacement_ux']:.6e}")
    print(f"Braced roof ux:   {b['roof_displacement_ux']:.6e}")
    print(f"Roof reduction:   {_fmt(m['roof_displacement_reduction_percent'])}%")
    print(f"Unbraced max drift: {u['max_story_drift']:.6e}")
    print(f"Braced max drift:   {b['max_story_drift']:.6e}")
    print(f"Drift reduction:    {_fmt(m['max_story_drift_reduction_percent'])}%")
    print(f"Unbraced f1: {u['f1_Hz']:.6e} Hz")
    print(f"Braced f1:   {b['f1_Hz']:.6e} Hz")
    print(f"f1 increase: {_fmt(m['fundamental_frequency_increase_percent'])}%")
    if comparison.get("warnings"):
        print("Warnings:")
        for warning in comparison["warnings"]:
            print(f"  - {warning}")
    print(f"Output directory: {OUTPUT_DIR}")


def _fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return f"{float(value):.6e}"
    return str(value)


if __name__ == "__main__":
    raise SystemExit(main())
