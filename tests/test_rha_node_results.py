from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"

for path in (SRC_ROOT, ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from gui.result_tables import format_rha_node_peak_response_rows  # noqa: E402
from postprocessing.rha_node_results import (  # noqa: E402
    compute_node_response_peaks,
    extract_node_response_history,
    format_node_response_rows,
    get_available_rha_nodes,
)


def _rha_result() -> dict:
    return {
        "time": np.array([0.0, 1.0, 2.0, 3.0]),
        "node_displacement_histories": {
            1: np.array([0.0, 0.2, -0.1, 0.05]),
            2: np.array([0.0, -0.4, 0.1, 0.2]),
        },
    }


def test_extracting_node_ux_history_and_peaks():
    result = extract_node_response_history(_rha_result(), 1, "ux")

    assert result["node"] == 1
    assert result["dof"] == "ux"
    assert result["peak_positive"] == pytest.approx(0.2)
    assert result["time_peak_positive"] == pytest.approx(1.0)
    assert result["peak_negative"] == pytest.approx(-0.1)
    assert result["peak_absolute"] == pytest.approx(0.2)


def test_available_nodes_and_peak_rows():
    rha = _rha_result()
    rows = compute_node_response_peaks(rha)

    assert get_available_rha_nodes(rha) == [1, 2]
    assert len(rows) == 2


def test_missing_node_and_missing_dof_raise_clear_errors():
    with pytest.raises(ValueError, match="Node 99"):
        extract_node_response_history(_rha_result(), 99, "ux")
    with pytest.raises(ValueError, match="DOF uy is not available"):
        extract_node_response_history(_rha_result(), 1, "uy")


def test_node_response_table_formatting():
    headers, rows = format_node_response_rows(compute_node_response_peaks(_rha_result()))
    gui_headers, gui_rows = format_rha_node_peak_response_rows(_rha_result())

    assert headers[0:2] == ["Node", "DOF"]
    assert headers == gui_headers
    assert rows == gui_rows
    assert len(rows) == 2
