"""Lightweight Tkinter static/modal post-processing result viewer."""

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

from analysis.modal_solver import solve_modal_analysis  # noqa: E402
from model.structure import Structure  # noqa: E402
from postprocessing.modal_results import package_modal_results  # noqa: E402
from postprocessing.static_results import run_static_analysis  # noqa: E402
from visualization.modal_plots import (  # noqa: E402
    plot_modal_frequencies,
    plot_modal_periods,
    plot_mode_shape,
)
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
    "Mode 1",
    "Mode 2",
    "Mode 3",
    "Mode 4",
    "Modal Frequencies",
    "Modal Periods",
)

PLOT_SCALES = {
    "Geometry": 1.0,
    "Deformed Shape": 1.0,
    "Axial Force Diagram": 1.0e-6,
    "Shear Force Diagram": 1.0e-6,
    "Bending Moment Diagram": 1.0e-6,
}

STATIC_PLOT_TYPES = {
    "Geometry",
    "Deformed Shape",
    "Axial Force Diagram",
    "Shear Force Diagram",
    "Bending Moment Diagram",
}

MODAL_PLOT_TYPES = {
    "Mode 1",
    "Mode 2",
    "Mode 3",
    "Mode 4",
    "Modal Frequencies",
    "Modal Periods",
}


class StaticAnalysisApp:
    """SAP2000-like static/modal result viewer around existing backends."""

    def __init__(self, root: tk.Tk | tk.Toplevel):
        self.root = root
        self.root.title("CE4011 Static/Modal Result Viewer")
        self.root.minsize(900, 600)

        self.loaded_path: Path | None = None
        self.model_data: dict[str, Any] | None = None
        self.static_result: dict[str, Any] | None = None
        self.modal_result: dict[str, Any] | None = None

        self.plot_type = tk.StringVar(value=PLOT_TYPES[0])
        self.default_mass = tk.StringVar(value="10000.0")
        self.num_modes = tk.StringVar(value="4")
        self.mode_scale = tk.StringVar(value="1.0")

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

        modal_button = tk.Button(top, text="Run Modal Analysis", command=self.run_modal_analysis)
        modal_button.pack(side=tk.LEFT, padx=(0, 12))

        tk.Label(top, text="Mass/free ux:").pack(side=tk.LEFT)
        tk.Entry(top, textvariable=self.default_mass, width=10).pack(side=tk.LEFT, padx=(4, 8))

        tk.Label(top, text="Modes:").pack(side=tk.LEFT)
        tk.Spinbox(top, from_=1, to=4, textvariable=self.num_modes, width=4).pack(side=tk.LEFT, padx=(4, 8))

        tk.Label(top, text="Mode scale:").pack(side=tk.LEFT)
        tk.Entry(top, textvariable=self.mode_scale, width=7).pack(side=tk.LEFT, padx=(4, 12))

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
        self.static_result = None
        self.modal_result = None
        self._draw_empty_canvas()
        self._update_summary(f"Loaded file: {path.name}\nRun static or modal analysis to view results.")

    def run_analysis(self) -> None:
        if self.model_data is None:
            messagebox.showerror("No model loaded", "Load an XML or JSON model before running static analysis.")
            return

        try:
            self.static_result = run_static_analysis(self.model_data)
            if self.plot_type.get() not in STATIC_PLOT_TYPES:
                self.plot_type.set("Geometry")
            self._redraw_current_plot()
            self._update_summary()
        except Exception as exc:
            self.static_result = None
            self._show_error("Static analysis failed", exc)

    def run_modal_analysis(self) -> None:
        if self.model_data is None:
            messagebox.showerror("No model loaded", "Load an XML or JSON model before running modal analysis.")
            return

        try:
            mass_value = _parse_positive_float(self.default_mass.get(), "default lateral mass")
            n_modes = _parse_positive_int(self.num_modes.get(), "number of modes")
            structure = Structure.from_dict(self.model_data)
            mass_mapping = build_default_ux_mass_mapping(structure, mass_value)
            if not mass_mapping:
                raise ValueError("No free ux translational DOFs were found for automatic modal mass assignment.")

            modal = solve_modal_analysis(structure, mass_mapping, n_modes=n_modes)
            self.modal_result = package_modal_results(modal, structure)
            if self.plot_type.get() not in MODAL_PLOT_TYPES:
                self.plot_type.set("Mode 1")
            self._redraw_current_plot()
            self._update_summary()
        except Exception as exc:
            self.modal_result = None
            self._show_error("Modal analysis failed", exc)

    def on_plot_type_changed(self, _value: str | None = None) -> None:
        plot_name = self.plot_type.get()
        if plot_name in STATIC_PLOT_TYPES and self.static_result is None:
            messagebox.showerror("No static results", "Run static analysis before selecting a static result plot.")
            self.plot_type.set("Geometry")
            return
        if plot_name in MODAL_PLOT_TYPES and self.modal_result is None:
            messagebox.showerror("No modal results", "Run modal analysis before selecting a modal result plot.")
            self.plot_type.set("Geometry")
            return

        try:
            self._redraw_current_plot()
            self._update_summary()
        except Exception as exc:
            self._show_error("Plot update failed", exc)

    def _redraw_current_plot(self) -> None:
        self.figure.clear()
        self.ax = self.figure.add_subplot(111)

        plot_name = self.plot_type.get()
        if plot_name in STATIC_PLOT_TYPES:
            if self.static_result is None:
                return
            plot_func = _static_plot_function(plot_name)
            kwargs: dict[str, Any] = {"ax": self.ax}
            if plot_name != "Geometry":
                kwargs["scale"] = PLOT_SCALES[plot_name]
            plot_func(self.static_result, **kwargs)
        elif plot_name in MODAL_PLOT_TYPES:
            if self.modal_result is None:
                return
            self._draw_modal_plot(plot_name)
        else:
            raise ValueError(f"Unknown plot type: {plot_name}")

        self.figure.tight_layout()
        if self.canvas is not None:
            self.canvas.draw_idle()

    def _draw_modal_plot(self, plot_name: str) -> None:
        if self.modal_result is None:
            return

        if plot_name.startswith("Mode "):
            mode_index = int(plot_name.split()[1]) - 1
            n_modes = len(self.modal_result["frequencies_hz"])
            if mode_index >= n_modes:
                raise ValueError(f"{plot_name} is not available; modal analysis computed {n_modes} mode(s).")
            scale = _parse_positive_float(self.mode_scale.get(), "mode-shape scale")
            plot_mode_shape(self.modal_result, mode_index=mode_index, scale=scale, ax=self.ax)
        elif plot_name == "Modal Frequencies":
            plot_modal_frequencies(self.modal_result, ax=self.ax)
        elif plot_name == "Modal Periods":
            plot_modal_periods(self.modal_result, ax=self.ax)
        else:
            raise ValueError(f"Unknown modal plot type: {plot_name}")

    def _draw_empty_canvas(self) -> None:
        self.figure.clear()
        self.ax = self.figure.add_subplot(111)
        self.ax.set_title("Load a model and run static or modal analysis")
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
        else:
            loaded_name = self.loaded_path.name if self.loaded_path is not None else "(unknown)"
            lines = [f"Loaded file: {loaded_name}", f"Current plot: {self.plot_type.get()}"]

            if self.static_result is not None:
                max_disp = max(abs(value) for value in self.static_result["displacement_vector"])
                lines.extend(
                    [
                        "",
                        "Static analysis: run",
                        f"Nodes: {len(self.static_result['nodes'])}",
                        f"Elements: {len(self.static_result['elements'])}",
                        f"Max |displacement|: {max_disp:.6e}",
                        f"Support reaction records: {len(self.static_result['reactions'])}",
                        f"Member-force records: {len(self.static_result['member_end_forces'])}",
                    ]
                )
            else:
                lines.extend(["", "Static analysis: not run"])

            if self.modal_result is not None:
                lines.extend(self._modal_summary_lines())
            else:
                lines.extend(["", "Modal analysis: not run"])
                lines.append("Mass assumption: default mass is assigned to free ux DOFs only.")

            summary = "\n".join(lines)

        self.summary_text.configure(state=tk.NORMAL)
        self.summary_text.delete("1.0", tk.END)
        self.summary_text.insert(tk.END, summary)
        self.summary_text.configure(state=tk.DISABLED)

    def _show_error(self, title: str, exc: Exception) -> None:
        detail = "".join(traceback.format_exception_only(type(exc), exc)).strip()
        messagebox.showerror(title, detail)

    def _modal_summary_lines(self) -> list[str]:
        if self.modal_result is None:
            return []

        lines = [
            "",
            "Modal analysis: run",
            f"Modes computed: {len(self.modal_result['frequencies_hz'])}",
            "Mass assumption: default mass assigned to free ux DOFs only; uy/rz mass = 0.",
        ]

        freq_preview = self.modal_result["frequency_table"][:4]
        if freq_preview:
            lines.append("Frequencies (Hz):")
            for row in freq_preview:
                lines.append(f"  Mode {row['mode']}: {row['frequency_hz']:.6g}")

        period_preview = self.modal_result["period_table"][:4]
        if period_preview:
            lines.append("Periods (s):")
            for row in period_preview:
                lines.append(f"  Mode {row['mode']}: {row['period']:.6g}")

        participation = self.modal_result.get("participation", [])[:4]
        if participation:
            lines.append("ux participation:")
            for row in participation:
                lines.append(
                    f"  Mode {row['mode']}: Gamma={row['gamma']:.4g}, "
                    f"Meff ratio={row['effective_modal_mass_ratio']:.4g}"
                )

        return lines


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


def build_default_ux_mass_mapping(structure: Structure, mass_value: float) -> dict[int, dict[str, float]]:
    """Assign mass to each node with a free ux DOF; leave uy/rz massless."""
    mapping: dict[int, dict[str, float]] = {}
    for node_id, node in sorted(structure.nodes.items()):
        ux_eq = node.get_dof_number("ux")
        if ux_eq != 0:
            mapping[int(node_id)] = {"ux": mass_value, "uy": 0.0, "rz": 0.0}
    return mapping


def _parse_positive_float(value: str, label: str) -> float:
    try:
        number = float(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be a number.") from exc
    if number <= 0.0:
        raise ValueError(f"{label} must be positive.")
    return number


def _parse_positive_int(value: str, label: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be an integer.") from exc
    if number <= 0:
        raise ValueError(f"{label} must be positive.")
    return number


def _static_plot_function(plot_name: str) -> Callable[..., Any]:
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
