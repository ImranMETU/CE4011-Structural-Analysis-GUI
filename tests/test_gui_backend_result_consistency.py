from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
IO_ROOT = SRC_ROOT / "io"

for path in (SRC_ROOT, IO_ROOT, ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from analysis.modal_solver import solve_modal_analysis  # noqa: E402
from gui.result_tables import (  # noqa: E402
    format_member_force_rows,
    format_modal_frequency_rows,
    format_nodal_displacement_rows,
    format_reaction_rows,
    format_solver_diagnostics_table_rows,
)
from gui.static_app import _load_companion_masses, load_model_data  # noqa: E402
from model.structure import Structure  # noqa: E402
from postprocessing.modal_results import package_modal_results  # noqa: E402
from postprocessing.solver_diagnostics import compute_solver_diagnostics  # noqa: E402
from postprocessing.static_results import collect_static_results  # noqa: E402


CASE_PATH = ROOT / "inputs" / "generated" / "model_a_5story_unbraced.json"


def _backend_static_case():
    data = load_model_data(CASE_PATH)
    structure = Structure.from_dict(data)
    static_result = collect_static_results(structure, solve=True)
    return data, structure, static_result


def _as_float(value: str) -> float:
    return float(value)


def _row_value(rows: list[list[str]], label: str) -> str:
    for row in rows:
        if row and row[0] == label:
            return row[1]
    raise AssertionError(f"Row label not found: {label}")


def test_nodal_displacement_table_matches_backend_static_result():
    data, _structure, static_result = _backend_static_case()

    headers, rows = format_nodal_displacement_rows(static_result)
    table_max = max(abs(_as_float(value)) for row in rows for value in row[1:])
    backend_max = max(
        abs(float(value))
        for values in static_result["displacements"].values()
        for value in (values["ux"], values["uy"], values["rz"])
    )

    assert headers == ["Node", "ux [m]", "uy [m]", "rz [rad]"]
    assert len(rows) == len(data["nodes"])
    assert table_max == pytest.approx(backend_max, rel=1.0e-6, abs=1.0e-12)


def test_support_reaction_table_row_count_matches_backend_records():
    _data, _structure, static_result = _backend_static_case()

    _headers, rows = format_reaction_rows(static_result)

    assert len(rows) == len(static_result["reactions"])


def test_member_end_force_table_row_count_matches_backend_records():
    _data, _structure, static_result = _backend_static_case()

    _headers, rows = format_member_force_rows(static_result)

    assert len(rows) == len(static_result["member_end_forces"])
    assert len(rows) == len(static_result["elements"])


def test_modal_frequency_table_matches_backend_frequency_relationships():
    pytest.importorskip("scipy.linalg", reason="SciPy is required for modal analysis.")
    data = load_model_data(CASE_PATH)
    masses = _load_companion_masses(CASE_PATH)
    assert masses is not None
    structure = Structure.from_dict(data)
    if structure.K is None:
        structure.assemble_global_stiffness()

    raw_modal = solve_modal_analysis(structure, masses, n_modes=4)
    modal_result = package_modal_results(raw_modal, structure=structure)
    headers, rows = format_modal_frequency_rows(modal_result)

    assert headers == ["Mode", "omega [rad/s]", "frequency [Hz]", "period [s]"]
    assert len(rows) == len(modal_result["frequency_table"])
    for row in rows:
        omega = _as_float(row[1])
        frequency = _as_float(row[2])
        period = _as_float(row[3])
        assert omega == pytest.approx(2.0 * math.pi * frequency, rel=1.0e-6)
        assert period == pytest.approx(1.0 / frequency, rel=1.0e-6)


def test_solver_diagnostics_table_matches_backend_matrix_size():
    _data, structure, _static_result = _backend_static_case()
    matrix = structure.K if structure.K is not None else structure.assemble_global_stiffness()
    diagnostics = compute_solver_diagnostics(structure, matrix)

    _headers, rows = format_solver_diagnostics_table_rows(diagnostics)
    table_matrix_size = int(_row_value(rows, "K matrix size"))

    assert table_matrix_size == diagnostics["matrix_size"]
    assert table_matrix_size == int(np.asarray(matrix_to_array(matrix)).shape[0])


def matrix_to_array(matrix):
    if hasattr(matrix, "get") and hasattr(matrix, "size"):
        return [[matrix.get(i, j) for j in range(matrix.size)] for i in range(matrix.size)]
    return matrix
