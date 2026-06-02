"""
FrameElement class: 2D frame element with axial and bending stiffness.
Supports moment releases at element ends and member loads (UDL, point loads).
"""

from .element import Element
from .frame_element import compute_local_stiffness


class FrameElement(Element):
    """
    2D frame element with axial + bending stiffness.
    
    Supports:
        - Moment releases at start node (rz DOF set to zero)
        - Moment releases at end node (rz DOF set to zero)
        - Uniformly distributed transverse loads
        - Point loads at arbitrary locations
    
    Attributes (inherited):
        id, node_i, node_j, material, section, member_loads
    
    Attributes (new):
        release_start: bool, whether moment at node_i is released
        release_end: bool, whether moment at node_j is released
    """

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
        """
        Initialize frame element.
        
        Args:
            element_id: unique identifier
            node_i, node_j: Node objects
            material: Material object (E)
            section: Section object (A, I)
            release_start: bool, if True, moment is released at node_i
            release_end: bool, if True, moment is released at node_j
        """
        super().__init__(element_id, node_i, node_j, material, section)
        self.release_start = bool(release_start)
        self.release_end = bool(release_end)

    def local_stiffness(self):
        """
        Compute local stiffness matrix with moment releases applied.
        
        If releases are present, static condensation is used to zero out
        the corresponding rotational stiffness terms without removing the DOF.
        
        Returns:
            6×6 local stiffness matrix
        """
        # Compute base (unreleased) stiffness
        k_base = compute_local_stiffness(
            self.section.A,
            self.section.I,
            self.material.E,
            self.length(),
        )

        # If no releases, return base matrix
        if not (self.release_start or self.release_end):
            return k_base

        # Apply releases via static condensation
        f_zero = [0.0] * 6
        k_mod, _ = self._apply_releases(k_base, f_zero)
        return k_mod

    def equivalent_nodal_load_local(self):
        """
        Compute equivalent nodal loads from member loads in local coordinates.
        
        Supports:
            - Uniformly distributed load (UDL): w per unit length
            - Point load: P at distance a from node_i
        
        Member loads are applied as fixed-end forces, then adjusted if
        moment releases are present.
        
        Returns:
            6-element list of equivalent nodal forces in local coordinates
        """
        L = self.length()
        f_local = [0.0] * 6

        # Process each member load
        for load in self.member_loads:
            load_type = load.get("type", "").lower()
            direction = load.get("direction", "local_y").lower()

            if load_type == "udl":
                w = float(load["w"])
                if direction == "local_y":
                    # Uniform transverse load in local y direction
                    # Fixed-end reactions oppose the applied distributed load.
                    f_local[1] += -0.5 * w * L             # Node i: Fy
                    f_local[2] += -(w * L * L) / 12.0      # Node i: Mz
                    f_local[4] += -0.5 * w * L             # Node j: Fy
                    f_local[5] += (w * L * L) / 12.0       # Node j: Mz
                elif direction == "local_x":
                    # Uniform axial load
                    f_local[0] += 0.5 * w * L
                    f_local[3] += 0.5 * w * L
                else:
                    raise ValueError(f"Unknown UDL direction: {direction}")

            elif load_type == "point":
                # Point load at distance a from node_i
                P = float(load["p"])
                a = float(load["a"])
                if a < 0.0 or a > L:
                    raise ValueError(
                        f"Point load location a={a} is outside element length L={L}"
                    )
                b = L - a

                if direction == "local_y":
                    # Point load in transverse direction
                    # Fixed-end reactions oppose the applied point load.
                    f_local[1] += -P * (b * b) * (3.0 * a + b) / (L ** 3)
                    f_local[4] += -P * (a * a) * (a + 3.0 * b) / (L ** 3)
                    f_local[2] += -P * a * (b * b) / (L ** 2)
                    f_local[5] += P * (a * a) * b / (L ** 2)
                elif direction == "local_x":
                    # Axial point load
                    f_local[0] += P * b / L
                    f_local[3] += P * a / L
                else:
                    raise ValueError(f"Unknown point-load direction: {direction}")

            else:
                raise ValueError(f"Unknown member load type: {load_type}")

        # If releases are present, adjust the equivalent loads
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
        """
        Apply moment releases via static condensation.
        
        When a moment is released at a node, the corresponding rotational DOF
        is decoupled by zeroing its rows/columns in the stiffness matrix
        via condensation.
        
        Args:
            k_local: 6×6 local stiffness matrix (unreleased)
            f_local: 6-element load vector
        
        Returns:
            (k_mod, f_mod): Condensed stiffness and load vectors
        """
        released = []
        if self.release_start:
            released.append(2)  # DOF 2 = rotation at node i
        if self.release_end:
            released.append(5)  # DOF 5 = rotation at node j

        if not released:
            return k_local, f_local

        # Partition DOFs into retained and released
        retained = [i for i in range(6) if i not in released]

        # Partition stiffness matrix
        k_rr = self._submatrix(k_local, retained, retained)
        k_rl = self._submatrix(k_local, retained, released)
        k_lr = self._submatrix(k_local, released, retained)
        k_ll = self._submatrix(k_local, released, released)

        # Partition load vector
        f_r = [f_local[i] for i in retained]
        f_l = [f_local[i] for i in released]

        # Static condensation: K_condensed = K_rr - K_rl * K_ll^-1 * K_lr
        inv_k_ll = self._inverse_small(k_ll)
        k_cond = self._mat_sub(
            k_rr,
            self._mat_mul(k_rl, self._mat_mul(inv_k_ll, k_lr)),
        )
        f_cond = self._vec_sub(f_r, self._mat_vec(self._mat_mul(k_rl, inv_k_ll), f_l))

        # Build modified 6×6 matrices with released DOFs zeroed
        k_mod = [[0.0 for _ in range(6)] for _ in range(6)]
        f_mod = [0.0 for _ in range(6)]

        for ii, gi in enumerate(retained):
            f_mod[gi] = f_cond[ii]
            for jj, gj in enumerate(retained):
                k_mod[gi][gj] = k_cond[ii][jj]

        return k_mod, f_mod

    @staticmethod
    def _submatrix(a, row_ids, col_ids):
        """Extract submatrix from rows and columns specified by indices."""
        return [[a[i][j] for j in col_ids] for i in row_ids]

    @staticmethod
    def _inverse_small(a):
        """
        Invert small 1×1 or 2×2 matrix.
        
        Used for condensation of at most 2 released DOFs.
        """
        n = len(a)
        if n == 1:
            if abs(a[0][0]) < 1e-14:
                raise ValueError("Cannot invert singular matrix in release condensation.")
            return [[1.0 / a[0][0]]]

        if n == 2:
            det = a[0][0] * a[1][1] - a[0][1] * a[1][0]
            if abs(det) < 1e-14:
                raise ValueError("Cannot invert singular matrix in release condensation.")
            return [
                [a[1][1] / det, -a[0][1] / det],
                [-a[1][0] / det, a[0][0] / det],
            ]

        raise ValueError("Condensation supports up to 2 released DOFs (start and end).")

    @staticmethod
    def _mat_sub(a, b):
        """Subtract two matrices element-wise: a - b."""
        out = [[0.0 for _ in range(len(a[0]))] for _ in range(len(a))]
        for i in range(len(a)):
            for j in range(len(a[0])):
                out[i][j] = a[i][j] - b[i][j]
        return out

    @staticmethod
    def _mat_mul(a, b):
        """Multiply two small (≤6×6) dense matrices."""
        n_row = len(a)
        n_col = len(b[0]) if b and b[0] else 0
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
        """Multiply matrix by vector."""
        out = [0.0 for _ in range(len(a))]
        for i in range(len(a)):
            s = 0.0
            for j in range(len(x)):
                s += a[i][j] * x[j]
            out[i] = s
        return out

    @staticmethod
    def _vec_sub(a, b):
        """Subtract two vectors: a - b."""
        return [a[i] - b[i] for i in range(len(a))]
