from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from analysis.modal_combination import (  # noqa: E402
    combine_abssum,
    combine_cqc,
    combine_srss,
    cqc_correlation_coefficient,
)


def test_abssum_and_srss_examples():
    assert combine_abssum([2.0, -3.0, 4.0]) == pytest.approx(9.0)
    assert combine_srss([3.0, 4.0]) == pytest.approx(5.0)


def test_cqc_correlation_is_symmetric_and_unity_on_diagonal():
    assert cqc_correlation_coefficient(4.0, 4.0) == pytest.approx(1.0)
    assert cqc_correlation_coefficient(4.0, 10.0) == pytest.approx(
        cqc_correlation_coefficient(10.0, 4.0)
    )


def test_cqc_approaches_srss_for_well_separated_modes():
    values = np.array([3.0, 4.0])
    omegas = np.array([1.0, 20.0])

    assert combine_cqc(values, omegas) == pytest.approx(combine_srss(values), rel=0.01)
