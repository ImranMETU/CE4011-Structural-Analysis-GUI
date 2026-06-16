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
        self.axis_offsets: dict[int, dict[str, Any]] = {}
        self.nodal_loads: dict[int, dict[str, Any]] = {}
        self.member_loads: dict[int, dict[str, Any]] = {}
        self._next_member_load_id = 1
        self.thermal_loads: dict[int, dict[str, Any]] = {}
        self.support_settlements: dict[int, dict[str, float | None]] = {}
        self.modal_masses: dict[int, dict[str, float]] = {}
        self.modal_mass_source_type = "manual"
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

    def add_axis_offset(self, element_id: int, i_local_y: float = 0.0, j_local_y: float = 0.0) -> None:
        element_id = int(element_id)
        if element_id in self.truss_elements:
            raise ValueError("Axis offsets are supported for frame elements only.")
        if element_id not in self.frame_elements:
            raise ValueError(f"Unknown frame element id {element_id}.")
        self.axis_offsets[element_id] = {
            "element": element_id,
            "i_local_y": float(i_local_y),
            "j_local_y": float(j_local_y),
        }

    def add_nodal_load(self, node_id: int, fx: float = 0.0, fy: float = 0.0, mz: float = 0.0) -> None:
        self._require_node(node_id)
        self.nodal_loads[int(node_id)] = {
            "node": int(node_id),
            "fx": float(fx),
            "fy": float(fy),
            "mz": float(mz),
        }

    def add_member_load(
        self,
        element_id: int,
        load_type: str,
        direction: str = "local_y",
        w: float | str | None = None,
        p: float | str | None = None,
        a: float | str | None = None,
        x_start: float | str | None = None,
        x_end: float | str | None = None,
        load_id: int | None = None,
    ) -> int:
        """Add or update a mechanical UDL/point member load."""
        load_id = int(load_id) if load_id not in (None, "") else self._allocate_member_load_id()
        payload, display_range = self._member_load_payload(
            element_id,
            load_type,
            direction,
            w=w,
            p=p,
            a=a,
            x_start=x_start,
            x_end=x_end,
        )
        record = {
            "id": load_id,
            "element": int(element_id),
            "load_type": str(load_type),
            "direction": str(direction).strip().lower(),
            "w": payload.get("w"),
            "p": payload.get("p"),
            "a": payload.get("a"),
            "x_start": display_range.get("x_start"),
            "x_end": display_range.get("x_end"),
            "payload": payload,
        }
        self.member_loads[load_id] = record
        self._next_member_load_id = max(self._next_member_load_id, load_id + 1)
        return load_id

    def update_member_load(
        self,
        load_id: int,
        element_id: int,
        load_type: str,
        direction: str = "local_y",
        w: float | str | None = None,
        p: float | str | None = None,
        a: float | str | None = None,
        x_start: float | str | None = None,
        x_end: float | str | None = None,
    ) -> None:
        if int(load_id) not in self.member_loads:
            raise ValueError(f"Unknown member load id {load_id}.")
        self.add_member_load(
            element_id,
            load_type,
            direction,
            w=w,
            p=p,
            a=a,
            x_start=x_start,
            x_end=x_end,
            load_id=int(load_id),
        )

    def get_member_loads(self) -> list[dict[str, Any]]:
        return self.table_records("member_loads")

    def add_thermal_load(
        self,
        element_id: int,
        thermal_type: str,
        T_uniform: float | str | None = None,
        T_top: float | str | None = None,
        T_bottom: float | str | None = None,
    ) -> None:
        """Add one thermal member load for an existing element."""
        element_id = int(element_id)
        self._require_element(element_id)
        thermal_type_norm = str(thermal_type).strip().lower()
        record = {
            "element": element_id,
            "thermal_type": thermal_type,
            "T_uniform": _optional_float(T_uniform),
            "T_top": _optional_float(T_top),
            "T_bottom": _optional_float(T_bottom),
        }
        payload = _thermal_payload(record, thermal_type_norm)
        record["payload"] = payload
        self.thermal_loads[element_id] = record

    def add_support_settlement(
        self,
        node_id: int,
        ux: float | str | None = None,
        uy: float | str | None = None,
        rz: float | str | None = None,
    ) -> None:
        """Add prescribed support displacement values for an existing node."""
        node_id = int(node_id)
        self._require_node(node_id)
        self.support_settlements[node_id] = {
            "node": node_id,
            "ux": _optional_float(ux),
            "uy": _optional_float(uy),
            "rz": _optional_float(rz),
        }

    def add_modal_mass(self, node_id: int, ux: float = 0.0, uy: float = 0.0, rz: float = 0.0) -> None:
        self._require_node(node_id)
        self.modal_masses[int(node_id)] = {
            "ux": float(ux),
            "uy": float(uy),
            "rz": float(rz),
        }
        self.modal_mass_source_type = "manual"

    def set_modal_mass_mapping(self, mapping: dict[int, dict[str, float]], source_type: str = "manual") -> None:
        self.modal_masses = {}
        for node_id, masses in mapping.items():
            self._require_node(int(node_id))
            self.modal_masses[int(node_id)] = {
                "ux": float(masses.get("ux", 0.0)),
                "uy": float(masses.get("uy", 0.0)),
                "rz": float(masses.get("rz", 0.0)),
            }
        self.modal_mass_source_type = source_type

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
        nodes = self.table_records("nodes")
        by_node = {node["id"]: node for node in nodes}
        for node_id, settlement in self.support_settlements.items():
            prescribed = {
                dof: value
                for dof, value in (
                    ("ux", settlement.get("ux")),
                    ("uy", settlement.get("uy")),
                    ("rz", settlement.get("rz")),
                )
                if value is not None
            }
            if prescribed:
                by_node[node_id]["prescribed_displacements"] = prescribed

        elements = self.table_records("frame_elements") + self.table_records("truss_elements")
        by_element = {element["id"]: element for element in elements}
        for load in self.table_records("member_loads"):
            by_element[load["element"]].setdefault("member_loads", []).append(deepcopy(load["payload"]))
        for element_id, load in self.thermal_loads.items():
            by_element[element_id].setdefault("member_loads", []).append(deepcopy(load["payload"]))
        for element_id, offset in self.axis_offsets.items():
            by_element[element_id]["axis_offset"] = {
                "i_local_y": float(offset.get("i_local_y", 0.0)),
                "j_local_y": float(offset.get("j_local_y", 0.0)),
            }

        return {
            "nodes": nodes,
            "materials": self.table_records("materials"),
            "sections": self.table_records("sections"),
            "elements": elements,
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
            prescribed = node.get("prescribed_displacements", {})
            if prescribed and any(float(prescribed.get(dof, 0.0)) != 0.0 for dof in ("ux", "uy", "rz")):
                self.add_support_settlement(
                    node["id"],
                    prescribed.get("ux"),
                    prescribed.get("uy"),
                    prescribed.get("rz"),
                )
        for element in data.get("elements", []):
            if element["type"].lower() == "frame":
                self.add_frame_element(
                    element["id"], element["node_i"], element["node_j"], element["material"], element["section"]
                )
                axis_offset = element.get("axis_offset", {}) or {}
                if axis_offset:
                    self.add_axis_offset(
                        element["id"],
                        axis_offset.get("i_local_y", 0.0),
                        axis_offset.get("j_local_y", 0.0),
                    )
            elif element["type"].lower() == "truss":
                if element.get("axis_offset"):
                    raise ValueError("Axis offsets are supported for frame elements only.")
                self.add_truss_element(
                    element["id"], element["node_i"], element["node_j"], element["material"], element["section"]
                )
            for load in element.get("member_loads", []):
                load_type = str(load.get("type", "")).lower()
                if load_type == "thermal":
                    if "delta_T" in load:
                        self.add_thermal_load(
                            element["id"],
                            "Combined" if load.get("T_uniform") is not None else "Gradient / Top-Bottom",
                            load.get("T_uniform"),
                            0.0,
                            load.get("delta_T"),
                        )
                    else:
                        self.add_thermal_load(
                            element["id"],
                            "Gradient / Top-Bottom" if ("T_top" in load or "T_bottom" in load) else "Uniform",
                            load.get("T_uniform"),
                            load.get("T_top"),
                            load.get("T_bottom"),
                        )
                elif load_type in {"udl", "point"}:
                    self.add_member_load(
                        element["id"],
                        load_type,
                        load.get("direction", "local_y"),
                        w=load.get("w"),
                        p=load.get("p"),
                        a=load.get("a"),
                        x_start=load.get("x_start"),
                        x_end=load.get("x_end"),
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
            f"Axis offset records: {len(self.axis_offsets)}",
            f"Nodal loads: {len(self.nodal_loads)}",
            f"Member loads: {len(self.member_loads)}",
            f"Thermal loads: {len(self.thermal_loads)}",
            f"Support settlements: {len(self.support_settlements)}",
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
        if table == "axis_offsets":
            return self.axis_offsets
        if table == "nodal_loads":
            return self.nodal_loads
        if table == "member_loads":
            return self.member_loads
        if table == "thermal_loads":
            return self.thermal_loads
        if table == "support_settlements":
            return self.support_settlements
        if table == "modal_masses":
            return self.modal_masses
        raise ValueError(f"Unknown model builder table: {table}")

    def _require_node(self, node_id: int) -> None:
        if int(node_id) not in self.nodes:
            raise ValueError(f"Unknown node id {node_id}.")

    def _require_element(self, element_id: int) -> None:
        if int(element_id) not in self.frame_elements and int(element_id) not in self.truss_elements:
            raise ValueError(f"Unknown element id {element_id}.")

    def _allocate_member_load_id(self) -> int:
        while self._next_member_load_id in self.member_loads:
            self._next_member_load_id += 1
        load_id = self._next_member_load_id
        self._next_member_load_id += 1
        return load_id

    def _member_load_payload(
        self,
        element_id: int,
        load_type: str,
        direction: str,
        w: float | str | None = None,
        p: float | str | None = None,
        a: float | str | None = None,
        x_start: float | str | None = None,
        x_end: float | str | None = None,
    ) -> tuple[dict[str, float | str], dict[str, float | None]]:
        element = self.validate_member_load_reference(element_id, load_type, direction)
        load_type_norm = str(load_type).strip().lower()
        direction_norm = str(direction).strip().lower()
        if load_type_norm == "udl":
            if w is None or str(w).strip() == "":
                raise ValueError("UDL member load requires w.")
            display_range = self._validate_full_span_udl_range(element, x_start, x_end)
            return {"type": "udl", "direction": direction_norm, "w": float(w)}, display_range
        if load_type_norm == "point":
            if p is None or str(p).strip() == "":
                raise ValueError("Point member load requires p.")
            if a is None or str(a).strip() == "":
                raise ValueError("Point member load requires a.")
            a_value = float(a)
            length = self._element_length(element)
            if length is not None and (a_value < 0.0 or a_value > length):
                raise ValueError(f"Point load location a must satisfy 0 <= a <= L ({length:.6g}).")
            if length is None and a_value < 0.0:
                raise ValueError("Point load location a must be nonnegative.")
            return {"type": "point", "direction": direction_norm, "p": float(p), "a": a_value}, {
                "x_start": None,
                "x_end": None,
            }
        raise ValueError("Member load type must be UDL or Point.")

    def validate_member_load_reference(
        self,
        element_id: int,
        load_type: str = "udl",
        direction: str = "local_y",
    ) -> dict[str, Any]:
        element_id = int(element_id)
        element = self.frame_elements.get(element_id) or self.truss_elements.get(element_id)
        if element is None:
            raise ValueError(f"Unknown element id {element_id}.")

        load_type_norm = str(load_type).strip().lower()
        direction_norm = str(direction).strip().lower()
        if load_type_norm not in {"udl", "point"}:
            raise ValueError("Member load type must be UDL or Point.")
        if direction_norm not in {"local_y", "local_x"}:
            raise ValueError("Member load direction must be local_y or local_x.")
        if element["type"] == "truss" and direction_norm == "local_y":
            raise ValueError("Transverse local_y member loads are only supported for frame elements in the GUI.")
        return element

    def _element_length(self, element: dict[str, Any]) -> float | None:
        node_i = self.nodes.get(int(element["node_i"]))
        node_j = self.nodes.get(int(element["node_j"]))
        if node_i is None or node_j is None:
            return None
        dx = float(node_j["x"]) - float(node_i["x"])
        dy = float(node_j["y"]) - float(node_i["y"])
        return (dx * dx + dy * dy) ** 0.5

    def _validate_full_span_udl_range(
        self,
        element: dict[str, Any],
        x_start: float | str | None,
        x_end: float | str | None,
    ) -> dict[str, float | None]:
        length = self._element_length(element)
        start_given = x_start is not None and str(x_start).strip() != ""
        end_given = x_end is not None and str(x_end).strip() != ""

        if length is None:
            if start_given or end_given:
                raise ValueError("UDL range cannot be validated because element length is unavailable.")
            return {"x_start": None, "x_end": None}

        start = float(x_start) if start_given else 0.0
        end = float(x_end) if end_given else length
        if start < 0.0 or end < 0.0 or start > end or end > length:
            raise ValueError(f"Invalid UDL range: require 0 <= x_start <= x_end <= L ({length:.6g}).")
        if abs(start) > 1.0e-9 or abs(end - length) > 1.0e-9:
            raise ValueError("Partial UDL range is not supported by the current backend. Use x_start=0 and x_end=L.")
        return {"x_start": 0.0, "x_end": length}


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
    return table in {
        "nodes",
        "frame_elements",
        "truss_elements",
        "axis_offsets",
        "nodal_loads",
        "member_loads",
        "thermal_loads",
        "support_settlements",
        "modal_masses",
    }


def _optional_float(value: float | str | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    return float(value)


def _thermal_payload(record: dict[str, Any], thermal_type: str) -> dict[str, float | str]:
    t_uniform = record["T_uniform"]
    t_top = record["T_top"]
    t_bottom = record["T_bottom"]

    if thermal_type == "uniform":
        if t_uniform is None:
            raise ValueError("Uniform thermal load requires T_uniform.")
        return {"type": "thermal", "T_uniform": float(t_uniform)}

    if thermal_type in {"gradient / top-bottom", "gradient", "top-bottom"}:
        if t_top is None or t_bottom is None:
            raise ValueError("Thermal gradient requires both T_top and T_bottom.")
        return {"type": "thermal", "T_top": float(t_top), "T_bottom": float(t_bottom)}

    if thermal_type == "combined":
        if t_uniform is None or t_top is None or t_bottom is None:
            raise ValueError("Combined thermal load requires T_uniform, T_top, and T_bottom.")
        return {
            "type": "thermal",
            "T_uniform": float(t_uniform),
            "delta_T": float(t_bottom) - float(t_top),
        }

    raise ValueError("Thermal type must be Uniform, Gradient / Top-Bottom, or Combined.")
