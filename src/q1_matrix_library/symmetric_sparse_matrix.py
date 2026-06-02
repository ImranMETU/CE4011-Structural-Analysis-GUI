from .matrix import Matrix
from .vector import Vector


class SymmetricSparseMatrix(Matrix):
    """Symmetric sparse matrix using dictionary storage with upper-triangle normalization.
    
    Exploits symmetry A[i,j] = A[j,i] to store only entries where i <= j.
    Ideal for structural analysis stiffness matrices (symmetric and sparse).
    
    Storage: Dictionary {(i, j): value} where i <= j (normalized).
    Complexity: 
        - get/set: O(1) on average
        - add: O(1) on average
        - matvec: O(nnz) where nnz is number of nonzeros
    
    Attributes:
        size (int): Matrix dimension.
        data (dict): Dictionary of nonzero entries {(i, j): float}.
    """
    
    def __init__(self, size):
        """Initialize symmetric sparse matrix.
        
        Args:
            size (int): Dimension.
        """
        super().__init__(size)
        self.data = {}

    def _normalize(self, i, j):
        """Normalize indices to store only upper triangle (i <= j).
        
        Args:
            i (int): Row index.
            j (int): Column index.
            
        Returns:
            tuple: (i, j) with i <= j.
        """
        return (i, j) if i <= j else (j, i)

    def _validate_indices(self, i, j):
        """Check indices are in valid range.
        
        Args:
            i (int): Row index.
            j (int): Column index.
            
        Raises:
            IndexError: If i or j out of bounds.
        """
        if i < 0 or i >= self.size or j < 0 or j >= self.size:
            raise IndexError(f"Matrix index ({i}, {j}) out of range [0, {self.size})")

    def add(self, i, j, value):
        """Add value to element at (i, j).
        
        Applies symmetry normalization: stores only upper triangle.
        
        Args:
            i (int): Row index.
            j (int): Column index.
            value (float): Value to add.
            
        Raises:
            IndexError: If indices out of bounds.
        """
        self._validate_indices(i, j)
        i, j = self._normalize(i, j)
        self.data[(i, j)] = self.data.get((i, j), 0.0) + value

    def set(self, i, j, value):
        """Set element at (i, j).
        
        Applies symmetry normalization: stores only upper triangle.
        
        Args:
            i (int): Row index.
            j (int): Column index.
            value (float): Value to set.
            
        Raises:
            IndexError: If indices out of bounds.
        """
        self._validate_indices(i, j)
        i, j = self._normalize(i, j)
        self.data[(i, j)] = value

    def get(self, i, j):
        """Get element at (i, j).
        
        Retrieves from upper triangle via normalization.
        Returns 0.0 for nonexistent entries (sparse).
        
        Args:
            i (int): Row index.
            j (int): Column index.
            
        Returns:
            float: Element value (0.0 if not explicitly stored).
            
        Raises:
            IndexError: If indices out of bounds.
        """
        self._validate_indices(i, j)
        i, j = self._normalize(i, j)
        return self.data.get((i, j), 0.0)

    def matvec(self, x):
        """Compute matrix-vector product exploiting symmetry.
        
        For each stored pair (i, j):
            - Diagonal (i == j): y[i] += A[i,i] * x[i]
            - Off-diagonal (i < j): y[i] += A[i,j] * x[j] and y[j] += A[i,j] * x[i]
        
        Complexity: O(nnz) where nnz = len(self.data)
        
        Args:
            x (Vector): Input vector of size matching matrix dimension.
            
        Returns:
            Vector: Result y = A @ x.
            
        Raises:
            ValueError: If x has wrong dimension.
        """
        if x.size != self.size:
            raise ValueError(f"Vector size {x.size} does not match matrix dimension {self.size}")
        
        y = Vector(self.size)
        
        for (i, j), val in self.data.items():
            if i == j:
                y.values[i] += val * x.values[j]
            else:
                y.values[i] += val * x.values[j]
                y.values[j] += val * x.values[i]
        
        return y

    def __repr__(self):
        return f"SymmetricSparseMatrix(size={self.size}, nnz={len(self.data)})"