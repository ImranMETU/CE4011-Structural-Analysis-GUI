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

from postprocessing.drift_results import (
    compute_roof_displacement,
    compute_story_drift,
    format_roof_displacement_rows,
    format_story_drift_rows,
)
from postprocessing.element_station_results import all_frame_station_results
from postprocessing.modal_diagnostics import (
    condensed_matrix_summary,
    full_mode_shape_rows,
    modal_dof_classification_rows,
    modal_mass_summary,
    modal_properties_rows,
)
from postprocessing.rha_results import (
    format_peak_floor_response_rows,
    format_peak_story_drift_rows,
    format_rha_summary_rows,
)
from postprocessing.rha_node_results import compute_node_response_peaks, format_node_response_rows
from postprocessing.rsa_results import (
    rsa_combined_response_rows,
    rsa_modal_peak_response_rows,
    rsa_modal_peak_story_drift_rows,
)
from postprocessing.solver_diagnostics import format_solver_diagnostics_rows


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


def format_element_station_force_rows(
    static_result: dict[str, Any],
    n_stations: int = 11,
) -> tuple[list[str], TableRows]:
    """Return station-based frame section force table headers and rows."""
    headers = ["Element", "Type", "Station", "xi", "x_local", "global_x", "global_y", "N", "V", "M"]
    rows = []
    for row in all_frame_station_results(static_result, n_stations=n_stations):
        rows.append(
            [
                str(row.get("element", "")),
                str(row.get("type", "")),
                str(row.get("station", "")),
                _format_number(row.get("xi", 0.0)),
                _format_number(row.get("x_local", 0.0)),
                _format_number(row.get("global_x", 0.0)),
                _format_number(row.get("global_y", 0.0)),
                _format_number(row.get("N", 0.0)),
                _format_number(row.get("V", 0.0)),
                _format_number(row.get("M", 0.0)),
            ]
        )
    return headers, rows


def format_element_deformed_slope_rows(
    static_result: dict[str, Any],
    n_stations: int = 11,
) -> tuple[list[str], TableRows]:
    """Return station-based Hermite displacement/slope table headers and rows."""
    headers = ["Element", "Station", "xi", "x_local", "global_x", "global_y", "u_local", "v_local", "slope_rad"]
    rows = []
    for row in all_frame_station_results(static_result, n_stations=n_stations):
        rows.append(
            [
                str(row.get("element", "")),
                str(row.get("station", "")),
                _format_number(row.get("xi", 0.0)),
                _format_number(row.get("x_local", 0.0)),
                _format_number(row.get("global_x", 0.0)),
                _format_number(row.get("global_y", 0.0)),
                _format_number(row.get("u_local", 0.0)),
                _format_number(row.get("v_local", 0.0)),
                _format_number(row.get("slope", 0.0)),
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


def format_modal_properties_rows(modal_result: dict[str, Any]) -> tuple[list[str], TableRows]:
    """Return detailed modal properties table."""
    headers = [
        "Mode",
        "lambda",
        "omega_rad_per_s",
        "frequency_Hz",
        "period_s",
        "Gamma",
        "Modal Mass Mn",
        "Modal Stiffness Kn",
        "Effective Modal Mass",
        "Effective Mass Ratio",
        "Cumulative Mass Ratio",
        "Normalization",
        "Max Component",
        "Controlling Node",
        "Controlling DOF",
    ]
    rows = []
    for row in modal_properties_rows(modal_result):
        rows.append(
            [
                str(row.get("mode", "")),
                _format_number(row.get("eigenvalue", "")),
                _format_number(row.get("omega", "")),
                _format_number(row.get("frequency_hz", "")),
                _format_number(row.get("period", "")),
                _format_number(row.get("gamma", "")),
                _format_number(row.get("modal_mass", "")),
                _format_number(row.get("modal_stiffness", "")),
                _format_number(row.get("effective_modal_mass", "")),
                _format_number(row.get("effective_modal_mass_ratio", "")),
                _format_number(row.get("cumulative_effective_mass_ratio", "")),
                str(row.get("normalization", "")),
                _format_number(row.get("max_modal_component", "")),
                str(row.get("controlling_node", "")),
                str(row.get("controlling_dof", "")),
            ]
        )
    return headers, rows


def format_modal_dof_classification_rows(modal_result: dict[str, Any]) -> tuple[list[str], TableRows]:
    """Return modal DOF mass classification table."""
    headers = ["Free DOF Index", "Node", "DOF", "Mass", "Classification", "Note"]
    rows = []
    for row in modal_dof_classification_rows(modal_result):
        rows.append(
            [
                str(row.get("free_dof_index", "")),
                str(row.get("node", "")),
                str(row.get("dof", "")),
                _format_number(row.get("mass", 0.0)),
                str(row.get("classification", "")),
                str(row.get("note", "")),
            ]
        )
    return headers, rows


def format_condensed_modal_matrix_rows(modal_result: dict[str, Any]) -> tuple[list[str], TableRows]:
    """Return matrix-level modal condensation diagnostics."""
    headers = ["Property", "Value"]
    summary = condensed_matrix_summary(modal_result)
    keys = [
        "free_stiffness_size",
        "free_mass_size",
        "massive_dof_count",
        "massless_dof_count",
        "condensed_stiffness_size",
        "condensed_mass_size",
        "condensed_stiffness_symmetry_error",
        "condensed_mass_symmetry_error",
        "kbb_condition_number",
        "notes",
    ]
    rows = [[key, _format_number(summary[key]) if isinstance(summary.get(key), (float, int)) else str(summary.get(key, ""))] for key in keys]
    return headers, rows


def format_full_mode_shape_rows(modal_result: dict[str, Any]) -> tuple[list[str], TableRows]:
    """Return recovered full free-DOF mode shapes by node."""
    headers = ["Mode", "Node", "ux", "uy", "rz"]
    rows = []
    for row in full_mode_shape_rows(modal_result):
        rows.append(
            [
                str(row.get("mode", "")),
                str(row.get("node", "")),
                _format_number(row.get("ux", 0.0)),
                _format_number(row.get("uy", 0.0)),
                _format_number(row.get("rz", 0.0)),
            ]
        )
    return headers, rows


def format_modal_mass_summary_rows(modal_result: dict[str, Any]) -> tuple[list[str], TableRows]:
    """Return modal mass source and active-mass summary."""
    headers = ["Property", "Value"]
    summary = modal_mass_summary(modal_result, modal_result.get("mass_source_summary"))
    rows = []
    for key, value in summary.items():
        rows.append([key, _format_number(value) if isinstance(value, (float, int)) else str(value)])
    return headers, rows


def format_rha_summary_table_rows(rha_result: dict[str, Any]) -> tuple[list[str], TableRows]:
    """Return RHA summary table headers and rows."""
    return format_rha_summary_rows(rha_result)


def format_rha_peak_floor_response_rows(rha_result: dict[str, Any]) -> tuple[list[str], TableRows]:
    """Return RHA peak floor response table headers and rows."""
    return format_peak_floor_response_rows(rha_result)


def format_rha_peak_story_drift_rows(rha_result: dict[str, Any]) -> tuple[list[str], TableRows]:
    """Return RHA peak story drift table headers and rows."""
    return format_peak_story_drift_rows(rha_result)


def format_rha_node_peak_response_rows(rha_result: dict[str, Any]) -> tuple[list[str], TableRows]:
    """Return RHA selected-node peak response table for available ux histories."""
    return format_node_response_rows(compute_node_response_peaks(rha_result, dofs=("ux",)))


def format_rsa_modal_peak_response_rows(rsa_result: dict[str, Any]) -> tuple[list[str], TableRows]:
    """Return RSA per-mode peak response table."""
    headers = [
        "Mode",
        "Period s",
        "Frequency Hz",
        "Omega rad/s",
        "Gamma",
        "Sa",
        "Sd",
        "qmax",
        "Peak Roof ux",
        "Controlling Roof Node",
    ]
    rows = []
    for row in rsa_modal_peak_response_rows(rsa_result):
        rows.append(
            [
                str(row.get("mode", "")),
                _format_number(row.get("period_s", 0.0)),
                _format_number(row.get("frequency_hz", 0.0)),
                _format_number(row.get("omega_rad_per_s", 0.0)),
                _format_number(row.get("gamma", 0.0)),
                _format_number(row.get("Sa", 0.0)),
                _format_number(row.get("Sd", 0.0)),
                _format_number(row.get("qmax", 0.0)),
                _format_number(row.get("peak_roof_ux", 0.0)),
                str(row.get("controlling_roof_node", "")),
            ]
        )
    return headers, rows


def format_rsa_modal_peak_story_drift_rows(rsa_result: dict[str, Any]) -> tuple[list[str], TableRows]:
    """Return RSA per-mode story drift table."""
    headers = ["Mode", "Story", "Lower Elevation", "Upper Elevation", "Peak Story Drift", "Peak Drift Ratio"]
    rows = []
    for row in rsa_modal_peak_story_drift_rows(rsa_result):
        rows.append(
            [
                str(row.get("mode", "")),
                str(row.get("story", "")),
                _format_number(row.get("lower_elevation", 0.0)),
                _format_number(row.get("upper_elevation", 0.0)),
                _format_number(row.get("peak_story_drift", 0.0)),
                _format_number(row.get("peak_drift_ratio", 0.0)),
            ]
        )
    return headers, rows


def format_rsa_combined_response_rows(rsa_result: dict[str, Any]) -> tuple[list[str], TableRows]:
    """Return RSA ABSSUM/SRSS/CQC combined response table."""
    headers = ["Quantity", "Location", "ABSSUM", "SRSS", "CQC"]
    rows = []
    for row in rsa_combined_response_rows(rsa_result):
        rows.append(
            [
                str(row.get("quantity", "")),
                str(row.get("location", "")),
                _format_number(row.get("ABSSUM", 0.0)),
                _format_number(row.get("SRSS", 0.0)),
                _format_number(row.get("CQC", 0.0)),
            ]
        )
    return headers, rows


def format_solver_diagnostics_table_rows(diagnostics: dict[str, Any]) -> tuple[list[str], TableRows]:
    """Return solver diagnostics table headers and rows."""
    return format_solver_diagnostics_rows(diagnostics)


def format_static_story_drift_rows(static_result: dict[str, Any]) -> tuple[list[str], TableRows]:
    """Return static story drift table headers and rows."""
    drift_result = compute_story_drift(static_result, direction="ux", method="mean")
    _backend_headers, rows = format_story_drift_rows(drift_result)
    headers = [
        "Story",
        "Lower Elevation",
        "Upper Elevation",
        "Story Height",
        "Lower Floor ux",
        "Upper Floor ux",
        "Story Drift",
        "Abs Story Drift",
        "Drift Ratio",
        "Abs Drift Ratio",
    ]
    return headers, rows


def format_static_roof_displacement_rows(static_result: dict[str, Any]) -> tuple[list[str], TableRows]:
    """Return static roof displacement table headers and rows."""
    roof_result = compute_roof_displacement(static_result, direction="ux", method="max_abs")
    _backend_headers, rows = format_roof_displacement_rows(roof_result)
    headers = ["Roof Elevation", "Roof Nodes", "Direction", "Roof Displacement", "Controlling Node"]
    return headers, [[row[0], row[1], roof_result["direction"], row[2], row[3]] for row in rows]


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
