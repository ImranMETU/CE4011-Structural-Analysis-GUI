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


def test_rsa_dialog_imports_without_mainloop():
    from gui.rsa_dialog import ResponseSpectrumAnalysisDialog, open_rsa_dialog

    assert callable(open_rsa_dialog)
    assert ResponseSpectrumAnalysisDialog is not None
