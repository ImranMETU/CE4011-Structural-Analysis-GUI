"""Plots for per-mode response-spectrum postprocessing."""

from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt


def plot_rsa_modal_peak_roof_response(rsa_result: dict[str, Any], ax=None):
    """Plot peak roof response contribution by mode."""
    fig, ax = _get_fig_ax(ax)
    rows = rsa_result.get("roof_peak_by_mode", [])
    modes = [int(row.get("mode", idx + 1)) for idx, row in enumerate(rows)]
    values = [float(row.get("peak_roof_response", row.get("peak_roof_ux", 0.0))) for row in rows]
    ax.bar(modes, values, color="tab:blue", alpha=0.8)
    ax.set_title("RSA Modal Peak Roof Response")
    ax.set_xlabel("Mode")
    ax.set_ylabel("Peak roof ux contribution")
    if modes:
        ax.set_xticks(modes)
    ax.grid(True, axis="y", color="0.9")
    return fig, ax


def plot_rsa_modal_peak_story_drift(rsa_result: dict[str, Any], ax=None):
    """Plot peak story-drift contribution by mode/story."""
    fig, ax = _get_fig_ax(ax)
    rows = rsa_result.get("story_drift_peak_by_mode", [])
    for mode in sorted({int(row.get("mode", 0)) for row in rows}):
        mode_rows = [row for row in rows if int(row.get("mode", 0)) == mode]
        stories = [int(row.get("story", 0)) for row in mode_rows]
        values = [abs(float(row.get("peak_story_drift", 0.0))) for row in mode_rows]
        ax.plot(values, stories, marker="o", linewidth=1.4, label=f"Mode {mode}")
    ax.set_title("RSA Modal Peak Story Drift")
    ax.set_xlabel("Peak |story drift| contribution")
    ax.set_ylabel("Story")
    ax.grid(True, color="0.9")
    if rows:
        ax.legend(fontsize=8)
    return fig, ax


def plot_rsa_combined_roof_response(rsa_result: dict[str, Any], ax=None):
    """Plot ABSSUM/SRSS/CQC combined roof response."""
    fig, ax = _get_fig_ax(ax)
    roof = rsa_result.get("combined", {}).get("roof_response", {})
    methods = ["ABSSUM", "SRSS", "CQC"]
    values = [float(roof.get(method, 0.0)) for method in methods]
    ax.bar(methods, values, color=["tab:red", "tab:blue", "tab:green"], alpha=0.8)
    ax.set_title("RSA Combined Roof Response")
    ax.set_xlabel("Combination method")
    ax.set_ylabel("Combined roof ux")
    ax.grid(True, axis="y", color="0.9")
    return fig, ax


def plot_rsa_combined_story_drift_envelope(rsa_result: dict[str, Any], ax=None):
    """Plot ABSSUM/SRSS/CQC combined story-drift envelopes."""
    fig, ax = _get_fig_ax(ax)
    rows = rsa_result.get("combined", {}).get("story_drifts", [])
    methods = ["ABSSUM", "SRSS", "CQC"]
    for method in methods:
        stories = [int(row.get("story", 0)) for row in rows]
        values = [abs(float(row.get(method, 0.0))) for row in rows]
        ax.plot(values, stories, marker="o", linewidth=1.4, label=method)
    ax.set_title("RSA Combined Story Drift Envelope")
    ax.set_xlabel("Combined |story drift|")
    ax.set_ylabel("Story")
    ax.grid(True, color="0.9")
    if rows:
        ax.legend(fontsize=8)
    return fig, ax


def _get_fig_ax(ax):
    if ax is not None:
        return ax.figure, ax
    fig, new_ax = plt.subplots()
    return fig, new_ax
