"""Structure class: model container + DSM assembly/solve/postprocess workflow."""

from matrixlib import ConjugateGradientSolver, SymmetricSparseMatrix, Vector

from .frame_element import FrameElement
from .material import Material
from .node import Node
from .section import Section
from .truss_element import TrussElement


class _EmptyVector:
    def __init__(self):
        self.size = 0

    def get(self, i):
        raise IndexError("Vector index out of range for empty solution vector")

    def norm(self):
        return 0.0

    def copy(self):
        return self


class _EmptySparseMatrix:
    def __init__(self):
        self.size = 0
        self.data = {}


class Structure:
    """Stores full structural model and coordinates assembly, solving, and postprocessing."""

    def __init__(self):
        self.nodes = {}
        self.materials = {}
        self.sections = {}
        self.elements = []
        self.node_index = {}

        self.n_active_dofs = 0
        self.K = None
        self.F = None
        self.D = None

    def add_node(self, node):
        if node.id in self.nodes:
            raise ValueError(f"Duplicate node id: {node.id}")
        self.nodes[node.id] = node

    def add_material(self, material):
        if material.id in self.materials:
            raise ValueError(f"Duplicate material id: {material.id}")
        self.materials[material.id] = material

    def add_section(self, section):
        if section.id in self.sections:
            raise ValueError(f"Duplicate section id: {section.id}")
        self.sections[section.id] = section

    def add_element(self, element):
        self.elements.append(element)

    def connected_components(self):
        """Return connected components of the structural graph as sets of node ids."""
        if not self.nodes:
            return []

        adjacency = {node_id: set() for node_id in self.nodes}
        for element in self.elements:
            node_i = element.node_i.id
            node_j = element.node_j.id
            adjacency[node_i].add(node_j)
            adjacency[node_j].add(node_i)

        components = []
        visited = set()

        for start_node in sorted(self.nodes):
            if start_node in visited:
                continue
            stack = [start_node]
            component = set()
            visited.add(start_node)

            while stack:
                current = stack.pop()
                component.add(current)
                for neighbor in adjacency[current]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        stack.append(neighbor)

            components.append(component)

        return components

    def validate_connectivity(self):
        """Raise an error if the structure contains disconnected components."""
        components = self.connected_components()
        if len(components) > 1:
            raise ValueError(
                "Structure contains disconnected components. At least one part is not connected to the main structural system."
            )

    def assign_dofs(self):
        self._enforce_truss_only_rotational_restraints()

        eq = 1
        self.node_index = {}
        for pos, node_id in enumerate(sorted(self.nodes)):
            self.node_index[node_id] = pos
            node = self.nodes[node_id]
            for dof in Node.DOF_KEYS:
                if node.restraints[dof]:
                    node.set_dof_number(dof, 0)
                else:
                    node.set_dof_number(dof, eq)
                    eq += 1
        self.n_active_dofs = eq - 1

    def _enforce_truss_only_rotational_restraints(self):
        """Deactivate rotational DOFs at nodes connected only to truss elements."""
        incident_types = {node_id: set() for node_id in self.nodes}
        for element in self.elements:
            elem_type = "frame" if isinstance(element, FrameElement) else "truss"
            incident_types[element.node_i.id].add(elem_type)
            incident_types[element.node_j.id].add(elem_type)

        for node_id, types in incident_types.items():
            if types and types == {"truss"}:
                self.nodes[node_id].restraints["rz"] = True

    def assemble_global_stiffness(self):
        if self.n_active_dofs <= 0:
            raise ValueError("No active DOFs. Run assign_dofs() first.")

        K = SymmetricSparseMatrix(self.n_active_dofs)
        for element in self.elements:
            k_global = element.active_global_stiffness()
            eqs = element.active_global_dof_numbers()
            n_dof = len(eqs)
            for i in range(n_dof):
                for j in range(i, n_dof):
                    gi = eqs[i]
                    gj = eqs[j]
                    if gi != 0 and gj != 0:
                        K.add(gi - 1, gj - 1, k_global[i][j])

        self.K = K
        return K

    def assemble_global_load_vector(self):
        if self.n_active_dofs <= 0:
            raise ValueError("No active DOFs. Run assign_dofs() first.")

        F = Vector(self.n_active_dofs)

        # Nodal loads
        for node_id in sorted(self.nodes):
            node = self.nodes[node_id]
            node_load = [node.loads["fx"], node.loads["fy"], node.loads["mz"]]
            node_eqs = node.get_global_dof_numbers()
            for i in range(3):
                if node_eqs[i] != 0:
                    F.add(node_eqs[i] - 1, node_load[i])

        # Equivalent loads from member loads
        for element in self.elements:
            f_eq_global = element.active_equivalent_nodal_load()
            eqs = element.active_global_dof_numbers()
            n_dof = len(eqs)
            for i in range(n_dof):
                if eqs[i] != 0:
                    F.add(eqs[i] - 1, f_eq_global[i])

        self.F = F
        return F

    def solve(self, tol=1e-8, max_iter=2000):
        if self.n_active_dofs == 0:
            self.K = _EmptySparseMatrix()
            self.F = _EmptyVector()
            self.D = _EmptyVector()
            return self.D

        if not any(node.restraints.get("ux", False) for node in self.nodes.values()):
            raise ValueError(
                "Global stiffness matrix is singular or nearly singular. The structure may be unstable "
                "due to insufficient lateral restraint or a rigid-body sway mechanism."
            )

        if self.K is None:
            self.assemble_global_stiffness()
        if self.F is None:
            self.assemble_global_load_vector()

        # SETTLEMENT EXTENSION START
        # Apply settlement correction: F_corrected = F - K_fr @ u_r
        self._apply_settlement_correction()
        # SETTLEMENT EXTENSION END

        stiffness_tol = 1e-14
        for i in range(self.n_active_dofs):
            if hasattr(self.K, "get_diagonal"):
                kii = self.K.get_diagonal(i)
            else:
                kii = self.K.get(i, i)
            if abs(kii) <= stiffness_tol:
                raise ValueError(
                    f"Active DOF {i + 1} has zero stiffness contribution. "
                    "This suggests an unconnected node, released rotational DOF without supporting "
                    "stiffness, or a mechanism."
                )

        solver = ConjugateGradientSolver(tol=tol, max_iter=max_iter)
        try:
            self.D = solver.solve(self.K, self.F)
        except RuntimeError as exc:
            raise ValueError(
                "Global stiffness matrix is singular or nearly singular. The structure may be unstable "
                "due to insufficient lateral restraint or a rigid-body sway mechanism."
            ) from exc
        return self.D

    def full_displacement_vector(self):
        if self.D is None:
            raise ValueError("No solution found. Run solve() first.")

        n_nodes = len(self.nodes)
        d_full = [0.0 for _ in range(n_nodes * 3)]

        for node_id in sorted(self.nodes):
            node = self.nodes[node_id]
            eqs = node.get_global_dof_numbers()
            node_pos = self.node_index[node_id]
            for local_dof in range(3):
                eq = eqs[local_dof]
                idx = node_pos * 3 + local_dof
                if eq != 0:
                    d_full[idx] = self.D.get(eq - 1)
                # SETTLEMENT EXTENSION START
                else:
                    # Restrained DOF: use prescribed displacement (settlement)
                    dof_key = Node.DOF_KEYS[local_dof]
                    d_full[idx] = node.get_prescribed_displacement(dof_key)
                # SETTLEMENT EXTENSION END

        return d_full

    # SETTLEMENT EXTENSION START
    def _apply_settlement_correction(self):
        """Apply settlement correction to RHS: F_corrected = F - K_fr @ u_r.
        
        This implements the partitioned DSM step where settlements u_r modify
        the right-hand side for free DOFs before solving.
        """
        # Build K_fr by iterating elements and extracting coupling terms
        # between active (free) and restrained DOFs.
        n_nodes = len(self.nodes)
        n_dofs = n_nodes * 3
        
        # Only proceed if there are actual settlements
        has_settlement = any(
            node.get_prescribed_displacement(dof) != 0.0
            for node in self.nodes.values()
            for dof in Node.DOF_KEYS
        )
        if not has_settlement:
            return
        
        # Build the settlement contribution vector by iterating elements
        settlement_correction = [0.0] * self.n_active_dofs
        
        for element in self.elements:
            k_global = element.global_stiffness()
            eqs = element.global_dof_numbers()
            
            # Build displacement vector with zeros for active DOFs, settlements for restrained
            u_elem = [0.0] * len(eqs)
            for i, eq in enumerate(eqs):
                if eq == 0:
                    # Restrained DOF: use prescribed displacement
                    node_id = element.node_i.id if i < 3 else element.node_j.id
                    node = self.nodes[node_id]
                    dof_key = Node.DOF_KEYS[i % 3]
                    u_elem[i] = node.get_prescribed_displacement(dof_key)
            
            # Compute f_settlement = K * u_settlement at element level
            f_settlement_global = self._mat_vec(k_global, u_elem)
            
            # Extract only the active DOF contributions
            for i, eq in enumerate(eqs):
                if eq != 0:  # Active DOF
                    settlement_correction[eq - 1] += f_settlement_global[i]
        
        # Modify load vector: F = F - settlement_correction
        for i in range(self.n_active_dofs):
            self.F.add(i, -settlement_correction[i])
    
    @staticmethod
    def _mat_vec(a, x):
        """Multiply matrix a by vector x."""
        return [sum(a[i][j] * x[j] for j in range(len(x))) for i in range(len(a))]
    # SETTLEMENT EXTENSION END

    def compute_reactions(self):
        if self.D is None:
            raise ValueError("No solution found. Run solve() first.")

        n_nodes = len(self.nodes)
        n_dofs = n_nodes * 3
        d_full = self.full_displacement_vector()

        K_full = [[0.0 for _ in range(n_dofs)] for _ in range(n_dofs)]
        F_full = [0.0 for _ in range(n_dofs)]

        # Nodal external loads
        for node_id in sorted(self.nodes):
            node = self.nodes[node_id]
            node_pos = self.node_index[node_id]
            F_full[node_pos * 3 + 0] += node.loads["fx"]
            F_full[node_pos * 3 + 1] += node.loads["fy"]
            F_full[node_pos * 3 + 2] += node.loads["mz"]

        for element in self.elements:
            k_global = element.global_stiffness()
            f_eq_global = element.equivalent_nodal_load()
            map_full = [
                self.node_index[element.node_i.id] * 3 + 0,
                self.node_index[element.node_i.id] * 3 + 1,
                self.node_index[element.node_i.id] * 3 + 2,
                self.node_index[element.node_j.id] * 3 + 0,
                self.node_index[element.node_j.id] * 3 + 1,
                self.node_index[element.node_j.id] * 3 + 2,
            ]

            for i in range(6):
                gi = map_full[i]
                for j in range(6):
                    gj = map_full[j]
                    K_full[gi][gj] += k_global[i][j]
                F_full[gi] += f_eq_global[i]

        internal = [0.0 for _ in range(n_dofs)]
        for i in range(n_dofs):
            s = 0.0
            for j in range(n_dofs):
                s += K_full[i][j] * d_full[j]
            internal[i] = s

        reactions = {}
        for node_id in sorted(self.nodes):
            node_pos = self.node_index[node_id]
            rx = internal[node_pos * 3 + 0] - F_full[node_pos * 3 + 0]
            ry = internal[node_pos * 3 + 1] - F_full[node_pos * 3 + 1]
            mz = internal[node_pos * 3 + 2] - F_full[node_pos * 3 + 2]
            reactions[node_id] = {"rx": rx, "ry": ry, "mz": mz}

        return reactions

    def compute_member_end_forces(self):
        if self.D is None:
            raise ValueError("No solution found. Run solve() first.")

        d_full = self.full_displacement_vector()
        out = {}

        for element in self.elements:
            ids = [
                self.node_index[element.node_i.id] * 3 + 0,
                self.node_index[element.node_i.id] * 3 + 1,
                self.node_index[element.node_i.id] * 3 + 2,
                self.node_index[element.node_j.id] * 3 + 0,
                self.node_index[element.node_j.id] * 3 + 1,
                self.node_index[element.node_j.id] * 3 + 2,
            ]
            d_elem = [d_full[i] for i in ids]
            q_local = element.local_end_forces(d_elem)
            out[element.id] = {
                "node_i": {"nx": q_local[0], "vy": q_local[1], "mz": q_local[2]},
                "node_j": {"nx": q_local[3], "vy": q_local[4], "mz": q_local[5]},
            }

        return out

    @staticmethod
    def from_dict(data):
        s = Structure()

        for nd in data.get("nodes", []):
            node = Node(nd["id"], nd["x"], nd["y"])
            restraints = nd.get("restraints", {})
            node.set_restraints(
                restraints.get("ux", False),
                restraints.get("uy", False),
                restraints.get("rz", False),
            )
            # SETTLEMENT EXTENSION START
            # Parse prescribed displacements (settlements) for restrained DOFs
            prescribed = nd.get("prescribed_displacements", {})
            if prescribed:
                node.set_prescribed_displacements(
                    ux=prescribed.get("ux", 0.0),
                    uy=prescribed.get("uy", 0.0),
                    rz=prescribed.get("rz", 0.0),
                )
            # SETTLEMENT EXTENSION END
            s.add_node(node)

        for md in data.get("materials", []):
            s.add_material(Material(md["id"], md["E"], md.get("alpha", 0.0)))

        for sd in data.get("sections", []):
            s.add_section(Section(sd["id"], sd["A"], sd.get("I", 0.0), sd.get("d", None)))

        for ld in data.get("nodal_loads", []):
            node = s.nodes[ld["node"]]
            node.add_load(ld.get("fx", 0.0), ld.get("fy", 0.0), ld.get("mz", 0.0))

        for ed in data.get("elements", []):
            node_i = s.nodes[ed["node_i"]]
            node_j = s.nodes[ed["node_j"]]
            material = s.materials[ed["material"]]
            section = s.sections[ed["section"]]

            elem_type = ed["type"].lower()
            if elem_type == "frame":
                releases = ed.get("releases", {})
                elem = FrameElement(
                    ed["id"],
                    node_i,
                    node_j,
                    material,
                    section,
                    release_start=releases.get("start", False),
                    release_end=releases.get("end", False),
                )
            elif elem_type == "truss":
                elem = TrussElement(ed["id"], node_i, node_j, material, section)
            else:
                raise ValueError(f"Unknown element type: {ed['type']}")

            for ml in ed.get("member_loads", []):
                elem.member_loads.append(ml)

            s.add_element(elem)

        # SETTLEMENT EXTENSION START
        # Validate prescribed displacements
        for node in s.nodes.values():
            for dof in Node.DOF_KEYS:
                prescribed = node.get_prescribed_displacement(dof)
                if prescribed != 0.0 and not node.restraints[dof]:
                    raise ValueError(
                        f"Node {node.id}: prescribed displacement {prescribed} on unrestrained DOF {dof}. "
                        "Settlements can only be prescribed on restrained DOFs."
                    )
        # SETTLEMENT EXTENSION END

        s.assign_dofs()
        return s
