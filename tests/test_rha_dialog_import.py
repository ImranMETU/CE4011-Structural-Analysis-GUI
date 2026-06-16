from __future__ import annotations

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


def test_rha_dialog_module_imports_safely():
    import gui.rha_dialog as dialog

    assert hasattr(dialog, "ResponseHistoryAnalysisDialog")
    assert callable(dialog.open_rha_dialog)


def test_static_app_imports_with_rha_hook():
    from gui.static_app import StaticAnalysisApp

    assert hasattr(StaticAnalysisApp, "open_response_history_analysis")
