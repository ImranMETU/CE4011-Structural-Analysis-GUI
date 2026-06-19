from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "src" / "io", ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from analysis.modal_solver import solve_modal_analysis  # noqa: E402
from gui.static_app import load_companion_mass_mapping, load_model_data  # noqa: E402
from model.structure import Structure  # noqa: E402
from postprocessing.modal_response_parameters import modal_response_parameters_from_result  # noqa: E402
from postprocessing.modal_results import package_modal_results  # noqa: E402
from postprocessing.modal_static_equivalent_loads import create_static_equivalent_modal_loads  # noqa: E402


CASES = (
    ("CE586_Example_6_2_frame_model.json", "CE586_Example_6_2_frame_model_static_mode1.json"),
    ("CE586_Examples_6_4_6_6_frame_model.json", "CE586_Examples_6_4_6_6_frame_model_static_mode1.json"),
)


def main() -> None:
    examples = ROOT / "inputs" / "examples"
    for source_name, output_name in CASES:
        source = examples / source_name
        output = examples / output_name
        masses = load_companion_mass_mapping(source)
        if not masses:
            raise ValueError(f"No companion modal masses found for {source.name}.")
        model = load_model_data(source)
        structure = Structure.from_dict(model)
        modal = package_modal_results(solve_modal_analysis(structure, masses), structure)
        parameters = modal_response_parameters_from_result(modal, normalization="display")
        generated = create_static_equivalent_modal_loads(model, modal, parameters, mode_number=1, A_value=1.0)
        output.write_text(json.dumps(generated, indent=2) + "\n", encoding="utf-8")
        mass_output = output.with_name(f"{output.stem}_masses.json")
        mass_output.write_text(
            json.dumps({str(node): values for node, values in sorted(masses.items())}, indent=2) + "\n",
            encoding="utf-8",
        )
        total_fx = sum(float(load.get("fx", 0.0)) for load in generated["nodal_loads"])
        expected = parameters["rows"][0]["Vb_coeff"]
        print(f"Original: {source.name}")
        print(f"Generated: {output.name}")
        print(f"Mode: 1, A_value: 1.0")
        print(f"Total applied Fx: {total_fx:.9g}")
        print(f"Expected base shear coefficient: {expected:.9g}")
        print(f"Nodal loads written: {len(generated['nodal_loads'])}")


if __name__ == "__main__":
    main()
