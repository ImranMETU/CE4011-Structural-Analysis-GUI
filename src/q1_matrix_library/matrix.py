class Matrix:
    """Abstract base class for matrices.
    
    Defines interface for matrix storage (get/set/add) and operations (matvec).
    Subclasses implement efficiency via specific storage schemes:
    - SymmetricSparseMatrix: sparse dictionary with symmetry normalization
    - DenseMatrix: dense row-major storage (future)
    - BandedMatrix: banded storage (future)
    
    Attributes:
        size (int): Dimension (assumes square matrices).
    """
    
    def __init__(self, size):
        """Initialize matrix of given dimension.
        
        Args:
            size (int): Square matrix dimension.
        """
        if size <= 0:
            raise ValueError(f"Matrix size must be positive, got {size}")
        self.size = size

    def get(self, i, j):
        """Get element at position (i, j).
        
        Args:
            i (int): Row index.
            j (int): Column index.
            
        Returns:
            float: Element value.
            
        Raises:
            NotImplementedError: Must be implemented by subclass.
        """
        raise NotImplementedError

    def set(self, i, j, value):
        """Set element at position (i, j).
        
        Args:
            i (int): Row index.
            j (int): Column index.
            value (float): Value to set.
            
        Raises:
            NotImplementedError: Must be implemented by subclass.
        """
        raise NotImplementedError

    def add(self, i, j, value):
        """Add value to element at (i, j).
        
        Args:
            i (int): Row index.
            j (int): Column index.
            value (float): Value to add.
            
        Raises:
            NotImplementedError: Must be implemented by subclass.
        """
        raise NotImplementedError

    def matvec(self, x):
        """Compute matrix-vector product A @ x.
        
        Args:
            x (Vector): Input vector of size matching matrix dimension.
            
        Returns:
            Vector: Result vector.
            
        Raises:
            NotImplementedError: Must be implemented by subclass.
        """
        raise NotImplementedError