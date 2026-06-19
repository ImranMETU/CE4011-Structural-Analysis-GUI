from __future__ import annotations

import sys
import inspect
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from gui.result_tables import (  # noqa: E402
    format_rsa_combined_response_rows,
    format_rsa_modal_base_response_factor_rows,
    format_rsa_modal_response_factor_rows,
    format_rsa_spectrum_at_modal_period_rows,
)
from gui.static_app import StaticAnalysisApp  # noqa: E402
from postprocessing.modal_response_parameters import compute_modal_generalized_parameters  # noqa: E402
from postprocessing.modal_rsa_results import compute_modal_rsa_responses, compute_rsa_combinations  # noqa: E402


def _rsa_result():
    parameters = compute_modal_generalized_parameters(
        np.array([[0.5], [1.0]]), np.array([10.0, 5.0]), np.array([2.0]), np.array([3.0, 6.0])
    )
    spectrum = {
        "periods": [parameters["rows"][0]["period_s"]],
        "Sa": [2.5],
        "damping_ratio": 0.05,
        "source": "synthetic",
    }
    responses = compute_modal_rsa_responses(parameters, spectrum)
    return {
        "response_factor_results": responses,
        "response_factor_combinations": compute_rsa_combinations(responses),
    }


def test_rsa_factor_tables_expose_separate_coefficients_and_responses():
    rsa = _rsa_result()
    spectrum_headers, spectrum_rows = format_rsa_spectrum_at_modal_period_rows(rsa)
    response_headers, response_rows = format_rsa_modal_response_factor_rows(rsa)
    base_headers, base_rows = format_rsa_modal_base_response_factor_rows(rsa)
    combined_headers, combined_rows = format_rsa_combined_response_rows(rsa)

    assert "Sa(T_n) [m/s^2]" in spectrum_headers
    assert spectrum_rows[0][-1] == "synthetic"
    assert response_headers == ["Mode", "Floor / DOF", "Height h [m]", "phi", "u_coeff", "Sa(T_n)", "u_n", "sn", "f_n"]
    assert response_rows
    assert base_headers == ["Mode", "Sa(T_n)", "Vb_coeff", "Vbn", "Mb_coeff", "Mbn"]
    assert base_rows
    assert combined_headers == ["Quantity", "Location", "ABSSUM", "SRSS", "CQC"]
    assert any(row[0] == "Base shear Vb" for row in combined_rows)


def test_gui_exposes_nested_rsa_tables_and_modal_force_state():
    source = inspect.getsource(StaticAnalysisApp._build_menu)

    assert 'tables_menu.add_cascade(label="RSA", menu=rsa_tables_menu)' in source
    assert 'rsa_tables_menu.add_command(label="Spectrum at Modal Periods"' in source
    assert 'rsa_tables_menu.add_command(label="Modal Responses"' in source
    assert 'rsa_tables_menu.add_command(label="Modal Base Responses"' in source
    assert 'rsa_tables_menu.add_command(label="Combined Responses"' in source
    assert '("Modal Force State", "RSA Modal Force State")' in source
