from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"

for path in (SRC_ROOT, ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


from analysis.eigen_calculator import (  # noqa: E402
    compute_modal_properties,
    format_eigenvalue_table,
    format_eigenvector_table,
    format_modal_property_table,
    normalize_modes,
    solve_generalized_eigen,
)


def _two_dof_matrices():
    k = np.array([[3.0, -1.0], [-1.0, 1.0]], dtype=float)
    m = np.array([[2.0, 0.0], [0.0, 1.0]], dtype=float)
    return k, m


def test_simple_2dof_generalized_eigenproblem_returns_positive_sorted_frequencies():
    k, m = _two_dof_matrices()

    result = solve_generalized_eigen(k, m)

    assert len(result["eigenvalues"]) == 2
    assert np.all(result["frequency_Hz"] > 0.0)
    assert np.all(np.diff(result["frequency_Hz"]) >= 0.0)
    assert result["modes"].shape == (2, 2)


def test_mass_normalization_gives_unit_modal_mass():
    k, m = _two_dof_matrices()

    result = solve_generalized_eigen(k, m, normalize="mass")

    assert result["modal_mass"] == pytest.approx([1.0, 1.0])


def test_last_dof_positive_normalization_makes_last_component_positive_when_possible():
    modes = np.array([[2.0, -1.0], [-4.0, 3.0]], dtype=float)

    normalized = normalize_modes(modes, method="last_dof_positive")

    assert normalized[-1, 0] > 0.0
    assert normalized[-1, 1] > 0.0
    assert np.max(np.abs(normalized[:, 0])) == pytest.approx(1.0)


def test_damping_ratio_calculation_works_for_supplied_c_matrix():
    k, m = _two_dof_matrices()
    c = 0.05 * m
    result = solve_generalized_eigen(k, m, normalize="mass")

    props = compute_modal_properties(k, m, C=c, modes=result["modes"])

    assert "modal_damping" in props
    assert "damping_ratio" in props
    assert np.all(np.isfinite(props["damping_ratio"]))
    assert np.all(props["damping_ratio"] > 0.0)


def test_participation_factors_and_effective_mass_ratios_are_computed():
    k, m = _two_dof_matrices()
    result = solve_generalized_eigen(k, m, normalize="mass")

    props = compute_modal_properties(k, m, modes=result["modes"], influence_vector=[1.0, 1.0])

    assert np.all(np.isfinite(props["participation_factor"]))
    assert np.all(props["effective_modal_mass"] >= 0.0)
    assert props["cumulative_effective_mass_ratio"][-1] == pytest.approx(1.0)


def test_format_helpers_return_expected_tables():
    k, m = _two_dof_matrices()
    result = solve_generalized_eigen(k, m)

    freq_headers, freq_rows = format_eigenvalue_table(result)
    prop_headers, prop_rows = format_modal_property_table(result)
    vec_headers, vec_rows = format_eigenvector_table(result)

    assert freq_headers == ["Mode", "Eigenvalue lambda", "omega rad/s", "frequency Hz", "period s"]
    assert prop_headers[0:3] == ["Mode", "Modal mass", "Modal stiffness"]
    assert vec_headers == ["DOF", "Mode 1", "Mode 2"]
    assert len(freq_rows) == 2
    assert len(prop_rows) == 2
    assert len(vec_rows) == 2


def test_invalid_matrix_dimensions_raise_clear_errors():
    k, m = _two_dof_matrices()

    with pytest.raises(ValueError, match="square"):
        solve_generalized_eigen([[1.0, 2.0]], m)

    with pytest.raises(ValueError, match="same shape"):
        solve_generalized_eigen(k, np.eye(3))

    with pytest.raises(ValueError, match="nonsingular"):
        solve_generalized_eigen(k, [[1.0, 0.0], [0.0, 0.0]])
