"""Enhanced SAP-like model view plotting utilities."""

from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Patch, Polygon, Rectangle


DEFAULT_OPTIONS = {
    "show_axes": True,
    "show_grid": True,
    "show_legend": False,
    "show_node_labels": True,
    "show_element_labels": True,
    "show_loads": True,
    "show_supports": True,
    "show_settlements": True,
    "show_thermal": True,
    "show_thermal_loads": True,
    "show_masses": True,
}


def plot_model_view(result_or_model: dict[str, Any], ax=None, options: dict[str, Any] | None = None):
    """Plot an enhanced engineering model view.

    The input can be a raw Structure.from_dict-style model dictionary or a
    packaged result dictionary containing node coordinates and element
    connectivity. Raw model dictionaries allow richer annotations because they
    include restraints, loads, settlements, thermal member loads, and material
    references.
    """
    fig, ax = _get_fig_ax(ax)
    opts = {**DEFAULT_OPTIONS, **(options or {})}
    if options and "show_thermal" in options:
        opts["show_thermal_loads"] = bool(options["show_thermal"])
    elif options and "show_thermal_loads" in options:
        opts["show_thermal"] = bool(options["show_thermal_loads"])
    nodes, elements = _normalize_nodes_elements(result_or_model)
    if not nodes:
        ax.set_title("Model View")
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        _apply_axes_options(ax, opts)
        return fig, ax

    span = _model_span(nodes)
    offset = 0.035 * span

    _draw_elements(ax, nodes, elements, opts, offset)
    _draw_nodes(ax, nodes, opts, offset)
    if opts["show_supports"]:
        _draw_supports(ax, nodes, offset)
    if opts["show_loads"]:
        _draw_nodal_loads(ax, nodes, result_or_model.get("nodal_loads", []), span)
    if opts["show_settlements"]:
        _draw_settlements(ax, nodes, offset)
    if opts["show_thermal_loads"]:
        _draw_thermal_loads(ax, nodes, elements, offset)
    if opts["show_masses"]:
        _draw_modal_masses(ax, nodes, opts.get("mass_mapping", {}), offset)
    if opts["show_legend"]:
        _draw_legend(ax)

    ax.set_title("Model View")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    _apply_axes_options(ax, opts)
    ax.set_aspect("equal", adjustable="datalim")
    ax.autoscale()
    ax.margins(0.15)
    return fig, ax


def _draw_elements(ax, nodes: dict[int, dict[str, Any]], elements: dict[int, dict[str, Any]], opts, offset: float) -> None:
    for element_id, element in sorted(elements.items()):
        node_i = nodes.get(int(element["node_i"]))
        node_j = nodes.get(int(element["node_j"]))
        if node_i is None or node_j is None:
            continue
        element_type = str(element.get("type", "")).lower()
        is_truss = element_type == "truss"
        ax.plot(
            [node_i["x"], node_j["x"]],
            [node_i["y"], node_j["y"]],
            color="black",
            linewidth=1.2 if is_truss else 2.0,
            linestyle="--" if is_truss else "-",
            zorder=10,
        )
        if opts["show_element_labels"]:
            mx, my, nx, ny = _element_mid_normal(node_i, node_j)
            ax.text(
                mx + nx * offset,
                my + ny * offset,
                f"E{element_id}",
                color="tab:blue",
                fontsize=8,
                ha="center",
                va="center",
                zorder=20,
            )


def _draw_nodes(ax, nodes: dict[int, dict[str, Any]], opts, offset: float) -> None:
    xs = [node["x"] for node in nodes.values()]
    ys = [node["y"] for node in nodes.values()]
    ax.scatter(xs, ys, s=30, color="white", edgecolor="black", linewidth=1.1, zorder=30)
    if opts["show_node_labels"]:
        for node_id, node in sorted(nodes.items()):
            ax.text(
                node["x"] + 1.1 * offset,
                node["y"] + 0.9 * offset,
                f"N{node_id}",
                color="tab:red",
                fontsize=8,
                ha="left",
                va="bottom",
                zorder=40,
            )


def _draw_supports(ax, nodes: dict[int, dict[str, Any]], offset: float) -> None:
    for node in nodes.values():
        restraints = node.get("restraints", {})
        fixed_dofs = [dof for dof in ("ux", "uy", "rz") if restraints.get(dof)]
        if not fixed_dofs:
            continue
        kind = _support_kind(restraints)
        if kind == "fixed":
            _draw_fixed_support(ax, node["x"], node["y"], offset)
            label = "FIX"
        elif kind == "pinned":
            _draw_pinned_support(ax, node["x"], node["y"], offset)
            label = "PIN"
        else:
            _draw_roller_support(ax, node["x"], node["y"], offset)
            label = ",".join(fixed_dofs)
        ax.text(node["x"], node["y"] - 3.3 * offset, label, color="0.25", fontsize=8, ha="center", zorder=40)


def _draw_nodal_loads(ax, nodes: dict[int, dict[str, Any]], nodal_loads: list[dict[str, Any]], span: float) -> None:
    if not nodal_loads:
        return
    max_force = max(
        max(abs(float(load.get("fx", 0.0))), abs(float(load.get("fy", 0.0)))) for load in nodal_loads
    )
    arrow_unit = 0.12 * span / max_force if max_force > 0.0 else 0.0
    for load in nodal_loads:
        node = nodes.get(int(load["node"]))
        if node is None:
            continue
        fx = float(load.get("fx", 0.0))
        fy = float(load.get("fy", 0.0))
        mz = float(load.get("mz", 0.0))
        labels = []
        if fx:
            _arrow(ax, node["x"], node["y"], fx * arrow_unit, 0.0, "tab:green")
            labels.append(f"Fx={fx:.3g}")
        if fy:
            _arrow(ax, node["x"], node["y"], 0.0, fy * arrow_unit, "tab:green")
            labels.append(f"Fy={fy:.3g}")
        if mz:
            labels.append(f"Mz={mz:.3g}")
            ax.text(node["x"], node["y"], "M", color="tab:green", fontsize=9, ha="center", va="center", zorder=45)
        if labels:
            ax.text(node["x"] + 0.03 * span, node["y"] + 0.13 * span, ", ".join(labels), color="tab:green", fontsize=8, ha="left")


def _draw_settlements(ax, nodes: dict[int, dict[str, Any]], offset: float) -> None:
    for node in nodes.values():
        prescribed = node.get("prescribed_displacements", {})
        if not prescribed:
            continue
        labels = []
        ux = float(prescribed.get("ux", 0.0))
        uy = float(prescribed.get("uy", 0.0))
        rz = float(prescribed.get("rz", 0.0))
        if ux:
            _arrow(ax, node["x"], node["y"], 2.0 * offset * _sign(ux), 0.0, "tab:purple")
            labels.append(f"du_x={ux:.3g}")
        if uy:
            _arrow(ax, node["x"], node["y"], 0.0, 2.0 * offset * _sign(uy), "tab:purple")
            labels.append(f"du_y={uy:.3g}")
        if rz:
            labels.append(f"du_rz={rz:.3g}")
        if labels:
            ax.text(node["x"] - offset, node["y"] - 4.8 * offset, ", ".join(labels), color="tab:purple", fontsize=8)


def _draw_thermal_loads(ax, nodes: dict[int, dict[str, Any]], elements: dict[int, dict[str, Any]], offset: float) -> None:
    for element in elements.values():
        labels = [_thermal_label(load) for load in element.get("member_loads", []) if str(load.get("type", "")).lower() == "thermal"]
        labels = [label for label in labels if label]
        if not labels:
            continue
        node_i = nodes.get(int(element["node_i"]))
        node_j = nodes.get(int(element["node_j"]))
        if node_i is None or node_j is None:
            continue
        mx, my, nx, ny = _element_mid_normal(node_i, node_j)
        ax.text(
            mx - nx * offset,
            my - ny * offset,
            "; ".join(labels),
            color="tab:orange",
            fontsize=8,
            ha="center",
            va="center",
            zorder=35,
        )


def _draw_modal_masses(ax, nodes: dict[int, dict[str, Any]], mass_mapping: dict[int, dict[str, float]], offset: float) -> None:
    for node_id, masses in sorted((mass_mapping or {}).items()):
        node = nodes.get(int(node_id))
        if node is None:
            continue
        labels = []
        if float(masses.get("ux", 0.0)):
            labels.append(f"m_x={float(masses['ux']):.3g}")
        if float(masses.get("uy", 0.0)):
            labels.append(f"m_y={float(masses['uy']):.3g}")
        if labels:
            ax.text(node["x"] + 2.0 * offset, node["y"] - 2.0 * offset, ", ".join(labels), color="0.35", fontsize=8)


def _normalize_nodes_elements(data: dict[str, Any]) -> tuple[dict[int, dict[str, Any]], dict[int, dict[str, Any]]]:
    raw_nodes = data.get("nodes", {})
    if isinstance(raw_nodes, dict):
        nodes = {int(node_id): dict(node) for node_id, node in raw_nodes.items()}
    else:
        nodes = {int(node["id"]): dict(node) for node in raw_nodes}

    raw_elements = data.get("elements", {})
    if isinstance(raw_elements, dict):
        elements = {int(element_id): dict(element) for element_id, element in raw_elements.items()}
    else:
        elements = {int(element["id"]): dict(element) for element in raw_elements}

    return nodes, elements


def _support_kind(restraints: dict[str, Any]) -> str:
    ux = bool(restraints.get("ux"))
    uy = bool(restraints.get("uy"))
    rz = bool(restraints.get("rz"))
    if ux and uy and rz:
        return "fixed"
    if ux and uy and not rz:
        return "pinned"
    return "roller"


def _draw_fixed_support(ax, x: float, y: float, offset: float) -> None:
    width = 1.3 * offset
    height = 0.75 * offset
    rect = Rectangle((x - width / 2.0, y - 2.0 * offset), width, height, facecolor="0.25", edgecolor="0.15", zorder=24)
    ax.add_patch(rect)
    for i in range(4):
        hx = x - width / 2.0 + i * width / 3.0
        ax.plot([hx, hx - 0.45 * offset], [y - 2.0 * offset, y - 2.55 * offset], color="0.25", linewidth=0.8, zorder=24)


def _draw_pinned_support(ax, x: float, y: float, offset: float) -> None:
    points = [
        (x, y - 0.45 * offset),
        (x - 0.9 * offset, y - 2.0 * offset),
        (x + 0.9 * offset, y - 2.0 * offset),
    ]
    ax.add_patch(Polygon(points, closed=True, facecolor="white", edgecolor="0.2", linewidth=1.1, zorder=24))
    ax.plot([x - 1.05 * offset, x + 1.05 * offset], [y - 2.0 * offset, y - 2.0 * offset], color="0.2", linewidth=1.0, zorder=24)


def _draw_roller_support(ax, x: float, y: float, offset: float) -> None:
    _draw_pinned_support(ax, x, y, offset)
    ax.add_patch(Circle((x - 0.42 * offset, y - 2.35 * offset), 0.18 * offset, facecolor="white", edgecolor="0.2", linewidth=0.9, zorder=24))
    ax.add_patch(Circle((x + 0.42 * offset, y - 2.35 * offset), 0.18 * offset, facecolor="white", edgecolor="0.2", linewidth=0.9, zorder=24))
    ax.plot([x - 1.1 * offset, x + 1.1 * offset], [y - 2.6 * offset, y - 2.6 * offset], color="0.2", linewidth=1.0, zorder=24)


def _element_mid_normal(node_i: dict[str, Any], node_j: dict[str, Any]) -> tuple[float, float, float, float]:
    xi, yi = float(node_i["x"]), float(node_i["y"])
    xj, yj = float(node_j["x"]), float(node_j["y"])
    dx = xj - xi
    dy = yj - yi
    length = (dx * dx + dy * dy) ** 0.5
    if length == 0.0:
        return xi, yi, 0.0, 1.0
    return 0.5 * (xi + xj), 0.5 * (yi + yj), -dy / length, dx / length


def _draw_legend(ax) -> None:
    handles = [
        Line2D([0], [0], color="black", linewidth=2.0, linestyle="-", label="Frame element"),
        Line2D([0], [0], color="black", linewidth=1.2, linestyle="--", label="Truss element"),
        Line2D([0], [0], marker="o", color="black", markerfacecolor="white", linestyle="", label="Node / node label"),
        Line2D([0], [0], color="tab:blue", linestyle="", marker="$E$", label="Element label"),
        Line2D([0], [0], color="tab:orange", linestyle="", marker="$T$", label="Thermal load"),
        Line2D([0], [0], color="tab:purple", linewidth=1.4, label="Settlement"),
        Patch(facecolor="0.25", edgecolor="0.15", label="Support"),
    ]
    ax.legend(handles=handles, loc="best", fontsize=8, frameon=True)


def _thermal_label(load: dict[str, Any]) -> str:
    if "T_top" in load or "T_bottom" in load:
        return f"Ttop={float(load.get('T_top', 0.0)):.3g}, Tbot={float(load.get('T_bottom', 0.0)):.3g}"
    if "delta_T" in load:
        parts = []
        if "T_uniform" in load:
            parts.append(f"T={float(load['T_uniform']):.3g}")
        parts.append(f"dT={float(load['delta_T']):.3g}")
        return ", ".join(parts)
    if "T_uniform" in load:
        return f"T={float(load['T_uniform']):.3g}"
    return ""


def _arrow(ax, x: float, y: float, dx: float, dy: float, color: str) -> None:
    ax.annotate(
        "",
        xy=(x + dx, y + dy),
        xytext=(x, y),
        arrowprops={"arrowstyle": "->", "color": color, "lw": 1.4},
        zorder=38,
    )


def _model_span(nodes: dict[int, dict[str, Any]]) -> float:
    xs = [float(node["x"]) for node in nodes.values()]
    ys = [float(node["y"]) for node in nodes.values()]
    return max(max(xs) - min(xs), max(ys) - min(ys), 1.0)


def _apply_axes_options(ax, opts: dict[str, Any]) -> None:
    if opts["show_grid"]:
        ax.grid(True, color="0.9")
    else:
        ax.grid(False)
    if not opts["show_axes"]:
        ax.set_axis_off()


def _sign(value: float) -> float:
    return 1.0 if value >= 0.0 else -1.0


def _get_fig_ax(ax):
    if ax is not None:
        return ax.figure, ax
    fig, new_ax = plt.subplots()
    return fig, new_ax
