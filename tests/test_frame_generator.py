from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"

for path in (SRC_ROOT, ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from generators.frame_generator import generate_floor_mass_mapping, generate_frame_model  # noqa: E402
from model.structure import Structure  # noqa: E402
from postprocessing.static_results import run_static_analysis  # noqa: E402


def test_frame_generator_imports_successfully():
    import generators.frame_generator as frame_generator

    assert callable(frame_generator.generate_frame_model)


def test_generated_model_counts_for_unbraced_frame():
    data = generate_frame_model(n_stories=2, n_bays=3, story_height=3.0, bay_width=5.0)

    assert len(data["nodes"]) == (3 + 1) * (2 + 1)
    frame_elements = [element for element in data["elements"] if element["type"] == "frame"]
    assert len(frame_elements) == 2 * (3 + 1) + 2 * 3
    assert not any(element["type"] == "truss" for element in data["elements"])


def test_braced_model_has_truss_elements():
    data = generate_frame_model(n_stories=2, n_bays=2, story_height=3.0, bay_width=5.0, braced=True)

    truss_elements = [element for element in data["elements"] if element["type"] == "truss"]
    assert len(truss_elements) == 2 * 2


def test_base_nodes_fixed_and_upper_nodes_free():
    data = generate_frame_model(n_stories=1, n_bays=2, story_height=3.0, bay_width=5.0)

    for node in data["nodes"]:
        if node["y"] == 0.0:
            assert node["restraints"] == {"ux": True, "uy": True, "rz": True}
        else:
            assert node["restraints"] == {"ux": False, "uy": False, "rz": False}


def test_lateral_loads_are_assigned_to_floor_nodes():
    data = generate_frame_model(
        n_stories=2,
        n_bays=1,
        story_height=3.0,
        bay_width=5.0,
        lateral_load_per_floor=12000.0,
    )

    assert len(data["nodal_loads"]) == 2 * (1 + 1)
    assert all(load["fx"] == 6000.0 for load in data["nodal_loads"])
    assert all(load["fy"] == 0.0 and load["mz"] == 0.0 for load in data["nodal_loads"])


def test_generated_dictionary_can_build_structure_and_solve_static():
    data = generate_frame_model(n_stories=1, n_bays=1, story_height=3.0, bay_width=5.0)

    structure = Structure.from_dict(data)
    result = run_static_analysis(data)

    assert structure.n_active_dofs > 0
    assert result["displacements"]
    assert result["reactions"]
    assert result["member_end_forces"]


def test_mass_mapping_assigns_floor_mass_to_non_base_nodes():
    data = generate_frame_model(n_stories=2, n_bays=1, story_height=3.0, bay_width=5.0)

    mapping = generate_floor_mass_mapping(data, floor_mass=20000.0)

    assert set(mapping) == {3, 4, 5, 6}
    assert all(mass["ux"] == 10000.0 for mass in mapping.values())
    assert all(mass["uy"] == 0.0 and mass["rz"] == 0.0 for mass in mapping.values())


def test_generated_proposal_models_can_be_written_to_temp_directory(tmp_path):
    specs = [
        ("model_a_5story_unbraced", {"n_stories": 5, "n_bays": 1, "braced": False}),
        ("model_b_10story_unbraced", {"n_stories": 10, "n_bays": 2, "braced": False}),
        ("model_c_10story_braced", {"n_stories": 10, "n_bays": 2, "braced": True}),
    ]

    for name, spec in specs:
        data = generate_frame_model(story_height=3.0, bay_width=6.0, **spec)
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        assert path.exists()
        assert json.loads(path.read_text(encoding="utf-8"))["nodes"]
