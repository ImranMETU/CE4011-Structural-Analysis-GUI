"""Smoke script for generating an enhanced model-view plot."""

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

from text_loader import load_text_model  # noqa: E402
from visualization.model_view import plot_model_view  # noqa: E402


def main() -> None:
    case_path = PROJECT_ROOT / "inputs" / "examples" / "a4_thermal_example.txt"
    output_dir = PROJECT_ROOT / "results" / "model_view"
    output_dir.mkdir(parents=True, exist_ok=True)

    data, mass_mapping = load_text_model(case_path)
    fig, _ax = plot_model_view(data, options={"mass_mapping": mass_mapping})
    fig.tight_layout()
    fig.savefig(output_dir / "model_view.png", dpi=150)
    plt.close(fig)

    print(f"Saved model view plot to: {output_dir / 'model_view.png'}")


if __name__ == "__main__":
    main()
