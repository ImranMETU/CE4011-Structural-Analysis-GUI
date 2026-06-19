"""Result-table helpers for the Tkinter GUI.

The formatting functions in this module are intentionally pure so tests can
exercise table behavior without launching a GUI mainloop.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
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
)
from postprocessing.modal_response_parameters import modal_response_parameters_from_result
from postprocessing.rha_modal_response import package_modal_rha_response
from postprocessing.rha_results import (
    format_peak_floor_response_rows,
    format_peak_story_drift_rows,
    format_rha_summary_rows,
)
from postprocessing.rha_node_results import compute_node_response_peaks, format_node_response_rows
from postprocessing.rsa_results import (
    rsa_combined_response_rows,
    rsa_modal_base_response_factor_rows,
    rsa_modal_peak_response_rows,
    rsa_modal_peak_story_drift_rows,
    rsa_modal_response_factor_rows,
    rsa_spectrum_at_modal_period_rows,
)
from postprocessing.solver_diagnostics import format_solver_diagnostics_rows
from units.unit_system import result_column_label


TableRows = list[list[str]]


def format_nodal_displacement_rows(static_result: dict[str, Any]) -> tuple[list[str], TableRows]:
    """Return node displacement table headers and rows."""
    units = static_result.get("units")
    headers = [
        "Node",
        result_column_label("ux", "displacement", units),
        result_column_label("uy", "displacement", units),
        result_column_label("rz", "rotation", units),
    ]
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
    units = static_result.get("units")
    headers = [
        "Node",
        result_column_label("Rx", "force", units),
        result_column_label("Ry", "force", units),
        result_column_label("Mz", "moment", units),
    ]
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
    units = static_result.get("units")
    headers = [
        "Element",
        "Type",
        result_column_label("i-end Nx", "force", units),
        result_column_label("i-end Vy", "force", units),
        result_column_label("i-end Mz", "moment", units),
        result_column_label("j-end Nx", "force", units),
        result_column_label("j-end Vy", "force", units),
        result_column_label("j-end Mz", "moment", units),
    ]
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
    units = static_result.get("units")
    headers = [
        "Element",
        "Type",
        "Station",
        "xi [-]",
        result_column_label("x_local", "length", units),
        result_column_label("global_x", "length", units),
        result_column_label("global_y", "length", units),
        result_column_label("N", "force", units),
        result_column_label("V", "force", units),
        result_column_label("M", "moment", units),
    ]
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
    units = static_result.get("units")
    headers = [
        "Element",
        "Station",
        "xi [-]",
        result_column_label("x_local", "length", units),
        result_column_label("global_x", "length", units),
        result_column_label("global_y", "length", units),
        result_column_label("u_local", "displacement", units),
        result_column_label("v_local", "displacement", units),
        result_column_label("slope", "rotation", units),
    ]
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
    units = modal_result.get("units")
    headers = [
        "Mode",
        result_column_label("omega", "angular_frequency", units),
        result_column_label("frequency", "frequency", units),
        result_column_label("period", "period", units),
    ]
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
    """Return CE586-style generalized participation and effective-mass rows."""
    parameters = modal_response_parameters_from_result(modal_result, normalization="display")
    headers = [
        "Mode", "Mn", "Lnh", "Gamma = Lnh/Mn", "Ln_theta",
        "h_star = Ln_theta/Lnh", "M_eff / M_n*", "M_eff ratio",
        "Cumulative M_eff ratio",
    ]
    rows = []
    for row in parameters["rows"]:
        rows.append(
            [
                str(row["mode"]),
                _format_number(row["Mn"]),
                _format_number(row["Lnh"]),
                _format_number(row["Gamma"]),
                _format_number(row["Ln_theta"]),
                _format_number(row["h_star"]),
                _format_number(row["M_eff"]),
                _format_number(row["M_eff_ratio"]),
                _format_number(row["cumulative_M_eff_ratio"]),
            ]
        )
    return headers, rows


def format_modal_properties_rows(modal_result: dict[str, Any]) -> tuple[list[str], TableRows]:
    """Return basic eigenvalue/frequency properties using display normalization."""
    parameters = modal_response_parameters_from_result(modal_result, normalization="display")
    headers = [
        "Mode",
        "eigenvalue lambda = omega^2",
        "omega [rad/s]",
        "frequency [Hz]",
        "period [s]",
        "Normalization",
        "Sign convention",
        "Roof phi",
    ]
    rows = []
    sign_convention = modal_result.get("display_sign_convention", "raw")
    for row in parameters["rows"]:
        rows.append(
            [
                str(row["mode"]),
                _format_number(row["omega"] ** 2),
                _format_number(row["omega"]),
                _format_number(row["frequency_hz"]),
                _format_number(row["period_s"]),
                str(row["normalization"]),
                str(sign_convention),
                _format_number(row["phi"][-1]),
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


def format_modal_response_parameter_rows(modal_result: dict[str, Any]) -> tuple[list[str], TableRows]:
    parameters = modal_response_parameters_from_result(modal_result, normalization="display")
    headers = [
        "Mode", "omega [rad/s]", "f [Hz]", "T [s]", "Mn", "Lnh", "Gamma",
        "Ln_theta", "h_star [m]", "M_eff", "M_eff ratio",
        "Cumulative M_eff ratio", "Vb coefficient", "Mb coefficient", "Normalization",
    ]
    rows = []
    for row in parameters["rows"]:
        rows.append([
            str(row["mode"]), _format_number(row["omega"]), _format_number(row["frequency_hz"]),
            _format_number(row["period_s"]), _format_number(row["Mn"]), _format_number(row["Lnh"]),
            _format_number(row["Gamma"]), _format_number(row["Ln_theta"]), _format_number(row["h_star"]),
            _format_number(row["M_eff"]), _format_number(row["M_eff_ratio"]),
            _format_number(row["cumulative_M_eff_ratio"]), _format_number(row["base_shear_coefficient"]),
            _format_number(row["base_moment_coefficient"]), str(row["normalization"]),
        ])
    return headers, rows


def format_modal_response_factors_rows(modal_result: dict[str, Any]) -> tuple[list[str], TableRows]:
    parameters = modal_response_parameters_from_result(modal_result, normalization="display")
    headers = [
        "Mode", "Floor / DOF", "Height h [m]", "phi", "mass",
        "sn = Gamma*m*phi", "u_coeff = Gamma*phi/omega^2",
        "Vb_coeff = sum(sn)", "Mb_coeff = sum(sn*h)",
    ]
    rows = []
    for mode in parameters["rows"]:
        for idx, height in enumerate(parameters["floor_heights"]):
            rows.append([
                str(mode["mode"]), str(parameters["floor_labels"][idx]), _format_number(height),
                _format_number(mode["phi"][idx]), _format_number(parameters["masses"][idx]),
                _format_number(mode["sn"][idx]), _format_number(mode["u_coeff"][idx]),
                _format_number(mode["Vb_coeff"]), _format_number(mode["Mb_coeff"]),
            ])
    return headers, rows


def format_modal_force_coefficient_rows(modal_result: dict[str, Any]) -> tuple[list[str], TableRows]:
    """Compatibility wrapper; the GUI now exposes Modal Response Factors."""
    return format_modal_response_factors_rows(modal_result)


def _modal_rha_package(rha_result, modal_result):
    return package_modal_rha_response(
        rha_result, modal_response_parameters_from_result(modal_result, normalization="display")
    )


def format_rha_modal_acceleration_rows(rha_result, modal_result):
    package = _modal_rha_package(rha_result, modal_result)
    acceleration = package["pseudo_acceleration_histories"]
    headers = ["Time [s]"] + [f"A{idx + 1}(t)" for idx in range(acceleration.shape[0])]
    rows = [[_format_number(time)] + [_format_number(acceleration[idx, step]) for idx in range(acceleration.shape[0])]
            for step, time in enumerate(package["time"])]
    return headers, rows


def format_rha_modal_displacement_rows(rha_result, modal_result):
    package = _modal_rha_package(rha_result, modal_result)
    p = package["modal_parameters"]
    headers = ["Time [s]", "Mode", "Floor", "u_coeff", "A_n(t)", "u_n(t)"]
    rows = []
    for step, time in enumerate(package["time"]):
        for mode_idx, mode in enumerate(p["rows"][: package["pseudo_acceleration_histories"].shape[0]]):
            for floor_idx, floor in enumerate(p["floor_labels"]):
                rows.append([_format_number(time), str(mode_idx + 1), str(floor),
                             _format_number(mode["u_coeff"][floor_idx]),
                             _format_number(package["pseudo_acceleration_histories"][mode_idx, step]),
                             _format_number(package["modal_displacement_contributions"][mode_idx, floor_idx, step])])
    return headers, rows


def format_rha_modal_force_rows(rha_result, modal_result):
    package = _modal_rha_package(rha_result, modal_result)
    p = package["modal_parameters"]
    headers = ["Time [s]", "Mode", "Floor", "sn", "A_n(t)", "f_n(t)"]
    rows = []
    for step, time in enumerate(package["time"]):
        for mode_idx, mode in enumerate(p["rows"][: package["pseudo_acceleration_histories"].shape[0]]):
            for floor_idx, floor in enumerate(p["floor_labels"]):
                rows.append([_format_number(time), str(mode_idx + 1), str(floor), _format_number(mode["sn"][floor_idx]),
                             _format_number(package["pseudo_acceleration_histories"][mode_idx, step]),
                             _format_number(package["modal_force_contributions"][mode_idx, floor_idx, step])])
    return headers, rows


def format_rha_modal_base_response_rows(rha_result, modal_result):
    package = _modal_rha_package(rha_result, modal_result)
    p = package["modal_parameters"]
    headers = ["Time [s]", "Mode", "Vb_coeff", "Mb_coeff", "A_n(t)", "Vbn(t)", "Mbn(t)"]
    rows = []
    for step, time in enumerate(package["time"]):
        for mode_idx, mode in enumerate(p["rows"][: package["pseudo_acceleration_histories"].shape[0]]):
            rows.append([_format_number(time), str(mode_idx + 1), _format_number(mode["base_shear_coefficient"]),
                         _format_number(mode["base_moment_coefficient"]),
                         _format_number(package["pseudo_acceleration_histories"][mode_idx, step]),
                         _format_number(package["modal_base_shear_histories"][mode_idx, step]),
                         _format_number(package["modal_base_moment_histories"][mode_idx, step])])
    return headers, rows


def format_rha_modal_peak_response_rows(rha_result, modal_result):
    package = _modal_rha_package(rha_result, modal_result)
    p = package["modal_parameters"]
    headers = ["Mode", "Floor", "max |A_n(t)|", "max |u_n(t)|", "max |f_n(t)|", "max |Vbn(t)|", "max |Mbn(t)|"]
    rows = []
    for mode_idx in range(package["pseudo_acceleration_histories"].shape[0]):
        for floor_idx, floor in enumerate(p["floor_labels"]):
            rows.append([
                str(mode_idx + 1), str(floor),
                _format_number(abs(package["pseudo_acceleration_histories"][mode_idx]).max()),
                _format_number(abs(package["modal_displacement_contributions"][mode_idx, floor_idx]).max()),
                _format_number(abs(package["modal_force_contributions"][mode_idx, floor_idx]).max()),
                _format_number(abs(package["modal_base_shear_histories"][mode_idx]).max()),
                _format_number(abs(package["modal_base_moment_histories"][mode_idx]).max()),
            ])
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


def format_rsa_spectrum_at_modal_period_rows(rsa_result):
    unit = rsa_result.get("response_factor_results", {}).get("spectrum_unit", "m/s^2")
    headers = ["Mode", "T_n [s]", "omega [rad/s]", "f [Hz]", "Damping ratio", f"Sa(T_n) [{unit}]", "Spectrum source"]
    rows = [[str(row["mode"]), _format_number(row["period_s"]), _format_number(row["omega"]),
             _format_number(row["frequency_hz"]), _format_number(row["damping_ratio"]),
             _format_number(row["Sa"]), str(row["source"])]
            for row in rsa_spectrum_at_modal_period_rows(rsa_result)]
    return headers, rows


def format_rsa_modal_response_factor_rows(rsa_result):
    headers = ["Mode", "Floor / DOF", "Height h [m]", "phi", "u_coeff", "Sa(T_n)", "u_n", "sn", "f_n"]
    rows = [[str(row["mode"]), str(row["floor"]), _format_number(row["height"]), _format_number(row["phi"]),
             _format_number(row["u_coeff"]), _format_number(row["Sa"]), _format_number(row["u"]),
             _format_number(row["sn"]), _format_number(row["f"])]
            for row in rsa_modal_response_factor_rows(rsa_result)]
    return headers, rows


def format_rsa_modal_base_response_factor_rows(rsa_result):
    headers = ["Mode", "Sa(T_n)", "Vb_coeff", "Vbn", "Mb_coeff", "Mbn"]
    rows = [[str(row["mode"]), _format_number(row["Sa"]), _format_number(row["Vb_coeff"]),
             _format_number(row["Vbn"]), _format_number(row["Mb_coeff"]), _format_number(row["Mbn"])]
            for row in rsa_modal_base_response_factor_rows(rsa_result)]
    return headers, rows


def format_rsa_cqc_correlation_rows(rsa_result):
    matrix = np.asarray(
        rsa_result.get("response_factor_combinations", {}).get("cqc_correlation_matrix", []),
        dtype=float,
    )
    headers = ["Mode"] + [f"Mode {idx + 1}" for idx in range(matrix.shape[0])]
    rows = [[f"Mode {idx + 1}"] + [_format_number(value) for value in matrix[idx]] for idx in range(matrix.shape[0])]
    return headers, rows


def format_solver_diagnostics_table_rows(diagnostics: dict[str, Any]) -> tuple[list[str], TableRows]:
    """Return solver diagnostics table headers and rows."""
    return format_solver_diagnostics_rows(diagnostics)


def format_static_story_drift_rows(static_result: dict[str, Any]) -> tuple[list[str], TableRows]:
    """Return static story drift table headers and rows."""
    drift_result = compute_story_drift(static_result, direction="ux", method="mean")
    _backend_headers, rows = format_story_drift_rows(drift_result)
    units = static_result.get("units")
    headers = [
        "Story",
        result_column_label("Lower Elevation", "length", units),
        result_column_label("Upper Elevation", "length", units),
        result_column_label("Story Height", "length", units),
        result_column_label("Lower Floor ux", "displacement", units),
        result_column_label("Upper Floor ux", "displacement", units),
        result_column_label("Story Drift", "displacement", units),
        result_column_label("Abs Story Drift", "displacement", units),
        "Drift Ratio [-]",
        "Abs Drift Ratio [-]",
    ]
    return headers, rows


def format_static_roof_displacement_rows(static_result: dict[str, Any]) -> tuple[list[str], TableRows]:
    """Return static roof displacement table headers and rows."""
    roof_result = compute_roof_displacement(static_result, direction="ux", method="max_abs")
    _backend_headers, rows = format_roof_displacement_rows(roof_result)
    units = static_result.get("units")
    headers = [
        result_column_label("Roof Elevation", "length", units),
        "Roof Nodes",
        "Direction",
        result_column_label("Roof Displacement", "displacement", units),
        "Controlling Node",
    ]
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
