"""Simplified SAP-like input dialogs for GUI-defined models."""

from __future__ import annotations

from typing import Any, Callable

import tkinter as tk
from tkinter import messagebox, ttk

from .model_builder import ModelBuilder


FieldSpec = dict[str, Any]


def open_materials_dialog(parent, builder: ModelBuilder, on_change: Callable[[], None] | None = None) -> None:
    _RecordDialog(
        parent,
        "Define Materials",
        ("name", "E", "alpha"),
        [
            {"key": "name", "label": "Name", "default": "steel"},
            {"key": "E", "label": "E", "default": "200000000"},
            {"key": "alpha", "label": "alpha", "default": "1.2e-5"},
        ],
        lambda: [{"name": r["id"], "E": r["E"], "alpha": r["alpha"]} for r in builder.table_records("materials")],
        lambda values: builder.add_material(values["name"], values["E"], values["alpha"]),
        lambda key: builder.delete_record("materials", key),
        "name",
        on_change=on_change,
    )


def open_sections_dialog(parent, builder: ModelBuilder, on_change: Callable[[], None] | None = None) -> None:
    _RecordDialog(
        parent,
        "Define Sections",
        ("name", "A", "I", "d"),
        [
            {"key": "name", "label": "Name", "default": "beam"},
            {"key": "A", "label": "A", "default": "0.01"},
            {"key": "I", "label": "I", "default": "1e-4"},
            {"key": "d", "label": "d", "default": "0.3"},
        ],
        lambda: [
            {"name": r["id"], "A": r["A"], "I": r["I"], "d": r.get("d", "")}
            for r in builder.table_records("sections")
        ],
        lambda values: builder.add_section(values["name"], values["A"], values["I"], values["d"] or None),
        lambda key: builder.delete_record("sections", key),
        "name",
        on_change=on_change,
    )


def open_nodes_dialog(parent, builder: ModelBuilder, on_change: Callable[[], None] | None = None) -> None:
    restraint = ["FIX", "FREE"]
    _RecordDialog(
        parent,
        "Define Nodes / Joints",
        ("id", "x", "y", "ux", "uy", "rz"),
        [
            {"key": "id", "label": "ID", "default": "1"},
            {"key": "x", "label": "X", "default": "0"},
            {"key": "y", "label": "Y", "default": "0"},
            {"key": "ux", "label": "ux", "default": "FREE", "choices": restraint},
            {"key": "uy", "label": "uy", "default": "FREE", "choices": restraint},
            {"key": "rz", "label": "rz", "default": "FREE", "choices": restraint},
        ],
        lambda: [_node_record(r) for r in builder.table_records("nodes")],
        lambda values: builder.add_node(values["id"], values["x"], values["y"], values["ux"], values["uy"], values["rz"]),
        lambda key: builder.delete_record("nodes", key),
        "id",
        on_change=on_change,
    )


def open_frame_elements_dialog(parent, builder: ModelBuilder, on_change: Callable[[], None] | None = None) -> None:
    _element_dialog(parent, builder, "Define Frame Elements", "frame_elements", builder.add_frame_element, on_change)


def open_truss_elements_dialog(parent, builder: ModelBuilder, on_change: Callable[[], None] | None = None) -> None:
    _element_dialog(parent, builder, "Define Truss Elements", "truss_elements", builder.add_truss_element, on_change)


def open_nodal_loads_dialog(parent, builder: ModelBuilder, on_change: Callable[[], None] | None = None) -> None:
    _RecordDialog(
        parent,
        "Define Nodal Loads",
        ("node", "fx", "fy", "mz"),
        [
            {"key": "node", "label": "Node ID", "default": "1"},
            {"key": "fx", "label": "FX", "default": "0"},
            {"key": "fy", "label": "FY", "default": "0"},
            {"key": "mz", "label": "MZ", "default": "0"},
        ],
        lambda: builder.table_records("nodal_loads"),
        lambda values: builder.add_nodal_load(values["node"], values["fx"], values["fy"], values["mz"]),
        lambda key: builder.delete_record("nodal_loads", key),
        "node",
        on_change=on_change,
    )


def open_member_loads_dialog(parent, builder: ModelBuilder, on_change: Callable[[], None] | None = None) -> None:
    element_ids = sorted(set(builder.frame_elements) | set(builder.truss_elements))
    _RecordDialog(
        parent,
        "Define Member Loads",
        ("id", "element", "load_type", "direction", "w", "p", "a"),
        [
            {"key": "id", "label": "Load ID", "default": ""},
            {"key": "element", "label": "Element", "default": str(element_ids[0]) if element_ids else "", "choices": [str(eid) for eid in element_ids]},
            {"key": "load_type", "label": "Type", "default": "UDL", "choices": ["UDL", "Point"]},
            {"key": "direction", "label": "Direction", "default": "local_y", "choices": ["local_y", "local_x"]},
            {"key": "w", "label": "UDL w", "default": "-10000"},
            {"key": "p", "label": "Point p", "default": ""},
            {"key": "a", "label": "Point a", "default": ""},
        ],
        lambda: [_member_load_record(record) for record in builder.table_records("member_loads")],
        lambda values: _save_member_load(builder, values),
        lambda key: builder.delete_record("member_loads", key),
        "id",
        on_change=on_change,
        help_text="Negative local_y usually means downward load for a horizontal member, depending on local-axis orientation.",
    )


def open_thermal_loads_dialog(parent, builder: ModelBuilder, on_change: Callable[[], None] | None = None) -> None:
    _RecordDialog(
        parent,
        "Define Thermal Loads",
        ("element", "thermal_type", "T_uniform", "T_top", "T_bottom"),
        [
            {"key": "element", "label": "Element ID", "default": "1"},
            {
                "key": "thermal_type",
                "label": "Type",
                "default": "Uniform",
                "choices": ["Uniform", "Gradient / Top-Bottom", "Combined"],
            },
            {"key": "T_uniform", "label": "T_uniform", "default": "0"},
            {"key": "T_top", "label": "T_top", "default": ""},
            {"key": "T_bottom", "label": "T_bottom", "default": ""},
        ],
        lambda: [
            {
                "element": record["element"],
                "thermal_type": record["thermal_type"],
                "T_uniform": _blank_none(record.get("T_uniform")),
                "T_top": _blank_none(record.get("T_top")),
                "T_bottom": _blank_none(record.get("T_bottom")),
            }
            for record in builder.table_records("thermal_loads")
        ],
        lambda values: _save_thermal_load(parent, builder, values),
        lambda key: builder.delete_record("thermal_loads", key),
        "element",
        on_change=on_change,
    )


def open_support_settlements_dialog(parent, builder: ModelBuilder, on_change: Callable[[], None] | None = None) -> None:
    _RecordDialog(
        parent,
        "Define Support Settlements",
        ("node", "ux", "uy", "rz"),
        [
            {"key": "node", "label": "Node ID", "default": "1"},
            {"key": "ux", "label": "ux", "default": ""},
            {"key": "uy", "label": "uy", "default": ""},
            {"key": "rz", "label": "rz", "default": ""},
        ],
        lambda: [
            {
                "node": record["node"],
                "ux": _blank_none(record.get("ux")),
                "uy": _blank_none(record.get("uy")),
                "rz": _blank_none(record.get("rz")),
            }
            for record in builder.table_records("support_settlements")
        ],
        lambda values: _save_support_settlement(parent, builder, values),
        lambda key: builder.delete_record("support_settlements", key),
        "node",
        on_change=on_change,
    )


def open_modal_masses_dialog(parent, builder: ModelBuilder, on_change: Callable[[], None] | None = None) -> None:
    _RecordDialog(
        parent,
        "Define Modal Masses",
        ("node", "ux", "uy", "rz"),
        [
            {"key": "node", "label": "Node ID", "default": "1"},
            {"key": "ux", "label": "UX mass", "default": "10000"},
            {"key": "uy", "label": "UY mass", "default": "0"},
            {"key": "rz", "label": "RZ mass", "default": "0"},
        ],
        lambda: [{"node": k, **v} for k, v in sorted(builder.to_mass_mapping().items())],
        lambda values: builder.add_modal_mass(values["node"], values["ux"], values["uy"], values["rz"]),
        lambda key: builder.delete_record("modal_masses", key),
        "node",
        on_change=on_change,
    )


def open_analysis_options_dialog(parent, builder: ModelBuilder, on_apply: Callable[[], None] | None = None) -> None:
    dialog = tk.Toplevel(parent)
    dialog.title("Analysis Options")
    dialog.transient(parent)

    entries: dict[str, tk.Entry] = {}
    labels = [
        ("default_lateral_mass", "Default lateral mass"),
        ("num_modes", "Number of modes"),
        ("static_deformation_scale", "Static deformation scale"),
        ("force_diagram_scale", "Force diagram scale"),
        ("mode_shape_scale", "Mode shape scale"),
    ]
    for row, (key, label) in enumerate(labels):
        tk.Label(dialog, text=label).grid(row=row, column=0, sticky="w", padx=6, pady=4)
        entry = tk.Entry(dialog)
        entry.insert(0, str(builder.analysis_options[key]))
        entry.grid(row=row, column=1, sticky="ew", padx=6, pady=4)
        entries[key] = entry

    def apply() -> None:
        try:
            builder.update_analysis_options(
                default_lateral_mass=float(entries["default_lateral_mass"].get()),
                num_modes=int(entries["num_modes"].get()),
                static_deformation_scale=float(entries["static_deformation_scale"].get()),
                force_diagram_scale=float(entries["force_diagram_scale"].get()),
                mode_shape_scale=float(entries["mode_shape_scale"].get()),
            )
        except Exception as exc:
            messagebox.showerror("Invalid analysis options", str(exc), parent=dialog)
            return
        if on_apply is not None:
            on_apply()
        dialog.destroy()

    buttons = tk.Frame(dialog)
    buttons.grid(row=len(labels), column=0, columnspan=2, sticky="e", padx=6, pady=8)
    tk.Button(buttons, text="OK", command=apply).pack(side=tk.LEFT, padx=3)
    tk.Button(buttons, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=3)


def _element_dialog(
    parent,
    builder: ModelBuilder,
    title: str,
    table: str,
    save_func: Callable[..., None],
    on_change: Callable[[], None] | None = None,
) -> None:
    _RecordDialog(
        parent,
        title,
        ("id", "node_i", "node_j", "material", "section"),
        [
            {"key": "id", "label": "ID", "default": "1"},
            {"key": "node_i", "label": "Node i", "default": "1"},
            {"key": "node_j", "label": "Node j", "default": "2"},
            {"key": "material", "label": "Material", "default": "", "choices": sorted(builder.materials)},
            {"key": "section", "label": "Section", "default": "", "choices": sorted(builder.sections)},
        ],
        lambda: builder.table_records(table),
        lambda values: save_func(values["id"], values["node_i"], values["node_j"], values["material"], values["section"]),
        lambda key: builder.delete_record(table, key),
        "id",
        on_change=on_change,
    )


def _save_thermal_load(parent, builder: ModelBuilder, values: dict[str, Any]) -> None:
    element_id = int(values["element"])
    element = _find_element(builder, element_id)
    thermal_type = values["thermal_type"]
    if element is None:
        raise ValueError(f"Unknown element id {element_id}.")

    has_gradient = thermal_type in {"Gradient / Top-Bottom", "Combined"}
    if has_gradient and element["type"] == "truss":
        messagebox.showwarning(
            "Thermal gradient on truss",
            "Truss elements are axial-only. The backend ignores thermal-gradient bending for trusses.",
            parent=parent,
        )
    if has_gradient and element["type"] == "frame":
        section = builder.sections.get(element["section"])
        if section is not None and section.get("d") is None:
            messagebox.showwarning(
                "Missing section depth",
                "Frame thermal gradients require section depth d. Analysis may fail until d is defined.",
                parent=parent,
            )

    builder.add_thermal_load(
        element_id,
        thermal_type,
        values.get("T_uniform"),
        values.get("T_top"),
        values.get("T_bottom"),
    )


def _save_member_load(builder: ModelBuilder, values: dict[str, Any]) -> None:
    load_id = values.get("id") or None
    builder.add_member_load(
        values["element"],
        values["load_type"],
        values.get("direction", "local_y"),
        w=values.get("w"),
        p=values.get("p"),
        a=values.get("a"),
        load_id=load_id,
    )


def _save_support_settlement(parent, builder: ModelBuilder, values: dict[str, Any]) -> None:
    node_id = int(values["node"])
    node = builder.nodes.get(node_id)
    if node is None:
        raise ValueError(f"Unknown node id {node_id}.")

    prescribed = {dof: _optional_float(values.get(dof)) for dof in ("ux", "uy", "rz")}
    free_dofs = [
        dof
        for dof, value in prescribed.items()
        if value not in (None, 0.0) and not node["restraints"].get(dof, False)
    ]
    if free_dofs:
        messagebox.showwarning(
            "Settlement on free DOF",
            "The backend requires prescribed settlements on restrained DOFs. "
            f"Free DOF(s): {', '.join(free_dofs)}.",
            parent=parent,
        )

    builder.add_support_settlement(node_id, prescribed["ux"], prescribed["uy"], prescribed["rz"])


def _find_element(builder: ModelBuilder, element_id: int) -> dict[str, Any] | None:
    if element_id in builder.frame_elements:
        return builder.frame_elements[element_id]
    if element_id in builder.truss_elements:
        return builder.truss_elements[element_id]
    return None


def _blank_none(value) -> str:
    return "" if value is None else str(value)


def _optional_float(value) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    return float(value)


def _node_record(record: dict[str, Any]) -> dict[str, Any]:
    restraints = record["restraints"]
    return {
        "id": record["id"],
        "x": record["x"],
        "y": record["y"],
        "ux": "FIX" if restraints["ux"] else "FREE",
        "uy": "FIX" if restraints["uy"] else "FREE",
        "rz": "FIX" if restraints["rz"] else "FREE",
    }


def _member_load_record(record: dict[str, Any]) -> dict[str, Any]:
    load_type = str(record["load_type"]).upper() if str(record["load_type"]).lower() == "udl" else "Point"
    return {
        "id": record["id"],
        "element": record["element"],
        "load_type": load_type,
        "direction": record["direction"],
        "w": _blank_none(record.get("w")),
        "p": _blank_none(record.get("p")),
        "a": _blank_none(record.get("a")),
    }


class _RecordDialog:
    def __init__(
        self,
        parent,
        title: str,
        columns: tuple[str, ...],
        fields: list[FieldSpec],
        records_func: Callable[[], list[dict[str, Any]]],
        save_func: Callable[[dict[str, Any]], None],
        delete_func: Callable[[str], None],
        key_field: str,
        on_change: Callable[[], None] | None = None,
        help_text: str | None = None,
    ):
        self.records_func = records_func
        self.save_func = save_func
        self.delete_func = delete_func
        self.key_field = key_field
        self.fields = fields
        self.on_change = on_change
        self.entries: dict[str, tk.Entry | ttk.Combobox] = {}

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.transient(parent)

        form = tk.Frame(self.dialog, padx=8, pady=8)
        form.pack(side=tk.TOP, fill=tk.X)
        for col, spec in enumerate(fields):
            tk.Label(form, text=spec["label"]).grid(row=0, column=col, sticky="w")
            if "choices" in spec:
                widget = ttk.Combobox(form, values=spec["choices"], width=12)
            else:
                widget = tk.Entry(form, width=12)
            widget.insert(0, spec.get("default", ""))
            widget.grid(row=1, column=col, padx=3, pady=3)
            self.entries[spec["key"]] = widget

        if help_text:
            tk.Label(form, text=help_text, foreground="0.35", wraplength=760, justify=tk.LEFT).grid(
                row=2,
                column=0,
                columnspan=max(1, len(fields)),
                sticky="w",
                pady=(4, 0),
            )

        self.tree = ttk.Treeview(self.dialog, columns=columns, show="headings", height=8)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor=tk.CENTER)
        self.tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=8, pady=4)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        buttons = tk.Frame(self.dialog, padx=8, pady=8)
        buttons.pack(side=tk.TOP, fill=tk.X)
        tk.Button(buttons, text="Add", command=self._save).pack(side=tk.LEFT, padx=3)
        tk.Button(buttons, text="Update", command=self._save).pack(side=tk.LEFT, padx=3)
        tk.Button(buttons, text="Delete", command=self._delete).pack(side=tk.LEFT, padx=3)
        tk.Button(buttons, text="OK", command=self._close_ok).pack(side=tk.RIGHT, padx=3)
        tk.Button(buttons, text="Cancel", command=self.dialog.destroy).pack(side=tk.RIGHT, padx=3)

        self._refresh()

    def _values(self) -> dict[str, Any]:
        return {key: widget.get().strip() for key, widget in self.entries.items()}

    def _save(self) -> None:
        try:
            self.save_func(self._values())
        except Exception as exc:
            messagebox.showerror("Invalid input", str(exc), parent=self.dialog)
            return
        self._refresh()
        self._notify_change()

    def _delete(self) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        self.delete_func(selected[0])
        self._refresh()
        self._notify_change()

    def _close_ok(self) -> None:
        self._notify_change()
        self.dialog.destroy()

    def _on_select(self, _event=None) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0], "values")
        for spec, value in zip(self.fields, values):
            widget = self.entries[spec["key"]]
            widget.delete(0, tk.END)
            widget.insert(0, value)

    def _refresh(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for record in self.records_func():
            key = str(record[self.key_field])
            values = [record.get(col, "") for col in self.tree["columns"]]
            self.tree.insert("", tk.END, iid=key, values=values)

    def _notify_change(self) -> None:
        if self.on_change is not None:
            self.on_change()
