"""
Section class for structural model.
Encapsulates cross-section properties: area and second moment of inertia.
"""


class Section:
    """
    Cross-sectional properties for beam/truss elements.
    
    Attributes:
        id: section identifier
        A: cross-sectional area (required for both frame and truss)
        I: second moment of inertia (required for frame; zero for truss)
    """

    def __init__(self, section_id, A, I=0.0, d=None):
        """
        Initialize cross-section.
        
        Args:
            section_id: unique identifier
            A: area (must be positive)
            I: second moment of inertia (must be non-negative; default 0 for truss)
        """
        self.id = str(section_id)
        self.A = float(A)
        self.I = float(I)
        self.d = None if d is None else float(d)

        if self.A <= 0.0:
            raise ValueError(f"Area A must be positive, got {self.A}")
        if self.I < 0.0:
            raise ValueError(f"Second moment I cannot be negative, got {self.I}")
        if self.d is not None and self.d <= 0.0:
            raise ValueError(f"Section depth d must be positive when provided, got {self.d}")

    def __repr__(self):
        return f"Section({self.id}, A={self.A}, I={self.I}, d={self.d})"
