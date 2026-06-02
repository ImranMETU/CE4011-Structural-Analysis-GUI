"""
Frame Element Module
====================
Legacy stiffness helpers + OO FrameElement class.
"""

import math

from .element import Element


class FrameElement(Element):
    """2D frame element (axial + bending) with optional end releases and member loads."""

    def __init__(
        self,
        element_id,
        node_i,
        node_j,
        material,
        section,
        release_start=False,
        release_end=False,
    ):
        super().__init__(element_id, node_i, node_j, material, section)
        if self.material.E <= 0.0 or self.section.A <= 0.0:
            raise ValueError("Frame element requires positive E and A.")
        if self.section.I <= 0.0:
            raise ValueError("Frame element requires nonzero moment of inertia I.")
        self.release_start = bool(release_start)
        self.release_end = bool(release_end)

    def local_stiffness(self):
        k_base = compute_local_stiffness(
            self.section.A,
            self.section.I,
            self.material.E,
            self.length(),
        )
        if not (self.release_start or self.release_end):
            return k_base
        f_zero = [0.0] * 6
        k_mod, _ = self._apply_releases(k_base, f_zero)
        return k_mod

    def equivalent_nodal_load_local(self):
        L = self.length()
        f_local = [0.0] * 6

        for load in self.member_loads:
            load_type = load.get("type", "").lower()
            direction = load.get("direction", "local_y").lower()

            if load_type == "udl":
                w = float(load["w"])
                if direction == "local_y":
                    # Fixed-end reactions (opposite sign of applied transverse load).
                    f_local[1] += -0.5 * w * L
                    f_local[2] += -(w * L * L) / 12.0
                    f_local[4] += -0.5 * w * L
                    f_local[5] += (w * L * L) / 12.0
                elif direction == "local_x":
                    f_local[0] += 0.5 * w * L
                    f_local[3] += 0.5 * w * L
                else:
                    raise ValueError(f"Unknown UDL direction: {direction}")

            elif load_type == "point":
                P = float(load["p"])
                a = float(load["a"])
                if a < 0.0 or a > L:
                    raise ValueError("Point load location a must satisfy 0 \u2264 a \u2264 L.")
                b = L - a

                if direction == "local_y":
                    # Fixed-end reactions (opposite sign of applied transverse load).
                    f_local[1] += -P * (b * b) * (3.0 * a + b) / (L ** 3)
                    f_local[4] += -P * (a * a) * (a + 3.0 * b) / (L ** 3)
                    f_local[2] += -P * a * (b * b) / (L ** 2)
                    f_local[5] += P * (a * a) * b / (L ** 2)
                elif direction == "local_x":
                    f_local[0] += P * b / L
                    f_local[3] += P * a / L
                else:
                    raise ValueError(f"Unknown point-load direction: {direction}")

            elif load_type == "thermal":
                f_th_local = self._thermal_equivalent_nodal_load_local(load)
                for i in range(6):
                    f_local[i] += f_th_local[i]

            else:
                raise ValueError(f"Unknown member-load type: {load_type}")

        if self.release_start or self.release_end:
            k_base = compute_local_stiffness(
                self.section.A,
                self.section.I,
                self.material.E,
                L,
            )
            _, f_mod = self._apply_releases(k_base, f_local)
            return f_mod

        return f_local

    def _apply_releases(self, k_local, f_local):
        released = []
        if self.release_start:
            released.append(2)
        if self.release_end:
            released.append(5)
        if not released:
            return k_local, f_local

        retained = [i for i in range(6) if i not in released]

        k_rr = self._submatrix(k_local, retained, retained)
        k_rl = self._submatrix(k_local, retained, released)
        k_lr = self._submatrix(k_local, released, retained)
        k_ll = self._submatrix(k_local, released, released)

        f_r = [f_local[i] for i in retained]
        f_l = [f_local[i] for i in released]

        inv_k_ll = self._inverse_small(k_ll)
        k_cond = self._mat_sub(k_rr, self._mat_mul(k_rl, self._mat_mul(inv_k_ll, k_lr)))
        f_cond = self._vec_sub(f_r, self._mat_vec(self._mat_mul(k_rl, inv_k_ll), f_l))

        k_mod = [[0.0 for _ in range(6)] for _ in range(6)]
        f_mod = [0.0 for _ in range(6)]
        for ii, gi in enumerate(retained):
            f_mod[gi] = f_cond[ii]
            for jj, gj in enumerate(retained):
                k_mod[gi][gj] = k_cond[ii][jj]
        return k_mod, f_mod

    def _thermal_equivalent_nodal_load_local(self, load):
        # Lazy import keeps legacy Assignment3 runs unaffected unless thermal loads are used.
        try:
            from thermal.thermal_load import get_equivalent_nodal_load_local
        except ImportError as exc:
            raise ImportError(
                "Thermal load support requires Classwork9 thermal module on PYTHONPATH. "
                "Run via Classwork9/run_thermal.py or add Classwork9 root to sys.path."
            ) from exc

        return get_equivalent_nodal_load_local(
            E=self.material.E,
            A=self.section.A,
            I=self.section.I,
            alpha=getattr(self.material, "alpha", 0.0),
            d=getattr(self.section, "d", None),
            thermal_load=load,
        )

    @staticmethod
    def _submatrix(a, row_ids, col_ids):
        return [[a[i][j] for j in col_ids] for i in row_ids]

    @staticmethod
    def _inverse_small(a):
        n = len(a)
        if n == 1:
            if abs(a[0][0]) < 1e-14:
                raise ValueError("Singular matrix in release condensation")
            return [[1.0 / a[0][0]]]
        if n == 2:
            det = a[0][0] * a[1][1] - a[0][1] * a[1][0]
            if abs(det) < 1e-14:
                raise ValueError("Singular matrix in release condensation")
            return [
                [a[1][1] / det, -a[0][1] / det],
                [-a[1][0] / det, a[0][0] / det],
            ]
        raise ValueError("Condensation supports max 2 released DOFs")

    @staticmethod
    def _mat_sub(a, b):
        return [[a[i][j] - b[i][j] for j in range(len(a[0]))] for i in range(len(a))]

    @staticmethod
    def _mat_mul(a, b):
        n_row = len(a)
        n_col = len(b[0]) if b else 0
        n_mid = len(b)
        out = [[0.0 for _ in range(n_col)] for _ in range(n_row)]
        for i in range(n_row):
            for j in range(n_col):
                s = 0.0
                for k in range(n_mid):
                    s += a[i][k] * b[k][j]
                out[i][j] = s
        return out

    @staticmethod
    def _mat_vec(a, x):
        return [sum(a[i][j] * x[j] for j in range(len(x))) for i in range(len(a))]

    @staticmethod
    def _vec_sub(a, b):
        return [a[i] - b[i] for i in range(len(a))]


def compute_local_stiffness(A, I, E, L):
    """Compute local stiffness matrix k' for a 2D frame element."""
    if L <= 0:
        raise ValueError(f"Element length L must be positive, got {L}")

    EA_L = (E * A) / L
    EI_2L = (2 * E * I) / L
    EI_4L = (4 * E * I) / L
    EI_6L2 = (6 * E * I) / (L ** 2)
    EI_12L3 = (12 * E * I) / (L ** 3)

    k_prime = [[0.0 for _ in range(6)] for _ in range(6)]

    k_prime[0][0] = EA_L
    k_prime[0][3] = -EA_L

    k_prime[1][1] = EI_12L3
    k_prime[1][2] = EI_6L2
    k_prime[1][4] = -EI_12L3
    k_prime[1][5] = EI_6L2

    k_prime[2][2] = EI_4L
    k_prime[2][4] = -EI_6L2
    k_prime[2][5] = EI_2L

    k_prime[3][3] = EA_L

    k_prime[4][4] = EI_12L3
    k_prime[4][5] = -EI_6L2

    k_prime[5][5] = EI_4L

    for i in range(6):
        for j in range(i):
            k_prime[i][j] = k_prime[j][i]

    return k_prime
