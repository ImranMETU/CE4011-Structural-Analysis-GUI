from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "src" / "io", ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from postprocessing.static_results import run_static_analysis  # noqa: E402
from visualization.static_plots import plot_bending_moment_diagram, plot_deformed_shape  # noqa: E402


CASES = (
    ("6_2", "CE586_Example_6_2_frame_model_static_mode1.json"),
    ("6_4_6_6", "CE586_Examples_6_4_6_6_frame_model_static_mode1.json"),
)


def main() -> None:
    output_dir = ROOT / "results" / "ce586_static_equivalent"
    output_dir.mkdir(parents=True, exist_ok=True)
    for label, filename in CASES:
        path = ROOT / "inputs" / "examples" / filename
        data = json.loads(path.read_text(encoding="utf-8"))
        result = run_static_analysis(data)
        max_displacement = max(abs(float(value)) for value in result["displacement_vector"])
        reaction_nonzero = any(
            abs(float(value)) > 1.0e-10
            for reaction in result["reactions"].values()
            for value in reaction.values()
        )
        force_nonzero = any(
            abs(float(value)) > 1.0e-10
            for element in result["member_end_forces"].values()
            for end in element.values()
            for value in end.values()
        )
        if max_displacement <= 0.0 or not reaction_nonzero or not force_nonzero:
            raise AssertionError(f"{filename} did not produce a nonzero static response.")
        for suffix, plotter in (("deformed_shape", plot_deformed_shape), ("bmd", plot_bending_moment_diagram)):
            fig, _ax = plotter(result)
            fig.savefig(output_dir / f"{label}_{suffix}.png", dpi=150)
            fig.clf()
        print(
            f"PASS {filename}: max displacement={max_displacement:.6e}, "
            f"nonzero reactions={reaction_nonzero}, nonzero member forces={force_nonzero}"
        )
    print(f"Outputs written to {output_dir}")


if __name__ == "__main__":
    main()
