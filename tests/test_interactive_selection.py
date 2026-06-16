from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
import pytest

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
IO_ROOT = SRC_ROOT / "io"

for path in (SRC_ROOT, IO_ROOT, ROOT):
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
    assert callable(selection.safe_remove_artist)


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


def test_safe_remove_artist_handles_none_and_unattached_artist():
    from gui.interactive_selection import safe_remove_artist

    safe_remove_artist(None)
    safe_remove_artist(Rectangle((0.0, 0.0), 1.0, 1.0))


def test_safe_remove_artist_handles_already_removed_artist():
    from gui.interactive_selection import safe_remove_artist

    fig, ax = plt.subplots()
    rect = Rectangle((0.0, 0.0), 1.0, 1.0)
    ax.add_patch(rect)

    safe_remove_artist(rect)
    safe_remove_artist(rect)
    plt.close(fig)


def test_clear_selection_twice_does_not_raise_for_stale_artists():
    from gui.static_app import StaticAnalysisApp

    app = StaticAnalysisApp.__new__(StaticAnalysisApp)
    app.selected_nodes = {1}
    app.selected_elements = {1}
    app._selection_artists = [Rectangle((0.0, 0.0), 1.0, 1.0)]
    app._selection_rect_artist = Rectangle((0.0, 0.0), 1.0, 1.0)
    app.canvas = None
    app._update_selection_panel = lambda: None

    StaticAnalysisApp.clear_selection(app, redraw=False)
    StaticAnalysisApp.clear_selection(app, redraw=False)

    assert app.selected_nodes == set()
    assert app.selected_elements == set()
    assert app._selection_artists == []
    assert app._selection_rect_artist is None


def test_canvas_coordinate_formatter_handles_inside_and_outside_axes():
    from gui.static_app import format_canvas_coordinates

    assert format_canvas_coordinates(1.23456, -2.5) == "x = 1.235, y = -2.5"
    assert format_canvas_coordinates(None, 0.0) == "outside axes"
    assert format_canvas_coordinates(0.0, None) == "outside axes"
