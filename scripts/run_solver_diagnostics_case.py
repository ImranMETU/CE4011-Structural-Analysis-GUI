from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
IO_ROOT = SRC_ROOT / "io"
for path in (SRC_ROOT, IO_ROOT, ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from gui.frame_generator_dialog import GENERATED_DIR, generate_proposal_default_models  # noqa: E402
from gui.static_app import load_model_data  # noqa: E402
from model.structure import Structure  # noqa: E402
from postprocessing.solver_diagnostics import (  # noqa: E402
    compute_solver_diagnostics,
    format_solver_diagnostics_rows,
)


def main() -> None:
    model_path = _model_path()
    data = load_model_data(model_path)
    structure = Structure.from_dict(data)
    diagnostics = compute_solver_diagnostics(structure)
    headers, rows = format_solver_diagnostics_rows(diagnostics)

    output_dir = ROOT / "results" / "solver_diagnostics"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "solver_diagnostics_summary.csv"
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

    print(f"Solver diagnostics for {model_path.name}")
    for quantity, value in rows:
        print(f"{quantity}: {value}")
    print(f"CSV written to {output_path}")


def _model_path() -> Path:
    path = GENERATED_DIR / "model_b_10story_unbraced.json"
    if path.exists():
        return path
    generate_proposal_default_models()
    if not path.exists():
        raise FileNotFoundError(f"Could not find or generate {path}")
    return path


if __name__ == "__main__":
    main()
