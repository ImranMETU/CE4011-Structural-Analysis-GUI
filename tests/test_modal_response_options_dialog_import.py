from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"

for path in (SRC_ROOT, ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


def test_modal_response_options_dialog_imports_without_mainloop():
    from gui.modal_response_options_dialog import (
        ModalResponseOptionsDialog,
        open_modal_response_options_dialog,
    )

    assert ModalResponseOptionsDialog is not None
    assert callable(open_modal_response_options_dialog)
