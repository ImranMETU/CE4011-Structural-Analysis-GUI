"""Editable in-memory model database for GUI-defined models."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


DEFAULT_ANALYSIS_OPTIONS = {
    "default_lateral_mass": 10000.0,
    "num_modes": 4,
    "static_deformation_scale": 1.0,
    "force_diagram_scale": 1.0e-6,
    "mode_shape_scale": 1.0,
}


class ModelBuilder:
    """Store GUI form records and convert them to solver-compatible input."""

    def __init__(self):
        self.clear()

    def clear(self) -> None:
        self.materials: dict[str, dict[str, Any]] = {}
        self.sections: dict[str, dict[str, Any]] = {}
        self.nodes: dict[int, dict[str, Any]] = {}
        self.frame_elements: dict[int, dict[str, Any]] = {}
        self.truss_elements: dict[int, dict[str, Any]] = {}
        self.nodal_loads: dict[int, dict[str, Any]] = {}
        self.modal_masses: dict[int, dict[str, float]] = {}
        self.analysis_options = deepcopy(DEFAULT_ANALYSIS_OPTIONS)

    def add_material(self, name: str, E: float, alpha: float = 0.0) -> None:
        self.materials[str(name)] = {"id": str(name), "E": float(E), "alpha": float(alpha)}

    def add_section(self, name: str, A: float, I: float, d: float | None = None) -> None:
        record = {"id": str(name), "A": float(A), "I": float(I)}
        if d is not None:
            record["d"] = float(d)
        self.sections[str(name)] = record

    def add_node(self, node_id: int, x: float, y: float, ux: str | bool, uy: str | bool, rz: str | bool) -> None:
        self.nodes[int(node_id)] = {
            "id": int(node_id),
            "x": float(x),
            "y": float(y),
            "restraints": {
                "ux": _restraint_bool(ux),
                "uy": _restraint_bool(uy),
                "rz": _restraint_bool(rz),
            },
        }

    def add_frame_element(self, element_id: int, node_i: int, node_j: int, material: str, section: str) -> None:
        self.frame_elements[int(element_id)] = _element_record(
            element_id, "frame", node_i, node_j, material, section
        )

    def add_truss_element(self, element_id: int, node_i: int, node_j: int, material: str, section: str) -> None:
        self.truss_elements[int(element_id)] = _element_record(
            element_id, "truss", node_i, node_j, material, section
        )

    def add_nodal_load(self, node_id: int, fx: float = 0.0, fy: float = 0.0, mz: float = 0.0) -> None:
        self.nodal_loads[int(node_id)] = {
            "node": int(node_id),
            "fx": float(fx),
            "fy": float(fy),
            "mz": float(mz),
        }

    def add_modal_mass(self, node_id: int, ux: float = 0.0, uy: float = 0.0, rz: float = 0.0) -> None:
        self.modal_masses[int(node_id)] = {
            "ux": float(ux),
            "uy": float(uy),
            "rz": float(rz),
        }

    def update_analysis_options(self, **options: float | int) -> None:
        for key, value in options.items():
            if key not in self.analysis_options:
                raise ValueError(f"Unknown analysis option: {key}")
            if key == "num_modes":
                self.analysis_options[key] = int(value)
            else:
                self.analysis_options[key] = float(value)

    def delete_record(self, table: str, record_id: str | int) -> None:
        table_obj = self._table(table)
        key = int(record_id) if _integer_keyed_table(table) else str(record_id)
        table_obj.pop(key, None)

    def table_records(self, table: str) -> list[dict[str, Any]]:
        table_obj = self._table(table)
        return [deepcopy(table_obj[key]) for key in sorted(table_obj)]

    def to_structure_dict(self) -> dict[str, Any]:
        return {
            "nodes": self.table_records("nodes"),
            "materials": self.table_records("materials"),
            "sections": self.table_records("sections"),
            "elements": self.table_records("frame_elements") + self.table_records("truss_elements"),
            "nodal_loads": self.table_records("nodal_loads"),
        }

    def to_mass_mapping(self) -> dict[int, dict[str, float]]:
        return deepcopy(self.modal_masses)

    def load_from_structure_dict(
        self,
        data: dict[str, Any],
        mass_mapping: dict[int, dict[str, float]] | None = None,
    ) -> None:
        self.clear()
        for material in data.get("materials", []):
            self.add_material(material["id"], material["E"], material.get("alpha", 0.0))
        for section in data.get("sections", []):
            self.add_section(section["id"], section["A"], section.get("I", 0.0), section.get("d"))
        for node in data.get("nodes", []):
            restraints = node.get("restraints", {})
            self.add_node(
                node["id"],
                node["x"],
                node["y"],
                restraints.get("ux", False),
                restraints.get("uy", False),
                restraints.get("rz", False),
            )
        for element in data.get("elements", []):
            if element["type"].lower() == "frame":
                self.add_frame_element(
                    element["id"], element["node_i"], element["node_j"], element["material"], element["section"]
                )
            elif element["type"].lower() == "truss":
                self.add_truss_element(
                    element["id"], element["node_i"], element["node_j"], element["material"], element["section"]
                )
        for load in data.get("nodal_loads", []):
            self.add_nodal_load(load["node"], load.get("fx", 0.0), load.get("fy", 0.0), load.get("mz", 0.0))
        if mass_mapping:
            for node_id, masses in mass_mapping.items():
                self.add_modal_mass(node_id, masses.get("ux", 0.0), masses.get("uy", 0.0), masses.get("rz", 0.0))

    def summary_lines(self) -> list[str]:
        return [
            f"Materials: {len(self.materials)}",
            f"Sections: {len(self.sections)}",
            f"Nodes: {len(self.nodes)}",
            f"Frame elements: {len(self.frame_elements)}",
            f"Truss elements: {len(self.truss_elements)}",
            f"Nodal loads: {len(self.nodal_loads)}",
            f"Modal masses: {len(self.modal_masses)}",
        ]

    def _table(self, table: str) -> dict:
        if table == "materials":
            return self.materials
        if table == "sections":
            return self.sections
        if table == "nodes":
            return self.nodes
        if table == "frame_elements":
            return self.frame_elements
        if table == "truss_elements":
            return self.truss_elements
        if table == "nodal_loads":
            return self.nodal_loads
        if table == "modal_masses":
            return self.modal_masses
        raise ValueError(f"Unknown model builder table: {table}")


def _restraint_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    upper = str(value).upper()
    if upper == "FIX":
        return True
    if upper == "FREE":
        return False
    raise ValueError(f"Restraint must be FIX/FREE or bool, got {value!r}.")


def _restraint_text(value: bool) -> str:
    return "FIX" if value else "FREE"


def _element_record(
    element_id: int,
    element_type: str,
    node_i: int,
    node_j: int,
    material: str,
    section: str,
) -> dict[str, Any]:
    return {
        "id": int(element_id),
        "type": element_type,
        "node_i": int(node_i),
        "node_j": int(node_j),
        "material": str(material),
        "section": str(section),
    }


def _integer_keyed_table(table: str) -> bool:
    return table in {"nodes", "frame_elements", "truss_elements", "nodal_loads", "modal_masses"}
