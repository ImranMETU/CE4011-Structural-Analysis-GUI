from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
IO_ROOT = SRC_ROOT / "io"

for path in (SRC_ROOT, IO_ROOT, ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from postprocessing.static_results import run_static_analysis
from text_loader import load_text_model


def test_assignment4_settlement_text_example_solves():
    data, _mass_mapping = load_text_model(ROOT / "inputs" / "examples" / "a4_settlement_example.txt")

    result = run_static_analysis(data)

    assert result["reactions"]
    assert result["member_end_forces"]
    assert any("prescribed_displacements" in node for node in data["nodes"])


def test_assignment4_thermal_text_example_solves():
    data, _mass_mapping = load_text_model(ROOT / "inputs" / "examples" / "a4_thermal_example.txt")

    result = run_static_analysis(data)

    assert result["reactions"]
    assert result["member_end_forces"]
    assert sum(len(element.get("member_loads", [])) for element in data["elements"]) == 4
