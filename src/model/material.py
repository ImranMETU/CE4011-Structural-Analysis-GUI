"""
Material class for structural model.
Encapsulates isotropic linear elastic material properties.
"""


class Material:
    """
    Isotropic linear elastic material with Young's modulus E.
    
    Attributes:
        id: material identifier
        E: Young's modulus
    """

    def __init__(self, material_id, E, alpha=0.0):
        """
        Initialize material.
        
        Args:
            material_id: unique identifier
            E: Young's modulus (must be positive)
        """
        self.id = str(material_id)
        self.E = float(E)
        self.alpha = float(alpha)

        if self.E <= 0.0:
            raise ValueError(f"Young's modulus E must be positive, got {self.E}")

    def __repr__(self):
        return f"Material({self.id}, E={self.E}, alpha={self.alpha})"
