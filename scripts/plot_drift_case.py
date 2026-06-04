"""Smoke script for static story drift and roof displacement plots."""

from __future__ import annotations

import json
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

from postprocessing.drift_results import (  # noqa: E402
    compute_floor_displacements,
    compute_roof_displacement,
    compute_story_drift,
)
from postprocessing.static_results import run_static_analysis  # noqa: E402
from visualization.drift_plots import (  # noqa: E402
    plot_drift_ratio_profile,
    plot_floor_displacement_profile,
    plot_story_drift_profile,
)


def main() -> None:
    case_path = PROJECT_ROOT / "inputs" / "generated" / "model_b_10story_unbraced.json"
    output_dir = PROJECT_ROOT / "results" / "drift"
    output_dir.mkdir(parents=True, exist_ok=True)

    with case_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    static_result = run_static_analysis(data)
    floor_displacements = compute_floor_displacements(static_result)
    drift = compute_story_drift(static_result)
    roof = compute_roof_displacement(static_result)

    plots = [
        ("story_drift_profile.png", plot_story_drift_profile, drift),
        ("drift_ratio_profile.png", plot_drift_ratio_profile, drift),
        ("floor_displacement_profile.png", plot_floor_displacement_profile, floor_displacements),
    ]
    for filename, plot_func, result in plots:
        fig, _ax = plot_func(result)
        fig.tight_layout()
        fig.savefig(output_dir / filename, dpi=150)
        plt.close(fig)

    print(
        "Roof displacement: "
        f"elevation={roof['roof_elevation']:.6g}, "
        f"value={roof['roof_displacement']:.6e}, "
        f"node={roof['controlling_node_id']}"
    )
    print(f"Saved drift plots to: {output_dir}")


if __name__ == "__main__":
    main()
