from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"

for path in (SRC_ROOT, ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from gui.model_builder import ModelBuilder
from model.structure import Structure


def _builder_with_records() -> ModelBuilder:
    builder = ModelBuilder()
    builder.add_material("steel", 200000000.0, 1.2e-5)
    builder.add_material("concrete", 30000000.0, 8e-6)
    builder.add_section("beam", 0.01, 1.0e-4, 0.3)
    builder.add_section("pipe", 9.11e-5, 0.0)
    builder.add_node(1, 0.0, 0.0, "FIX", "FIX", "FIX")
    builder.add_node(2, 3.0, 0.0, "FREE", "FREE", "FREE")
    builder.add_node(3, 6.0, 0.0, "FREE", "FIX", "FREE")
    builder.add_frame_element(1, 1, 2, "steel", "beam")
    builder.add_truss_element(2, 2, 3, "steel", "pipe")
    builder.add_nodal_load(2, 100.0, -50.0, 5.0)
    builder.add_modal_mass(2, 10000.0, 0.0, 0.0)
    return builder


def test_model_builder_creates_structure_compatible_dictionary():
    builder = _builder_with_records()
    data = builder.to_structure_dict()

    assert len(data["materials"]) == 2
    assert len(data["sections"]) == 2
    assert len(data["nodes"]) == 3
    assert len(data["elements"]) == 2
    assert data["elements"][0]["type"] == "frame"
    assert data["elements"][1]["type"] == "truss"
    assert data["nodal_loads"][0] == {"node": 2, "fx": 100.0, "fy": -50.0, "mz": 5.0}

    structure = Structure.from_dict(data)
    assert len(structure.nodes) == 3
    assert len(structure.elements) == 2


def test_model_builder_creates_modal_mass_mapping():
    builder = _builder_with_records()

    assert builder.to_mass_mapping() == {2: {"ux": 10000.0, "uy": 0.0, "rz": 0.0}}


def test_model_builder_loads_from_structure_dict_and_mass_mapping():
    builder = _builder_with_records()
    data = builder.to_structure_dict()
    masses = builder.to_mass_mapping()

    other = ModelBuilder()
    other.load_from_structure_dict(data, masses)

    assert other.to_structure_dict() == data
    assert other.to_mass_mapping() == masses


def test_model_builder_analysis_options():
    builder = ModelBuilder()
    builder.update_analysis_options(default_lateral_mass=5000.0, num_modes=2, mode_shape_scale=0.25)

    assert builder.analysis_options["default_lateral_mass"] == pytest.approx(5000.0)
    assert builder.analysis_options["num_modes"] == 2
    assert builder.analysis_options["mode_shape_scale"] == pytest.approx(0.25)
