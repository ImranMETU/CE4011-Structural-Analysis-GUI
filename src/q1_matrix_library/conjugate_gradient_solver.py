from .linear_solver import LinearSolver
from .vector import Vector


class ConjugateGradientSolver(LinearSolver):
    """Conjugate Gradient iterative solver for symmetric positive definite (SPD) systems.
    
    Solves A @ x = b using the Conjugate Gradient method.
    Suitable for large sparse SPD systems common in structural analysis (stiffness matrices).
    
    Algorithm:
        1. Initialize x = 0, r = b, p = r
        2. For k = 0, 1, ..., max_iter:
            - Compute α = (r^T r) / (p^T A p)
            - Update x += α p, r -= α Ap
            - Check relative residual norm: ||r|| / ||r_0|| < tol
            - Compute β = (r_new^T r_new) / (r_old^T r_old)
            - Update search direction: p = r + β p
    
    Convergence: Guaranteed for SPD matrices in at most n iterations (theory).
                 Practical convergence depends on matrix conditioning.
    
    Requirements:
        - A must be symmetric (user responsibility to ensure)
        - A must be positive definite (user responsibility)
    
    Attributes:
        tol (float): Relative residual tolerance for convergence.
        max_iter (int): Maximum number of iterations.
    """
    
    def __init__(self, tol=1e-6, max_iter=1000):
        """Initialize solver parameters.
        
        Args:
            tol (float): Relative residual tolerance. Default 1e-6.
            max_iter (int): Maximum iterations. Default 1000.
        """
        if tol <= 0:
            raise ValueError(f"Tolerance must be positive, got {tol}")
        if max_iter <= 0:
            raise ValueError(f"Max iterations must be positive, got {max_iter}")
        self.tol = tol
        self.max_iter = max_iter

    def solve(self, A, b):
        """Solve linear system A @ x = b using Conjugate Gradient method.
        
        Solves the system iteratively, starting from x = 0.
        Returns the solution vector after convergence or max iterations.
        
        Args:
            A (Matrix): Symmetric positive definite matrix (n x n).
            b (Vector): Right-hand side vector (n).
            
        Returns:
            Vector: Solution vector x of size n.
            
        Raises:
            ValueError: If matrix and vector sizes do not match.
            RuntimeError: If solver fails (e.g., division by zero indicates non-SPD matrix).
        """
        n = b.size
        
        if A.size != n:
            raise ValueError(f"Matrix dimension {A.size} does not match vector size {n}")
        
        x = Vector(n)
        r = b.copy()
        p = r.copy()
        
        rs_old = r.dot(r)
        rs_0 = rs_old  # Initial residual squared for relative tolerance
        
        if rs_0 == 0.0:
            # b is already zero (or near zero)
            return x
        
        for iteration in range(self.max_iter):
            # Compute A @ p
            Ap = A.matvec(p)
            
            # Compute α = (r^T r) / (p^T A p)
            p_Ap = p.dot(Ap)
            
            if p_Ap <= 0:
                # p^T A p should be positive for SPD matrix
                raise RuntimeError(
                    f"Solver failed at iteration {iteration}: p^T A p = {p_Ap} <= 0. "
                    "Matrix may not be symmetric positive definite."
                )
            
            alpha = rs_old / p_Ap
            
            # Update solution and residual
            for i in range(n):
                x.values[i] += alpha * p.values[i]
                r.values[i] -= alpha * Ap.values[i]
            
            # Check convergence using relative residual norm
            rs_new = r.dot(r)
            relative_residual = (rs_new / rs_0) ** 0.5
            
            if relative_residual < self.tol:
                # Converged
                break
            
            # Compute β and update search direction
            beta = rs_new / rs_old
            for i in range(n):
                p.values[i] = r.values[i] + beta * p.values[i]
            
            rs_old = rs_new
        
        return x