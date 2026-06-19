from __future__ import annotations

import json
import sys
import zipfile
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
    companion_mass_path,
    create_model_package,
    load_companion_mass_mapping,
    load_model_file_data,
    save_model_files,
)


def _simple_model():
    return {
        "units": {
            "name": "N-m-C-kg",
            "force": "N",
            "length": "m",
            "mass": "kg",
            "temperature": "C",
            "time": "s",
            "rotation": "rad",
        },
        "materials": [{"id": "steel", "E": 200.0e9, "alpha": 1.2e-5}],
        "sections": [{"id": "section", "A": 0.01, "I": 1.0e-4}],
        "nodes": [
            {"id": 1, "x": 0.0, "y": 0.0, "restraints": {"ux": True, "uy": True, "rz": True}},
            {"id": 2, "x": 3.0, "y": 0.0, "restraints": {"ux": False, "uy": False, "rz": False}},
        ],
        "elements": [
            {"id": 1, "type": "frame", "node_i": 1, "node_j": 2, "material": "steel", "section": "section"}
        ],
        "nodal_loads": [{"node": 2, "fx": 0.0, "fy": -1000.0, "mz": 0.0}],
        "analysis_options": {"num_modes": 2},
        "diagram_display_convention": {"convention_name": "Ftool-style"},
    }


def test_save_json_and_companion_masses(tmp_path):
    model_path = tmp_path / "saved_model.json"
    masses = {
        2: {"ux": 15.0, "uy": 0.0, "rz": 0.0},
        3: {"ux": 7.5, "uy": 0.0, "rz": 0.0},
    }

    mass_path = save_model_files(model_path, _simple_model(), masses)

    saved = json.loads(model_path.read_text(encoding="utf-8"))
    assert saved["nodes"]
    assert saved["elements"]
    assert saved["materials"]
    assert saved["sections"]
    assert mass_path == companion_mass_path(model_path)
    assert sum(values["ux"] for values in load_companion_mass_mapping(model_path).values()) == pytest.approx(22.5)


def test_fallback_masses_are_not_saved_as_explicit_mapping(tmp_path):
    model_path = tmp_path / "fallback_model.json"
    companion_mass_path(model_path).write_text(
        json.dumps({"2": {"ux": 999.0}}),
        encoding="utf-8",
    )

    mass_path = save_model_files(model_path, _simple_model(), {})

    assert model_path.exists()
    assert mass_path is None
    assert not companion_mass_path(model_path).exists()


def test_saved_json_and_companion_can_be_reopened(tmp_path):
    model_path = tmp_path / "reopen_model.json"
    masses = {2: {"ux": 22.5, "uy": 0.0, "rz": 0.0}}
    save_model_files(model_path, _simple_model(), masses)

    data, embedded_masses = load_model_file_data(model_path)
    reopened_masses = load_companion_mass_mapping(model_path)

    assert embedded_masses is None
    assert len(data["nodes"]) == 2
    assert reopened_masses == masses


def test_generated_model_save_as_preserves_explicit_masses(tmp_path):
    source = ROOT / "inputs" / "generated" / "model_a_5story_unbraced.json"
    data, _embedded = load_model_file_data(source)
    masses = load_companion_mass_mapping(source)
    target = tmp_path / "generated_copy.json"

    save_model_files(target, data, masses)

    assert target.exists()
    assert companion_mass_path(target).exists()
    assert sum(values["ux"] for values in load_companion_mass_mapping(target).values()) == pytest.approx(500000.0)


def test_xml_and_text_sources_export_to_json_without_overwrite(tmp_path):
    for source in (
        ROOT / "inputs" / "regression" / "xml" / "regression_thermal_combined_frame.xml",
        ROOT / "inputs" / "examples" / "basic_cantilever_beam.txt",
    ):
        original = source.read_text(encoding="utf-8")
        data, _masses = load_model_file_data(source)
        target = tmp_path / f"{source.stem}.json"

        save_model_files(target, data, {})

        assert target.exists()
        assert source.read_text(encoding="utf-8") == original


def test_save_model_package_contains_model_masses_and_readme(tmp_path):
    package_path = tmp_path / "example_package.zip"
    masses = {2: {"ux": 22.5, "uy": 0.0, "rz": 0.0}}

    create_model_package(
        package_path,
        "example",
        _simple_model(),
        masses,
        "companion mass file: example_masses.json",
    )

    with zipfile.ZipFile(package_path) as archive:
        assert set(archive.namelist()) == {
            "example.json",
            "example_masses.json",
            "README.txt",
        }
        readme = archive.read("README.txt").decode("utf-8")
        assert "File -> Open Model... -> example.json" in readme
        assert "Modal mass source: companion mass file" in readme
