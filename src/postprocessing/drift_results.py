"""Story drift and roof displacement post-processing helpers."""

from __future__ import annotations

from typing import Any


DOF_KEYS = {"ux", "uy", "rz"}


def get_floor_levels(node_coordinates: dict[int, dict[str, float]], base_y: float | None = None, tol: float = 1e-8) -> list[float]:
    """Return sorted floor elevations, including base level."""
    grouped = group_nodes_by_floor(node_coordinates, tol=tol)
    levels = sorted(grouped)
    if base_y is not None and not any(abs(level - base_y) <= tol for level in levels):
        levels.insert(0, float(base_y))
    return levels


def group_nodes_by_floor(node_coordinates: dict[int, dict[str, float]], tol: float = 1e-8) -> dict[float, list[int]]:
    """Group node ids by approximately equal y-coordinate."""
    groups: list[tuple[float, list[int]]] = []
    for node_id, node in sorted(_normalize_nodes(node_coordinates).items()):
        y = float(node["y"])
        for idx, (level, node_ids) in enumerate(groups):
            if abs(y - level) <= tol:
                node_ids.append(int(node_id))
                # Keep a stable representative level close to the mean.
                groups[idx] = ((level * (len(node_ids) - 1) + y) / len(node_ids), node_ids)
                break
        else:
            groups.append((y, [int(node_id)]))

    return {level: sorted(node_ids) for level, node_ids in sorted(groups, key=lambda item: item[0])}


def get_roof_level(node_coordinates: dict[int, dict[str, float]]) -> float:
    """Return maximum floor elevation."""
    levels = get_floor_levels(node_coordinates)
    if not levels:
        raise ValueError("Cannot determine roof level without nodes.")
    return levels[-1]


def get_roof_nodes(node_coordinates: dict[int, dict[str, float]], tol: float = 1e-8) -> list[int]:
    """Return node ids located at the roof level."""
    nodes = _normalize_nodes(node_coordinates)
    roof = get_roof_level(nodes)
    return sorted(int(node_id) for node_id, node in nodes.items() if abs(float(node["y"]) - roof) <= tol)


def compute_floor_displacements(
    static_result: dict[str, Any],
    direction: str = "ux",
    method: str = "mean",
) -> dict[str, Any]:
    """Compute representative static displacement per floor."""
    return _compute_floor_displacements(
        static_result.get("nodes", {}),
        static_result.get("displacements", {}),
        direction=direction,
        method=method,
    )


def compute_story_drift(
    static_result: dict[str, Any],
    direction: str = "ux",
    method: str = "mean",
) -> dict[str, Any]:
    """Compute static interstory drift and drift ratio."""
    floors = compute_floor_displacements(static_result, direction=direction, method=method)
    return _story_drift_from_floors(floors)


def compute_roof_displacement(
    static_result: dict[str, Any],
    direction: str = "ux",
    method: str = "max_abs",
) -> dict[str, Any]:
    """Compute representative static roof displacement."""
    return _compute_roof_displacement(
        static_result.get("nodes", {}),
        static_result.get("displacements", {}),
        direction=direction,
        method=method,
    )


def compute_modal_floor_displacements(
    modal_result: dict[str, Any],
    mode_index: int = 0,
    direction: str = "ux",
    method: str = "mean",
) -> dict[str, Any]:
    """Compute floor displacements from recovered modal node mode shapes."""
    mode_shapes = modal_result.get("node_mode_shapes", [])
    if mode_index < 0 or mode_index >= len(mode_shapes):
        raise IndexError(f"mode_index {mode_index} out of range for {len(mode_shapes)} mode(s).")
    return _compute_floor_displacements(
        modal_result.get("nodes", {}),
        mode_shapes[mode_index],
        direction=direction,
        method=method,
        result_type="modal",
        mode_index=mode_index,
    )


def compute_modal_story_drift(
    modal_result: dict[str, Any],
    mode_index: int = 0,
    direction: str = "ux",
    method: str = "mean",
) -> dict[str, Any]:
    """Compute interstory drift from recovered modal node mode shapes."""
    floors = compute_modal_floor_displacements(modal_result, mode_index=mode_index, direction=direction, method=method)
    return _story_drift_from_floors(floors)


def compute_modal_roof_displacement(
    modal_result: dict[str, Any],
    mode_index: int = 0,
    direction: str = "ux",
    method: str = "max_abs",
) -> dict[str, Any]:
    """Compute representative modal roof displacement."""
    mode_shapes = modal_result.get("node_mode_shapes", [])
    if mode_index < 0 or mode_index >= len(mode_shapes):
        raise IndexError(f"mode_index {mode_index} out of range for {len(mode_shapes)} mode(s).")
    return _compute_roof_displacement(
        modal_result.get("nodes", {}),
        mode_shapes[mode_index],
        direction=direction,
        method=method,
        result_type="modal",
        mode_index=mode_index,
    )


def format_story_drift_rows(drift_result: dict[str, Any]) -> tuple[list[str], list[list[str]]]:
    """Format drift rows for GUI tables and CSV export."""
    headers = [
        "Story",
        "Lower Elevation",
        "Upper Elevation",
        "Story Height",
        "Lower Disp",
        "Upper Disp",
        "Story Drift",
        "Abs Drift",
        "Drift Ratio",
        "Abs Drift Ratio",
    ]
    rows = []
    for story in drift_result.get("stories", []):
        rows.append(
            [
                str(story["story"]),
                _fmt(story["lower_elevation"]),
                _fmt(story["upper_elevation"]),
                _fmt(story["story_height"]),
                _fmt(story["lower_floor_displacement"]),
                _fmt(story["upper_floor_displacement"]),
                _fmt(story["story_drift"]),
                _fmt(story["abs_story_drift"]),
                _fmt(story["drift_ratio"]),
                _fmt(story["abs_drift_ratio"]),
            ]
        )
    return headers, rows


def format_roof_displacement_rows(roof_result: dict[str, Any]) -> tuple[list[str], list[list[str]]]:
    """Format roof displacement rows for GUI tables and CSV export."""
    headers = ["Roof Elevation", "Roof Nodes", "Roof Displacement", "Controlling Node"]
    return headers, [
        [
            _fmt(roof_result["roof_elevation"]),
            ",".join(str(node_id) for node_id in roof_result["roof_node_ids"]),
            _fmt(roof_result["roof_displacement"]),
            "" if roof_result.get("controlling_node_id") is None else str(roof_result["controlling_node_id"]),
        ]
    ]


def _compute_floor_displacements(
    node_coordinates: dict[int, dict[str, float]],
    node_displacements: dict[int, dict[str, float]],
    direction: str,
    method: str,
    result_type: str = "static",
    mode_index: int | None = None,
) -> dict[str, Any]:
    _validate_direction(direction)
    grouped = group_nodes_by_floor(node_coordinates)
    floors = []
    for floor_index, (elevation, node_ids) in enumerate(grouped.items()):
        values = [
            (node_id, float(node_displacements.get(node_id, {}).get(direction, 0.0)))
            for node_id in node_ids
        ]
        representative, controlling = _representative_value(values, method)
        floors.append(
            {
                "floor_index": floor_index,
                "elevation": elevation,
                "node_ids": node_ids,
                "displacement": representative,
                "controlling_node_id": controlling,
            }
        )
    return {
        "type": result_type,
        "mode_index": mode_index,
        "direction": direction,
        "method": method,
        "floors": floors,
    }


def _story_drift_from_floors(floor_result: dict[str, Any]) -> dict[str, Any]:
    floors = floor_result.get("floors", [])
    stories = []
    for idx in range(1, len(floors)):
        lower = floors[idx - 1]
        upper = floors[idx]
        story_height = float(upper["elevation"]) - float(lower["elevation"])
        if story_height <= 0.0:
            raise ValueError("Floor elevations must be strictly increasing for drift calculation.")
        story_drift = float(upper["displacement"]) - float(lower["displacement"])
        stories.append(
            {
                "story": idx,
                "lower_elevation": lower["elevation"],
                "upper_elevation": upper["elevation"],
                "story_height": story_height,
                "lower_floor_displacement": lower["displacement"],
                "upper_floor_displacement": upper["displacement"],
                "story_drift": story_drift,
                "abs_story_drift": abs(story_drift),
                "drift_ratio": story_drift / story_height,
                "abs_drift_ratio": abs(story_drift / story_height),
            }
        )
    return {
        "type": floor_result.get("type", "static"),
        "mode_index": floor_result.get("mode_index"),
        "direction": floor_result["direction"],
        "method": floor_result["method"],
        "stories": stories,
        "floors": floors,
    }


def _compute_roof_displacement(
    node_coordinates: dict[int, dict[str, float]],
    node_displacements: dict[int, dict[str, float]],
    direction: str,
    method: str,
    result_type: str = "static",
    mode_index: int | None = None,
) -> dict[str, Any]:
    _validate_direction(direction)
    roof_node_ids = get_roof_nodes(node_coordinates)
    values = [
        (node_id, float(node_displacements.get(node_id, {}).get(direction, 0.0)))
        for node_id in roof_node_ids
    ]
    representative, controlling = _representative_value(values, method)
    return {
        "type": result_type,
        "mode_index": mode_index,
        "direction": direction,
        "method": method,
        "roof_elevation": get_roof_level(node_coordinates),
        "roof_node_ids": roof_node_ids,
        "roof_displacement": representative,
        "controlling_node_id": controlling,
    }


def _representative_value(values: list[tuple[int, float]], method: str) -> tuple[float, int | None]:
    if not values:
        return 0.0, None
    if method == "mean":
        return sum(value for _node_id, value in values) / len(values), None
    if method == "max_abs":
        node_id, value = max(values, key=lambda item: abs(item[1]))
        return value, node_id
    raise ValueError("method must be 'mean' or 'max_abs'.")


def _normalize_nodes(nodes: dict[int, dict[str, float]] | list[dict[str, Any]]) -> dict[int, dict[str, float]]:
    if isinstance(nodes, dict):
        return {int(node_id): {"x": float(node["x"]), "y": float(node["y"])} for node_id, node in nodes.items()}
    return {int(node["id"]): {"x": float(node["x"]), "y": float(node["y"])} for node in nodes}


def _validate_direction(direction: str) -> None:
    if direction not in DOF_KEYS:
        raise ValueError("direction must be one of 'ux', 'uy', or 'rz'.")


def _fmt(value: float) -> str:
    return f"{float(value):.6e}"
