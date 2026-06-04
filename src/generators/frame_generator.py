"""Parametric multi-story 2D frame model generator."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def generate_frame_model(
    *,
    n_stories: int,
    n_bays: int,
    story_height: float,
    bay_width: float,
    braced: bool = False,
    brace_pattern: str = "single_diagonal",
    E_frame: float = 30.0e9,
    E_brace: float = 200.0e9,
    column_A: float = 0.25,
    column_I: float = 0.00521,
    beam_A: float = 0.32,
    beam_I: float = 0.01707,
    brace_A: float = 0.001,
    lateral_load_per_floor: float = 10000.0,
    fixed_base: bool = True,
) -> dict[str, Any]:
    """Generate a Structure.from_dict-compatible multi-story frame model."""
    _validate_positive_int(n_stories, "n_stories")
    _validate_positive_int(n_bays, "n_bays")
    _validate_positive(story_height, "story_height")
    _validate_positive(bay_width, "bay_width")
    if brace_pattern != "single_diagonal":
        raise ValueError("Only brace_pattern='single_diagonal' is supported in this first generator.")

    data: dict[str, Any] = {
        "nodes": [],
        "materials": [
            {"id": "frame_material", "E": float(E_frame), "alpha": 0.0},
            {"id": "brace_material", "E": float(E_brace), "alpha": 0.0},
        ],
        "sections": [
            {"id": "column_section", "A": float(column_A), "I": float(column_I)},
            {"id": "beam_section", "A": float(beam_A), "I": float(beam_I)},
            {"id": "brace_section", "A": float(brace_A), "I": 0.0},
        ],
        "elements": [],
        "nodal_loads": [],
    }

    for level in range(n_stories + 1):
        for bay_line in range(n_bays + 1):
            is_base = level == 0
            data["nodes"].append(
                {
                    "id": _node_id(level, bay_line, n_bays),
                    "x": float(bay_line * bay_width),
                    "y": float(level * story_height),
                    "restraints": {
                        "ux": bool(fixed_base and is_base),
                        "uy": bool(fixed_base and is_base),
                        "rz": bool(fixed_base and is_base),
                    },
                }
            )

    element_id = 1
    for story in range(n_stories):
        lower = story
        upper = story + 1
        for bay_line in range(n_bays + 1):
            data["elements"].append(
                _element(
                    element_id,
                    "frame",
                    _node_id(lower, bay_line, n_bays),
                    _node_id(upper, bay_line, n_bays),
                    "frame_material",
                    "column_section",
                )
            )
            element_id += 1

    for level in range(1, n_stories + 1):
        for bay in range(n_bays):
            data["elements"].append(
                _element(
                    element_id,
                    "frame",
                    _node_id(level, bay, n_bays),
                    _node_id(level, bay + 1, n_bays),
                    "frame_material",
                    "beam_section",
                )
            )
            element_id += 1

    if braced:
        for story in range(n_stories):
            lower = story
            upper = story + 1
            for bay in range(n_bays):
                if (story + bay) % 2 == 0:
                    node_i = _node_id(lower, bay, n_bays)
                    node_j = _node_id(upper, bay + 1, n_bays)
                else:
                    node_i = _node_id(lower, bay + 1, n_bays)
                    node_j = _node_id(upper, bay, n_bays)
                data["elements"].append(
                    _element(element_id, "truss", node_i, node_j, "brace_material", "brace_section")
                )
                element_id += 1

    load_per_node = float(lateral_load_per_floor) / float(n_bays + 1)
    for level in range(1, n_stories + 1):
        for bay_line in range(n_bays + 1):
            data["nodal_loads"].append(
                {
                    "node": _node_id(level, bay_line, n_bays),
                    "fx": load_per_node,
                    "fy": 0.0,
                    "mz": 0.0,
                }
            )

    return data


def generate_floor_mass_mapping(
    data: dict[str, Any],
    floor_mass: float,
    direction: str = "ux",
) -> dict[int, dict[str, float]]:
    """Assign floor mass equally to nodes at each non-base floor level."""
    if direction not in {"ux", "uy", "rz"}:
        raise ValueError("direction must be one of 'ux', 'uy', or 'rz'.")
    _validate_positive(floor_mass, "floor_mass")

    floors: dict[float, list[int]] = defaultdict(list)
    for node in data.get("nodes", []):
        floors[float(node["y"])].append(int(node["id"]))
    if not floors:
        return {}

    base_y = min(floors)
    mapping: dict[int, dict[str, float]] = {}
    for y, node_ids in floors.items():
        if y == base_y:
            continue
        mass_per_node = float(floor_mass) / float(len(node_ids))
        for node_id in node_ids:
            masses = {"ux": 0.0, "uy": 0.0, "rz": 0.0}
            masses[direction] = mass_per_node
            mapping[node_id] = masses
    return mapping


def _node_id(level: int, bay_line: int, n_bays: int) -> int:
    return level * (n_bays + 1) + bay_line + 1


def _element(
    element_id: int,
    element_type: str,
    node_i: int,
    node_j: int,
    material: str,
    section: str,
) -> dict[str, Any]:
    return {
        "id": int(element_id),
        "type": element_type,
        "node_i": int(node_i),
        "node_j": int(node_j),
        "material": material,
        "section": section,
    }


def _validate_positive_int(value: int, label: str) -> None:
    if int(value) != value or int(value) <= 0:
        raise ValueError(f"{label} must be a positive integer.")


def _validate_positive(value: float, label: str) -> None:
    if float(value) <= 0.0:
        raise ValueError(f"{label} must be positive.")
