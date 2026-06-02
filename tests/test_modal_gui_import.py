from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
IO_ROOT = SRC_ROOT / "io"

for path in (SRC_ROOT, IO_ROOT, ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


def test_combined_gui_exports_modal_views():
    from gui.static_app import MODAL_PLOT_TYPES, PLOT_TYPES

    assert "Mode 1" in PLOT_TYPES
    assert "Mode 4" in PLOT_TYPES
    assert "Modal Frequencies" in PLOT_TYPES
    assert "Modal Periods" in PLOT_TYPES
    assert "Mode 1" in MODAL_PLOT_TYPES


def test_default_ux_mass_mapping_assigns_only_free_ux():
    from gui.static_app import build_default_ux_mass_mapping
    from model.structure import Structure

    structure = Structure.from_dict(
        {
            "nodes": [
                {"id": 1, "x": 0.0, "y": 0.0, "restraints": {"ux": True, "uy": True, "rz": True}},
                {"id": 2, "x": 3.0, "y": 0.0, "restraints": {"ux": False, "uy": False, "rz": False}},
            ],
            "materials": [{"id": "steel", "E": 200.0e9}],
            "sections": [{"id": "rect", "A": 0.01, "I": 1.0e-4, "d": 0.3}],
            "elements": [
                {"id": 1, "type": "frame", "node_i": 1, "node_j": 2, "material": "steel", "section": "rect"}
            ],
        }
    )

    mapping = build_default_ux_mass_mapping(structure, 10000.0)

    assert mapping == {2: {"ux": 10000.0, "uy": 0.0, "rz": 0.0}}
