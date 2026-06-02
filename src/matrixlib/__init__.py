"""Compatibility layer that re-exports the existing HW2/HW3 matrix library."""

from q1_matrix_library.vector import Vector
from q1_matrix_library.symmetric_sparse_matrix import SymmetricSparseMatrix
from q1_matrix_library.conjugate_gradient_solver import ConjugateGradientSolver

__all__ = ["Vector", "SymmetricSparseMatrix", "ConjugateGradientSolver"]
