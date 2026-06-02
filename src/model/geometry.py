"""
Frame Geometry Module
=====================
Manages frame node coordinates and connectivity.

Stores node positions and computes derived geometric properties (element lengths).

Inputs:
    nodes: List of [x, y] coordinates
    elements: List of [node1, node2, ...] connectivity

Outputs:
    Element lengths for use in stiffness calculations

Units:
    Coordinates: [length]
    Lengths: [length]

Assumptions:
    - 2D planar frame (x, y coordinates)
    - Element defined by two nodes
"""

import math


class FrameGeometry:
    """Manages frame geometry: node coordinates and element properties."""
    
    def __init__(self, nodes):
        """
        Initialize frame geometry.
        
        Args:
            nodes (list): List of [x, y] node coordinates
        """
        self.nodes = nodes
        self.n_nodes = len(nodes)
    
    def get_element_length(self, node1, node2):
        """
        Compute element length from two node indices.
        
        Args:
            node1 (int): First node index
            node2 (int): Second node index
        
        Returns:
            L (float): Element length
        """
        x1, y1 = self.nodes[node1]
        x2, y2 = self.nodes[node2]
        dx = x2 - x1
        dy = y2 - y1
        L = math.sqrt(dx*dx + dy*dy)
        return L
    
    def get_element_angle(self, node1, node2):
        """
        Compute element orientation angle from horizontal.
        
        Args:
            node1 (int): First node index
            node2 (int): Second node index
        
        Returns:
            angle (float): Angle in radians (counterclockwise from x-axis)
        """
        x1, y1 = self.nodes[node1]
        x2, y2 = self.nodes[node2]
        dx = x2 - x1
        dy = y2 - y1
        angle = math.atan2(dy, dx)
        return angle
    
    def print_geometry(self):
        """Print frame geometry information."""
        print("\n" + "="*70)
        print("FRAME GEOMETRY")
        print("="*70)
        print("\nNode Coordinates:")
        for i, (x, y) in enumerate(self.nodes):
            print(f"  Node {i}: ({x:8.3f}, {y:8.3f})")
        print()
