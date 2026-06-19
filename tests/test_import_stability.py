from __future__ import annotations

import importlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
IO_ROOT = SRC_ROOT / "io"

for path in (SRC_ROOT, IO_ROOT, ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


CORE_IMPORTS = [
    "model.structure",
    "model.frame_element",
    "analysis.axis_transformation",
    "analysis.modal_solver",
    "postprocessing.static_results",
    "postprocessing.modal_results",
    "postprocessing.drift_results",
    "visualization.static_plots",
    "visualization.modal_plots",
]

OPTIONAL_IMPORTS = [
    "analysis.modal_rha",
    "postprocessing.comparison_results",
]


def test_core_imports_do_not_trigger_circular_import_errors():
    for module_name in CORE_IMPORTS:
        module = importlib.import_module(module_name)
        assert module is not None


def test_active_optional_imports_do_not_break_core_package_imports():
    for module_name in OPTIONAL_IMPORTS:
        module = importlib.import_module(module_name)
        assert module is not None

