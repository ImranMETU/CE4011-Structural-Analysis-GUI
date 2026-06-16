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
from postprocessing.comparison_results import (  # noqa: E402
    compare_two_models,
    compute_model_summary,
    percent_change,
    percent_reduction,
)


def _summary(**overrides):
    base = {
        "model_name": "model",
        "roof_displacement_ux": 10.0,
        "max_story_drift": 5.0,
        "max_drift_ratio": 0.02,
        "f1_Hz": 2.0,
        "T1_s": 0.5,
        "warnings": [],
    }
    base.update(overrides)
    return base


def test_comparison_module_imports():
    import postprocessing.comparison_results as comparison

    assert callable(comparison.compute_model_summary)


def test_percent_change_and_reduction_helpers():
    warnings = []

    assert percent_change(2.0, 3.0, warnings=warnings) == 50.0
    assert percent_reduction(10.0, 7.5, warnings=warnings) == 25.0
    assert warnings == []


def test_percent_helpers_handle_zero_denominator():
    warnings = []

    assert percent_change(0.0, 3.0, "zero change", warnings) is None
    assert percent_reduction(None, 3.0, "missing reduction", warnings) is None
    assert len(warnings) == 2


def test_model_summary_can_be_computed_for_small_generated_frame(tmp_path):
    data = generate_frame_model(n_stories=2, n_bays=1, story_height=3.0, bay_width=6.0)
    masses = generate_floor_mass_mapping(data, floor_mass=10000.0)
    model_path = tmp_path / "small_frame.json"
    mass_path = tmp_path / "small_frame_masses.json"
    model_path.write_text(json.dumps(data), encoding="utf-8")
    mass_path.write_text(json.dumps(masses), encoding="utf-8")

    summary = compute_model_summary("small", model_path, mass_path, num_modes=2)

    assert summary["node_count"] == 6
    assert summary["frame_element_count"] == 6
    assert summary["roof_displacement_ux"] is not None
    assert summary["f1_Hz"] is not None


def test_compare_two_models_returns_expected_keys_and_warnings():
    unbraced = _summary(model_name="unbraced")
    braced = _summary(model_name="braced", roof_displacement_ux=12.0, max_story_drift=6.0, f1_Hz=1.0)

    comparison = compare_two_models(unbraced, braced)

    assert "roof_displacement_reduction_percent" in comparison["metrics"]
    assert "fundamental_frequency_increase_percent" in comparison["metrics"]
    assert comparison["warnings"]


def test_braced_generated_model_has_more_truss_elements_than_unbraced(tmp_path):
    unbraced = generate_frame_model(n_stories=2, n_bays=2, story_height=3.0, bay_width=6.0, braced=False)
    braced = generate_frame_model(n_stories=2, n_bays=2, story_height=3.0, bay_width=6.0, braced=True)
    unbraced_path = tmp_path / "unbraced.json"
    braced_path = tmp_path / "braced.json"
    unbraced_path.write_text(json.dumps(unbraced), encoding="utf-8")
    braced_path.write_text(json.dumps(braced), encoding="utf-8")

    unbraced_summary = compute_model_summary("unbraced", unbraced_path)
    braced_summary = compute_model_summary("braced", braced_path)

    assert braced_summary["truss_element_count"] > unbraced_summary["truss_element_count"]
