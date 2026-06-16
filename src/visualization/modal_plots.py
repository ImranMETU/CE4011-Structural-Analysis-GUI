"""Matplotlib plots for packaged modal-analysis results."""

from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt

from postprocessing.modal_results import (
    apply_mode_shape_sign_convention,
    mode_shape_component_labels,
)


def plot_mode_shape(
    result: dict[str, Any],
    mode_index: int = 0,
    scale: float = 1.0,
    ax=None,
    show_undeformed: bool = True,
    show_values: bool = False,
    sign_convention: str = "raw",
):
    """Plot one normalized mode shape."""
    fig, ax = _get_fig_ax(ax)
    display_result = apply_mode_shape_sign_convention(result, sign_convention)
    _validate_mode_index(display_result, mode_index)

    if show_undeformed:
        for element in display_result["elements"].values():
            xi, yi, xj, yj = _element_end_coordinates(display_result, element)
            ax.plot([xi, xj], [yi, yj], color="0.75", linestyle="--", linewidth=1.0)

    mode = display_result["normalized_node_mode_shapes"][mode_index]
    deformed_nodes = {}
    for element in display_result["elements"].values():
        node_i = display_result["nodes"][element["node_i"]]
        node_j = display_result["nodes"][element["node_j"]]
        disp_i = mode[element["node_i"]]
        disp_j = mode[element["node_j"]]

        xi = node_i["x"] + scale * disp_i["ux"]
        yi = node_i["y"] + scale * disp_i["uy"]
        xj = node_j["x"] + scale * disp_j["ux"]
        yj = node_j["y"] + scale * disp_j["uy"]
        deformed_nodes[int(element["node_i"])] = (xi, yi)
        deformed_nodes[int(element["node_j"])] = (xj, yj)
        ax.plot([xi, xj], [yi, yj], color="tab:orange", linewidth=1.8, marker="o", markersize=4)

    if show_values:
        _add_mode_shape_value_labels(ax, display_result, mode_index, deformed_nodes)

    mode_no = mode_index + 1
    frequency = display_result["frequencies_hz"][mode_index]
    convention_text = ""
    if str(sign_convention).strip().lower() not in {"", "raw"}:
        convention_text = f", sign={sign_convention}"
    ax.set_title(f"Mode {mode_no} Shape ({frequency:.4g} Hz, scale={scale:g}{convention_text})")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    _set_equal_axes(ax)
    return fig, ax


def plot_modal_periods(result: dict[str, Any], ax=None):
    """Plot modal periods by mode number."""
    fig, ax = _get_fig_ax(ax)
    rows = result["period_table"]
    modes = [row["mode"] for row in rows]
    periods = [row["period"] for row in rows]

    ax.bar(modes, periods, color="tab:blue")
    ax.set_title("Modal Periods")
    ax.set_xlabel("Mode")
    ax.set_ylabel("Period")
    ax.set_xticks(modes)
    return fig, ax


def plot_modal_frequencies(result: dict[str, Any], ax=None):
    """Plot modal frequencies by mode number."""
    fig, ax = _get_fig_ax(ax)
    rows = result["frequency_table"]
    modes = [row["mode"] for row in rows]
    frequencies = [row["frequency_hz"] for row in rows]

    ax.bar(modes, frequencies, color="tab:green")
    ax.set_title("Modal Frequencies")
    ax.set_xlabel("Mode")
    ax.set_ylabel("Frequency (Hz)")
    ax.set_xticks(modes)
    return fig, ax


def plot_modal_angular_frequencies(result: dict[str, Any], ax=None):
    """Plot modal circular/angular frequencies by mode number."""
    fig, ax = _get_fig_ax(ax)
    rows = result["frequency_table"]
    modes = [row["mode"] for row in rows]
    omega = [row["omega"] for row in rows]

    ax.bar(modes, omega, color="tab:purple")
    ax.set_title("Modal Angular Frequencies")
    ax.set_xlabel("Mode")
    ax.set_ylabel("Angular frequency (rad/s)")
    ax.set_xticks(modes)
    return fig, ax


def _validate_mode_index(result: dict[str, Any], mode_index: int) -> None:
    n_modes = len(result["normalized_node_mode_shapes"])
    if mode_index < 0 or mode_index >= n_modes:
        raise IndexError(f"mode_index {mode_index} out of range for {n_modes} mode(s).")
    if not result.get("nodes") or not result.get("elements"):
        raise ValueError("Mode-shape plotting requires packaged node coordinates and element connectivity.")


def _element_end_coordinates(result: dict[str, Any], element: dict[str, Any]) -> tuple[float, float, float, float]:
    node_i = result["nodes"][element["node_i"]]
    node_j = result["nodes"][element["node_j"]]
    return node_i["x"], node_i["y"], node_j["x"], node_j["y"]


def _get_fig_ax(ax):
    if ax is not None:
        return ax.figure, ax
    fig, new_ax = plt.subplots()
    return fig, new_ax


def _set_equal_axes(ax) -> None:
    ax.set_aspect("equal", adjustable="datalim")
    ax.autoscale()
    ax.margins(0.1)


def _add_mode_shape_value_labels(
    ax,
    result: dict[str, Any],
    mode_index: int,
    deformed_nodes: dict[int, tuple[float, float]],
) -> None:
    labels = mode_shape_component_labels(result, mode_index=mode_index, normalized=True, convention="raw")
    dx, dy = _label_offset(result)
    for node_id in sorted(labels):
        x, y = deformed_nodes.get(int(node_id), _node_xy(result, int(node_id)))
        ax.text(
            x + dx,
            y + dy,
            labels[node_id],
            fontsize=8,
            color="tab:brown",
            bbox={"boxstyle": "round,pad=0.2", "facecolor": "white", "edgecolor": "0.8", "alpha": 0.85},
            zorder=80,
        )


def _label_offset(result: dict[str, Any]) -> tuple[float, float]:
    nodes = result.get("nodes", {})
    if not nodes:
        return 0.05, 0.05
    xs = [float(node["x"]) for node in nodes.values()]
    ys = [float(node["y"]) for node in nodes.values()]
    span = max(max(xs) - min(xs), max(ys) - min(ys), 1.0)
    return 0.02 * span, 0.02 * span


def _node_xy(result: dict[str, Any], node_id: int) -> tuple[float, float]:
    node = result["nodes"][node_id]
    return float(node["x"]), float(node["y"])
