from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.axes import Axes  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"

for path in (SRC_ROOT, ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


def _small_model():
    return {
        "nodes": [
            {
                "id": 1,
                "x": 0.0,
                "y": 0.0,
                "restraints": {"ux": True, "uy": True, "rz": True},
            },
            {
                "id": 2,
                "x": 4.0,
                "y": 0.0,
                "restraints": {"ux": False, "uy": True, "rz": False},
                "prescribed_displacements": {"uy": -0.01},
            },
        ],
        "elements": [
            {
                "id": 1,
                "type": "frame",
                "node_i": 1,
                "node_j": 2,
                "material": "concrete",
                "section": "beam",
                "member_loads": [{"type": "thermal", "T_top": 0.0, "T_bottom": 50.0}],
            }
        ],
        "nodal_loads": [{"node": 2, "fx": 1000.0, "fy": -500.0, "mz": 100.0}],
    }


def _support_model():
    return {
        "nodes": [
            {"id": 1, "x": 0.0, "y": 0.0, "restraints": {"ux": True, "uy": True, "rz": True}},
            {"id": 2, "x": 2.0, "y": 0.0, "restraints": {"ux": True, "uy": True, "rz": False}},
            {"id": 3, "x": 4.0, "y": 0.0, "restraints": {"ux": False, "uy": True, "rz": False}},
        ],
        "elements": [
            {"id": 1, "type": "frame", "node_i": 1, "node_j": 2},
            {"id": 2, "type": "truss", "node_i": 2, "node_j": 3},
        ],
        "nodal_loads": [],
    }


def test_model_view_plot_function_imports():
    from visualization.model_view import plot_model_view

    assert callable(plot_model_view)


def test_model_view_returns_figure_and_axes():
    from visualization.model_view import plot_model_view

    fig, ax = plot_model_view(_small_model())

    assert isinstance(fig, Figure)
    assert isinstance(ax, Axes)
    plt.close(fig)


def test_model_view_draws_node_and_element_labels():
    from visualization.model_view import plot_model_view

    fig, ax = plot_model_view(
        _small_model(),
        options={"show_node_labels": True, "show_element_labels": True, "mass_mapping": {2: {"ux": 10000.0}}},
    )

    labels = {text.get_text() for text in ax.texts}
    assert "N1" in labels
    assert "N2" in labels
    assert "E1" in labels
    assert any("Ttop=0" in label for label in labels)
    assert any("du_y=-0.01" in label for label in labels)
    assert any("m_x=1e+04" in label for label in labels)
    plt.close(fig)


def test_model_view_can_hide_node_and_element_labels():
    from visualization.model_view import plot_model_view

    fig, ax = plot_model_view(
        _small_model(),
        options={"show_node_labels": False, "show_element_labels": False},
    )

    labels = {text.get_text() for text in ax.texts}
    assert "N1" not in labels
    assert "E1" not in labels
    plt.close(fig)


def test_model_view_figure_can_be_saved(tmp_path):
    from visualization.model_view import plot_model_view

    fig, _ax = plot_model_view(_small_model())
    output_path = tmp_path / "model_view.png"
    fig.savefig(output_path)
    plt.close(fig)

    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_model_view_presentation_options_hide_axes_and_show_legend():
    from visualization.model_view import plot_model_view

    fig, ax = plot_model_view(
        _small_model(),
        options={"show_axes": False, "show_grid": False, "show_legend": True},
    )

    assert not ax.axison
    assert ax.get_legend() is not None
    legend_labels = {text.get_text() for text in ax.get_legend().get_texts()}
    assert "Frame element" in legend_labels
    assert "Thermal load" in legend_labels
    plt.close(fig)


def test_model_view_can_hide_thermal_and_settlement_annotations():
    from visualization.model_view import plot_model_view

    fig, ax = plot_model_view(
        _small_model(),
        options={"show_thermal": False, "show_settlements": False},
    )

    labels = {text.get_text() for text in ax.texts}
    assert not any("Ttop" in label for label in labels)
    assert not any("du_y" in label for label in labels)
    plt.close(fig)


def test_model_view_draws_fixed_pinned_and_roller_supports():
    from visualization.model_view import plot_model_view

    fig, ax = plot_model_view(_support_model())

    labels = {text.get_text() for text in ax.texts}
    assert "FIX" in labels
    assert "PIN" in labels
    assert "uy" in labels
    assert len(ax.patches) >= 3
    plt.close(fig)
