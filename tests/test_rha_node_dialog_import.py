from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"

for path in (SRC_ROOT, ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


def test_rha_node_dialog_imports_without_mainloop():
    from gui.rha_node_dialog import RhaNodeResponseDialog, open_rha_node_dialog

    assert callable(open_rha_node_dialog)
    assert RhaNodeResponseDialog is not None
