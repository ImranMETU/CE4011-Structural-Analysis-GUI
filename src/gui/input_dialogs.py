"""Simplified SAP-like input dialogs for GUI-defined models."""

from __future__ import annotations

from typing import Any, Callable

import tkinter as tk
from tkinter import messagebox, ttk

from .model_builder import ModelBuilder


FieldSpec = dict[str, Any]


def open_materials_dialog(parent, builder: ModelBuilder) -> None:
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
    )


def open_sections_dialog(parent, builder: ModelBuilder) -> None:
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
    )


def open_nodes_dialog(parent, builder: ModelBuilder) -> None:
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
    )


def open_frame_elements_dialog(parent, builder: ModelBuilder) -> None:
    _element_dialog(parent, builder, "Define Frame Elements", "frame_elements", builder.add_frame_element)


def open_truss_elements_dialog(parent, builder: ModelBuilder) -> None:
    _element_dialog(parent, builder, "Define Truss Elements", "truss_elements", builder.add_truss_element)


def open_nodal_loads_dialog(parent, builder: ModelBuilder) -> None:
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
    )


def open_modal_masses_dialog(parent, builder: ModelBuilder) -> None:
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


def _element_dialog(parent, builder: ModelBuilder, title: str, table: str, save_func: Callable[..., None]) -> None:
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
    )


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
    ):
        self.records_func = records_func
        self.save_func = save_func
        self.delete_func = delete_func
        self.key_field = key_field
        self.fields = fields
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
        tk.Button(buttons, text="OK", command=self.dialog.destroy).pack(side=tk.RIGHT, padx=3)
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

    def _delete(self) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        self.delete_func(selected[0])
        self._refresh()

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
