from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
IO_ROOT = SRC_ROOT / "io"

for path in (SRC_ROOT, IO_ROOT, ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


class _DummyVar:
    def __init__(self, value: str):
        self.value = value

    def get(self) -> str:
        return self.value

    def set(self, value: str) -> None:
        self.value = value


def _form_builder():
    from gui.model_builder import ModelBuilder

    builder = ModelBuilder()
    builder.add_material("steel", 200000000.0, 1.2e-5)
    builder.add_section("beam", 0.01, 1.0e-4, 0.3)
    builder.add_node(1, 0.0, 0.0, "FIX", "FIX", "FIX")
    builder.add_node(2, 4.0, 0.0, "FREE", "FREE", "FREE")
    builder.add_frame_element(1, 1, 2, "steel", "beam")
    builder.add_modal_mass(2, 10000.0, 0.0, 0.0)
    return builder


def test_form_model_dictionary_plots_without_static_analysis():
    from visualization.model_view import plot_model_view

    data = _form_builder().to_structure_dict()
    fig, ax = plot_model_view(data)

    labels = {text.get_text() for text in ax.texts}
    assert "N1" in labels
    assert "N2" in labels
    assert "E1" in labels
    plt.close(fig)


def test_static_app_refreshes_state_from_form_builder_without_tk_root():
    from gui.static_app import MODEL_VIEW_TYPES, StaticAnalysisApp

    app = StaticAnalysisApp.__new__(StaticAnalysisApp)
    app.model_builder = _form_builder()
    app.loaded_path = Path("old.json")
    app.model_data = None
    app.text_mass_mapping = None
    app.input_source = None
    app.generated_model_name = None
    app.static_result = {"stale": True}
    app.modal_result = {"stale": True}
    app.current_table = {"stale": True}
    app.plot_type = _DummyVar(next(iter(MODEL_VIEW_TYPES)))
    app.clear_selection = lambda redraw=False: None
    app._apply_analysis_options_to_controls = lambda: None
    app._redraw_current_plot = lambda: None
    app._update_summary = lambda message=None: None

    StaticAnalysisApp._refresh_model_from_builder(app, source_label="Form Model", redraw=True)

    assert app.loaded_path is None
    assert app.input_source == "form"
    assert app.generated_model_name == "Form Model"
    assert len(app.model_data["nodes"]) == 2
    assert len(app.model_data["elements"]) == 1
    assert app.text_mass_mapping == {2: {"ux": 10000.0, "uy": 0.0, "rz": 0.0}}
    assert app.static_result is None
    assert app.modal_result is None
    assert app.current_table is None


def test_static_app_exposes_form_refresh_helper():
    from gui.static_app import StaticAnalysisApp

    assert callable(getattr(StaticAnalysisApp, "_refresh_model_from_builder"))
