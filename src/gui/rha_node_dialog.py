"""Tkinter dialog for selected-node RHA response-history plots."""

from __future__ import annotations

from typing import Any, Callable

import tkinter as tk
from tkinter import messagebox, ttk

from postprocessing.rha_node_results import get_available_rha_nodes


def open_rha_node_dialog(
    parent: tk.Misc,
    rha_result: dict[str, Any] | None,
    on_plot: Callable[[int, str], None],
) -> "RhaNodeResponseDialog | None":
    """Open selected-node RHA response dialog."""
    if rha_result is None:
        messagebox.showerror(
            "No RHA results",
            "Run Response History Analysis before opening node response plots.",
        )
        return None
    return RhaNodeResponseDialog(parent, rha_result, on_plot)


class RhaNodeResponseDialog:
    """Small selector for node and DOF response-history plotting."""

    def __init__(self, parent: tk.Misc, rha_result: dict[str, Any], on_plot: Callable[[int, str], None]):
        self.rha_result = rha_result
        self.on_plot = on_plot
        nodes = get_available_rha_nodes(rha_result)

        self.window = tk.Toplevel(parent)
        self.window.title("Selected Node Response History")
        self.window.geometry("420x180")

        self.node_var = tk.StringVar(value=str(nodes[-1]) if nodes else "")
        self.dof_var = tk.StringVar(value="ux")

        frame = ttk.Frame(self.window, padding=10)
        frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Node:").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Combobox(frame, values=[str(node) for node in nodes], textvariable=self.node_var).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=6,
            pady=4,
        )
        ttk.Label(frame, text="DOF:").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Combobox(frame, values=("ux", "uy", "rz"), textvariable=self.dof_var, state="readonly").grid(
            row=1,
            column=1,
            sticky="w",
            padx=6,
            pady=4,
        )

        buttons = ttk.Frame(frame)
        buttons.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        ttk.Button(buttons, text="Plot", command=self.plot).pack(side=tk.LEFT)
        ttk.Button(buttons, text="Close", command=self.window.destroy).pack(side=tk.RIGHT)

    def plot(self) -> None:
        try:
            node_id = int(self.node_var.get())
            self.on_plot(node_id, self.dof_var.get())
        except Exception as exc:
            messagebox.showerror("Node response plot failed", str(exc), parent=self.window)
