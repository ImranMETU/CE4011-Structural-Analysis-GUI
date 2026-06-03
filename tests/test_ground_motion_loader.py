from __future__ import annotations

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

from ground_motion_loader import convert_acceleration, load_ground_motion, validate_constant_dt


def test_ground_motion_loader_reads_two_column_file_and_metadata(tmp_path):
    path = tmp_path / "record.thf"
    path.write_text("0.0 0.0\n0.1 10.0\n0.2 -20.0\n", encoding="utf-8")

    record = load_ground_motion(path, input_unit="cm/s2")

    assert record["n_points"] == 3
    assert record["dt"] == pytest.approx(0.1)
    assert record["duration"] == pytest.approx(0.2)
    assert record["pga"] == pytest.approx(0.2)
    assert np.allclose(record["time"], [0.0, 0.1, 0.2])
    assert np.allclose(record["acceleration"], [0.0, 0.1, -0.2])


def test_ground_motion_loader_detects_nonconstant_dt(tmp_path):
    path = tmp_path / "bad_record.thf"
    path.write_text("0.0 0.0\n0.1 1.0\n0.25 2.0\n", encoding="utf-8")

    with pytest.raises(ValueError, match="not constant"):
        load_ground_motion(path)


def test_validate_constant_dt_returns_increment():
    assert validate_constant_dt(np.array([0.0, 0.02, 0.04])) == pytest.approx(0.02)


def test_unit_conversion_to_mps2():
    assert np.allclose(convert_acceleration([100.0], "cm/s2"), [1.0])
    assert np.allclose(convert_acceleration([1.0], "m/s2"), [1.0])
    assert np.allclose(convert_acceleration([1.0], "g"), [9.80665])
