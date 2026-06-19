from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
IO_ROOT = SRC_ROOT / "io"

for path in (SRC_ROOT, IO_ROOT, ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from gui.model_builder import ModelBuilder
from postprocessing.static_results import run_static_analysis
from units.unit_system import (
    default_unit_system,
    get_unit_preset,
    result_column_label,
    unit_label,
)


def test_default_unit_system_labels():
    units = default_unit_system()

    assert (units.force, units.length, units.mass, units.temperature, units.time, units.rotation) == (
        "N",
        "m",
        "kg",
        "C",
        "s",
        "rad",
    )
    assert unit_label("displacement", units) == "m"
    assert unit_label("force", units) == "N"
    assert unit_label("moment", units) == "N-m"
    assert unit_label("frequency", units) == "Hz"
    assert unit_label("angular_frequency", units) == "rad/s"
    assert result_column_label("Mz", "moment", units) == "Mz [N-m]"


def test_unit_preset_lookup_and_unknown_name():
    assert get_unit_preset("kN-m-C-tonne").force == "kN"
    assert get_unit_preset("N-mm-C-kg").length == "mm"
    with pytest.raises(KeyError, match="Unknown unit preset"):
        get_unit_preset("made-up-units")


def test_model_builder_includes_default_units_metadata():
    builder = ModelBuilder()

    data = builder.to_structure_dict()

    assert data["units"]["name"] == "N-m-C-kg"
    assert data["units"]["length"] == "m"


def test_changing_unit_metadata_does_not_change_static_results():
    base = {
        "nodes": [
            {"id": 1, "x": 0.0, "y": 0.0, "restraints": {"ux": True, "uy": True, "rz": True}},
            {"id": 2, "x": 5.0, "y": 0.0, "restraints": {"ux": False, "uy": False, "rz": False}},
        ],
        "materials": [{"id": "steel", "E": 200.0e9, "alpha": 1.2e-5}],
        "sections": [{"id": "beam", "A": 0.02, "I": 8.0e-5, "d": 0.4}],
        "elements": [{"id": 1, "type": "frame", "node_i": 1, "node_j": 2, "material": "steel", "section": "beam"}],
        "nodal_loads": [{"node": 2, "fx": 0.0, "fy": -10000.0, "mz": 0.0}],
    }
    metric = copy.deepcopy(base)
    metric["units"] = get_unit_preset("N-m-C-kg").to_dict()
    alternate = copy.deepcopy(base)
    alternate["units"] = get_unit_preset("kip-ft-F-slug").to_dict()

    metric_result = run_static_analysis(metric)
    alternate_result = run_static_analysis(alternate)

    assert alternate_result["displacement_vector"] == pytest.approx(metric_result["displacement_vector"])
    assert alternate_result["reactions"] == metric_result["reactions"]
    assert alternate_result["member_end_forces"] == metric_result["member_end_forces"]
    assert alternate_result["units"]["name"] == "kip-ft-F-slug"

