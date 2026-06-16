"""Tkinter dialog for per-mode response-spectrum analysis postprocessing."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from analysis.modal_rsa import run_modal_rsa
from analysis.response_spectrum_generator import generate_elastic_response_spectrum
from ground_motion_loader import load_ground_motion


GROUND_MOTION_UNITS = ("cm/s2", "m/s2", "g")


def open_rsa_dialog(
    parent: tk.Misc,
    modal_result: dict[str, Any] | None,
    model_data: dict[str, Any] | None,
    on_complete: Callable[[dict[str, Any]], None],
) -> "ResponseSpectrumAnalysisDialog | None":
    """Open RSA dialog after modal analysis is available."""
    if modal_result is None:
        messagebox.showerror("No modal results", "Run modal analysis before RSA.")
        return None
    return ResponseSpectrumAnalysisDialog(parent, modal_result, model_data, on_complete)


class ResponseSpectrumAnalysisDialog:
    """Small dialog that loads a THF record, generates a spectrum, and runs per-mode RSA."""

    def __init__(
        self,
        parent: tk.Misc,
        modal_result: dict[str, Any],
        model_data: dict[str, Any] | None,
        on_complete: Callable[[dict[str, Any]], None],
    ):
        self.parent = parent
        self.modal_result = modal_result
        self.model_data = model_data
        self.on_complete = on_complete

        self.window = tk.Toplevel(parent)
        self.window.title("Response Spectrum Analysis")
        self.window.geometry("640x430")
        self.window.minsize(580, 360)

        self.path_var = tk.StringVar(value=_default_ground_motion_path())
        self.unit_var = tk.StringVar(value="cm/s2")
        self.damping_var = tk.StringVar(value="0.05")
        self.modes_var = tk.StringVar(value=str(min(4, _available_modes(modal_result))))
        self.direction_var = tk.StringVar(value="ux")
        self.status_var = tk.StringVar(value="Select a THF file and run RSA.")

        self._build_widgets()

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

        status = ttk.LabelFrame(frame, text="Status / Warnings", padding=8)
        status.grid(row=5, column=0, columnspan=3, sticky="nsew", pady=(10, 8))
        ttk.Label(status, textvariable=self.status_var, justify=tk.LEFT, wraplength=560).pack(anchor=tk.W)

        buttons = ttk.Frame(frame)
        buttons.grid(row=6, column=0, columnspan=3, sticky="ew")
        ttk.Button(buttons, text="Run RSA", command=self.run_rsa).pack(side=tk.LEFT)
        ttk.Button(buttons, text="Close", command=self.window.destroy).pack(side=tk.RIGHT)

    def browse_record(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.window,
            title="Open THF ground motion",
            filetypes=[("THF ground motion", "*.THF *.thf"), ("Text files", "*.txt"), ("All files", "*.*")],
        )
        if path:
            self.path_var.set(path)

    def run_rsa(self) -> None:
        try:
            path = Path(self.path_var.get())
            if not path.exists():
                raise FileNotFoundError(f"THF file not found: {path}")
            damping = float(self.damping_var.get())
            modes = int(self.modes_var.get())
            ground_motion = load_ground_motion(path, input_unit=self.unit_var.get())
            max_period = max(float(np.max(self.modal_result.get("periods", [1.0]))) * 1.5, 5.0)
            periods = np.linspace(0.02, max_period, 250)
            spectrum = generate_elastic_response_spectrum(
                ground_motion["time"],
                ground_motion["acceleration"],
                periods,
                damping_ratio=damping,
            )
            spectrum["record_path"] = str(path)
            result = run_modal_rsa(
                self.modal_result,
                spectrum,
                static_or_model_data=self.model_data,
                num_modes=modes,
                direction=self.direction_var.get(),
            )
        except Exception as exc:
            messagebox.showerror("RSA failed", str(exc), parent=self.window)
            return

        self.on_complete(result)
        warning_text = "\n".join(result.get("warnings", []))
        self.status_var.set(
            f"RSA complete. Modes used: {result['modes_used']}."
            + (f"\n{warning_text}" if warning_text else "")
        )


def _available_modes(modal_result: dict[str, Any]) -> int:
    return len(modal_result.get("frequencies_hz", []))


def _default_ground_motion_path() -> str:
    root = Path(__file__).resolve().parents[2]
    path = root / "inputs" / "groundmotion" / "DIN95Y01.THF"
    return str(path) if path.exists() else ""
