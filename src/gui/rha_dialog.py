"""Tkinter dialog for linear elastic modal response-history analysis."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from analysis.modal_rha import run_modal_rha
from ground_motion_loader import load_ground_motion


GROUND_MOTION_UNITS = ("cm/s2", "m/s2", "g")


def open_rha_dialog(
    parent: tk.Misc,
    modal_result: dict[str, Any] | None,
    on_complete: Callable[[dict[str, Any]], None],
) -> "ResponseHistoryAnalysisDialog | None":
    """Open the RHA dialog after confirming modal results are available."""
    if modal_result is None:
        messagebox.showerror("No modal results", "Run modal analysis before Response History Analysis.")
        return None
    return ResponseHistoryAnalysisDialog(parent, modal_result, on_complete)


class ResponseHistoryAnalysisDialog:
    """Small modal RHA setup dialog."""

    def __init__(
        self,
        parent: tk.Misc,
        modal_result: dict[str, Any],
        on_complete: Callable[[dict[str, Any]], None],
    ):
        self.parent = parent
        self.modal_result = modal_result
        self.on_complete = on_complete
        self.ground_motion: dict[str, Any] | None = None

        self.window = tk.Toplevel(parent)
        self.window.title("Response History Analysis")
        self.window.geometry("620x420")
        self.window.minsize(560, 360)

        self.path_var = tk.StringVar(value=_default_ground_motion_path())
        self.unit_var = tk.StringVar(value="cm/s2")
        self.damping_var = tk.StringVar(value="0.05")
        self.modes_var = tk.StringVar(value=str(min(3, _available_modes(modal_result))))
        self.direction_var = tk.StringVar(value="ux")
        self.record_summary_var = tk.StringVar(value="No ground motion loaded.")
        self.status_var = tk.StringVar(value="Load a THF file, then run RHA.")

        self._build_widgets()
        if self.path_var.get():
            self.load_record()

    def _build_widgets(self) -> None:
        frame = ttk.Frame(self.window, padding=10)
        frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="THF file:").grid(row=0, column=0, sticky="w", pady=3)
        ttk.Entry(frame, textvariable=self.path_var).grid(row=0, column=1, sticky="ew", padx=6, pady=3)
        ttk.Button(frame, text="Browse", command=self.browse_record).grid(row=0, column=2, pady=3)

        ttk.Label(frame, text="Input unit:").grid(row=1, column=0, sticky="w", pady=3)
        ttk.Combobox(frame, values=GROUND_MOTION_UNITS, textvariable=self.unit_var, state="readonly", width=12).grid(
            row=1,
            column=1,
            sticky="w",
            padx=6,
            pady=3,
        )
        ttk.Button(frame, text="Load / Refresh Record", command=self.load_record).grid(row=1, column=2, pady=3)

        ttk.Label(frame, text="Damping ratio:").grid(row=2, column=0, sticky="w", pady=3)
        ttk.Entry(frame, textvariable=self.damping_var, width=12).grid(row=2, column=1, sticky="w", padx=6, pady=3)

        ttk.Label(frame, text="Modes to include:").grid(row=3, column=0, sticky="w", pady=3)
        ttk.Entry(frame, textvariable=self.modes_var, width=12).grid(row=3, column=1, sticky="w", padx=6, pady=3)

        ttk.Label(frame, text="Direction:").grid(row=4, column=0, sticky="w", pady=3)
        ttk.Combobox(frame, values=("ux",), textvariable=self.direction_var, state="readonly", width=12).grid(
            row=4,
            column=1,
            sticky="w",
            padx=6,
            pady=3,
        )

        summary = ttk.LabelFrame(frame, text="Record Summary", padding=8)
        summary.grid(row=5, column=0, columnspan=3, sticky="nsew", pady=(10, 6))
        ttk.Label(summary, textvariable=self.record_summary_var, justify=tk.LEFT).pack(anchor=tk.W)

        status = ttk.LabelFrame(frame, text="Status / Warnings", padding=8)
        status.grid(row=6, column=0, columnspan=3, sticky="nsew", pady=(0, 8))
        ttk.Label(status, textvariable=self.status_var, justify=tk.LEFT, wraplength=540).pack(anchor=tk.W)

        buttons = ttk.Frame(frame)
        buttons.grid(row=7, column=0, columnspan=3, sticky="ew")
        ttk.Button(buttons, text="Run RHA", command=self.run_rha).pack(side=tk.LEFT)
        ttk.Button(buttons, text="Close", command=self.window.destroy).pack(side=tk.RIGHT)

    def browse_record(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.window,
            title="Open THF ground motion",
            filetypes=[("THF ground motion", "*.THF *.thf"), ("Text files", "*.txt"), ("All files", "*.*")],
        )
        if path:
            self.path_var.set(path)
            self.load_record()

    def load_record(self) -> None:
        path = Path(self.path_var.get())
        if not path.exists():
            self.ground_motion = None
            self.record_summary_var.set("Selected THF file does not exist.")
            return
        try:
            gm = load_ground_motion(path, input_unit=self.unit_var.get())
            gm["path"] = str(path)
        except Exception as exc:
            self.ground_motion = None
            messagebox.showerror("Ground motion load failed", str(exc))
            return

        self.ground_motion = gm
        self.record_summary_var.set(
            f"File: {path.name}\n"
            f"Points: {gm['n_points']}\n"
            f"dt: {gm['dt']:.6g} s\n"
            f"Duration: {gm['duration']:.6g} s\n"
            f"PGA: {gm['pga']:.6g} m/s2 ({gm['pga'] / 9.80665:.6g} g)"
        )
        self.status_var.set("Ground motion loaded. Ready to run RHA.")

    def run_rha(self) -> None:
        if self.ground_motion is None:
            self.load_record()
        if self.ground_motion is None:
            return
        try:
            damping = float(self.damping_var.get())
            modes = int(self.modes_var.get())
            result = run_modal_rha(
                self.modal_result,
                self.ground_motion,
                damping_ratio=damping,
                num_modes=modes,
                direction=self.direction_var.get(),
            )
        except Exception as exc:
            messagebox.showerror("RHA failed", str(exc))
            return

        self.on_complete(result)
        self.status_var.set(
            f"RHA complete. Modes used: {result['modes_used']}; "
            f"peak roof ux: {result['peak_roof_displacement']['value']:.6e}."
        )


def _available_modes(modal_result: dict[str, Any]) -> int:
    return len(modal_result.get("frequencies_hz", modal_result.get("frequency_Hz", [])))


def _default_ground_motion_path() -> str:
    root = Path(__file__).resolve().parents[2]
    path = root / "inputs" / "groundmotion" / "DIN95Y01.THF"
    return str(path) if path.exists() else ""
