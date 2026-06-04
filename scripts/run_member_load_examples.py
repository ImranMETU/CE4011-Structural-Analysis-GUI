from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
IO_ROOT = SRC_ROOT / "io"
for path in (SRC_ROOT, IO_ROOT, PROJECT_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from postprocessing.static_results import run_static_analysis  # noqa: E402
from text_loader import load_text_model  # noqa: E402
from visualization.model_view import plot_model_view  # noqa: E402
from visualization.static_plots import plot_bending_moment_diagram  # noqa: E402


EXAMPLES = (
    ("udl", PROJECT_ROOT / "inputs" / "examples" / "member_load_udl_frame.txt"),
    ("point", PROJECT_ROOT / "inputs" / "examples" / "member_load_point_frame.txt"),
)


def main() -> None:
    output_dir = PROJECT_ROOT / "results" / "member_load_examples"
    output_dir.mkdir(parents=True, exist_ok=True)

    for name, path in EXAMPLES:
        data, _masses = load_text_model(path)
        result = run_static_analysis(data)
        disp = result.get("displacement_vector", [])
        disp_norm = sum(float(value) ** 2 for value in disp) ** 0.5

        fig, _ax = plot_model_view(data, options={"show_legend": True})
        fig.savefig(output_dir / f"{name}_model_view.png", dpi=150)
        fig.clf()

        fig, _ax = plot_bending_moment_diagram(result)
        fig.savefig(output_dir / f"{name}_bending_moment.png", dpi=150)
        fig.clf()

        print(f"{name.upper()} example: {path.name}")
        print(f"  Nodes: {len(data['nodes'])}")
        print(f"  Elements: {len(data['elements'])}")
        print(f"  Displacement norm: {disp_norm:.6e}")
        print(f"  Reactions: {result['reactions']}")
        print(f"  Member-end forces: {result['member_end_forces']}")
        print(f"  Plots: {output_dir}")


if __name__ == "__main__":
    main()
