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

from analysis.mass_assembly import (  # noqa: E402
    distribute_floor_mass_to_nodes,
    lump_element_distributed_mass_to_nodes,
    mass_mapping_summary,
    merge_mass_mappings,
)
from text_loader import parse_text_model  # noqa: E402


MODEL = {
    "nodes": [
        {"id": 1, "x": 0.0, "y": 0.0},
        {"id": 2, "x": 4.0, "y": 3.0},
        {"id": 3, "x": 8.0, "y": 3.0},
    ],
    "elements": [
        {"id": 1, "type": "frame", "node_i": 2, "node_j": 3, "material": "steel", "section": "beam"}
    ],
}


TEXT_MODEL = """
MATERIAL steel E=200000000000
SECTION beam A=0.02 I=8e-5 d=0.4
NODE 1 0 0 FIX FIX FIX
NODE 2 4 3 FREE FREE FREE
NODE 3 8 3 FREE FREE FREE
FRAME 1 2 3 steel beam
"""


def test_floor_lumped_mass_distribution():
    mapping = distribute_floor_mass_to_nodes(MODEL, floor_y=3.0, total_mass=200.0, direction="ux")

    assert mapping == {2: {"ux": 100.0}, 3: {"ux": 100.0}}


def test_element_distributed_mass_lumps_half_to_each_end():
    mapping = lump_element_distributed_mass_to_nodes(MODEL, 1, mass_per_length=50.0, direction="ux")

    assert mapping == {2: {"ux": 100.0}, 3: {"ux": 100.0}}


def test_merge_mass_mappings_and_summary():
    merged = merge_mass_mappings({2: {"ux": 10.0}}, {2: {"ux": 5.0}, 3: {"uy": 4.0}})
    summary = mass_mapping_summary(merged, source_type="test")

    assert merged[2]["ux"] == pytest.approx(15.0)
    assert summary["total_ux_mass"] == pytest.approx(15.0)
    assert summary["total_uy_mass"] == pytest.approx(4.0)


def test_text_loader_parses_floor_and_element_mass_sources():
    data, masses = parse_text_model(
        TEXT_MODEL
        + "FLOOR_MASS Y=3 UX=200\n"
        + "ELEMENT_MASS 1 M_PER_LENGTH=50 DIR=UX\n"
    )

    assert len(data["elements"]) == 1
    assert masses[2]["ux"] == pytest.approx(200.0)
    assert masses[3]["ux"] == pytest.approx(200.0)


def test_text_loader_rejects_spring_until_backend_exists():
    with pytest.raises(ValueError, match="SPRING input is not implemented"):
        parse_text_model(TEXT_MODEL + "SPRING 2 DOF=UX K=1000\n")
