"""Matplotlib plots for packaged modal-analysis results."""

from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt


def plot_mode_shape(
    result: dict[str, Any],
    mode_index: int = 0,
    scale: float = 1.0,
    ax=None,
    show_undeformed: bool = True,
):
    """Plot one normalized mode shape."""
    fig, ax = _get_fig_ax(ax)
    _validate_mode_index(result, mode_index)

    if show_undeformed:
        for element in result["elements"].values():
            xi, yi, xj, yj = _element_end_coordinates(result, element)
            ax.plot([xi, xj], [yi, yj], color="0.75", linestyle="--", linewidth=1.0)

    mode = result["normalized_node_mode_shapes"][mode_index]
    for element in result["elements"].values():
        node_i = result["nodes"][element["node_i"]]
        node_j = result["nodes"][element["node_j"]]
        disp_i = mode[element["node_i"]]
        disp_j = mode[element["node_j"]]

        xi = node_i["x"] + scale * disp_i["ux"]
        yi = node_i["y"] + scale * disp_i["uy"]
        xj = node_j["x"] + scale * disp_j["ux"]
        yj = node_j["y"] + scale * disp_j["uy"]
        ax.plot([xi, xj], [yi, yj], color="tab:orange", linewidth=1.8, marker="o", markersize=4)

    mode_no = mode_index + 1
    frequency = result["frequencies_hz"][mode_index]
    ax.set_title(f"Mode {mode_no} Shape ({frequency:.4g} Hz, scale={scale:g})")
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
