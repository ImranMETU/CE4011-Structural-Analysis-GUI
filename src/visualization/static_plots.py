"""Matplotlib plots for static post-processing result dictionaries."""

from __future__ import annotations

import math
from typing import Any

import matplotlib.pyplot as plt

from postprocessing.force_diagrams import element_force_diagrams
from postprocessing.element_station_results import frame_station_results
from units.unit_system import unit_label
from visualization.diagram_conventions import (
    ForceDiagramConvention,
    default_force_diagram_convention,
    get_display_sign,
)


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
    ax.set_xlabel(f"X [{unit_label('length', result.get('units'))}]")
    ax.set_ylabel(f"Y [{unit_label('length', result.get('units'))}]")
    _set_equal_axes(ax)
    return fig, ax


def plot_deformed_shape(
    result: dict[str, Any],
    scale: float | str | None = None,
    ax=None,
    show_undeformed: bool = True,
):
    """Plot deformed shape using packaged nodal displacements."""
    fig, ax = _get_fig_ax(ax)
    auto_scale = scale is None or (isinstance(scale, str) and scale.strip().lower() == "auto")
    if not auto_scale:
        numeric_scale = float(scale)
        auto_scale = numeric_scale <= 0.0
    used_scale = (
        compute_deformed_shape_auto_scale(result["nodes"], result["displacements"])
        if auto_scale
        else numeric_scale
    )

    if show_undeformed:
        for element in result["elements"].values():
            xi, yi, xj, yj = _element_end_coordinates(result, element)
            ax.plot([xi, xj], [yi, yj], color="0.75", linestyle="--", linewidth=1.0)

    for element in result["elements"].values():
        node_i = result["nodes"][element["node_i"]]
        node_j = result["nodes"][element["node_j"]]
        disp_i = result["displacements"][element["node_i"]]
        disp_j = result["displacements"][element["node_j"]]

        xi = node_i["x"] + used_scale * disp_i["ux"]
        yi = node_i["y"] + used_scale * disp_i["uy"]
        xj = node_j["x"] + used_scale * disp_j["ux"]
        yj = node_j["y"] + used_scale * disp_j["uy"]
        ax.plot([xi, xj], [yi, yj], color="tab:orange", linewidth=1.8, marker="o", markersize=4)

    if auto_scale:
        ax.set_title(f"Deformed Shape (auto scale={used_scale:.2g})")
    else:
        ax.set_title(f"Deformed Shape (scale={used_scale:g})")
    ax.set_xlabel(f"X [{unit_label('length', result.get('units'))}]")
    ax.set_ylabel(f"Y [{unit_label('length', result.get('units'))}]")
    _set_equal_axes(ax)
    return fig, ax


def compute_deformed_shape_auto_scale(
    nodes,
    displacements,
    target_ratio: float = 0.10,
    min_scale: float = 1.0,
    max_scale: float = 1.0e6,
) -> float:
    """Return a visual scale that maps peak translation to part of the model extent."""
    xs = [float(node["x"]) for node in nodes.values()]
    ys = [float(node["y"]) for node in nodes.values()]
    model_extent = max(
        max(xs) - min(xs) if xs else 0.0,
        max(ys) - min(ys) if ys else 0.0,
    )
    max_disp = max(
        (
            math.hypot(float(displacement["ux"]), float(displacement["uy"]))
            for displacement in displacements.values()
        ),
        default=0.0,
    )
    if max_disp == 0.0:
        return 1.0

    scale = float(target_ratio) * model_extent / max_disp
    return min(max(float(min_scale), scale), float(max_scale))


def plot_axial_force_diagram(
    result: dict[str, Any],
    scale: float = 1.0,
    ax=None,
    auto_scale_fraction: float = 0.12,
    convention: ForceDiagramConvention | None = None,
):
    """Plot axial-force diagram data for frame and truss elements."""
    fig, ax = _get_fig_ax(ax)
    active = convention or default_force_diagram_convention()
    info = _plot_structural_force_diagram(
        result, "N", scale, ax, color="tab:green",
        auto_scale_fraction=auto_scale_fraction, convention=active,
    )
    ax.set_title(_force_diagram_title("Axial Force Diagram", "N", "force", info, result.get("units"), active))
    _set_force_diagram_axes(result, ax)
    return fig, ax


def plot_shear_force_diagram(
    result: dict[str, Any],
    scale: float = 1.0,
    ax=None,
    auto_scale_fraction: float = 0.12,
    convention: ForceDiagramConvention | None = None,
):
    """Plot shear-force diagram data for frame elements."""
    fig, ax = _get_fig_ax(ax)
    active = convention or default_force_diagram_convention()
    info = _plot_structural_force_diagram(
        result, "V", scale, ax, color="tab:purple",
        auto_scale_fraction=auto_scale_fraction, convention=active,
    )
    ax.set_title(_force_diagram_title("Shear Force Diagram", "V", "force", info, result.get("units"), active))
    _set_force_diagram_axes(result, ax)
    return fig, ax


def plot_bending_moment_diagram(
    result: dict[str, Any],
    scale: float = 1.0,
    ax=None,
    auto_scale_fraction: float = 0.12,
    convention: ForceDiagramConvention | None = None,
):
    """Plot bending-moment diagram data for frame elements."""
    fig, ax = _get_fig_ax(ax)
    active = convention or default_force_diagram_convention()
    info = _plot_structural_force_diagram(
        result, "M", scale, ax, color="tab:blue",
        auto_scale_fraction=auto_scale_fraction, convention=active,
    )
    ax.set_title(_force_diagram_title("Bending Moment Diagram", "M", "moment", info, result.get("units"), active))
    _set_force_diagram_axes(result, ax)
    return fig, ax


def compute_force_diagram_ordinates(
    values,
    model_extent: float,
    auto_fraction: float = 0.12,
    user_scale: float = 1.0,
    value_tolerance: float = 1.0e-12,
) -> list[float]:
    """Return normalized visual ordinates for force diagram values."""
    values = list(values)
    scale = compute_force_diagram_scale(
        values,
        model_extent,
        auto_scale_fraction=auto_fraction,
        user_scale_factor=user_scale,
        value_tolerance=value_tolerance,
    )
    if scale == 0.0:
        return [0.0 for _value in values]
    return [float(value) * scale for value in values]


def compute_force_diagram_scale(
    values,
    model_extent: float,
    auto_scale_fraction: float = 0.12,
    user_scale_factor: float = 1.0,
    value_tolerance: float = 1.0e-12,
) -> float:
    """Return coordinate-per-unit scale for a normalized force diagram.

    The largest absolute diagram ordinate is mapped to
    ``auto_scale_fraction * model_extent * user_scale_factor``. Zero-valued
    diagrams return ``0.0`` so plotting avoids division by zero.
    """
    max_abs_value = max((abs(float(value)) for value in values), default=0.0)
    if max_abs_value <= value_tolerance:
        return 0.0
    safe_extent = float(model_extent)
    if abs(safe_extent) <= value_tolerance:
        safe_extent = 1.0
    target_height = float(auto_scale_fraction) * safe_extent * float(user_scale_factor)
    return target_height / max_abs_value


def build_structural_force_diagram_coordinates(
    result: dict[str, Any],
    element_id: int,
    quantity: str,
    scale: float = 1.0,
    n_stations: int = 31,
    convention: ForceDiagramConvention | None = None,
) -> dict[str, Any]:
    """Return 2D global baseline and diagram coordinates for one element.

    ``quantity`` is one of ``N`` axial force, ``V`` shear force, or ``M``
    bending moment. Frame elements use station results; truss elements support
    axial force only as a constant station diagram.
    """
    quantity = _normalize_quantity(quantity)
    element = result["elements"][element_id]
    node_i = result["nodes"][element["node_i"]]
    node_j = result["nodes"][element["node_j"]]
    xi, yi, xj, yj = float(node_i["x"]), float(node_i["y"]), float(node_j["x"]), float(node_j["y"])
    dx = xj - xi
    dy = yj - yi
    length = math.hypot(dx, dy)
    if length <= 0.0:
        raise ValueError(f"Element {element_id} has zero length.")
    tx = dx / length
    ty = dy / length
    nx = -ty
    ny = tx
    display_sign = get_display_sign(quantity, convention or default_force_diagram_convention())

    values_by_x = _station_values_for_element(result, element_id, quantity, n_stations=n_stations)
    base_x: list[float] = []
    base_y: list[float] = []
    diagram_x: list[float] = []
    diagram_y: list[float] = []
    values: list[float] = []
    for x_local, value in values_by_x:
        bx = xi + x_local * tx
        by = yi + x_local * ty
        base_x.append(bx)
        base_y.append(by)
        values.append(value)
        display_value = display_sign * value
        diagram_x.append(bx + scale * display_value * nx)
        diagram_y.append(by + scale * display_value * ny)

    return {
        "element": element_id,
        "quantity": quantity,
        "baseline_x": base_x,
        "baseline_y": base_y,
        "diagram_x": diagram_x,
        "diagram_y": diagram_y,
        "values": values,
        "tangent": (tx, ty),
        "normal": (nx, ny),
        "display_sign": display_sign,
        "max_value": max(values) if values else 0.0,
        "min_value": min(values) if values else 0.0,
        "max_abs_value": max((abs(value) for value in values), default=0.0),
    }


def _plot_structural_force_diagram(
    result: dict[str, Any],
    quantity: str,
    scale: float,
    ax,
    color: str,
    auto_scale_fraction: float,
    convention: ForceDiagramConvention,
) -> dict[str, float]:
    quantity = _normalize_quantity(quantity)
    raw_data = []
    all_values: list[float] = []
    for element_id in sorted(result["elements"]):
        try:
            coords = build_structural_force_diagram_coordinates(
                result, int(element_id), quantity, scale=1.0, convention=convention
            )
        except (KeyError, ValueError):
            continue
        if not coords["values"]:
            continue
        raw_data.append(coords)
        all_values.extend(float(value) for value in coords["values"])

    model_extent = _model_extent(result)
    user_scale_factor = 1.0 if scale is None else float(scale)
    max_abs = max((abs(value) for value in all_values), default=0.0)
    used_scale = compute_force_diagram_scale(
        all_values,
        model_extent,
        auto_scale_fraction=auto_scale_fraction,
        user_scale_factor=user_scale_factor,
    )
    for element_id, element in sorted(result["elements"].items()):
        xi, yi, xj, yj = _element_end_coordinates(result, element)
        ax.plot([xi, xj], [yi, yj], color="0.55", linewidth=1.0, zorder=5)

    if not raw_data:
        ax.text(0.5, 0.5, "No force values to plot.", transform=ax.transAxes, ha="center", va="center")
        ax.set_xlabel(f"X [{unit_label('length', result.get('units'))}]")
        ax.set_ylabel(f"Y [{unit_label('length', result.get('units'))}]")
        return {
            "coordinate_scale": used_scale,
            "max_abs_value": max_abs,
            "model_extent": model_extent,
            "auto_scale_fraction": auto_scale_fraction,
            "user_scale_factor": user_scale_factor,
        }

    if max_abs <= 0.0:
        ax.text(0.5, 0.5, "Zero diagram values.", transform=ax.transAxes, ha="center", va="center")

    for raw in raw_data:
        coords = build_structural_force_diagram_coordinates(
            result,
            int(raw["element"]),
            quantity,
            scale=used_scale,
            convention=convention,
        )
        bx = coords["baseline_x"]
        by = coords["baseline_y"]
        px = coords["diagram_x"]
        py = coords["diagram_y"]
        ax.plot(px, py, color=color, linewidth=1.7, zorder=15)
        ax.fill(px + list(reversed(bx)), py + list(reversed(by)), color=color, alpha=0.16, zorder=10)
        _label_diagram_extremes(ax, coords, color)

    ax.set_xlabel(f"X [{unit_label('length', result.get('units'))}]")
    ax.set_ylabel(f"Y [{unit_label('length', result.get('units'))}]")
    return {
        "coordinate_scale": used_scale,
        "max_abs_value": max_abs,
        "model_extent": model_extent,
        "auto_scale_fraction": auto_scale_fraction,
        "user_scale_factor": user_scale_factor,
    }


def _station_values_for_element(
    result: dict[str, Any],
    element_id: int,
    quantity: str,
    n_stations: int,
) -> list[tuple[float, float]]:
    element = result["elements"][element_id]
    element_type = str(element.get("type", "")).lower()
    if element_type == "frame":
        rows = frame_station_results(result, element_id, n_stations=n_stations)
        return [(float(row["x_local"]), float(row[quantity])) for row in rows]
    if element_type == "truss" and quantity == "N":
        force = result.get("member_end_forces", {}).get(element_id)
        if force is None:
            force = result.get("member_end_forces", {}).get(str(element_id))
        if not force:
            return []
        start = float(force.get("node_i", {}).get("nx", 0.0))
        end = -float(force.get("node_j", {}).get("nx", -start))
        value = 0.5 * (start + end)
        length = float(element.get("length", 0.0))
        return [(length * i / (n_stations - 1), value) for i in range(n_stations)]
    return []


def _model_extent(result: dict[str, Any]) -> float:
    xs = [float(node["x"]) for node in result.get("nodes", {}).values()]
    ys = [float(node["y"]) for node in result.get("nodes", {}).values()]
    if not xs or not ys:
        return 1.0
    extent = max(max(xs) - min(xs), max(ys) - min(ys))
    return extent if extent > 1.0e-12 else 1.0


def _force_diagram_title(
    label: str,
    quantity: str,
    unit_quantity: str,
    info: dict[str, float],
    units=None,
    convention: ForceDiagramConvention | None = None,
) -> str:
    max_abs = info.get("max_abs_value", 0.0)
    user_scale = info.get("user_scale_factor", 1.0)
    maximum = f"max |{quantity}| = {max_abs:.3e} {unit_label(unit_quantity, units)}"
    convention_text = (convention or default_force_diagram_convention()).convention_name
    if abs(user_scale - 1.0) <= 1.0e-12:
        return f"{label} - {maximum}, {convention_text} display"
    return f"{label} - {maximum}, {convention_text} display, {user_scale:g}x"


def _label_diagram_extremes(ax, coords: dict[str, Any], color: str) -> None:
    values = coords["values"]
    if not values:
        return
    indices = {int(max(range(len(values)), key=lambda idx: values[idx])), int(min(range(len(values)), key=lambda idx: values[idx]))}
    for idx in indices:
        value = values[idx]
        if abs(value) <= 1.0e-12:
            continue
        ax.text(
            coords["diagram_x"][idx],
            coords["diagram_y"][idx],
            f"{value:.3g}",
            color=color,
            fontsize=8,
            ha="center",
            va="bottom",
            zorder=20,
        )


def _normalize_quantity(quantity: str) -> str:
    normalized = str(quantity).strip().upper()
    aliases = {"AXIAL": "N", "SHEAR": "V", "MOMENT": "M"}
    normalized = aliases.get(normalized, normalized)
    if normalized not in {"N", "V", "M"}:
        raise ValueError("quantity must be N, V, or M.")
    return normalized


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


def _expand_limits_to_data(ax, padding_fraction: float = 0.08) -> None:
    ax.relim()
    ax.autoscale_view()
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    width = x1 - x0
    height = y1 - y0
    pad_x = padding_fraction * width if width > 0.0 else padding_fraction
    pad_y = padding_fraction * height if height > 0.0 else padding_fraction
    ax.set_xlim(x0 - pad_x, x1 + pad_x)
    ax.set_ylim(y0 - pad_y, y1 + pad_y)


def _set_force_diagram_axes(result: dict[str, Any], ax) -> None:
    xs, ys = _plotted_data_points(ax)
    if not xs or not ys:
        xs = [float(node["x"]) for node in result.get("nodes", {}).values()]
        ys = [float(node["y"]) for node in result.get("nodes", {}).values()]
    if not xs or not ys:
        ax.set_xlim(-0.5, 0.5)
        ax.set_ylim(-0.5, 0.5)
        ax.set_aspect("equal", adjustable="box")
        return

    data_x_min, data_x_max = min(xs), max(xs)
    data_y_min, data_y_max = min(ys), max(ys)
    nodes = list(result.get("nodes", {}).values())
    model_xs = [float(node["x"]) for node in nodes]
    model_ys = [float(node["y"]) for node in nodes]
    model_width = max(model_xs) - min(model_xs) if model_xs else data_x_max - data_x_min
    model_height = max(model_ys) - min(model_ys) if model_ys else data_y_max - data_y_min
    tolerance = 1.0e-12

    x_range = data_x_max - data_x_min
    if x_range <= tolerance:
        center = 0.5 * (data_x_min + data_x_max)
        padding = 0.20 * max(model_height, 1.0)
        x_min, x_max = center - padding, center + padding
    else:
        padding = 0.08 * x_range
        x_min, x_max = data_x_min - padding, data_x_max + padding

    y_range = data_y_max - data_y_min
    if y_range <= tolerance:
        center = 0.5 * (data_y_min + data_y_max)
        padding = 0.20 * max(model_width, 1.0)
        y_min, y_max = center - padding, center + padding
    else:
        padding = 0.08 * y_range
        y_min, y_max = data_y_min - padding, data_y_max + padding

    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    ax.set_aspect("equal", adjustable="box")


def _plotted_data_points(ax) -> tuple[list[float], list[float]]:
    xs: list[float] = []
    ys: list[float] = []
    for line in ax.lines:
        xs.extend(float(value) for value in line.get_xdata())
        ys.extend(float(value) for value in line.get_ydata())
    for patch in ax.patches:
        if hasattr(patch, "get_xy"):
            vertices = patch.get_xy()
            xs.extend(float(vertex[0]) for vertex in vertices)
            ys.extend(float(vertex[1]) for vertex in vertices)
    return xs, ys


def _set_equal_axes(ax, adjustable: str = "datalim") -> None:
    ax.set_aspect("equal", adjustable=adjustable)
    ax.autoscale()
    ax.margins(0.1)
