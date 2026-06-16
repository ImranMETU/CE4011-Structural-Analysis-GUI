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


def test_eigen_calculator_dialog_module_imports():
    import gui.eigen_calculator_dialog as dialog

    assert hasattr(dialog, "EigenanalysisCalculatorDialog")
    assert callable(dialog.open_eigen_calculator_dialog)


def test_static_app_imports_with_eigen_calculator_menu_hook():
    from gui.static_app import StaticAnalysisApp

    assert hasattr(StaticAnalysisApp, "open_eigenanalysis_calculator")


def test_launcher_import_does_not_start_gui_mainloop():
    launcher_path = ROOT / "scripts" / "run_static_gui.py"
    spec = importlib.util.spec_from_file_location("run_static_gui_eigen_import_test", launcher_path)
    module = importlib.util.module_from_spec(spec)

    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)

    assert hasattr(module, "main")
