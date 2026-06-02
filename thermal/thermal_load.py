"""Thermal member-load utilities for 2D frame elements."""

from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class ThermalLoadInput:
    """Normalized thermal load state for one member."""

    T_uniform: float = 0.0
    delta_T: float = 0.0


def normalize_thermal_input(load: Mapping[str, float]) -> ThermalLoadInput:
    """Normalize user thermal input to (T_uniform, delta_T).

    Convention:
      T_uniform = 0.5 * (T_top + T_bottom)
      delta_T   = T_bottom - T_top

    With this definition, a hotter bottom fiber (T_bottom > T_top) yields
    positive delta_T and therefore positive sagging thermal curvature.
    """
    if "T_top" in load or "T_bottom" in load:
        if "T_top" not in load or "T_bottom" not in load:
            raise ValueError("Thermal load with T_top/T_bottom must provide both values.")

        t_top = float(load["T_top"])
        t_bottom = float(load["T_bottom"])
        t_uniform = 0.5 * (t_top + t_bottom)
        delta_t = t_bottom - t_top
        return ThermalLoadInput(T_uniform=t_uniform, delta_T=delta_t)

    t_uniform = float(load.get("T_uniform", 0.0))
    delta_t = float(load.get("delta_T", 0.0))
    return ThermalLoadInput(T_uniform=t_uniform, delta_T=delta_t)


def compute_uniform_axial_force(E: float, A: float, alpha: float, T_uniform: float) -> float:
    """Return restrained thermal axial force magnitude: N = E A alpha T_uniform."""
    return float(E) * float(A) * float(alpha) * float(T_uniform)


def compute_gradient_moment(E: float, I: float, alpha: float, delta_T: float, d: float) -> float:
    """Return restrained thermal moment magnitude: M = E I alpha delta_T / d."""
    d_val = float(d)
    if d_val <= 0.0:
        raise ValueError("Section depth d must be positive for temperature-gradient thermal loading.")
    return float(E) * float(I) * float(alpha) * float(delta_T) / d_val


def get_fixed_end_forces_local(
    *,
    E: float,
    A: float,
    I: float,
    alpha: float,
    d: float | None,
    thermal_load: Mapping[str, float],
) -> list[float]:
    """
    Return local fixed-end action vector for thermal effects.

    Sign convention used (may be calibrated per solver convention):
      uniform:  [-N, 0, 0, +N, 0, 0]
      gradient: [ 0, 0, -M, 0, 0, +M]
    """
    t = normalize_thermal_input(thermal_load)

    out = [0.0] * 6

    if t.T_uniform != 0.0:
        n = compute_uniform_axial_force(E, A, alpha, t.T_uniform)
        out[0] += -n
        out[3] += n

    if t.delta_T != 0.0:
        if d is None:
            raise ValueError("Section depth d is required for thermal gradient loading.")
        m = compute_gradient_moment(E, I, alpha, t.delta_T, d)
        # THERMAL SIGN PATCH START
        out[2] += m
        out[5] += -m
        # THERMAL SIGN PATCH END

    return out


def get_equivalent_nodal_load_local(
    *,
    E: float,
    A: float,
    I: float,
    alpha: float,
    d: float | None,
    thermal_load: Mapping[str, float],
) -> list[float]:
    """Return local equivalent nodal vector for thermal loading."""
    return get_fixed_end_forces_local(
        E=E,
        A=A,
        I=I,
        alpha=alpha,
        d=d,
        thermal_load=thermal_load,
    )


def get_equivalent_nodal_load_global(
    local_vec: Sequence[float],
    transformation_matrix: Sequence[Sequence[float]],
) -> list[float]:
    """Convert local equivalent nodal vector to global: f_g = R^T f_l."""
    if len(local_vec) != 6:
        raise ValueError("local_vec must have length 6.")
    if len(transformation_matrix) != 6 or any(len(row) != 6 for row in transformation_matrix):
        raise ValueError("transformation_matrix must be 6x6.")

    r_t = _transpose(transformation_matrix)
    return _mat_vec(r_t, local_vec)


def _transpose(a: Sequence[Sequence[float]]) -> list[list[float]]:
    return [list(row) for row in zip(*a)]


def _mat_vec(a: Sequence[Sequence[float]], x: Sequence[float]) -> list[float]:
    return [sum(a[i][j] * x[j] for j in range(len(x))) for i in range(len(a))]
