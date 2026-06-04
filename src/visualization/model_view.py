"""Enhanced SAP-like model view plotting utilities."""

from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt


DEFAULT_OPTIONS = {
    "show_node_labels": True,
    "show_element_labels": True,
    "show_loads": True,
    "show_supports": True,
    "show_settlements": True,
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
    nodes, elements = _normalize_nodes_elements(result_or_model)
    if not nodes:
        ax.set_title("Model View")
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.grid(True, color="0.9")
        return fig, ax

    span = _model_span(nodes)
    offset = 0.025 * span

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

    ax.set_title("Model View")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.grid(True, color="0.9")
    ax.set_aspect("equal", adjustable="datalim")
    ax.autoscale()
    ax.margins(0.15)
    return fig, ax


def _draw_elements(ax, nodes: dict[int, dict[str, Any]], elements: dict[int, dict[str, Any]], opts, offset: float) -> None:
    for element_id, element in sorted(elements.items()):
        node_i = nodes[int(element["node_i"])]
        node_j = nodes[int(element["node_j"])]
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
            mx = 0.5 * (node_i["x"] + node_j["x"])
            my = 0.5 * (node_i["y"] + node_j["y"])
            ax.text(mx, my + offset, f"E{element_id}", color="tab:blue", fontsize=8, ha="center", zorder=20)


def _draw_nodes(ax, nodes: dict[int, dict[str, Any]], opts, offset: float) -> None:
    xs = [node["x"] for node in nodes.values()]
    ys = [node["y"] for node in nodes.values()]
    ax.scatter(xs, ys, s=30, color="white", edgecolor="black", linewidth=1.1, zorder=30)
    if opts["show_node_labels"]:
        for node_id, node in sorted(nodes.items()):
            ax.text(node["x"] + offset, node["y"] + offset, f"N{node_id}", color="tab:red", fontsize=8, zorder=40)


def _draw_supports(ax, nodes: dict[int, dict[str, Any]], offset: float) -> None:
    for node in nodes.values():
        restraints = node.get("restraints", {})
        fixed_dofs = [dof for dof in ("ux", "uy", "rz") if restraints.get(dof)]
        if not fixed_dofs:
            continue
        if len(fixed_dofs) == 3:
            ax.scatter([node["x"]], [node["y"] - 1.5 * offset], marker="s", s=42, color="0.2", zorder=25)
            label = "FIX"
        else:
            label = ",".join(fixed_dofs)
        ax.text(node["x"], node["y"] - 3.0 * offset, label, color="0.25", fontsize=8, ha="center", zorder=40)


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
            ax.text(node["x"], node["y"] + 0.16 * span, ", ".join(labels), color="tab:green", fontsize=8, ha="center")


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
            ax.text(node["x"] - offset, node["y"] - 4.5 * offset, ", ".join(labels), color="tab:purple", fontsize=8)


def _draw_thermal_loads(ax, nodes: dict[int, dict[str, Any]], elements: dict[int, dict[str, Any]], offset: float) -> None:
    for element in elements.values():
        labels = [_thermal_label(load) for load in element.get("member_loads", []) if str(load.get("type", "")).lower() == "thermal"]
        labels = [label for label in labels if label]
        if not labels:
            continue
        node_i = nodes[int(element["node_i"])]
        node_j = nodes[int(element["node_j"])]
        mx = 0.5 * (node_i["x"] + node_j["x"])
        my = 0.5 * (node_i["y"] + node_j["y"])
        ax.text(mx, my - offset, "; ".join(labels), color="tab:orange", fontsize=8, ha="center", zorder=35)


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


def _sign(value: float) -> float:
    return 1.0 if value >= 0.0 else -1.0


def _get_fig_ax(ax):
    if ax is not None:
        return ax.figure, ax
    fig, new_ax = plt.subplots()
    return fig, new_ax
