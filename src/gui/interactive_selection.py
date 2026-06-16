"""Pure geometry helpers for GUI object selection."""

from __future__ import annotations

import math
from typing import Any


Point = tuple[float, float]
Rect = tuple[float, float, float, float]


def safe_remove_artist(artist: Any | None) -> None:
    """Remove a Matplotlib artist if possible, ignoring stale artist states."""
    if artist is None:
        return
    try:
        artist.remove()
    except (ValueError, NotImplementedError, RuntimeError, AttributeError):
        pass


def normalize_rectangle(rect: Rect) -> Rect:
    """Return rectangle as (xmin, ymin, xmax, ymax)."""
    x0, y0, x1, y1 = rect
    return min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)


def point_in_rectangle(point: Point, rect: Rect) -> bool:
    """Return true if point lies inside or on the rectangle boundary."""
    xmin, ymin, xmax, ymax = normalize_rectangle(rect)
    x, y = point
    return xmin <= x <= xmax and ymin <= y <= ymax


def point_to_segment_distance(point: Point, start: Point, end: Point) -> float:
    """Return shortest distance from point to a line segment."""
    px, py = point
    x0, y0 = start
    x1, y1 = end
    dx = x1 - x0
    dy = y1 - y0
    length_sq = dx * dx + dy * dy
    if length_sq == 0.0:
        return math.hypot(px - x0, py - y0)

    t = ((px - x0) * dx + (py - y0) * dy) / length_sq
    t = max(0.0, min(1.0, t))
    closest = (x0 + t * dx, y0 + t * dy)
    return math.hypot(px - closest[0], py - closest[1])


def segment_intersects_rectangle(start: Point, end: Point, rect: Rect) -> bool:
    """Return true if a segment is inside or intersects a rectangle."""
    if point_in_rectangle(start, rect) or point_in_rectangle(end, rect):
        return True

    xmin, ymin, xmax, ymax = normalize_rectangle(rect)
    corners = ((xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax))
    edges = (
        (corners[0], corners[1]),
        (corners[1], corners[2]),
        (corners[2], corners[3]),
        (corners[3], corners[0]),
    )
    return any(_segments_intersect(start, end, edge_start, edge_end) for edge_start, edge_end in edges)


def pick_node(nodes: dict[int, dict[str, float]], point: Point, tolerance: float) -> int | None:
    """Return nearest node id within tolerance."""
    best_id = None
    best_distance = float("inf")
    for node_id, node in nodes.items():
        distance = math.hypot(point[0] - float(node["x"]), point[1] - float(node["y"]))
        if distance <= tolerance and distance < best_distance:
            best_id = int(node_id)
            best_distance = distance
    return best_id


def pick_element(
    elements: dict[int, dict[str, Any]],
    nodes: dict[int, dict[str, float]],
    point: Point,
    tolerance: float,
) -> int | None:
    """Return nearest element id within tolerance."""
    best_id = None
    best_distance = float("inf")
    for element_id, element in elements.items():
        start, end = _element_points(element, nodes)
        distance = point_to_segment_distance(point, start, end)
        if distance <= tolerance and distance < best_distance:
            best_id = int(element_id)
            best_distance = distance
    return best_id


def select_nodes_in_rectangle(nodes: dict[int, dict[str, float]], rect: Rect) -> set[int]:
    """Select nodes inside a rectangle."""
    return {
        int(node_id)
        for node_id, node in nodes.items()
        if point_in_rectangle((float(node["x"]), float(node["y"])), rect)
    }


def select_elements_in_rectangle(
    elements: dict[int, dict[str, Any]],
    nodes: dict[int, dict[str, float]],
    rect: Rect,
    crossing: bool = False,
) -> set[int]:
    """Select elements by window or crossing rectangle."""
    selected: set[int] = set()
    for element_id, element in elements.items():
        start, end = _element_points(element, nodes)
        start_inside = point_in_rectangle(start, rect)
        end_inside = point_in_rectangle(end, rect)
        if crossing:
            if start_inside or end_inside or segment_intersects_rectangle(start, end, rect):
                selected.add(int(element_id))
        elif start_inside and end_inside:
            selected.add(int(element_id))
    return selected


def _element_points(element: dict[str, Any], nodes: dict[int, dict[str, float]]) -> tuple[Point, Point]:
    node_i = nodes[int(element["node_i"])]
    node_j = nodes[int(element["node_j"])]
    return (float(node_i["x"]), float(node_i["y"])), (float(node_j["x"]), float(node_j["y"]))


def _segments_intersect(a: Point, b: Point, c: Point, d: Point) -> bool:
    o1 = _orientation(a, b, c)
    o2 = _orientation(a, b, d)
    o3 = _orientation(c, d, a)
    o4 = _orientation(c, d, b)

    if o1 != o2 and o3 != o4:
        return True
    if o1 == 0 and _on_segment(a, c, b):
        return True
    if o2 == 0 and _on_segment(a, d, b):
        return True
    if o3 == 0 and _on_segment(c, a, d):
        return True
    return o4 == 0 and _on_segment(c, b, d)


def _orientation(a: Point, b: Point, c: Point) -> int:
    value = (b[1] - a[1]) * (c[0] - b[0]) - (b[0] - a[0]) * (c[1] - b[1])
    if abs(value) < 1.0e-12:
        return 0
    return 1 if value > 0.0 else 2


def _on_segment(a: Point, b: Point, c: Point) -> bool:
    return (
        min(a[0], c[0]) <= b[0] <= max(a[0], c[0])
        and min(a[1], c[1]) <= b[1] <= max(a[1], c[1])
    )
