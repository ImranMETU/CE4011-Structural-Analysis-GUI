from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"

for path in (SRC_ROOT, ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from analysis.modal_combination import combine_abssum, combine_cqc, combine_srss  # noqa: E402


def test_abssum_and_srss_basic_values():
    assert combine_abssum([3.0, 4.0]) == pytest.approx(7.0)
    assert combine_srss([3.0, 4.0]) == pytest.approx(5.0)


def test_cqc_widely_separated_modes_is_close_to_srss():
    cqc = combine_cqc([3.0, 4.0], [1.0, 100.0], damping_ratio=0.02)
    srss = combine_srss([3.0, 4.0])

    assert cqc == pytest.approx(srss, rel=1.0e-3)


def test_cqc_similar_modes_exceeds_srss_for_same_sign_values():
    cqc = combine_cqc([3.0, 4.0], [10.0, 10.1], damping_ratio=0.05)
    srss = combine_srss([3.0, 4.0])

    assert cqc > srss


def test_cqc_rejects_invalid_omega_and_mismatched_lengths():
    with pytest.raises(ValueError, match="positive"):
        combine_cqc([1.0, 2.0], [1.0, 0.0])
    with pytest.raises(ValueError, match="same length"):
        combine_cqc([1.0, 2.0], [1.0])


def test_cqc_handles_tiny_negative_roundoff_safely():
    assert combine_cqc([1.0, -1.0], [1.0, 1.0], damping_ratio=0.05) == pytest.approx(0.0)
