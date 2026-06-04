from __future__ import annotations

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

from model.structure import Structure
from text_loader import load_text_model, parse_text_model


TEXT_MODEL = """
# simple mixed model
MATERIAL concrete E=30000000 alpha=8e-6
MATERIAL steel E=200000000 alpha=1.2e-5

SECTION beam A=0.32 I=0.01707 d=0.8
SECTION pipe A=9.11e-5 I=0

NODE 1 0 0 FIX FIX FIX
NODE 2 5 0 FREE FREE FREE
NODE 3 10 0 FREE FIX FREE

FRAME 1 1 2 concrete beam
TRUSS 2 2 3 steel pipe

LOAD 2 FX=10000 FY=-500 MZ=25
MASS 2 UX=10000 UY=0 RZ=0
"""

THERMAL_SETTLEMENT_TEXT_MODEL = """
MATERIAL steel E=200000000000 alpha=1.2e-5
SECTION beam A=0.02 I=8e-5 d=0.5
NODE 1 0 0 FIX FIX FIX
NODE 2 5 0 FIX FIX FIX
FRAME 1 1 2 steel beam
THERMAL 1 T_TOP=0 T_BOTTOM=50
SETTLEMENT 2 UY=-0.002
"""


def test_text_loader_parses_materials_sections_nodes_elements_loads_and_masses():
    data, mass_mapping = parse_text_model(TEXT_MODEL)

    assert data["materials"][0] == {"id": "concrete", "E": 30000000.0, "alpha": 8e-6}
    assert data["sections"][0] == {"id": "beam", "A": 0.32, "I": 0.01707, "d": 0.8}
    assert data["nodes"][0]["restraints"] == {"ux": True, "uy": True, "rz": True}
    assert data["nodes"][1]["restraints"] == {"ux": False, "uy": False, "rz": False}
    assert data["elements"][0]["type"] == "frame"
    assert data["elements"][1]["type"] == "truss"
    assert data["nodal_loads"][0] == {"node": 2, "fx": 10000.0, "fy": -500.0, "mz": 25.0}
    assert mass_mapping == {2: {"ux": 10000.0, "uy": 0.0, "rz": 0.0}}


def test_text_loader_output_builds_structure():
    data, _mass_mapping = parse_text_model(TEXT_MODEL)

    structure = Structure.from_dict(data)

    assert len(structure.nodes) == 3
    assert len(structure.elements) == 2
    assert structure.materials["concrete"].E == pytest.approx(30000000.0)


def test_load_text_model_reads_file(tmp_path):
    path = tmp_path / "model.txt"
    path.write_text(TEXT_MODEL, encoding="utf-8")

    data, mass_mapping = load_text_model(path)

    assert len(data["nodes"]) == 3
    assert mass_mapping[2]["ux"] == pytest.approx(10000.0)


def test_text_loader_rejects_unknown_keyword():
    with pytest.raises(ValueError, match="unknown keyword"):
        parse_text_model("BOGUS 1 2 3")


def test_text_loader_parses_thermal_and_settlement_lines():
    data, _mass_mapping = parse_text_model(THERMAL_SETTLEMENT_TEXT_MODEL)

    assert data["elements"][0]["member_loads"] == [{"type": "thermal", "T_top": 0.0, "T_bottom": 50.0}]
    assert data["nodes"][1]["prescribed_displacements"] == {"ux": 0.0, "uy": -0.002, "rz": 0.0}

    structure = Structure.from_dict(data)
    structure.solve()
    assert structure.compute_member_end_forces()
