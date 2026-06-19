from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from visualization.diagram_conventions import (
    ForceDiagramConvention,
    default_force_diagram_convention,
    ftool_force_diagram_convention,
    get_display_sign,
    internal_force_diagram_convention,
)


def test_default_and_named_diagram_conventions_exist():
    assert default_force_diagram_convention() == ftool_force_diagram_convention()
    assert ftool_force_diagram_convention().convention_name == "Ftool-style"
    assert internal_force_diagram_convention().convention_name == "Internal sign convention"


@pytest.mark.parametrize("quantity", ["axial", "shear", "moment", "N", "V", "M"])
def test_display_sign_is_numeric_for_supported_quantities(quantity):
    assert get_display_sign(quantity, default_force_diagram_convention()) in {-1.0, 1.0}


def test_moment_tension_and_compression_are_opposite():
    tension = ForceDiagramConvention("Custom", "tension", "top", "top")
    compression = ForceDiagramConvention("Custom", "compression", "top", "top")

    assert get_display_sign("moment", tension) == -get_display_sign("moment", compression)


def test_shear_top_and_bottom_are_opposite():
    top = ForceDiagramConvention("Custom", "tension", "top", "top")
    bottom = ForceDiagramConvention("Custom", "tension", "bottom", "top")

    assert get_display_sign("shear", top) == -get_display_sign("shear", bottom)


def test_axial_top_and_bottom_are_opposite():
    top = ForceDiagramConvention("Custom", "tension", "top", "top")
    bottom = ForceDiagramConvention("Custom", "tension", "top", "bottom")

    assert get_display_sign("axial", top) == -get_display_sign("axial", bottom)


def test_internal_convention_keeps_internal_plot_signs():
    convention = internal_force_diagram_convention()

    assert get_display_sign("axial", convention) == 1.0
    assert get_display_sign("shear", convention) == 1.0
    assert get_display_sign("moment", convention) == 1.0

