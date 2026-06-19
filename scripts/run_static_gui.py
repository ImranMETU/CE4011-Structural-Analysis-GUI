"""Launch the CE4011 static result viewer."""

from __future__ import annotations

import sys
from pathlib import Path

# Resolve paths from this launcher, not from the caller's working directory.
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
SRC_DIR = PROJECT_ROOT / "src"
IO_DIR = SRC_DIR / "io"

if not getattr(sys, "frozen", False) and not SRC_DIR.is_dir():
    raise RuntimeError(f"CE4011 source directory was not found: {SRC_DIR}")

for import_path in (SRC_DIR, IO_DIR, PROJECT_ROOT):
    path_str = str(import_path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from gui.static_app import main  # noqa: E402


if __name__ == "__main__":
    main()
