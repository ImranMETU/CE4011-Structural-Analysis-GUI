"""Smoke script for station-based static element postprocessing."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
IO_ROOT = SRC_ROOT / "io"
for path in (SRC_ROOT, IO_ROOT, ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from postprocessing.element_station_results import all_frame_station_results  # noqa: E402
from postprocessing.static_results import run_static_analysis  # noqa: E402
from text_loader import load_text_model  # noqa: E402
from visualization.element_station_plots import (  # noqa: E402
    plot_deformed_slope_profile,
    plot_hermite_deformed_shape,
)


def main() -> None:
    result_dir = ROOT / "results" / "station_postprocessing"
    result_dir.mkdir(parents=True, exist_ok=True)

    model_path = ROOT / "inputs" / "examples" / "member_load_udl_frame.txt"
    if model_path.exists():
        data, _masses = load_text_model(model_path)
    else:
        data = _internal_udl_case()

    result = run_static_analysis(data)
    station_rows = all_frame_station_results(result, n_stations=21)

    fig, _ax = plot_hermite_deformed_shape(result, scale=50.0)
    fig.savefig(result_dir / "hermite_deformed_shape.png", dpi=160)

    fig, _ax = plot_deformed_slope_profile(result, n_stations=21)
    fig.savefig(result_dir / "deformed_slope_profile.png", dpi=160)

    force_headers = ["element", "type", "station", "xi", "x_local", "global_x", "global_y", "N", "V", "M"]
    slope_headers = ["element", "station", "xi", "x_local", "global_x", "global_y", "u_local", "v_local", "slope"]
    _write_csv(result_dir / "element_station_forces.csv", force_headers, station_rows)
    _write_csv(result_dir / "deformed_slopes.csv", slope_headers, station_rows)

    print(f"Wrote station postprocessing results to {result_dir}")


def _write_csv(path: Path, headers: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _internal_udl_case() -> dict:
    return {
        "nodes": [
            {"id": 1, "x": 0.0, "y": 0.0, "restraints": {"ux": True, "uy": True, "rz": True}},
            {"id": 2, "x": 5.0, "y": 0.0, "restraints": {"ux": False, "uy": False, "rz": False}},
        ],
        "materials": [{"id": "steel", "E": 200_000_000.0}],
        "sections": [{"id": "beam", "A": 0.02, "I": 8.0e-5}],
        "elements": [
            {
                "id": 1,
                "type": "frame",
                "node_i": 1,
                "node_j": 2,
                "material": "steel",
                "section": "beam",
                "member_loads": [{"type": "udl", "direction": "local_y", "w": -1000.0}],
            }
        ],
        "nodal_loads": [],
    }


if __name__ == "__main__":
    main()
