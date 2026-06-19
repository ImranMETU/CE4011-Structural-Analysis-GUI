import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from gui.input_dialogs import material_preset_to_dialog_values, section_preset_to_dialog_values


def test_material_preset_dialog_values_fill_existing_material_fields():
    values = material_preset_to_dialog_values("Steel S235")

    assert values["fields"]["name"] == "Steel S235"
    assert values["fields"]["E"] == "200000000000"
    assert values["fields"]["alpha"] == "1.2e-05"
    assert "density" in values["notes"]


def test_section_preset_dialog_values_fill_existing_section_fields():
    values = section_preset_to_dialog_values("Beam 300x600")

    assert values["fields"]["name"] == "Beam 300x600"
    assert values["fields"]["A"] == "0.18"
    assert values["fields"]["I"] == "0.0054"
    assert values["fields"]["d"] == "0.6"
    assert "shape" in values["notes"]
