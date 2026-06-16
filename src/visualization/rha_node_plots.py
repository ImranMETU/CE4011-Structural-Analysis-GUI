"""Selected-node response-history plots for modal RHA results."""

from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt

from postprocessing.rha_node_results import extract_node_response_history


def plot_node_response_history(rha_result: dict[str, Any], node_id: int, dof: str = "ux", ax=None):
    """Plot selected node response versus time."""
    fig, ax = _get_fig_ax(ax)
    history = extract_node_response_history(rha_result, node_id, dof=dof)
    ax.plot(history["time"], history["response"], color="tab:blue", linewidth=1.2)
    ax.set_title(f"Node {int(node_id)} {dof} Response History")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Response (model displacement/rotation units)")
    ax.grid(True, color="0.9")
    return fig, ax


def _get_fig_ax(ax):
    if ax is not None:
        return ax.figure, ax
    fig, new_ax = plt.subplots()
    return fig, new_ax
