from __future__ import annotations

import importlib.util
import inspect
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


def test_gui_package_imports_successfully():
    import gui

    assert hasattr(gui, "StaticAnalysisApp")


def test_static_app_class_exists():
    from gui.static_app import StaticAnalysisApp

    assert StaticAnalysisApp.__name__ == "StaticAnalysisApp"


def test_force_diagram_gui_defaults_use_auto_scale_multiplier():
    from gui.model_builder import DEFAULT_ANALYSIS_OPTIONS
    from gui.static_app import PLOT_SCALES

    assert DEFAULT_ANALYSIS_OPTIONS["force_diagram_scale"] == 1.0
    assert PLOT_SCALES["Axial Force Diagram"] == 1.0
    assert PLOT_SCALES["Shear Force Diagram"] == 1.0
    assert PLOT_SCALES["Bending Moment Diagram"] == 1.0


def test_toolbar_omits_legacy_mass_and_mode_sign_controls():
    from gui.static_app import DEFAULT_MODAL_SIGN_CONVENTION, StaticAnalysisApp

    source = inspect.getsource(StaticAnalysisApp._build_widgets)

    assert "Mass/free ux:" not in source
    assert "Mode sign:" not in source
    assert "Run Static Analysis" in source
    assert "Run Modal Analysis" in source
    assert "Modes:" in source
    assert "Mode scale:" in source
    assert "Show mode values" in source
    assert "Result View:" in source
    assert "Force mode:" not in source
    assert "A_n:" not in source
    assert "Use RHA" not in source
    assert "time index:" not in source
    assert 'text="Update"' not in source
    assert DEFAULT_MODAL_SIGN_CONVENTION == "roof ux positive"


def test_modal_response_options_are_available_from_display_menu():
    from gui.static_app import StaticAnalysisApp

    menu_source = inspect.getsource(StaticAnalysisApp._build_menu)

    assert "Modal Response / Force-State Options" in menu_source
    assert "open_modal_response_options" in menu_source


def test_diagram_display_convention_menu_and_default_are_available():
    from gui.static_app import StaticAnalysisApp
    from visualization.diagram_conventions import default_force_diagram_convention

    menu_source = inspect.getsource(StaticAnalysisApp._build_menu)

    assert "Diagram Display Conventions" in menu_source
    assert default_force_diagram_convention().convention_name == "Ftool-style"


def test_text_loader_imports_successfully():
    from text_loader import load_text_model, parse_text_model

    assert callable(load_text_model)
    assert callable(parse_text_model)


def test_launcher_import_does_not_start_mainloop():
    launcher_path = ROOT / "scripts" / "run_static_gui.py"
    spec = importlib.util.spec_from_file_location("run_static_gui_import_test", launcher_path)
    module = importlib.util.module_from_spec(spec)

    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)

    assert hasattr(module, "main")
