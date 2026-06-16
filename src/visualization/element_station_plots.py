"""Plots for station-based static element postprocessing."""

from __future__ import annotations

import math
from typing import Any

import matplotlib.pyplot as plt

from postprocessing.element_station_results import (
    all_frame_station_results,
    hermite_deformed_polyline,
)


def plot_hermite_deformed_shape(
    result: dict[str, Any],
    scale: float = 1.0,
    ax=None,
    n_stations: int = 21,
    show_undeformed: bool = True,
):
    """Plot frame deformed shapes using Hermite station interpolation."""
    fig, ax = _get_fig_ax(ax)
    for element_id, element in sorted(result.get("elements", {}).items()):
        polyline = hermite_deformed_polyline(result, int(element_id), scale=scale, n_stations=n_stations)
        if show_undeformed:
            ax.plot(polyline["x"], polyline["y"], color="0.75", linestyle="--", linewidth=1.0)
        color = "tab:orange" if str(element.get("type", "")).lower() == "frame" else "tab:green"
        ax.plot(polyline["x_deformed"], polyline["y_deformed"], color=color, linewidth=1.8)
    ax.set_title(f"Hermite Deformed Shape (scale={scale:g})")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    _set_equal_axes(ax)
    return fig, ax


def plot_section_force_stations(
    result: dict[str, Any],
    quantity: str = "M",
    scale: float = 1.0,
    ax=None,
    n_stations: int = 11,
):
    """Plot station force values as offsets from each frame element chord."""
    fig, ax = _get_fig_ax(ax)
    quantity = quantity.upper()
    if quantity not in {"N", "V", "M"}:
        raise ValueError("quantity must be N, V, or M.")

    rows = all_frame_station_results(result, n_stations=n_stations)
    by_element: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        by_element.setdefault(int(row["element"]), []).append(row)

    for element_id, element in sorted(result.get("elements", {}).items()):
        node_i = result["nodes"][element["node_i"]]
        node_j = result["nodes"][element["node_j"]]
        ax.plot([node_i["x"], node_j["x"]], [node_i["y"], node_j["y"]], color="0.8", linewidth=1.0)
        if int(element_id) not in by_element:
            continue
        nx = -math.sin(float(element["angle"]))
        ny = math.cos(float(element["angle"]))
        px = []
        py = []
        for row in by_element[int(element_id)]:
            value = float(row[quantity])
            px.append(float(row["global_x"]) + scale * value * nx)
            py.append(float(row["global_y"]) + scale * value * ny)
        ax.plot(px, py, marker="o", markersize=3, linewidth=1.4, color="tab:blue")

    ax.set_title(f"Section Force Stations ({quantity}, scale={scale:g})")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    _set_equal_axes(ax)
    return fig, ax


def plot_deformed_slope_profile(result: dict[str, Any], ax=None, n_stations: int = 11):
    """Plot station slope values versus local x for all frame elements."""
    fig, ax = _get_fig_ax(ax)
    rows = all_frame_station_results(result, n_stations=n_stations)
    by_element: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        by_element.setdefault(int(row["element"]), []).append(row)
    for element_id, element_rows in sorted(by_element.items()):
        ax.plot(
            [row["x_local"] for row in element_rows],
            [row["slope"] for row in element_rows],
            marker="o",
            linewidth=1.4,
            label=f"E{element_id}",
        )
    ax.set_title("Deformed Slope Profile")
    ax.set_xlabel("Local x")
    ax.set_ylabel("dv/dx (rad)")
    ax.grid(True, color="0.9")
    if by_element:
        ax.legend(fontsize=8)
    return fig, ax


def _get_fig_ax(ax):
    if ax is not None:
        return ax.figure, ax
    fig, new_ax = plt.subplots()
    return fig, new_ax


def _set_equal_axes(ax) -> None:
    ax.set_aspect("equal", adjustable="datalim")
    ax.autoscale()
    ax.margins(0.1)
