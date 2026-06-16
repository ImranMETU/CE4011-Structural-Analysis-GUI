"""Matplotlib plots for braced/unbraced comparison results."""

from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt


def plot_roof_displacement_comparison(comparison_result: dict[str, Any], ax=None):
    fig, ax = _get_fig_ax(ax)
    _bar(ax, comparison_result, "roof_displacement_ux", "Roof Displacement ux", use_abs=True)
    return fig, ax


def plot_max_story_drift_comparison(comparison_result: dict[str, Any], ax=None):
    fig, ax = _get_fig_ax(ax)
    _bar(ax, comparison_result, "max_story_drift", "Max Story Drift", use_abs=False)
    return fig, ax


def plot_fundamental_frequency_comparison(comparison_result: dict[str, Any], ax=None):
    fig, ax = _get_fig_ax(ax)
    _bar(ax, comparison_result, "f1_Hz", "Fundamental Frequency f1 (Hz)", use_abs=False)
    return fig, ax


def plot_fundamental_period_comparison(comparison_result: dict[str, Any], ax=None):
    fig, ax = _get_fig_ax(ax)
    _bar(ax, comparison_result, "T1_s", "Fundamental Period T1 (s)", use_abs=False)
    return fig, ax


def plot_story_drift_profile_comparison(unbraced_drift: dict[str, Any], braced_drift: dict[str, Any], ax=None):
    fig, ax = _get_fig_ax(ax)
    for label, drift, color in (
        ("Unbraced", unbraced_drift, "tab:blue"),
        ("Braced", braced_drift, "tab:orange"),
    ):
        stories = drift.get("stories", [])
        x = [story["abs_story_drift"] for story in stories]
        y = [story["upper_elevation"] for story in stories]
        ax.plot(x, y, marker="o", label=label, color=color)
    ax.set_xlabel("Absolute Story Drift")
    ax.set_ylabel("Elevation")
    ax.set_title("Story Drift Profile Comparison")
    ax.grid(True, color="0.9")
    ax.legend()
    return fig, ax


def _bar(ax, comparison_result: dict[str, Any], key: str, title: str, use_abs: bool) -> None:
    values = []
    for side in ("unbraced", "braced"):
        value = comparison_result[side].get(key)
        value = 0.0 if value is None else float(value)
        values.append(abs(value) if use_abs else value)
    ax.bar(["Unbraced", "Braced"], values, color=["tab:blue", "tab:orange"])
    ax.set_title(title)
    ax.set_ylabel(title)
    ax.grid(True, axis="y", color="0.9")


def _get_fig_ax(ax):
    if ax is not None:
        return ax.figure, ax
    fig, new_ax = plt.subplots()
    return fig, new_ax
