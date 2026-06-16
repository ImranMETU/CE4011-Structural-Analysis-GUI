from __future__ import annotations

import csv
import sys
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
IO_ROOT = SRC_ROOT / "io"
for path in (SRC_ROOT, IO_ROOT, ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from analysis.modal_rsa import run_modal_rsa  # noqa: E402
from analysis.modal_solver import solve_modal_analysis  # noqa: E402
from analysis.response_spectrum_generator import generate_elastic_response_spectrum  # noqa: E402
from ground_motion_loader import load_ground_motion  # noqa: E402
from gui.frame_generator_dialog import GENERATED_DIR, generate_proposal_default_models  # noqa: E402
from gui.result_tables import (  # noqa: E402
    format_rsa_combined_response_rows,
    format_rsa_modal_peak_response_rows,
    format_rsa_modal_peak_story_drift_rows,
)
from gui.static_app import _load_companion_masses, load_model_data  # noqa: E402
from model.structure import Structure  # noqa: E402
from postprocessing.modal_results import package_modal_results  # noqa: E402
from visualization.rsa_plots import (  # noqa: E402
    plot_rsa_combined_roof_response,
    plot_rsa_combined_story_drift_envelope,
    plot_rsa_modal_peak_roof_response,
    plot_rsa_modal_peak_story_drift,
)


def main() -> None:
    output_dir = ROOT / "results" / "rsa"
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
    spectrum = generate_elastic_response_spectrum(
        ground_motion["time"],
        ground_motion["acceleration"],
        np.linspace(0.02, max(5.0, float(np.max(modal_result["periods"])) * 1.5), 250),
        damping_ratio=0.05,
    )
    rsa = run_modal_rsa(modal_result, spectrum, static_or_model_data=data, num_modes=min(4, len(modal_result["omega"])))

    _write_table(output_dir / "rsa_modal_peak_responses.csv", *format_rsa_modal_peak_response_rows(rsa))
    _write_table(output_dir / "rsa_modal_peak_story_drifts.csv", *format_rsa_modal_peak_story_drift_rows(rsa))
    _write_table(output_dir / "rsa_combined_responses.csv", *format_rsa_combined_response_rows(rsa))

    for filename, plot_func in (
        ("rsa_modal_peak_roof_response.png", plot_rsa_modal_peak_roof_response),
        ("rsa_modal_peak_story_drift.png", plot_rsa_modal_peak_story_drift),
        ("rsa_combined_roof_response.png", plot_rsa_combined_roof_response),
        ("rsa_combined_story_drift_envelope.png", plot_rsa_combined_story_drift_envelope),
    ):
        fig, _ax = plot_func(rsa)
        fig.savefig(output_dir / filename, dpi=150)
        fig.clf()

    print(f"RSA complete for {model_path.name}")
    print(f"Outputs written to {output_dir}")


def _write_table(path: Path, headers: list[str], rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)


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
