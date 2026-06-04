from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
import pytest

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
IO_ROOT = SRC_ROOT / "io"

for path in (SRC_ROOT, IO_ROOT, ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from gui.model_builder import ModelBuilder  # noqa: E402
from gui.input_dialogs import (  # noqa: E402
    MEMBER_LOAD_BUTTON_LABELS,
    get_member_load_field_states,
    member_load_default_values,
)
from postprocessing.static_results import run_static_analysis  # noqa: E402
from text_loader import load_text_model, parse_text_model  # noqa: E402
from visualization.model_view import plot_model_view  # noqa: E402


BASE_TEXT = """
MATERIAL steel E=200000000000 alpha=1.2e-5
SECTION beam A=0.02 I=8e-5 d=0.4
NODE 1 0 0 FIX FIX FREE
NODE 2 5 0 FREE FIX FREE
FRAME 1 1 2 steel beam
"""


def _builder() -> ModelBuilder:
    builder = ModelBuilder()
    builder.add_material("steel", 200000000000.0, 1.2e-5)
    builder.add_section("beam", 0.02, 8.0e-5, 0.4)
    builder.add_node(1, 0.0, 0.0, "FIX", "FIX", "FREE")
    builder.add_node(2, 5.0, 0.0, "FREE", "FIX", "FREE")
    builder.add_frame_element(1, 1, 2, "steel", "beam")
    return builder


def test_text_parser_handles_udl_member_load():
    data, _masses = parse_text_model(BASE_TEXT + "MEMBER_LOAD 1 TYPE=UDL DIR=LOCAL_Y W=-10000\n")

    assert data["elements"][0]["member_loads"] == [
        {"type": "udl", "direction": "local_y", "w": -10000.0}
    ]


def test_text_parser_accepts_full_span_udl_range_and_emits_backend_schema():
    data, _masses = parse_text_model(BASE_TEXT + "MEMBER_LOAD 1 TYPE=UDL DIR=LOCAL_Y W=-10000 X_START=0 X_END=5\n")

    assert data["elements"][0]["member_loads"] == [
        {"type": "udl", "direction": "local_y", "w": -10000.0}
    ]


def test_text_parser_rejects_partial_udl_range():
    with pytest.raises(ValueError, match="partial UDL range is not supported"):
        parse_text_model(BASE_TEXT + "MEMBER_LOAD 1 TYPE=UDL DIR=LOCAL_Y W=-10000 X_START=1 X_END=4\n")


def test_text_parser_handles_point_member_load():
    data, _masses = parse_text_model(BASE_TEXT + "MEMBER_LOAD 1 TYPE=POINT DIR=LOCAL_Y P=-20000 A=2.5\n")

    assert data["elements"][0]["member_loads"] == [
        {"type": "point", "direction": "local_y", "p": -20000.0, "a": 2.5}
    ]


def test_model_builder_emits_member_loads_in_structure_schema():
    builder = _builder()
    builder.add_member_load(1, "UDL", "local_y", w=-10000)
    builder.add_member_load(1, "Point", "local_y", p=-20000, a=2.5)

    data = builder.to_structure_dict()

    assert data["elements"][0]["member_loads"] == [
        {"type": "udl", "direction": "local_y", "w": -10000.0},
        {"type": "point", "direction": "local_y", "p": -20000.0, "a": 2.5},
    ]


def test_model_builder_accepts_full_span_udl_range_without_emitting_unsupported_keys():
    builder = _builder()
    builder.add_member_load(1, "UDL", "local_y", w=-10000, x_start=0.0, x_end=5.0)

    record = builder.table_records("member_loads")[0]
    data = builder.to_structure_dict()

    assert record["x_start"] == pytest.approx(0.0)
    assert record["x_end"] == pytest.approx(5.0)
    assert data["elements"][0]["member_loads"] == [
        {"type": "udl", "direction": "local_y", "w": -10000.0}
    ]


def test_model_builder_rejects_partial_udl_range():
    builder = _builder()

    with pytest.raises(ValueError, match="Partial UDL range is not supported"):
        builder.add_member_load(1, "UDL", "local_y", w=-10000, x_start=1.0, x_end=4.0)


def test_model_builder_rejects_unknown_element_member_load():
    builder = _builder()

    with pytest.raises(ValueError, match="Unknown element id 99"):
        builder.add_member_load(99, "UDL", "local_y", w=-10000)


def test_model_builder_rejects_invalid_point_position_when_length_available():
    builder = _builder()

    with pytest.raises(ValueError, match="0 <= a <= L"):
        builder.add_member_load(1, "Point", "local_y", p=-20000, a=7.0)


def test_member_load_dialog_defaults_to_point_load():
    defaults = member_load_default_values(_builder())

    assert defaults["load_type"] == "POINT"
    assert defaults["direction"] == "local_y"
    assert defaults["a"] == "2.5"
    assert defaults["w"] == ""


def test_member_load_dialog_button_labels_are_exposed():
    assert MEMBER_LOAD_BUTTON_LABELS == ("Add", "Update", "Delete", "Apply", "OK", "Cancel")


def test_member_load_field_states_switch_by_load_type():
    point_states = get_member_load_field_states("POINT")
    udl_states = get_member_load_field_states("UDL")

    assert point_states["p"] == "normal"
    assert point_states["a"] == "normal"
    assert point_states["w"] == "disabled"
    assert point_states["x_start"] == "disabled"
    assert point_states["x_end"] == "disabled"
    assert udl_states["w"] == "normal"
    assert udl_states["x_start"] == "normal"
    assert udl_states["x_end"] == "normal"
    assert udl_states["p"] == "disabled"
    assert udl_states["a"] == "disabled"


def test_static_app_member_load_command_dispatches_custom_dialog(monkeypatch):
    import gui.static_app as static_app

    calls = []

    def fake_open(parent, builder, on_change=None):
        calls.append((parent, builder, on_change))

    app = static_app.StaticAnalysisApp.__new__(static_app.StaticAnalysisApp)
    app.root = object()
    app.model_builder = _builder()
    app._ensure_form_source = lambda: None
    app._refresh_model_from_builder = lambda: None

    monkeypatch.setattr(static_app, "open_member_loads_dialog", fake_open)
    static_app.StaticAnalysisApp.define_member_loads(app)

    assert len(calls) == 1
    assert calls[0][0] is app.root
    assert calls[0][1] is app.model_builder
    assert calls[0][2] == app._refresh_model_from_builder


def test_gui_tkinter_color_literals_are_not_decimal_grayscale():
    input_dialogs_path = ROOT / "src" / "gui" / "input_dialogs.py"
    text = input_dialogs_path.read_text(encoding="utf-8")

    assert 'foreground="0.' not in text
    assert 'fg="0.' not in text
    assert 'background="0.' not in text
    assert 'bg="0.' not in text


def test_member_load_examples_solve_through_backend():
    for filename in ("member_load_udl_frame.txt", "member_load_point_frame.txt"):
        data, _masses = load_text_model(ROOT / "inputs" / "examples" / filename)
        result = run_static_analysis(data)

        assert result["displacement_vector"]
        assert result["reactions"]
        assert result["member_end_forces"]


def test_model_view_plots_member_loads_without_crashing():
    data, _masses = parse_text_model(BASE_TEXT + "MEMBER_LOAD 1 TYPE=POINT DIR=LOCAL_Y P=-20000 A=2.5\n")

    fig, ax = plot_model_view(data)

    labels = {text.get_text() for text in ax.texts}
    assert any("P=-2e+04" in label for label in labels)
    plt.close(fig)


def test_thermal_loads_are_preserved_with_member_loads():
    builder = _builder()
    builder.add_member_load(1, "UDL", "local_y", w=-10000)
    builder.add_thermal_load(1, "Uniform", T_uniform=20.0)

    data = builder.to_structure_dict()
    loads = data["elements"][0]["member_loads"]

    assert {"type": "udl", "direction": "local_y", "w": -10000.0} in loads
    assert {"type": "thermal", "T_uniform": 20.0} in loads
