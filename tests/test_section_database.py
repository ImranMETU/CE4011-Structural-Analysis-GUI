import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from data.section_database import (
    get_section_preset,
    get_section_preset_names,
    get_section_presets,
    make_circular_section,
    make_rectangular_section,
)


def test_section_presets_include_expected_rc_section():
    names = get_section_preset_names()

    assert "RC 400x400" in names
    preset = get_section_preset("RC 400x400")
    assert preset["A"] == pytest.approx(0.16)
    assert preset["I"] == pytest.approx(0.40 * 0.40**3 / 12.0)
    assert preset["d"] == pytest.approx(0.40)


def test_rectangular_and_circular_helpers_use_expected_formulas():
    rect = make_rectangular_section("test rect", 0.3, 0.5)
    circ = make_circular_section("test circ", 0.3)

    assert rect["A"] == pytest.approx(0.15)
    assert rect["I"] == pytest.approx(0.3 * 0.5**3 / 12.0)
    assert circ["A"] == pytest.approx(math.pi * 0.3**2 / 4.0)
    assert circ["I"] == pytest.approx(math.pi * 0.3**4 / 64.0)


def test_section_presets_return_copies():
    presets = get_section_presets()
    presets["Beam 300x500"]["A"] = 1.0

    assert get_section_preset("Beam 300x500")["A"] == pytest.approx(0.15)


def test_unknown_section_preset_raises_key_error():
    with pytest.raises(KeyError):
        get_section_preset("not a real section")
