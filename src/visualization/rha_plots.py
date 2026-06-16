"""Matplotlib plots for modal response-history analysis results."""

from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt
import numpy as np


def plot_ground_motion_history(rha_result: dict[str, Any], ax=None):
    fig, ax = _get_fig_ax(ax)
    ax.plot(rha_result["time"], rha_result["ground_acceleration"], color="tab:gray", linewidth=1.0)
    ax.set_title("Ground Motion Acceleration")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Acceleration (m/s^2)")
    ax.grid(True, color="0.9")
    return fig, ax


def plot_roof_displacement_history(rha_result: dict[str, Any], ax=None):
    fig, ax = _get_fig_ax(ax)
    roof = rha_result.get("peak_roof_displacement", {})
    ax.plot(rha_result["time"], roof.get("history", np.zeros_like(rha_result["time"])), color="tab:blue")
    ax.set_title("Roof Displacement History")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Roof ux")
    ax.grid(True, color="0.9")
    return fig, ax


def plot_floor_displacement_histories(rha_result: dict[str, Any], ax=None):
    fig, ax = _get_fig_ax(ax)
    for floor in rha_result.get("floor_displacement_histories", []):
        ax.plot(rha_result["time"], floor["history"], label=f"Floor {floor['floor']} y={floor['elevation']:.3g}")
    ax.set_title("Floor Displacement Histories")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Floor ux")
    ax.grid(True, color="0.9")
    if rha_result.get("floor_displacement_histories"):
        ax.legend(fontsize=8)
    return fig, ax


def plot_story_drift_histories(rha_result: dict[str, Any], ax=None):
    fig, ax = _get_fig_ax(ax)
    for story in rha_result.get("story_drift_histories", []):
        ax.plot(rha_result["time"], story["history"], label=f"Story {story['story']}")
    ax.set_title("Story Drift Histories")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Story drift")
    ax.grid(True, color="0.9")
    if rha_result.get("story_drift_histories"):
        ax.legend(fontsize=8)
    return fig, ax


def plot_peak_story_drift_envelope(rha_result: dict[str, Any], ax=None):
    fig, ax = _get_fig_ax(ax)
    rows = rha_result.get("peak_story_drifts", [])
    stories = [row["story"] for row in rows]
    values = [row["peak_absolute"] for row in rows]
    ax.plot(values, stories, marker="o", color="tab:red")
    ax.set_title("Peak Story Drift Envelope")
    ax.set_xlabel("Peak |story drift|")
    ax.set_ylabel("Story")
    ax.grid(True, color="0.9")
    if stories:
        ax.set_yticks(stories)
    return fig, ax


def plot_modal_coordinate_histories(rha_result: dict[str, Any], ax=None):
    fig, ax = _get_fig_ax(ax)
    q = np.asarray(rha_result.get("modal_coordinate_histories", []), dtype=float)
    for mode_idx in range(q.shape[0]):
        ax.plot(rha_result["time"], q[mode_idx, :], label=f"Mode {mode_idx + 1}")
    ax.set_title("Modal Coordinate Histories")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("q_n")
    ax.grid(True, color="0.9")
    if q.size:
        ax.legend(fontsize=8)
    return fig, ax


def _get_fig_ax(ax):
    if ax is not None:
        return ax.figure, ax
    fig, new_ax = plt.subplots()
    return fig, new_ax
