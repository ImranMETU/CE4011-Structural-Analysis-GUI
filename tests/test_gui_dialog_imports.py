from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
IO_ROOT = SRC_ROOT / "io"

for path in (SRC_ROOT, IO_ROOT, ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


def test_input_dialog_module_imports_successfully():
    import gui.input_dialogs as dialogs

    assert callable(dialogs.open_materials_dialog)
    assert callable(dialogs.open_sections_dialog)
    assert callable(dialogs.open_nodes_dialog)
    assert callable(dialogs.open_analysis_options_dialog)


def test_model_builder_module_imports_successfully():
    from gui.model_builder import ModelBuilder

    assert ModelBuilder.__name__ == "ModelBuilder"


def test_launcher_import_remains_safe():
    launcher_path = ROOT / "scripts" / "run_static_gui.py"
    spec = importlib.util.spec_from_file_location("run_static_gui_dialog_import_test", launcher_path)
    module = importlib.util.module_from_spec(spec)

    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)

    assert hasattr(module, "main")
