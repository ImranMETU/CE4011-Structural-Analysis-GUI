"""TrussElement class: 2D truss element (axial-only behavior)."""

import math

from .element import Element


class TrussElement(Element):
    """2D truss element embedded in 3-DOF-per-node frame formulation."""

    def active_global_dof_numbers(self):
        """Use translational DOFs only for truss assembly: [ux_i, uy_i, ux_j, uy_j]."""
        eq_i = self.node_i.get_global_dof_numbers()
        eq_j = self.node_j.get_global_dof_numbers()
        return [eq_i[0], eq_i[1], eq_j[0], eq_j[1]]

    def active_global_stiffness(self):
        """Return 4x4 truss stiffness in global coordinates."""
        L = self.length()
        c = math.cos(self.angle())
        s = math.sin(self.angle())
        EA_L = (self.material.E * self.section.A) / L

        return [
            [EA_L * c * c, EA_L * c * s, -EA_L * c * c, -EA_L * c * s],
            [EA_L * c * s, EA_L * s * s, -EA_L * c * s, -EA_L * s * s],
            [-EA_L * c * c, -EA_L * c * s, EA_L * c * c, EA_L * c * s],
            [-EA_L * c * s, -EA_L * s * s, EA_L * c * s, EA_L * s * s],
        ]

    def active_equivalent_nodal_load(self):
        """Return 4-element equivalent nodal loads for truss translational DOFs."""
        if not self.member_loads:
            return [0.0, 0.0, 0.0, 0.0]

        L = self.length()
        c = math.cos(self.angle())
        s = math.sin(self.angle())
        out = [0.0, 0.0, 0.0, 0.0]

        for load in self.member_loads:
            load_type = load.get("type", "").lower()
            direction = load.get("direction", "local_x").lower()

            if load_type == "udl":
                w = float(load["w"])
                if direction == "local_x":
                    fx = 0.5 * w * L * c
                    fy = 0.5 * w * L * s
                elif direction == "local_y":
                    fx = 0.5 * w * L * (-s)
                    fy = 0.5 * w * L * c
                else:
                    raise ValueError(f"Unknown UDL direction: {direction}")

                out[0] += fx
                out[1] += fy
                out[2] += fx
                out[3] += fy

            elif load_type == "point":
                P = float(load["p"])
                a = float(load["a"])
                if a < 0.0 or a > L:
                    raise ValueError("Point load location a must satisfy 0 <= a <= L.")
                b = L - a

                if direction == "local_x":
                    fx_i = P * b / L * c
                    fy_i = P * b / L * s
                    fx_j = P * a / L * c
                    fy_j = P * a / L * s
                elif direction == "local_y":
                    fx_i = P * b / L * (-s)
                    fy_i = P * b / L * c
                    fx_j = P * a / L * (-s)
                    fy_j = P * a / L * c
                else:
                    raise ValueError(f"Unknown point-load direction: {direction}")

                out[0] += fx_i
                out[1] += fy_i
                out[2] += fx_j
                out[3] += fy_j

            # THERMAL EXTENSION START
            elif load_type == "thermal":
                f_th_local = self._thermal_fixed_end_vector_local(load)
                # Truss thermal action is axial only; map local axial components to global x/y.
                out[0] += f_th_local[0] * c
                out[1] += f_th_local[0] * s
                out[2] += f_th_local[3] * c
                out[3] += f_th_local[3] * s
            # THERMAL EXTENSION END

            else:
                raise ValueError(f"Unknown member-load type: {load_type}")

        return out

    def local_stiffness(self):
        L = self.length()
        EA_L = (self.material.E * self.section.A) / L

        k = [[0.0 for _ in range(6)] for _ in range(6)]
        k[0][0] = EA_L
        k[0][3] = -EA_L
        k[3][0] = -EA_L
        k[3][3] = EA_L
        return k

    def equivalent_nodal_load_local(self):
        """
        Compute equivalent nodal loads for a truss element.
        
        Truss elements carry axial force only. Transverse loads (local_y direction)
        are physically meaningless for a pin-jointed truss and are ignored.
        Only loads in the local_x (axial) direction contribute to the equivalent vector.
        """
        L = self.length()
        f_local = [0.0 for _ in range(6)]

        for load in self.member_loads:
            load_type = load.get("type", "").lower()
            direction = load.get("direction", "local_x").lower()

            if load_type == "udl":
                w = float(load["w"])
                if direction == "local_x":
                    f_local[0] += 0.5 * w * L
                    f_local[3] += 0.5 * w * L
                elif direction == "local_y":
                    # Transverse loads are ignored for truss elements (no lateral stiffness)
                    pass
                else:
                    raise ValueError(f"Unknown UDL direction: {direction}")
            elif load_type == "point":
                P = float(load["p"])
                a = float(load["a"])
                if a < 0.0 or a > L:
                    raise ValueError("Point load location a must satisfy 0 \u2264 a \u2264 L.")
                b = L - a
                if direction == "local_x":
                    f_local[0] += P * b / L
                    f_local[3] += P * a / L
                elif direction == "local_y":
                    # Transverse loads are ignored for truss elements (no lateral stiffness)
                    pass
                else:
                    raise ValueError(f"Unknown point-load direction: {direction}")
            # THERMAL EXTENSION START
            elif load_type == "thermal":
                f_th = self._thermal_fixed_end_vector_local(load)
                for i in range(6):
                    f_local[i] += f_th[i]
            # THERMAL EXTENSION END
            else:
                raise ValueError(f"Unknown member-load type: {load_type}")

        return f_local

    # THERMAL EXTENSION START
    def _thermal_fixed_end_vector_local(self, load):
        """Return truss thermal fixed-end vector in local coordinates.

        Truss thermal behavior is axial-only:
            f_th_local = [-N_t, 0, 0, +N_t, 0, 0]
        with N_t = E * A * alpha * T_u.
        """
        if not hasattr(self.material, "alpha"):
            raise ValueError(f"Truss element {self.id} material is missing alpha for thermal load.")
        if not hasattr(self.section, "A"):
            raise ValueError(f"Truss element {self.id} section is missing area A for thermal load.")

        alpha = float(self.material.alpha)
        area = float(self.section.A)

        t_uniform = load.get("T_uniform", None)
        t_top = load.get("T_top", None)
        t_bottom = load.get("T_bottom", None)

        if t_uniform is None and (t_top is not None or t_bottom is not None):
            if t_top is None or t_bottom is None:
                raise ValueError("Thermal load with T_top/T_bottom must provide both values.")
            # For truss elements, only mean temperature contributes to axial thermal force.
            # Thermal-gradient bending is ignored because truss members do not resist bending.
            t_uniform = 0.5 * (float(t_top) + float(t_bottom))

        if t_uniform is None:
            t_uniform = 0.0

        n_t = float(self.material.E) * area * alpha * float(t_uniform)

        f_local = [0.0 for _ in range(6)]
        f_local[0] = -n_t
        f_local[3] = n_t
        return f_local
    # THERMAL EXTENSION END

