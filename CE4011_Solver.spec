# -*- mode: python ; coding: utf-8 -*-
"""Reliable Windows onedir build for the CE4011 Tkinter GUI."""

from pathlib import Path


PROJECT_ROOT = Path(SPECPATH).resolve()
SRC_DIR = PROJECT_ROOT / "src"
IO_DIR = SRC_DIR / "io"


def include_if_present(relative_path, destination=None):
    """Return a PyInstaller data entry only when the project artifact exists."""
    source = PROJECT_ROOT / relative_path
    if not source.exists():
        return []
    target = destination if destination is not None else str(Path(relative_path).parent)
    if target == ".":
        target = "."
    return [(str(source), target)]


datas = []

# Runtime/demo data. Including inputs recursively preserves generated model
# companion files such as model_a_5story_unbraced_masses.json.
for folder in ("inputs", "examples", "verification", "selected_results"):
    datas += include_if_present(folder, folder)

# Submission and user documentation, included when present.
for filename in (
    "README.md",
    "requirements.txt",
    "USER_MANUAL.pdf",
    "INSTALLATION_MANUAL.pdf",
    "PROJECT_REPORT.pdf",
    "video_link.txt",
    "GitHub_link.txt",
    "INSTALLER_README.txt",
):
    datas += include_if_present(filename, ".")


analysis = Analysis(
    [str(PROJECT_ROOT / "scripts" / "run_static_gui.py")],
    pathex=[
        str(PROJECT_ROOT),
        str(SRC_DIR),
        str(IO_DIR),
    ],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "tests"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="CE4011_Solver",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

collect = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="CE4011_Solver",
)
