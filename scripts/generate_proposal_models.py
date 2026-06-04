"""Generate proposal frame models for CE4011 final project studies."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

for path in (SRC_ROOT, PROJECT_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from generators.frame_generator import generate_floor_mass_mapping, generate_frame_model  # noqa: E402
from model.structure import Structure  # noqa: E402
from postprocessing.static_results import run_static_analysis  # noqa: E402


MODEL_SPECS = [
    ("model_a_5story_unbraced", {"n_stories": 5, "n_bays": 1, "braced": False}),
    ("model_b_10story_unbraced", {"n_stories": 10, "n_bays": 2, "braced": False}),
    ("model_c_10story_braced", {"n_stories": 10, "n_bays": 2, "braced": True}),
]


def main() -> None:
    output_dir = PROJECT_ROOT / "inputs" / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Generating proposal frame models")
    print("-" * 88)
    print(f"{'Model':32} {'Nodes':>6} {'Elements':>8} {'Active DOF':>10} {'Static':>10}")
    print("-" * 88)

    for name, spec in MODEL_SPECS:
        data = generate_frame_model(
            story_height=3.0,
            bay_width=6.0,
            lateral_load_per_floor=10000.0,
            **spec,
        )
        masses = generate_floor_mass_mapping(data, floor_mass=100000.0)

        model_path = output_dir / f"{name}.json"
        mass_path = output_dir / f"{name}_masses.json"
        _write_json(model_path, data)
        _write_json(mass_path, masses)

        smoke = _static_smoke(data)
        print(
            f"{name:32} {len(data['nodes']):6d} {len(data['elements']):8d} "
            f"{smoke['active_dofs']:10d} {smoke['status']:>10}"
        )

    print("-" * 88)
    print(f"Saved generated models to: {output_dir}")


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _static_smoke(data: dict[str, Any]) -> dict[str, Any]:
    structure = Structure.from_dict(data)
    try:
        run_static_analysis(data)
    except Exception as exc:
        return {"active_dofs": structure.n_active_dofs, "status": f"FAIL: {type(exc).__name__}"}
    return {"active_dofs": structure.n_active_dofs, "status": "PASS"}


if __name__ == "__main__":
    main()
