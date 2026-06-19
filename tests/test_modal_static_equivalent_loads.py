from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "src" / "io", ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from analysis.modal_solver import solve_modal_analysis  # noqa: E402
from gui.static_app import load_companion_mass_mapping, load_model_data, static_load_warning  # noqa: E402
from model.structure import Structure  # noqa: E402
from postprocessing.modal_response_parameters import modal_response_parameters_from_result  # noqa: E402
from postprocessing.modal_results import package_modal_results  # noqa: E402
from postprocessing.modal_static_equivalent_loads import create_static_equivalent_modal_loads  # noqa: E402


def _case(filename):
    path = ROOT / "inputs" / "examples" / filename
    model = load_model_data(path)
    structure = Structure.from_dict(model)
    modal = package_modal_results(
        solve_modal_analysis(structure, load_companion_mass_mapping(path)),
        structure,
    )
    return model, modal, modal_response_parameters_from_result(modal, normalization="display")


@pytest.mark.parametrize(
    ("filename", "expected_nodes"),
    [
        ("CE586_Example_6_2_frame_model.json", {2, 3}),
        ("CE586_Examples_6_4_6_6_frame_model.json", {3, 4, 5, 6, 7, 8}),
    ],
)
def test_static_equivalent_loads_are_applied_to_mass_bearing_nodes(filename, expected_nodes):
    model, modal, parameters = _case(filename)
    original = copy.deepcopy(model)

    generated = create_static_equivalent_modal_loads(model, modal, parameters, mode_number=1, A_value=1.0)

    assert model == original
    assert {load["node"] for load in generated["nodal_loads"]} == expected_nodes
    assert sum(load["fx"] for load in generated["nodal_loads"]) == pytest.approx(
        parameters["rows"][0]["Vb_coeff"]
    )
    assert all(load["fy"] == 0.0 and load["mz"] == 0.0 for load in generated["nodal_loads"])


def test_static_load_warning_explains_zero_response():
    model, _modal, _parameters = _case("CE586_Example_6_2_frame_model.json")

    warning = static_load_warning(model)

    assert "No static load records found" in warning
    assert "Static response and N/V/M diagrams will be zero" in warning
    loaded = copy.deepcopy(model)
    loaded["nodal_loads"] = [{"node": 2, "fx": 1.0, "fy": 0.0, "mz": 0.0}]
    assert static_load_warning(loaded) is None
