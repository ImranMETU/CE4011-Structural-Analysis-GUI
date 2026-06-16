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

from analysis.modal_solver import solve_modal_analysis  # noqa: E402
from analysis.modal_rha import run_modal_rha  # noqa: E402
from ground_motion_loader import load_ground_motion  # noqa: E402
from gui.frame_generator_dialog import GENERATED_DIR, generate_proposal_default_models  # noqa: E402
from gui.static_app import _load_companion_masses, load_model_data  # noqa: E402
from model.structure import Structure  # noqa: E402
from postprocessing.modal_results import package_modal_results  # noqa: E402
from postprocessing.rha_results import (  # noqa: E402
    format_peak_floor_response_rows,
    format_peak_story_drift_rows,
    format_rha_summary_rows,
)
from postprocessing.rha_node_results import compute_node_response_peaks, format_node_response_rows  # noqa: E402
from visualization.rha_node_plots import plot_node_response_history  # noqa: E402
from visualization.rha_plots import (  # noqa: E402
    plot_floor_displacement_histories,
    plot_ground_motion_history,
    plot_modal_coordinate_histories,
    plot_peak_story_drift_envelope,
    plot_roof_displacement_history,
    plot_story_drift_histories,
)


def main() -> None:
    output_dir = ROOT / "results" / "rha"
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = _model_path()
    motion_path = ROOT / "inputs" / "groundmotion" / "DIN95Y01.THF"
    if not motion_path.exists():
        raise FileNotFoundError(f"Ground motion file not found: {motion_path}")

    data = load_model_data(model_path)
    masses = _load_companion_masses(model_path)
    if not masses:
        raise ValueError(f"No companion modal mass file found for {model_path.name}.")

    structure = Structure.from_dict(data)
    modal = solve_modal_analysis(structure, masses, n_modes=4)
    modal_result = package_modal_results(modal, structure)
    ground_motion = load_ground_motion(motion_path, input_unit="cm/s2")
    ground_motion["path"] = str(motion_path)
    rha = run_modal_rha(modal_result, ground_motion, damping_ratio=0.05, num_modes=min(4, len(modal_result["omega"])))

    plot_cases = {
        "ground_motion.png": plot_ground_motion_history,
        "roof_displacement_history.png": plot_roof_displacement_history,
        "floor_displacement_histories.png": plot_floor_displacement_histories,
        "story_drift_histories.png": plot_story_drift_histories,
        "peak_story_drift_envelope.png": plot_peak_story_drift_envelope,
        "modal_coordinate_histories.png": plot_modal_coordinate_histories,
    }
    for filename, plot_func in plot_cases.items():
        fig, _ax = plot_func(rha)
        fig.savefig(output_dir / filename, dpi=150)
        fig.clf()

    with (output_dir / "rha_summary.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        for title, table in (
            ("RHA Summary", format_rha_summary_rows(rha)),
            ("Peak Floor Responses", format_peak_floor_response_rows(rha)),
            ("Peak Story Drifts", format_peak_story_drift_rows(rha)),
            ("Node Peak Responses", format_node_response_rows(compute_node_response_peaks(rha, dofs=("ux",)))),
        ):
            headers, rows = table
            writer.writerow([title])
            writer.writerow(headers)
            writer.writerows(rows)
            writer.writerow([])

    headers, rows = format_node_response_rows(compute_node_response_peaks(rha, dofs=("ux",)))
    with (output_dir / "rha_node_peak_responses.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

    for node_id in list(rha.get("node_displacement_histories", {}))[:2]:
        fig, _ax = plot_node_response_history(rha, int(node_id), dof="ux")
        fig.savefig(output_dir / f"node_{int(node_id)}_ux.png", dpi=150)
        fig.clf()

    print(f"RHA complete for {model_path.name}")
    print(f"Outputs written to {output_dir}")


def _model_path() -> Path:
    path = GENERATED_DIR / "model_a_5story_unbraced.json"
    if path.exists():
        return path
    generate_proposal_default_models()
    if not path.exists():
        raise FileNotFoundError(f"Could not find or generate {path}")
    return path


if __name__ == "__main__":
    main()
