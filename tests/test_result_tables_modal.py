from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "src" / "io", ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from analysis.modal_solver import solve_modal_analysis  # noqa: E402
from gui.result_tables import (  # noqa: E402
    format_modal_force_coefficient_rows,
    format_modal_participation_rows,
    format_modal_properties_rows,
    format_modal_response_factors_rows,
)
from gui.static_app import StaticAnalysisApp, _load_companion_masses, load_model_data  # noqa: E402
from model.structure import Structure  # noqa: E402
from postprocessing.modal_results import apply_mode_shape_sign_convention, package_modal_results  # noqa: E402


def _ce586_result():
    path = ROOT / "inputs" / "examples" / "CE586_Examples_6_4_6_6_frame_model.json"
    structure = Structure.from_dict(load_model_data(path))
    result = package_modal_results(
        solve_modal_analysis(structure, _load_companion_masses(path), n_modes=3),
        structure,
    )
    return apply_mode_shape_sign_convention(result, "roof ux positive")


def test_modal_properties_contains_only_basic_modal_information():
    headers, rows = format_modal_properties_rows(_ce586_result())

    assert headers == [
        "Mode", "eigenvalue lambda = omega^2", "omega [rad/s]",
        "frequency [Hz]", "period [s]", "Normalization",
        "Sign convention", "Roof phi",
    ]
    assert len(rows) == 3
    assert "Gamma" not in headers
    assert "Mn" not in headers


def test_modal_participation_uses_ce586_response_parameter_source():
    headers, rows = format_modal_participation_rows(_ce586_result())

    assert headers[0:6] == [
        "Mode", "Mn", "Lnh", "Gamma = Lnh/Mn",
        "Ln_theta", "h_star = Ln_theta/Lnh",
    ]
    mn, lnh, gamma = map(float, rows[0][1:4])
    assert mn == pytest.approx(45.3295, rel=1.0e-4)
    assert lnh == pytest.approx(64.4135, rel=1.0e-4)
    assert gamma == pytest.approx(lnh / mn, rel=1.0e-5)


def test_modal_response_factors_and_legacy_wrapper_match():
    headers, rows = format_modal_response_factors_rows(_ce586_result())
    old_headers, old_rows = format_modal_force_coefficient_rows(_ce586_result())

    assert old_headers == headers
    assert old_rows == rows
    assert "sn = Gamma*m*phi" in headers
    assert "u_coeff = Gamma*phi/omega^2" in headers
    assert "Vb_coeff = sum(sn)" in headers
    assert "Mb_coeff = sum(sn*h)" in headers


def test_modal_menu_is_nested_and_hides_redundant_entries():
    source = inspect.getsource(StaticAnalysisApp._build_menu)

    assert 'add_cascade(label="Modal", menu=modal_tables_menu)' in source
    assert 'modal_tables_menu.add_command(label="Modal Response Factors"' in source
    assert 'modal_tables_menu.add_command(label="Modal Properties"' in source
    assert 'modal_tables_menu.add_command(label="Modal Participation Factors"' in source
    assert 'modal_tables_menu.add_command(label="Modal Response Parameters"' not in source
    assert 'modal_tables_menu.add_command(label="Modal Force Coefficients sn"' not in source
