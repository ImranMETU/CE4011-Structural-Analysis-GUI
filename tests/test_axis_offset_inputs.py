from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
import pytest

matplotlib.use("Agg")

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
IO_ROOT = SRC_ROOT / "io"

for path in (ROOT, IO_ROOT, SRC_ROOT):
    path_str = str(path)
    if path_str in sys.path:
        sys.path.remove(path_str)
sys.path.insert(0, str(SRC_ROOT))
sys.path.insert(1, str(IO_ROOT))
sys.path.insert(2, str(ROOT))

from gui.input_dialogs import open_axis_offsets_dialog  # noqa: E402
from gui.model_builder import ModelBuilder  # noqa: E402
from text_loader import parse_text_model  # noqa: E402
from visualization.model_view import plot_model_view  # noqa: E402


BASE_TEXT = """
MATERIAL steel E=200000000
SECTION beam A=0.02 I=8e-5
NODE 1 0 0 FIX FIX FIX
NODE 2 5 0 FREE FREE FREE
FRAME 1 1 2 steel beam
"""


def _builder() -> ModelBuilder:
    builder = ModelBuilder()
    builder.add_material("steel", 200_000_000.0)
    builder.add_section("beam", 0.02, 8.0e-5)
    builder.add_node(1, 0.0, 0.0, "FIX", "FIX", "FIX")
    builder.add_node(2, 5.0, 0.0, "FREE", "FREE", "FREE")
    builder.add_frame_element(1, 1, 2, "steel", "beam")
    return builder


def test_axis_offsets_dialog_factory_imports():
    assert callable(open_axis_offsets_dialog)


def test_text_parser_attaches_axis_offset_to_frame_element():
    data, _masses = parse_text_model(BASE_TEXT + "AXIS_OFFSET 1 I_LOCAL_Y=0.25 J_LOCAL_Y=-0.1\n")

    assert data["elements"][0]["axis_offset"] == {"i_local_y": 0.25, "j_local_y": -0.1}


def test_text_parser_rejects_axis_offset_on_truss_element():
    text = BASE_TEXT.replace("FRAME 1", "TRUSS 1") + "AXIS_OFFSET 1 I_LOCAL_Y=0.25 J_LOCAL_Y=0\n"

    with pytest.raises(ValueError, match="axis offsets are supported for frame elements only"):
        parse_text_model(text)


def test_model_builder_emits_axis_offset_schema_and_round_trips():
    builder = _builder()
    builder.add_axis_offset(1, 0.12, -0.03)

    data = builder.to_structure_dict()
    reloaded = ModelBuilder()
    reloaded.load_from_structure_dict(data)

    assert data["elements"][0]["axis_offset"] == {"i_local_y": 0.12, "j_local_y": -0.03}
    assert reloaded.table_records("axis_offsets") == [
        {"element": 1, "i_local_y": 0.12, "j_local_y": -0.03}
    ]


def test_model_builder_rejects_axis_offset_on_truss_element():
    builder = _builder()
    builder.add_truss_element(2, 1, 2, "steel", "beam")

    with pytest.raises(ValueError, match="frame elements only"):
        builder.add_axis_offset(2, 0.1, 0.0)


def test_model_view_draws_axis_offset_label():
    import matplotlib.pyplot as plt

    model = _builder().to_structure_dict()
    model["elements"][0]["axis_offset"] = {"i_local_y": 0.12, "j_local_y": -0.03}

    fig, ax = plot_model_view(model)

    labels = {text.get_text() for text in ax.texts}
    assert "off i=0.12, j=-0.03" in labels
    plt.close(fig)
