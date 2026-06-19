"""CE586-style modal force-state visualization."""

from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Arc, FancyArrowPatch


def plot_modal_force_state(
    model_data: dict[str, Any],
    modal_response_parameters: dict[str, Any],
    mode_number: int,
    A_value: float = 1.0,
    time_value: float | None = None,
    ax=None,
    scale: float | None = None,
    title: str | None = None,
):
    """Plot one modal inertia-force distribution and its base resultants."""
    rows = modal_response_parameters["rows"]
    mode_index = int(mode_number) - 1
    if mode_index < 0 or mode_index >= len(rows):
        raise IndexError(f"mode_number {mode_number} is outside the available modes.")

    fig, ax = (ax.figure, ax) if ax is not None else plt.subplots()
    mode = rows[mode_index]
    heights = np.asarray(modal_response_parameters["floor_heights"], dtype=float)
    sn = np.asarray(mode["sn"], dtype=float)
    if sn.size != heights.size:
        raise ValueError("Modal force coefficients and floor heights must have the same length.")

    acceleration = float(A_value)
    floor_forces = sn * acceleration
    base_shear = float(mode["Vb_coeff"] * acceleration)
    base_moment = float(mode["Mb_coeff"] * acceleration)
    _draw_geometry(ax, model_data)

    x_min, x_max, y_min, y_max = _model_bounds(model_data, heights)
    width = max(x_max - x_min, 1.0)
    height_span = max(y_max - y_min, float(np.ptp(heights)) if heights.size > 1 else 1.0, 1.0)
    representative_x = x_max
    max_force = max(float(np.max(np.abs(floor_forces))), abs(base_shear), 1.0e-14)
    arrow_scale = float(scale) if scale is not None else 0.30 * width / max_force

    arrows = []
    for floor_index, (height, force) in enumerate(zip(heights, floor_forces), start=1):
        arrow = FancyArrowPatch(
            (representative_x, height),
            (representative_x + arrow_scale * force, height),
            arrowstyle="-|>",
            mutation_scale=13,
            linewidth=1.8,
            color="tab:red",
            zorder=30,
        )
        ax.add_patch(arrow)
        arrows.append(arrow)
        ax.text(
            representative_x + arrow_scale * force,
            height + 0.025 * height_span,
            f"f_{floor_index}(t) = {force:.4g}",
            color="tab:red",
            fontsize=8,
            ha="left" if force >= 0.0 else "right",
        )

    base_y = min(y_min, 0.0)
    base_arrow = FancyArrowPatch(
        (representative_x, base_y),
        (representative_x - arrow_scale * base_shear, base_y),
        arrowstyle="-|>",
        mutation_scale=14,
        linewidth=2.0,
        color="tab:blue",
        zorder=35,
    )
    ax.add_patch(base_arrow)
    ax.text(
        representative_x - arrow_scale * base_shear,
        base_y - 0.05 * height_span,
        f"V_bn = {base_shear:.4g}",
        color="tab:blue",
        fontsize=9,
        ha="left" if -base_shear >= 0.0 else "right",
        va="top",
    )
    arc_width = 0.18 * width
    arc_height = 0.12 * height_span
    moment_arc = Arc(
        (x_min, base_y),
        arc_width,
        arc_height,
        theta1=25 if base_moment >= 0.0 else 205,
        theta2=315 if base_moment >= 0.0 else 135,
        color="tab:purple",
        linewidth=2.0,
    )
    ax.add_patch(moment_arc)
    ax.text(x_min, base_y + 0.09 * height_span, f"M_bn = {base_moment:.4g}", color="tab:purple", fontsize=9)

    if title is None:
        if time_value is None:
            title = f"Mode {mode_number} Modal Force Coefficients, A_n = {acceleration:g}"
        else:
            title = f"Mode {mode_number} Modal Force State at t = {time_value:.4g} s"
    ax.set_title(f"{title}\nSigns follow modal force convention.")
    ax.text(
        0.02,
        0.98,
        "\n".join(
            [
                f"Mode {mode_number}",
                f"A_n(t) = {acceleration:.5g}",
                f"Vb_coeff = {mode['Vb_coeff']:.5g}",
                f"Mb_coeff = {mode['Mb_coeff']:.5g}",
                f"V_bn(t) = {mode['Vb_coeff']:.5g} A_n(t) = {base_shear:.5g}",
                f"M_bn(t) = {mode['Mb_coeff']:.5g} A_n(t) = {base_moment:.5g}",
            ]
        ),
        transform=ax.transAxes,
        va="top",
        fontsize=8,
        bbox={"facecolor": "white", "edgecolor": "0.8", "alpha": 0.9},
    )
    ax.set_xlabel("Global X / modal force direction")
    ax.set_ylabel("Height")
    ax.grid(True, color="0.92")
    ax.autoscale()
    ax.margins(0.18)
    ax._modal_force_state_data = {  # test/debug metadata; not used by calculations
        "mode_number": mode_number,
        "A_value": acceleration,
        "floor_forces": floor_forces,
        "base_shear": base_shear,
        "base_moment": base_moment,
        "sn": sn,
        "heights": heights,
        "floor_arrows": arrows,
        "base_arrow": base_arrow,
    }
    return fig, ax


def _draw_geometry(ax, model_data):
    nodes = _node_mapping(model_data)
    elements = model_data.get("elements", {})
    iterable = elements.values() if isinstance(elements, dict) else elements
    for element in iterable:
        node_i = nodes[int(element["node_i"])]
        node_j = nodes[int(element["node_j"])]
        ax.plot(
            [float(node_i["x"]), float(node_j["x"])],
            [float(node_i["y"]), float(node_j["y"])],
            color="0.55",
            linewidth=1.3,
            zorder=5,
        )


def _node_mapping(model_data):
    nodes = model_data.get("nodes", {})
    if isinstance(nodes, dict):
        return {int(node_id): node for node_id, node in nodes.items()}
    return {int(node["id"]): node for node in nodes}


def _model_bounds(model_data, heights):
    nodes = list(_node_mapping(model_data).values())
    if not nodes:
        return 0.0, 1.0, 0.0, max(float(np.max(heights)), 1.0)
    xs = [float(node["x"]) for node in nodes]
    ys = [float(node["y"]) for node in nodes]
    return min(xs), max(xs), min(ys), max(ys)
