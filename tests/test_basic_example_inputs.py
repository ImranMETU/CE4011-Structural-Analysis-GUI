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

from postprocessing.static_results import run_static_analysis
from text_loader import load_text_model


@pytest.mark.parametrize(
    "filename",
    [
        "basic_cantilever_beam.txt",
        "basic_simply_supported_beam.txt",
    ],
)
def test_basic_beam_examples_load_and_solve(filename):
    path = ROOT / "inputs" / "examples" / filename

    data, _mass_mapping = load_text_model(path)
    result = run_static_analysis(data)

    assert len(data["nodes"]) == 2
    assert len(data["elements"]) == 1
    assert result["displacement_vector"]
    assert result["reactions"]
    assert result["member_end_forces"]

