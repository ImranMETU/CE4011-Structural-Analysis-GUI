from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from postprocessing.modal_response_parameters import compute_modal_generalized_parameters  # noqa: E402
from postprocessing.modal_rsa_results import (  # noqa: E402
    compute_modal_rsa_responses,
    compute_rsa_combinations,
    interpolate_spectrum_at_periods,
)


def _parameters():
    return compute_modal_generalized_parameters(
        np.array([[0.5, -0.25], [1.0, 1.0]]),
        np.array([10.0, 5.0]),
        np.array([2.0, 5.0]),
        np.array([3.0, 6.0]),
    )


def test_spectrum_interpolation_at_modal_periods():
    values, warnings = interpolate_spectrum_at_periods(
        [0.5, 1.5], [0.0, 1.0, 2.0], [1.0, 3.0, 5.0]
    )

    assert values == pytest.approx([2.0, 4.0])
    assert warnings == []


def test_modal_rsa_responses_use_shared_response_factors():
    parameters = _parameters()
    periods = [row["period_s"] for row in parameters["rows"]]
    spectrum = {"periods": periods, "Sa": [2.0, 3.0], "damping_ratio": 0.05}

    result = compute_modal_rsa_responses(parameters, spectrum)

    for idx, row in enumerate(parameters["rows"]):
        assert result["modal_displacements"][idx] == pytest.approx(row["u_coeff"] * result["modal_spectrum_values"][idx])
        assert result["modal_forces"][idx] == pytest.approx(row["sn"] * result["modal_spectrum_values"][idx])
        assert result["modal_base_shear"][idx] == pytest.approx(row["Vb_coeff"] * result["modal_spectrum_values"][idx])
        assert result["modal_base_moment"][idx] == pytest.approx(row["Mb_coeff"] * result["modal_spectrum_values"][idx])


def test_rsa_combinations_include_floor_and_base_quantities():
    parameters = _parameters()
    spectrum = {
        "periods": [row["period_s"] for row in parameters["rows"]],
        "Sa": [2.0, 3.0],
        "damping_ratio": 0.05,
    }
    responses = compute_modal_rsa_responses(parameters, spectrum)
    combined = compute_rsa_combinations(responses)

    assert len(combined["floor_displacements"]) == 2
    assert len(combined["floor_forces"]) == 2
    assert {"ABSSUM", "SRSS", "CQC"} <= set(combined["base_shear"])
    assert combined["cqc_correlation_matrix"].shape == (2, 2)
