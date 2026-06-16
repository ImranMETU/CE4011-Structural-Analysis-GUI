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


from analysis.rayleigh_damping import (  # noqa: E402
    build_rayleigh_damping_matrix,
    format_rayleigh_table,
    rayleigh_coefficients,
    rayleigh_damping_ratios,
)


def test_ce586_example_6_1_rayleigh_coefficients_match_reference():
    omegas = np.array([11.57, 31.62, 43.20], dtype=float)

    a0, a1 = rayleigh_coefficients(omegas[0], 0.05, omegas[1], 0.05)

    assert a0 == pytest.approx(0.8473, rel=5.0e-4)
    assert a1 == pytest.approx(0.0023, rel=1.0e-2)


def test_ce586_example_6_1_third_damping_ratio_matches_reference():
    omegas = np.array([11.57, 31.62, 43.20], dtype=float)
    a0, a1 = rayleigh_coefficients(omegas[0], 0.05, omegas[1], 0.05)

    xis = rayleigh_damping_ratios(omegas, a0, a1)

    assert xis[0] == pytest.approx(0.05)
    assert xis[1] == pytest.approx(0.05)
    assert xis[2] == pytest.approx(0.0595, rel=8.0e-3)


def test_invalid_repeated_modes_are_rejected():
    with pytest.raises(ValueError, match="distinct"):
        rayleigh_coefficients(11.57, 0.05, 11.57, 0.05)


def test_zero_frequency_is_rejected():
    with pytest.raises(ValueError, match="positive"):
        rayleigh_coefficients(0.0, 0.05, 31.62, 0.05)

    with pytest.raises(ValueError, match="positive"):
        rayleigh_damping_ratios([11.57, 0.0], 0.8, 0.002)


def test_rayleigh_damping_matrix_and_table_helpers():
    mass = np.eye(2)
    stiffness = np.diag([10.0, 20.0])
    damping = build_rayleigh_damping_matrix(mass, stiffness, 0.2, 0.03)

    np.testing.assert_allclose(damping, [[0.5, 0.0], [0.0, 0.8]])

    omegas = np.array([2.0, 4.0])
    xis = rayleigh_damping_ratios(omegas, 0.2, 0.03)
    headers, rows = format_rayleigh_table(omegas, omegas / (2.0 * np.pi), 2.0 * np.pi / omegas, xis)

    assert headers == ["Mode", "omega rad/s", "frequency Hz", "period s", "Rayleigh xi"]
    assert rows[0][0] == "1"
    assert rows[1][-1] == f"{xis[1]:.6e}"
