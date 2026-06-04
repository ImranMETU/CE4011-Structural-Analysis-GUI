"""Matplotlib plots for story drift and roof displacement results."""

from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt


def plot_story_drift_profile(drift_result: dict[str, Any], ax=None):
    """Plot story drift versus upper story elevation."""
    fig, ax = _get_fig_ax(ax)
    stories = drift_result.get("stories", [])
    x = [story["story_drift"] for story in stories]
    y = [story["upper_elevation"] for story in stories]
    ax.plot(x, y, marker="o", color="tab:blue")
    ax.set_xlabel(f"Story drift ({drift_result.get('direction', 'ux')})")
    ax.set_ylabel("Elevation")
    ax.set_title("Story Drift Profile")
    ax.grid(True, color="0.9")
    return fig, ax


def plot_drift_ratio_profile(drift_result: dict[str, Any], ax=None):
    """Plot drift ratio versus upper story elevation."""
    fig, ax = _get_fig_ax(ax)
    stories = drift_result.get("stories", [])
    x = [story["drift_ratio"] for story in stories]
    y = [story["upper_elevation"] for story in stories]
    ax.plot(x, y, marker="o", color="tab:orange")
    ax.set_xlabel("Drift ratio")
    ax.set_ylabel("Elevation")
    ax.set_title("Drift Ratio Profile")
    ax.grid(True, color="0.9")
    return fig, ax


def plot_floor_displacement_profile(floor_displacement_result: dict[str, Any], ax=None):
    """Plot representative floor displacement versus elevation."""
    fig, ax = _get_fig_ax(ax)
    floors = floor_displacement_result.get("floors", [])
    x = [floor["displacement"] for floor in floors]
    y = [floor["elevation"] for floor in floors]
    ax.plot(x, y, marker="o", color="tab:green")
    ax.set_xlabel(f"Floor displacement ({floor_displacement_result.get('direction', 'ux')})")
    ax.set_ylabel("Elevation")
    ax.set_title("Floor Displacement Profile")
    ax.grid(True, color="0.9")
    return fig, ax


def plot_roof_displacement_marker(roof_result: dict[str, Any], ax=None):
    """Plot roof displacement as a single marker at roof elevation."""
    fig, ax = _get_fig_ax(ax)
    ax.scatter([roof_result["roof_displacement"]], [roof_result["roof_elevation"]], s=80, color="tab:red")
    ax.axvline(0.0, color="0.65", linewidth=1.0)
    ax.set_xlabel(f"Roof displacement ({roof_result.get('direction', 'ux')})")
    ax.set_ylabel("Elevation")
    ax.set_title("Roof Displacement")
    ax.grid(True, color="0.9")
    return fig, ax


def _get_fig_ax(ax):
    if ax is not None:
        return ax.figure, ax
    fig, new_ax = plt.subplots()
    return fig, new_ax
