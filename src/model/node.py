"""
Node class for structural model.
Represents a 2D node with 3 DOFs: ux, uy, rz.
"""


class Node:
    """
    2D structural node with 3 DOFs: ux (horizontal), uy (vertical), rz (rotation).
    
    Attributes:
        id: node identifier
        x, y: global coordinates
        restraints: dict of boolean flags for each DOF direction
        loads: dict of applied loads in each DOF direction
        dof_numbers: dict mapping DOF keys to global equation numbers (0 if restrained)
    """

    DOF_KEYS = ("ux", "uy", "rz")

    def __init__(self, node_id, x, y):
        """
        Initialize node at global coordinates (x, y).
        
        Args:
            node_id: unique node identifier (int or str)
            x, y: global Cartesian coordinates (float)
        """
        self.id = int(node_id)
        self.x = float(x)
        self.y = float(y)
        self.restraints = {"ux": False, "uy": False, "rz": False}
        self.loads = {"fx": 0.0, "fy": 0.0, "mz": 0.0}
        self.dof_numbers = {"ux": 0, "uy": 0, "rz": 0}
        # SETTLEMENT EXTENSION START
        self.prescribed_displacements = {"ux": 0.0, "uy": 0.0, "rz": 0.0}
        # SETTLEMENT EXTENSION END

    def set_restraints(self, ux=False, uy=False, rz=False):
        """Mark which DOFs are restrained."""
        self.restraints["ux"] = bool(ux)
        self.restraints["uy"] = bool(uy)
        self.restraints["rz"] = bool(rz)

    def add_load(self, fx=0.0, fy=0.0, mz=0.0):
        """Add nodal loads (accumulative)."""
        self.loads["fx"] += float(fx)
        self.loads["fy"] += float(fy)
        self.loads["mz"] += float(mz)

    def set_dof_number(self, dof_key, equation_number):
        """Set global equation number for a DOF (0 if restrained)."""
        self.dof_numbers[dof_key] = int(equation_number)

    def get_dof_number(self, dof_key):
        """Get global equation number for a DOF."""
        return self.dof_numbers[dof_key]

    def get_global_dof_numbers(self):
        """Return list of global DOF numbers [ux, uy, rz]."""
        return [
            self.dof_numbers["ux"],
            self.dof_numbers["uy"],
            self.dof_numbers["rz"],
        ]

    # SETTLEMENT EXTENSION START
    def set_prescribed_displacements(self, ux=0.0, uy=0.0, rz=0.0):
        """Set prescribed displacement values (settlements) for restrained DOFs.
        
        Prescribed displacements should only be set on restrained DOFs.
        Use this method to specify support settlements or other prescribed boundary displacements.
        """
        self.prescribed_displacements["ux"] = float(ux)
        self.prescribed_displacements["uy"] = float(uy)
        self.prescribed_displacements["rz"] = float(rz)

    def get_prescribed_displacement(self, dof_key):
        """Get prescribed displacement for a DOF (nonzero only if restrained)."""
        return self.prescribed_displacements.get(dof_key, 0.0)
    # SETTLEMENT EXTENSION END

    def __repr__(self):
        return f"Node({self.id}, x={self.x}, y={self.y})"
