"""2D frame member local-axis offset transformations.

This module implements a controlled 2D rigid end/neutral-axis offset in the
member local-y direction. For each frame end, the neutral-axis local DOFs are
related to reference-line DOFs by:

    u_neutral = u_ref - e * theta_ref
    v_neutral = v_ref
    theta_neutral = theta_ref

This is not a full 3D offset formulation and is only intended for 2D frame
elements with local-y eccentricity.
"""

from __future__ import annotations

from typing import Any

import numpy as np


def build_2d_axis_offset_matrix(offset_i: float = 0.0, offset_j: float = 0.0) -> np.ndarray:
    """Return the 6x6 local displacement transform for 2D frame axis offsets.

    The returned matrix ``A`` maps reference-line local displacements to
    neutral-axis local displacements:

        d_neutral = A @ d_reference

    Positive offsets follow the element local-y sign convention.
    """
    ei = float(offset_i)
    ej = float(offset_j)
    matrix = np.eye(6, dtype=float)
    matrix[0, 2] = -ei
    matrix[3, 5] = -ej
    return matrix


def transform_frame_local_stiffness_for_offsets(
    k_local: Any,
    offset_i: float = 0.0,
    offset_j: float = 0.0,
) -> list[list[float]]:
    """Transform neutral-axis local frame stiffness to reference-line DOFs.

    With ``d_neutral = A d_reference``, virtual work gives:

        K_reference = A.T @ K_neutral @ A
    """
    k = np.asarray(k_local, dtype=float)
    _validate_6_vector_or_matrix(k, "k_local", matrix=True)
    a = build_2d_axis_offset_matrix(offset_i, offset_j)
    return (a.T @ k @ a).tolist()


def transform_frame_fixed_end_forces_for_offsets(
    f_local: Any,
    offset_i: float = 0.0,
    offset_j: float = 0.0,
) -> list[float]:
    """Transform neutral-axis fixed-end forces to reference-line generalized forces."""
    f = np.asarray(f_local, dtype=float)
    _validate_6_vector_or_matrix(f, "f_local", matrix=False)
    a = build_2d_axis_offset_matrix(offset_i, offset_j)
    return (a.T @ f).tolist()


def axis_offset_record(offset_i: float = 0.0, offset_j: float = 0.0) -> dict[str, float]:
    """Return the model-data schema record for local-y frame axis offsets."""
    return {"i_local_y": float(offset_i), "j_local_y": float(offset_j)}


def _validate_6_vector_or_matrix(values: np.ndarray, label: str, matrix: bool) -> None:
    expected = (6, 6) if matrix else (6,)
    if values.shape != expected:
        raise ValueError(f"{label} must have shape {expected}.")
