from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "verification" / "gui_case_manifest.json"
ALLOWED_EXPECTED_BEHAVIORS = {"solve", "warning", "error"}


def test_gui_verification_manifest_json_is_valid():
    cases = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert isinstance(cases, list)
    assert cases
    assert all("id" in case for case in cases)


def test_gui_verification_manifest_input_paths_exist():
    cases = json.loads(MANIFEST.read_text(encoding="utf-8"))

    for case in cases:
        assert (ROOT / case["input_path"]).exists(), case["input_path"]


def test_gui_verification_manifest_expected_behavior_values():
    cases = json.loads(MANIFEST.read_text(encoding="utf-8"))

    for case in cases:
        assert case["expected_behavior"] in ALLOWED_EXPECTED_BEHAVIORS


def test_gui_backend_verification_script_imports_without_gui_mainloop():
    script_path = ROOT / "scripts" / "run_gui_backend_verification.py"
    spec = importlib.util.spec_from_file_location("run_gui_backend_verification_import_test", script_path)
    module = importlib.util.module_from_spec(spec)

    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)

    assert hasattr(module, "main")
