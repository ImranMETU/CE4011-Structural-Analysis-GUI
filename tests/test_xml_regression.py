from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
IO_ROOT = SRC_ROOT / "io"
COURSE_ROOT = ROOT.parent
A3_ROOT = COURSE_ROOT / "Assignment3"
A3_Q2_ROOT = A3_ROOT / "q2_frame_analysis"

for path in (SRC_ROOT, IO_ROOT, ROOT, A3_ROOT, A3_Q2_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from model.structure import Structure
from xml_loader import load_structure_from_xml


def _solve_from_xml(case_name: str):
    case_path = ROOT / "inputs" / "regression" / "xml" / case_name
    data = load_structure_from_xml(case_path)

    structure = Structure.from_dict(data)
    if structure.n_active_dofs > 0:
        structure.assemble_global_stiffness()
        structure.assemble_global_load_vector()

    structure.solve()
    reactions = structure.compute_reactions()
    member_forces = structure.compute_member_end_forces()
    return reactions, member_forces


def test_regression_xml_thermal_uniform_truss():
    reactions, member_forces = _solve_from_xml("regression_thermal_uniform_truss.xml")

    # Validated against current XML inputs:
    # steel pipe truss, A = 9.11061869541e-05 m^2
    expected_n = 6559.6454606952

    assert reactions[1]["rx"] == pytest.approx(expected_n)
    assert reactions[2]["rx"] == pytest.approx(-expected_n)
    assert reactions[1]["ry"] == pytest.approx(0.0)
    assert reactions[2]["ry"] == pytest.approx(0.0)
    assert reactions[1]["mz"] == pytest.approx(0.0)
    assert reactions[2]["mz"] == pytest.approx(0.0)

    q = member_forces[1]
    assert q["node_i"]["nx"] == pytest.approx(expected_n)
    assert q["node_j"]["nx"] == pytest.approx(-expected_n)
    assert q["node_i"]["vy"] == pytest.approx(0.0)
    assert q["node_j"]["vy"] == pytest.approx(0.0)
    assert q["node_i"]["mz"] == pytest.approx(0.0)
    assert q["node_j"]["mz"] == pytest.approx(0.0)


def test_regression_xml_thermal_gradient_frame():
    reactions, member_forces = _solve_from_xml("regression_thermal_gradient_frame.xml")

    # Validated against current XML inputs:
    # fully fixed concrete frame with current gradient case
    # Sign convention update: delta_T = T_bottom - T_top
    # (bottom hotter -> positive gradient -> sagging curvature)
    expected_m = -102400.02

    assert reactions[1]["rx"] == pytest.approx(0.0)
    assert reactions[2]["rx"] == pytest.approx(0.0)
    assert reactions[1]["ry"] == pytest.approx(0.0)
    assert reactions[2]["ry"] == pytest.approx(0.0)

    assert reactions[1]["mz"] == pytest.approx(expected_m)
    assert reactions[2]["mz"] == pytest.approx(-expected_m)

    q = member_forces[1]
    assert q["node_i"]["nx"] == pytest.approx(0.0)
    assert q["node_j"]["nx"] == pytest.approx(0.0)
    assert q["node_i"]["vy"] == pytest.approx(0.0)
    assert q["node_j"]["vy"] == pytest.approx(0.0)
    assert q["node_i"]["mz"] == pytest.approx(expected_m)
    assert q["node_j"]["mz"] == pytest.approx(-expected_m)


def test_regression_xml_thermal_combined_frame():
    reactions, member_forces = _solve_from_xml("regression_thermal_combined_frame.xml")

    # Validated against current XML inputs:
    # average temperature = 15 C, gradient = 10 C
    expected_n = 1152000.0
    # Sign convention update: gradient contribution follows delta_T = T_bottom - T_top.
    expected_m = -51200.01

    assert reactions[1]["rx"] == pytest.approx(expected_n)
    assert reactions[2]["rx"] == pytest.approx(-expected_n)
    assert reactions[1]["ry"] == pytest.approx(0.0)
    assert reactions[2]["ry"] == pytest.approx(0.0)
    assert reactions[1]["mz"] == pytest.approx(expected_m)
    assert reactions[2]["mz"] == pytest.approx(-expected_m)

    q = member_forces[1]
    assert q["node_i"]["nx"] == pytest.approx(expected_n)
    assert q["node_j"]["nx"] == pytest.approx(-expected_n)
    assert q["node_i"]["vy"] == pytest.approx(0.0)
    assert q["node_j"]["vy"] == pytest.approx(0.0)
    assert q["node_i"]["mz"] == pytest.approx(expected_m)
    assert q["node_j"]["mz"] == pytest.approx(-expected_m)


def test_regression_xml_settlement_single_frame():
    reactions, member_forces = _solve_from_xml("regression_settlement_single_frame.xml")

    # Validated against current XML inputs:
    # node 2 has uy settlement with ux/rz free, so only node 1 carries moment.
    expected_v = 73242.140625
    expected_m_node_1 = 292968.5625

    assert reactions[1]["rx"] == pytest.approx(0.0)
    assert reactions[2]["rx"] == pytest.approx(0.0)
    assert reactions[1]["ry"] + reactions[2]["ry"] == pytest.approx(0.0)

    assert abs(reactions[1]["ry"]) == pytest.approx(expected_v)
    assert abs(reactions[2]["ry"]) == pytest.approx(expected_v)
    assert reactions[1]["mz"] == pytest.approx(expected_m_node_1)
    assert reactions[2]["mz"] == pytest.approx(0.0)

    q = member_forces[1]
    assert q["node_i"]["nx"] == pytest.approx(0.0)
    assert q["node_j"]["nx"] == pytest.approx(0.0)
    assert abs(q["node_i"]["vy"]) == pytest.approx(expected_v)
    assert abs(q["node_j"]["vy"]) == pytest.approx(expected_v)
    assert q["node_i"]["mz"] == pytest.approx(expected_m_node_1)
    assert q["node_j"]["mz"] == pytest.approx(0.0)
