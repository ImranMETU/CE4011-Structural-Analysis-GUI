"""Matplotlib plots for ground motions and response spectra."""

from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt


def plot_acceleration_history(time, acceleration, ax=None):
    """Plot acceleration time history and return ``(fig, ax)``."""
    fig, ax = _get_fig_ax(ax)
    ax.plot(time, acceleration, color="tab:blue", linewidth=1.2)
    ax.set_title("Ground Acceleration Time History")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Acceleration (m/s^2)")
    ax.grid(True, color="0.9")
    return fig, ax


def plot_response_spectrum_sa(spectrum: dict[str, Any], ax=None):
    """Plot spectral acceleration versus period and return ``(fig, ax)``."""
    fig, ax = _get_fig_ax(ax)
    ax.plot(spectrum["periods"], spectrum["Sa"], color="tab:red", linewidth=1.4)
    ax.set_title("Elastic Response Spectrum - Sa")
    ax.set_xlabel("Period (s)")
    ax.set_ylabel("Sa (m/s^2)")
    ax.grid(True, color="0.9")
    return fig, ax


def plot_response_spectrum_sd(spectrum: dict[str, Any], ax=None):
    """Plot spectral displacement versus period and return ``(fig, ax)``."""
    fig, ax = _get_fig_ax(ax)
    ax.plot(spectrum["periods"], spectrum["Sd"], color="tab:green", linewidth=1.4)
    ax.set_title("Elastic Response Spectrum - Sd")
    ax.set_xlabel("Period (s)")
    ax.set_ylabel("Sd (m)")
    ax.grid(True, color="0.9")
    return fig, ax


def _get_fig_ax(ax):
    if ax is not None:
        return ax.figure, ax
    fig, new_ax = plt.subplots()
    return fig, new_ax
