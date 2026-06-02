"""Matplotlib plots for static post-processing result dictionaries."""

from __future__ import annotations

import math
from typing import Any

import matplotlib.pyplot as plt

from postprocessing.force_diagrams import element_force_diagrams


def plot_geometry(
    result: dict[str, Any],
    ax=None,
    show_node_ids: bool = True,
    show_element_ids: bool = True,
):
    """Plot undeformed structural geometry."""
    fig, ax = _get_fig_ax(ax)

    for element_id, element in sorted(result["elements"].items()):
        xi, yi, xj, yj = _element_end_coordinates(result, element)
        ax.plot([xi, xj], [yi, yj], color="black", linewidth=1.8, marker="o", markersize=4)

        if show_element_ids:
            ax.text((xi + xj) / 2.0, (yi + yj) / 2.0, str(element_id), color="tab:blue")

    if show_node_ids:
        for node_id, node in sorted(result["nodes"].items()):
            ax.text(node["x"], node["y"], str(node_id), color="tab:red")

    ax.set_title("Geometry")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    _set_equal_axes(ax)
    return fig, ax


def plot_deformed_shape(
    result: dict[str, Any],
    scale: float = 1.0,
    ax=None,
    show_undeformed: bool = True,
):
    """Plot deformed shape using packaged nodal displacements."""
    fig, ax = _get_fig_ax(ax)

    if show_undeformed:
        for element in result["elements"].values():
            xi, yi, xj, yj = _element_end_coordinates(result, element)
            ax.plot([xi, xj], [yi, yj], color="0.75", linestyle="--", linewidth=1.0)

    for element in result["elements"].values():
        node_i = result["nodes"][element["node_i"]]
        node_j = result["nodes"][element["node_j"]]
        disp_i = result["displacements"][element["node_i"]]
        disp_j = result["displacements"][element["node_j"]]

        xi = node_i["x"] + scale * disp_i["ux"]
        yi = node_i["y"] + scale * disp_i["uy"]
        xj = node_j["x"] + scale * disp_j["ux"]
        yj = node_j["y"] + scale * disp_j["uy"]
        ax.plot([xi, xj], [yi, yj], color="tab:orange", linewidth=1.8, marker="o", markersize=4)

    ax.set_title(f"Deformed Shape (scale={scale:g})")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    _set_equal_axes(ax)
    return fig, ax


def plot_axial_force_diagram(result: dict[str, Any], scale: float = 1.0, ax=None):
    """Plot axial-force diagram data for frame and truss elements."""
    fig, ax = _get_fig_ax(ax)
    _plot_force_diagram(result, "axial", scale, ax, color="tab:green")
    ax.set_title(f"Axial Force Diagram (scale={scale:g})")
    _set_equal_axes(ax)
    return fig, ax


def plot_shear_force_diagram(result: dict[str, Any], scale: float = 1.0, ax=None):
    """Plot shear-force diagram data for frame elements."""
    fig, ax = _get_fig_ax(ax)
    _plot_force_diagram(result, "shear", scale, ax, color="tab:purple")
    ax.set_title(f"Shear Force Diagram (scale={scale:g})")
    _set_equal_axes(ax)
    return fig, ax


def plot_bending_moment_diagram(result: dict[str, Any], scale: float = 1.0, ax=None):
    """Plot bending-moment diagram data for frame elements."""
    fig, ax = _get_fig_ax(ax)
    _plot_force_diagram(result, "moment", scale, ax, color="tab:blue")
    ax.set_title(f"Bending Moment Diagram (scale={scale:g})")
    _set_equal_axes(ax)
    return fig, ax


def _plot_force_diagram(result: dict[str, Any], diagram_key: str, scale: float, ax, color: str) -> None:
    for element_id, element in sorted(result["elements"].items()):
        xi, yi, xj, yj = _element_end_coordinates(result, element)
        ax.plot([xi, xj], [yi, yj], color="0.8", linewidth=1.0)

        diagrams = element_force_diagrams(result, element_id, n_points=20)
        if diagram_key not in diagrams:
            continue

        diagram = diagrams[diagram_key]
        px, py = _diagram_polyline(result, element, diagram, scale)
        ax.plot(px, py, color=color, linewidth=1.6)
        ax.fill(px + [xj, xi], py + [yj, yi], color=color, alpha=0.15)

    ax.set_xlabel("X")
    ax.set_ylabel("Y")


def _diagram_polyline(
    result: dict[str, Any],
    element: dict[str, Any],
    diagram: dict[str, list[float]],
    scale: float,
) -> tuple[list[float], list[float]]:
    node_i = result["nodes"][element["node_i"]]
    angle = element["angle"]
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    nx = -sin_a
    ny = cos_a

    px = []
    py = []
    for local_x, value in zip(diagram["x"], diagram["values"]):
        base_x = node_i["x"] + local_x * cos_a
        base_y = node_i["y"] + local_x * sin_a
        px.append(base_x + scale * value * nx)
        py.append(base_y + scale * value * ny)
    return px, py


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
