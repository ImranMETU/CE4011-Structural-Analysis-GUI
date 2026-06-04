from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"

for path in (SRC_ROOT, ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


NODES = {
    1: {"x": 0.0, "y": 0.0},
    2: {"x": 4.0, "y": 0.0},
    3: {"x": 4.0, "y": 3.0},
}

ELEMENTS = {
    1: {"node_i": 1, "node_j": 2, "type": "frame"},
    2: {"node_i": 2, "node_j": 3, "type": "truss"},
}


def test_interactive_selection_module_imports_successfully():
    import gui.interactive_selection as selection

    assert callable(selection.point_in_rectangle)
    assert callable(selection.pick_element)


def test_point_inside_rectangle_accepts_any_corner_order():
    from gui.interactive_selection import point_in_rectangle

    assert point_in_rectangle((1.0, 1.0), (2.0, 2.0, 0.0, 0.0))
    assert not point_in_rectangle((3.0, 1.0), (2.0, 2.0, 0.0, 0.0))


def test_segment_intersects_rectangle_for_crossing_line():
    from gui.interactive_selection import segment_intersects_rectangle

    assert segment_intersects_rectangle((-1.0, 1.0), (3.0, 1.0), (0.0, 0.0, 2.0, 2.0))
    assert not segment_intersects_rectangle((-1.0, 3.0), (3.0, 3.0), (0.0, 0.0, 2.0, 2.0))


def test_node_window_selection():
    from gui.interactive_selection import select_nodes_in_rectangle

    assert select_nodes_in_rectangle(NODES, (-0.5, -0.5, 1.0, 1.0)) == {1}
    assert select_nodes_in_rectangle(NODES, (-0.5, -0.5, 4.5, 0.5)) == {1, 2}


def test_element_window_selection_requires_both_end_nodes_inside():
    from gui.interactive_selection import select_elements_in_rectangle

    rect = (-0.5, -0.5, 4.5, 0.5)

    assert select_elements_in_rectangle(ELEMENTS, NODES, rect, crossing=False) == {1}


def test_element_crossing_selection_accepts_intersections():
    from gui.interactive_selection import select_elements_in_rectangle

    rect = (1.0, -0.5, 2.0, 0.5)

    assert select_elements_in_rectangle(ELEMENTS, NODES, rect, crossing=False) == set()
    assert select_elements_in_rectangle(ELEMENTS, NODES, rect, crossing=True) == {1}


def test_point_to_segment_distance():
    from gui.interactive_selection import point_to_segment_distance

    assert point_to_segment_distance((2.0, 1.0), (0.0, 0.0), (4.0, 0.0)) == pytest.approx(1.0)
    assert point_to_segment_distance((5.0, 0.0), (0.0, 0.0), (4.0, 0.0)) == pytest.approx(1.0)


def test_click_picking_chooses_nearest_node_or_element():
    from gui.interactive_selection import pick_element, pick_node

    assert pick_node(NODES, (0.1, 0.1), tolerance=0.25) == 1
    assert pick_element(ELEMENTS, NODES, (2.0, 0.1), tolerance=0.25) == 1
