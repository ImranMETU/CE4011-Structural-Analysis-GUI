from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
IO_ROOT = SRC_ROOT / "io"

for path in (SRC_ROOT, IO_ROOT, ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


def _raw_values(**overrides):
    from gui.frame_generator_dialog import DEFAULT_RAW_VALUES

    values = dict(DEFAULT_RAW_VALUES)
    values.update(overrides)
    return values


def test_frame_generator_dialog_module_imports_successfully():
    import gui.frame_generator_dialog as dialog

    assert callable(dialog.open_frame_generator_dialog)
    assert callable(dialog.parse_frame_generator_options)


def test_parse_frame_generator_options_converts_dialog_values():
    from gui.frame_generator_dialog import parse_frame_generator_options

    options = parse_frame_generator_options(_raw_values(n_stories="10", n_bays="2", braced=True))

    assert options["model_name"] == "generated_frame_model"
    assert options["n_stories"] == 10
    assert options["n_bays"] == 2
    assert options["braced"] is True
    assert options["floor_mass"] == 100000.0


def test_parse_frame_generator_options_rejects_invalid_values():
    from gui.frame_generator_dialog import parse_frame_generator_options

    try:
        parse_frame_generator_options(_raw_values(n_stories="0"))
    except ValueError as exc:
        assert "number of stories" in str(exc)
    else:
        raise AssertionError("Expected invalid story count to raise ValueError.")


def test_build_generated_model_from_raw_returns_model_and_mass_mapping():
    from gui.frame_generator_dialog import build_generated_model_from_raw

    data, masses, name = build_generated_model_from_raw(_raw_values(model_name="ui_test", n_stories="2"))

    assert name == "ui_test"
    assert data["nodes"]
    assert data["elements"]
    assert masses


def test_generate_proposal_defaults_writes_to_temp_directory(tmp_path):
    from gui.frame_generator_dialog import generate_proposal_default_models

    paths = generate_proposal_default_models(tmp_path)

    assert len(paths) == 6
    assert (tmp_path / "model_a_5story_unbraced.json").exists()
    assert (tmp_path / "model_c_10story_braced_masses.json").exists()
