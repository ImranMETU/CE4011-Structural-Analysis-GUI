import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from data.material_database import (
    get_material_preset,
    get_material_preset_names,
    get_material_presets,
)


def test_material_presets_include_expected_steel():
    names = get_material_preset_names()

    assert "Steel S355" in names
    preset = get_material_preset("Steel S355")
    assert preset["E"] == pytest.approx(210.0e9)
    assert preset["alpha"] == pytest.approx(1.2e-5)
    assert preset["density"] == pytest.approx(7850.0)


def test_material_presets_return_copies():
    presets = get_material_presets()
    presets["Steel S235"]["E"] = 1.0

    assert get_material_preset("Steel S235")["E"] == pytest.approx(200.0e9)


def test_unknown_material_preset_raises_key_error():
    with pytest.raises(KeyError):
        get_material_preset("not a real material")
