"""
Abstract base Element class for structural analysis.
Defines interface for 2D frame and truss elements.
"""

import math
from abc import ABC, abstractmethod


class Element(ABC):
    """
    Abstract 2D structural element connecting two nodes.
    
    Each element has 6 global DOFs (3 per node: ux, uy, rz).
    Subclasses must implement local_stiffness() and equivalent_nodal_load_local().
    
    Attributes:
        id: element identifier
        node_i, node_j: Node objects at start and end
        material: Material object
        section: Section object
        member_loads: list of member loads (UDL, point loads)
    """

    def __init__(self, element_id, node_i, node_j, material, section):
        """
        Initialize element.
        
        Args:
            element_id: unique identifier
            node_i, node_j: Node objects (start and end)
            material: Material object
            section: Section object
        """
        self.id = int(element_id)
        self.node_i = node_i
        self.node_j = node_j
        self.material = material
        self.section = section
        self.member_loads = []

    def length(self):
        """Compute element length from node coordinates."""
        dx = self.node_j.x - self.node_i.x
        dy = self.node_j.y - self.node_i.y
        L = math.hypot(dx, dy)
        if L <= 0.0:
            raise ValueError(f"Element {self.id} has zero or negative length.")
        return L

    def angle(self):
        """
        Compute element orientation angle from horizontal (global x-axis).
        
        Returns:
            angle in radians, measured counterclockwise from +x direction
        """
        dx = self.node_j.x - self.node_i.x
        dy = self.node_j.y - self.node_i.y
        return math.atan2(dy, dx)

    def transformation_matrix(self):
        """
        Compute 6×6 transformation matrix from global to local DOF directions.
        
        For a 2D element with 2 nodes and 3 DOFs per node:
            d_local = R * d_global
        
        where R contains rotations for [node_i] and [node_j] blocks.
        
        Returns:
            6×6 transformation matrix (list of lists)
        """
        c = math.cos(self.angle())
        s = math.sin(self.angle())
        return [
            [c, s, 0.0, 0.0, 0.0, 0.0],
            [-s, c, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, c, s, 0.0],
            [0.0, 0.0, 0.0, -s, c, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 1.0],
        ]

    def global_dof_numbers(self):
        """Return list of global equation numbers [eq_i1, eq_i2, eq_i3, eq_j1, eq_j2, eq_j3]."""
        return self.node_i.get_global_dof_numbers() + self.node_j.get_global_dof_numbers()

    def active_global_dof_numbers(self):
        """Return element DOF numbers used during global assembly."""
        return self.global_dof_numbers()

    def global_to_local_vector(self, vec_global):
        """Transform 6-element vector from global to local coordinates."""
        R = self.transformation_matrix()
        return self._mat_vec(R, vec_global)

    def local_to_global_vector(self, vec_local):
        """Transform 6-element vector from local to global coordinates."""
        R = self.transformation_matrix()
        R_T = self._transpose(R)
        return self._mat_vec(R_T, vec_local)

    def global_stiffness(self):
        """
        Compute 6×6 global element stiffness matrix.
        
        K_global = R^T * K_local * R
        
        Returns:
            6×6 global stiffness matrix
        """
        R = self.transformation_matrix()
        R_T = self._transpose(R)
        K_local = self.local_stiffness()
        
        # K_global = R_T @ K_local @ R
        temp = self._mat_mul(R_T, K_local)
        K_global = self._mat_mul(temp, R)
        return K_global

    def active_global_stiffness(self):
        """Return element stiffness matrix used during global assembly."""
        return self.global_stiffness()

    def equivalent_nodal_load(self):
        """
        Compute equivalent nodal loads from member loads in global coordinates.
        
        Member loads are converted to equivalent fixed-end forces in local coords,
        then transformed to global coords.
        
        Returns:
            6-element list of equivalent nodal forces in global coordinates
        """
        if not self.member_loads:
            return [0.0] * 6
        
        f_local = self.equivalent_nodal_load_local()
        return self.local_to_global_vector(f_local)

    def active_equivalent_nodal_load(self):
        """Return equivalent nodal loads used during global assembly."""
        return self.equivalent_nodal_load()

    def local_end_forces(self, element_global_displacements):
        """
        Compute member-end forces in local coordinates.
        
        q_local = K_local * d_local - f_eq_local
        
        where d_local is displacements in local coords and f_eq_local is equivalent loads.
        
        Args:
            element_global_displacements: 6-element list of displacements in global coords
        
        Returns:
            6-element list of forces in local coordinates [f1x, f1y, m1z, f2x, f2y, m2z]
        """
        d_local = self.global_to_local_vector(element_global_displacements)
        K_local = self.local_stiffness()
        f_eq_local = self.equivalent_nodal_load_local()
        
        # q = K * d - f_eq
        q_local = self._vec_sub(self._mat_vec(K_local, d_local), f_eq_local)
        return q_local

    @abstractmethod
    def local_stiffness(self):
        """
        Compute 6×6 local stiffness matrix.
        Must be implemented by subclasses.
        """
        raise NotImplementedError

    @abstractmethod
    def equivalent_nodal_load_local(self):
        """
        Compute equivalent nodal loads from member loads in local coordinates.
        Must be implemented by subclasses.
        """
        raise NotImplementedError

    # ========== Matrix/Vector Utilities ==========

    @staticmethod
    def _transpose(a):
        """Transpose a square matrix (list of lists)."""
        return [list(row) for row in zip(*a)]

    @staticmethod
    def _mat_mul(a, b):
        """Multiply two 6×6 matrices."""
        n_row = len(a)
        n_col = len(b[0])
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
        """Multiply 6×6 matrix by 6-element vector."""
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

    def __repr__(self):
        return f"{self.__class__.__name__}({self.id}, {self.node_i.id}-{self.node_j.id})"
