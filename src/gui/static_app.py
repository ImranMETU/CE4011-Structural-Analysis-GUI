"""Lightweight Tkinter static-analysis result viewer."""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path
from typing import Any, Callable

import tkinter as tk
from tkinter import filedialog, messagebox

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

SRC_ROOT = Path(__file__).resolve().parents[1]
IO_ROOT = SRC_ROOT / "io"
for path in (SRC_ROOT, IO_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from postprocessing.static_results import run_static_analysis  # noqa: E402
from visualization.static_plots import (  # noqa: E402
    plot_axial_force_diagram,
    plot_bending_moment_diagram,
    plot_deformed_shape,
    plot_geometry,
    plot_shear_force_diagram,
)
from xml_loader import load_structure_from_xml  # noqa: E402


PLOT_TYPES = (
    "Geometry",
    "Deformed Shape",
    "Axial Force Diagram",
    "Shear Force Diagram",
    "Bending Moment Diagram",
)

PLOT_SCALES = {
    "Geometry": 1.0,
    "Deformed Shape": 1.0,
    "Axial Force Diagram": 1.0e-6,
    "Shear Force Diagram": 1.0e-6,
    "Bending Moment Diagram": 1.0e-6,
}


class StaticAnalysisApp:
    """SAP2000-like static result viewer around the existing solver workflow."""

    def __init__(self, root: tk.Tk | tk.Toplevel):
        self.root = root
        self.root.title("CE4011 Static Result Viewer")
        self.root.minsize(900, 600)

        self.loaded_path: Path | None = None
        self.model_data: dict[str, Any] | None = None
        self.result: dict[str, Any] | None = None

        self.plot_type = tk.StringVar(value=PLOT_TYPES[0])

        self.figure = Figure(figsize=(7.0, 5.0), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas: FigureCanvasTkAgg | None = None

        self.summary_text: tk.Text | None = None
        self.plot_menu: tk.OptionMenu | None = None

        self._build_widgets()
        self._draw_empty_canvas()
        self._update_summary("No file loaded.")

    def _build_widgets(self) -> None:
        top = tk.Frame(self.root, padx=8, pady=8)
        top.pack(side=tk.TOP, fill=tk.X)

        load_button = tk.Button(top, text="Load XML/JSON Model", command=self.load_file)
        load_button.pack(side=tk.LEFT, padx=(0, 6))

        run_button = tk.Button(top, text="Run Static Analysis", command=self.run_analysis)
        run_button.pack(side=tk.LEFT, padx=(0, 12))

        tk.Label(top, text="Result View:").pack(side=tk.LEFT)
        self.plot_menu = tk.OptionMenu(top, self.plot_type, *PLOT_TYPES, command=self.on_plot_type_changed)
        self.plot_menu.pack(side=tk.LEFT, padx=(6, 0))

        body = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        plot_frame = tk.Frame(body)
        body.add(plot_frame, stretch="always")

        self.canvas = FigureCanvasTkAgg(self.figure, master=plot_frame)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        summary_frame = tk.Frame(body, width=260, padx=8, pady=8)
        body.add(summary_frame)

        tk.Label(summary_frame, text="Summary", font=("TkDefaultFont", 10, "bold")).pack(anchor=tk.W)
        self.summary_text = tk.Text(summary_frame, width=36, height=24, wrap=tk.WORD)
        self.summary_text.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.summary_text.configure(state=tk.DISABLED)

    def load_file(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Open structural model",
            filetypes=[
                ("Structural model", "*.xml *.json"),
                ("XML files", "*.xml"),
                ("JSON files", "*.json"),
                ("All files", "*.*"),
            ],
        )
        if not file_path:
            return

        try:
            path = Path(file_path)
            data = load_model_data(path)
        except Exception as exc:
            self._show_error("Failed to load model", exc)
            return

        self.loaded_path = path
        self.model_data = data
        self.result = None
        self._draw_empty_canvas()
        self._update_summary(f"Loaded file: {path.name}\nRun static analysis to view results.")

    def run_analysis(self) -> None:
        if self.model_data is None:
            messagebox.showerror("No model loaded", "Load an XML or JSON model before running static analysis.")
            return

        try:
            self.result = run_static_analysis(self.model_data)
            self._redraw_current_plot()
            self._update_summary()
        except Exception as exc:
            self.result = None
            self._show_error("Static analysis failed", exc)

    def on_plot_type_changed(self, _value: str | None = None) -> None:
        if self.result is None:
            messagebox.showerror("No analysis results", "Run static analysis before changing result plots.")
            self.plot_type.set(PLOT_TYPES[0])
            return

        try:
            self._redraw_current_plot()
            self._update_summary()
        except Exception as exc:
            self._show_error("Plot update failed", exc)

    def _redraw_current_plot(self) -> None:
        if self.result is None:
            return

        self.figure.clear()
        self.ax = self.figure.add_subplot(111)

        plot_name = self.plot_type.get()
        plot_func = _plot_function(plot_name)
        kwargs: dict[str, Any] = {"ax": self.ax}
        if plot_name != "Geometry":
            kwargs["scale"] = PLOT_SCALES[plot_name]

        plot_func(self.result, **kwargs)
        self.figure.tight_layout()
        if self.canvas is not None:
            self.canvas.draw_idle()

    def _draw_empty_canvas(self) -> None:
        self.figure.clear()
        self.ax = self.figure.add_subplot(111)
        self.ax.set_title("Load a model and run static analysis")
        self.ax.set_xlabel("X")
        self.ax.set_ylabel("Y")
        self.ax.grid(True, color="0.9")
        if self.canvas is not None:
            self.canvas.draw_idle()

    def _update_summary(self, message: str | None = None) -> None:
        if self.summary_text is None:
            return

        if message is not None:
            summary = message
        elif self.result is None:
            summary = "No analysis results."
        else:
            max_disp = max(abs(value) for value in self.result["displacement_vector"])
            loaded_name = self.loaded_path.name if self.loaded_path is not None else "(unknown)"
            summary = "\n".join(
                [
                    f"Loaded file: {loaded_name}",
                    f"Nodes: {len(self.result['nodes'])}",
                    f"Elements: {len(self.result['elements'])}",
                    f"Max |displacement|: {max_disp:.6e}",
                    f"Support reaction records: {len(self.result['reactions'])}",
                    f"Member-force records: {len(self.result['member_end_forces'])}",
                    f"Current plot: {self.plot_type.get()}",
                ]
            )

        self.summary_text.configure(state=tk.NORMAL)
        self.summary_text.delete("1.0", tk.END)
        self.summary_text.insert(tk.END, summary)
        self.summary_text.configure(state=tk.DISABLED)

    def _show_error(self, title: str, exc: Exception) -> None:
        detail = "".join(traceback.format_exception_only(type(exc), exc)).strip()
        messagebox.showerror(title, detail)


def load_model_data(path: Path) -> dict[str, Any]:
    """Load XML or JSON model data into the Structure.from_dict schema."""
    suffix = path.suffix.lower()
    if suffix == ".xml":
        return load_structure_from_xml(path)
    if suffix == ".json":
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("JSON model root must be an object.")
        return data
    raise ValueError(f"Unsupported model file type: {path.suffix}")


def _plot_function(plot_name: str) -> Callable[..., Any]:
    mapping = {
        "Geometry": plot_geometry,
        "Deformed Shape": plot_deformed_shape,
        "Axial Force Diagram": plot_axial_force_diagram,
        "Shear Force Diagram": plot_shear_force_diagram,
        "Bending Moment Diagram": plot_bending_moment_diagram,
    }
    return mapping[plot_name]


def main() -> None:
    root = tk.Tk()
    StaticAnalysisApp(root)
    root.mainloop()
