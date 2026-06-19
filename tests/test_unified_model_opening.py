from __future__ import annotations

import inspect
import json
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

from gui.static_app import (  # noqa: E402
    StaticAnalysisApp,
    find_companion_mass_file,
    load_companion_mass_mapping,
    load_model_file_data,
)


class _DummyVar:
    def __init__(self):
        self.value = None

    def set(self, value):
        self.value = value


@pytest.mark.parametrize(
    ("source_path", "suffix"),
    [
        (ROOT / "inputs" / "generated" / "model_a_5story_unbraced.json", ".json"),
        (ROOT / "inputs" / "regression" / "xml" / "regression_thermal_combined_frame.xml", ".xml"),
        (ROOT / "inputs" / "examples" / "basic_cantilever_beam.txt", ".txt"),
    ],
)
def test_unified_model_loader_dispatches_supported_extensions(source_path, suffix):
    assert source_path.suffix == suffix

    data, embedded_masses = load_model_file_data(source_path)

    assert data["nodes"]
    assert data["elements"]
    if suffix != ".txt":
        assert embedded_masses is None


@pytest.mark.parametrize("suffix", [".json", ".xml", ".txt"])
def test_companion_mass_loading_is_format_independent(tmp_path, suffix):
    model_path = tmp_path / f"temporary_model{suffix}"
    model_path.write_text("placeholder", encoding="utf-8")
    mass_path = tmp_path / "temporary_model_masses.json"
    mass_path.write_text(
        json.dumps(
            {
                "2": {"ux": 15.0},
                3: {"ux": 7.5, "uy": 1.0, "rz": 2.0},
            }
        ),
        encoding="utf-8",
    )

    mapping = load_companion_mass_mapping(model_path)

    assert find_companion_mass_file(model_path) == mass_path
    assert mapping == {
        2: {"ux": 15.0, "uy": 0.0, "rz": 0.0},
        3: {"ux": 7.5, "uy": 1.0, "rz": 2.0},
    }
    assert sum(values["ux"] for values in mapping.values()) == pytest.approx(22.5)


def test_missing_companion_mass_file_returns_none(tmp_path):
    model_path = tmp_path / "model.json"
    model_path.write_text("{}", encoding="utf-8")

    assert find_companion_mass_file(model_path) is None
    assert load_companion_mass_mapping(model_path) is None


def test_generated_model_companion_mass_total():
    model_path = ROOT / "inputs" / "generated" / "model_a_5story_unbraced.json"

    mapping = load_companion_mass_mapping(model_path)

    assert len(mapping) == 10
    assert sum(values["ux"] for values in mapping.values()) == pytest.approx(500000.0)


def test_ce586_example_companion_mass_total():
    model_path = ROOT / "inputs" / "examples" / "CE586_Example_6_2_frame_model.json"

    mapping = load_companion_mass_mapping(model_path)

    assert len(mapping) == 2
    assert sum(values["ux"] for values in mapping.values()) == pytest.approx(22.5)


def test_app_unified_pipeline_uses_companion_mass_and_model_view(tmp_path):
    source = ROOT / "inputs" / "generated" / "model_a_5story_unbraced.json"
    model_path = tmp_path / "copied_model.json"
    model_path.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "copied_model_masses.json").write_text(
        json.dumps({"2": {"ux": 12.5}}),
        encoding="utf-8",
    )

    app = StaticAnalysisApp.__new__(StaticAnalysisApp)
    app.plot_type = _DummyVar()
    captured = {}
    app._set_loaded_model = lambda *args, **kwargs: captured.update(kwargs)
    app._redraw_current_plot = lambda: None
    app._update_summary = lambda message=None: None
    app._show_error = lambda title, exc: pytest.fail(f"{title}: {exc}")

    assert app._load_model_file(model_path)
    assert captured["source"] == "json"
    assert captured["mass_mapping"][2]["ux"] == pytest.approx(12.5)
    assert captured["mass_source"] == "companion mass file: copied_model_masses.json"
    assert app.plot_type.value == "Model View"


def test_file_menu_exposes_unified_open_and_save_commands():
    source = inspect.getsource(StaticAnalysisApp._build_menu)

    for label in ("Open Model...", "Open Generated Model...", "Save", "Save As...", "Save Model Package..."):
        assert f'label="{label}"' in source
    for old_label in ("Open JSON Model", "Open XML Model", "Open Text Model"):
        assert f'label="{old_label}"' not in source
