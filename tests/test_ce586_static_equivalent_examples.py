from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from postprocessing.static_results import run_static_analysis  # noqa: E402


CASES = (
    (
        "CE586_Example_6_2_frame_model.json",
        "CE586_Example_6_2_frame_model_static_mode1.json",
        2,
    ),
    (
        "CE586_Examples_6_4_6_6_frame_model.json",
        "CE586_Examples_6_4_6_6_frame_model_static_mode1.json",
        6,
    ),
)


def test_original_ce586_benchmarks_remain_unloaded():
    for original_name, _generated_name, _count in CASES:
        original = json.loads((ROOT / "inputs" / "examples" / original_name).read_text(encoding="utf-8"))
        assert original.get("nodal_loads", []) == []
        assert "static_equivalent_modal_load" not in original


def test_generated_static_equivalent_examples_have_nonzero_static_response():
    for _original_name, generated_name, expected_count in CASES:
        path = ROOT / "inputs" / "examples" / generated_name
        masses = path.with_name(f"{path.stem}_masses.json")
        data = json.loads(path.read_text(encoding="utf-8"))

        assert len(data["nodal_loads"]) == expected_count
        assert any(abs(float(load["fx"])) > 0.0 for load in data["nodal_loads"])
        assert masses.exists()
        result = run_static_analysis(data)
        assert max(abs(float(value)) for value in result["displacement_vector"]) > 0.0
        assert any(
            abs(float(value)) > 1.0e-10
            for element in result["member_end_forces"].values()
            for end in element.values()
            for value in end.values()
        )
