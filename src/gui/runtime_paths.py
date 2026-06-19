"""Resolve project data paths in source and PyInstaller builds."""

from __future__ import annotations

import sys
from pathlib import Path


def resource_root() -> Path:
    """Return the directory containing bundled ``inputs`` data."""
    bundled_root = getattr(sys, "_MEIPASS", None)
    if bundled_root:
        return Path(bundled_root)
    return Path(__file__).resolve().parents[2]
