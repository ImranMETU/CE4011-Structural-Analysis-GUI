"""Result-table helpers for the Tkinter GUI.

The formatting functions in this module are intentionally pure so tests can
exercise table behavior without launching a GUI mainloop.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Iterable, Sequence

import tkinter as tk
from tkinter import ttk


TableRows = list[list[str]]


def format_nodal_displacement_rows(static_result: dict[str, Any]) -> tuple[list[str], TableRows]:
    """Return node displacement table headers and rows."""
    headers = ["Node", "ux", "uy", "rz"]
    displacements = static_result.get("displacements", {})
    rows = []
    for node_id in sorted(displacements, key=_sort_key):
        values = displacements[node_id]
        rows.append(
            [
                str(node_id),
                _format_number(values.get("ux", 0.0)),
                _format_number(values.get("uy", 0.0)),
                _format_number(values.get("rz", 0.0)),
            ]
        )
    return headers, rows


def format_reaction_rows(static_result: dict[str, Any]) -> tuple[list[str], TableRows]:
    """Return support reaction table headers and rows."""
    headers = ["Node", "Rx", "Ry", "Mz"]
    reactions = static_result.get("reactions", {})
    rows = []
    for node_id in sorted(reactions, key=_sort_key):
        values = reactions[node_id]
        rows.append(
            [
                str(node_id),
                _format_number(values.get("rx", 0.0)),
                _format_number(values.get("ry", 0.0)),
                _format_number(values.get("mz", 0.0)),
            ]
        )
    return headers, rows


def format_member_force_rows(static_result: dict[str, Any]) -> tuple[list[str], TableRows]:
    """Return recovered local member-end force table headers and rows."""
    headers = ["Element", "Type", "i-end Nx", "i-end Vy", "i-end Mz", "j-end Nx", "j-end Vy", "j-end Mz"]
    member_forces = static_result.get("member_end_forces", {})
    elements = static_result.get("elements", {})
    rows = []
    for element_id in sorted(member_forces, key=_sort_key):
        values = member_forces[element_id]
        element = elements.get(element_id, elements.get(str(element_id), {}))
        i_end = values.get("node_i", {})
        j_end = values.get("node_j", {})
        rows.append(
            [
                str(element_id),
                str(element.get("type", "")),
                _format_number(i_end.get("nx", 0.0)),
                _format_number(i_end.get("vy", 0.0)),
                _format_number(i_end.get("mz", 0.0)),
                _format_number(j_end.get("nx", 0.0)),
                _format_number(j_end.get("vy", 0.0)),
                _format_number(j_end.get("mz", 0.0)),
            ]
        )
    return headers, rows


def format_modal_frequency_rows(modal_result: dict[str, Any]) -> tuple[list[str], TableRows]:
    """Return modal frequency table headers and rows."""
    headers = ["Mode", "omega_rad_per_s", "frequency_Hz", "period_s"]
    rows = []
    for row in modal_result.get("frequency_table", []):
        rows.append(
            [
                str(row.get("mode", "")),
                _format_number(row.get("omega", 0.0)),
                _format_number(row.get("frequency_hz", 0.0)),
                _format_number(row.get("period", 0.0)),
            ]
        )
    return headers, rows


def format_modal_participation_rows(modal_result: dict[str, Any]) -> tuple[list[str], TableRows]:
    """Return modal participation table headers and rows."""
    headers = ["Mode", "Gamma", "Effective Modal Mass", "Effective Mass Ratio"]
    rows = []
    for row in modal_result.get("participation", []) or []:
        rows.append(
            [
                str(row.get("mode", "")),
                _format_number(row.get("gamma", 0.0)),
                _format_number(row.get("effective_modal_mass", 0.0)),
                _format_number(row.get("effective_modal_mass_ratio", 0.0)),
            ]
        )
    return headers, rows


def write_table_csv(path: str | Path, headers: Sequence[str], rows: Iterable[Sequence[Any]]) -> None:
    """Write a result table to CSV using UTF-8."""
    with Path(path).open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(list(headers))
        for row in rows:
            writer.writerow(list(row))


def open_table_window(
    parent: tk.Misc,
    title: str,
    headers: Sequence[str],
    rows: Sequence[Sequence[Any]],
    export_command: Any | None = None,
) -> tk.Toplevel:
    """Open a reusable scrollable result-table window."""
    window = tk.Toplevel(parent)
    window.title(title)
    window.geometry("860x420")

    frame = ttk.Frame(window, padding=8)
    frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    tree = ttk.Treeview(frame, columns=list(headers), show="headings")
    y_scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
    x_scroll = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=tree.xview)
    tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

    for header in headers:
        tree.heading(header, text=header)
        tree.column(header, width=max(90, min(180, len(header) * 12)), anchor=tk.CENTER, stretch=True)

    for row in rows:
        tree.insert("", tk.END, values=[str(value) for value in row])

    tree.grid(row=0, column=0, sticky="nsew")
    y_scroll.grid(row=0, column=1, sticky="ns")
    x_scroll.grid(row=1, column=0, sticky="ew")
    frame.rowconfigure(0, weight=1)
    frame.columnconfigure(0, weight=1)

    button_frame = ttk.Frame(window, padding=(8, 0, 8, 8))
    button_frame.pack(side=tk.BOTTOM, fill=tk.X)
    if export_command is not None:
        ttk.Button(button_frame, text="Export CSV", command=export_command).pack(side=tk.RIGHT, padx=(6, 0))
    ttk.Button(button_frame, text="Close", command=window.destroy).pack(side=tk.RIGHT)

    return window


def _format_number(value: Any) -> str:
    if value is None or value == "":
        return ""
    return f"{float(value):.6e}"


def _sort_key(value: Any) -> tuple[int, Any]:
    try:
        return (0, int(value))
    except (TypeError, ValueError):
        return (1, str(value))
