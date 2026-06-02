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

from postprocessing.force_diagrams import element_force_diagrams
from postprocessing.static_results import run_static_analysis
from xml_loader import load_structure_from_xml


def _load_xml_case(case_name: str):
    case_path = ROOT / "inputs" / "regression" / "xml" / case_name
    return load_structure_from_xml(case_path)


def test_static_result_package_contains_core_outputs():
    results = run_static_analysis(_load_xml_case("regression_thermal_combined_frame.xml"))

    assert "displacement_vector" in results
    assert "displacements" in results
    assert "reactions" in results
    assert "member_end_forces" in results
    assert "nodes" in results
    assert "elements" in results

    assert len(results["displacement_vector"]) == 6
    assert set(results["displacements"]) == {1, 2}
    assert set(results["reactions"]) == {1, 2}
    assert 1 in results["member_end_forces"]
    assert results["nodes"][1] == {"x": 0.0, "y": 0.0}
    assert results["elements"][1]["type"] == "frame"
    assert results["elements"][1]["node_i"] == 1
    assert results["elements"][1]["node_j"] == 2


def test_frame_force_diagram_arrays_can_be_generated():
    results = run_static_analysis(_load_xml_case("regression_thermal_gradient_frame.xml"))
    diagrams = element_force_diagrams(results, 1, n_points=3)

    assert set(diagrams) == {"axial", "shear", "moment"}
    for diagram in diagrams.values():
        assert len(diagram["x"]) == 3
        assert len(diagram["values"]) == 3
        assert diagram["x"][0] == 0.0
        assert diagram["x"][-1] == results["elements"][1]["length"]


def test_truss_force_diagrams_are_axial_only():
    results = run_static_analysis(_load_xml_case("regression_thermal_uniform_truss.xml"))
    diagrams = element_force_diagrams(results, 1, n_points=4)

    assert set(diagrams) == {"axial"}
    assert len(diagrams["axial"]["x"]) == 4
    assert len(diagrams["axial"]["values"]) == 4
    assert results["elements"][1]["type"] == "truss"
