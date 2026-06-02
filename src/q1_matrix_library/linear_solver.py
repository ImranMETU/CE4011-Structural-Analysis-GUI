class LinearSolver:
    """Abstract base class for linear system solvers.
    
    Defines interface for solving A @ x = b for given matrix A and vector b.
    Subclasses implement specific algorithms:
    - ConjugateGradientSolver: Iterative method for symmetric positive definite (SPD) systems.
    - (Future) DirectSolver (LU factorization for dense/banded matrices).
    """
    
    def solve(self, A, b):
        """Solve linear system A @ x = b.
        
        Args:
            A (Matrix): System matrix (size n x n).
            b (Vector): Right-hand side vector (size n).
            
        Returns:
            Vector: Solution x (size n).
            
        Raises:
            NotImplementedError: Must be implemented by subclass.
        """
        raise NotImplementedError