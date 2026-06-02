class Vector:
    """Dense vector representation for linear algebra operations.
    
    Supports basic vector operations: dot product, norm, scalar operations.
    Used as input/output for matrix-vector products and linear solvers.
    
    Attributes:
        size (int): Dimension of the vector.
        values (list): Float values [0.0] * size.
    """
    
    def __init__(self, size):
        """Initialize a zero vector of given size.
        
        Args:
            size (int): Dimension.
            
        Raises:
            ValueError: If size <= 0.
        """
        if size <= 0:
            raise ValueError(f"Vector size must be positive, got {size}")
        self.size = size
        self.values = [0.0] * size

    def get(self, i):
        """Get value at index i.
        
        Args:
            i (int): Index.
            
        Returns:
            float: Value at index i.
            
        Raises:
            IndexError: If i is out of bounds.
        """
        if i < 0 or i >= self.size:
            raise IndexError(f"Vector index {i} out of range [0, {self.size})")
        return self.values[i]

    def set(self, i, value):
        """Set value at index i.
        
        Args:
            i (int): Index.
            value (float): Value to set.
            
        Raises:
            IndexError: If i is out of bounds.
        """
        if i < 0 or i >= self.size:
            raise IndexError(f"Vector index {i} out of range [0, {self.size})")
        self.values[i] = value

    def add(self, i, value):
        """Add value to the element at index i.
        
        Args:
            i (int): Index.
            value (float): Value to add.
            
        Raises:
            IndexError: If i is out of bounds.
        """
        if i < 0 or i >= self.size:
            raise IndexError(f"Vector index {i} out of range [0, {self.size})")
        self.values[i] += value

    def dot(self, other):
        """Compute dot product with another vector.
        
        Args:
            other (Vector): Vector of same dimension.
            
        Returns:
            float: Dot product.
            
        Raises:
            ValueError: If vectors have different sizes.
        """
        if self.size != other.size:
            raise ValueError(f"Vector size mismatch: {self.size} vs {other.size}")
        return sum(self.values[i] * other.values[i] for i in range(self.size))

    def norm(self):
        """Compute Euclidean norm (2-norm).
        
        Returns:
            float: sqrt(sum of squares).
        """
        return (self.dot(self)) ** 0.5

    def copy(self):
        """Create a deep copy of this vector.
        
        Returns:
            Vector: New vector with same values.
        """
        v = Vector(self.size)
        v.values = self.values[:]
        return v

    def __repr__(self):
        return f"Vector({self.values})"