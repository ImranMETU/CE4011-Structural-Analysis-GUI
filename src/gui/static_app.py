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
from gui.input_dialogs import (  # noqa: E402
    open_analysis_options_dialog,
    open_frame_elements_dialog,
    open_materials_dialog,
    open_modal_masses_dialog,
    open_nodal_loads_dialog,
    open_nodes_dialog,
    open_sections_dialog,
    open_truss_elements_dialog,
)
from gui.model_builder import ModelBuilder  # noqa: E402
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
from text_loader import load_text_model, parse_text_model  # noqa: E402
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

DEFAULT_TEXT_MODEL = """# CE4011 text model input deck
# MATERIAL name E=30000000 alpha=8e-6
# SECTION name A=0.32 I=0.01707 d=0.8
# NODE id x y ux uy rz
# FRAME id node_i node_j material section
# TRUSS id node_i node_j material section
# LOAD node_id FX=0 FY=0 MZ=0
# MASS node_id UX=10000 UY=0 RZ=0

MATERIAL steel E=200000000 alpha=1.2e-5
SECTION beam A=0.01 I=1e-4 d=0.3

NODE 1 0 0 FIX FIX FIX
NODE 2 3 0 FREE FREE FREE

FRAME 1 1 2 steel beam
LOAD 2 FX=0 FY=-1000 MZ=0
MASS 2 UX=10000 UY=0 RZ=0
"""

INPUT_FORMAT_HELP = """Supported text input syntax:

# comment
MATERIAL name E=30000000 alpha=8e-6
SECTION name A=0.32 I=0.01707 d=0.8
NODE id x y ux uy rz
FRAME id node_i node_j material section
TRUSS id node_i node_j material section
LOAD node_id FX=10000 FY=0 MZ=0
MASS node_id UX=10000 UY=0 RZ=0

Node restraints must be FIX or FREE.
MASS lines are optional and are used for modal analysis.
"""


class StaticAnalysisApp:
    """SAP2000-like static/modal result viewer around existing backends."""

    def __init__(self, root: tk.Tk | tk.Toplevel):
        self.root = root
        self.root.title("CE4011 Static/Modal Result Viewer")
        self.root.minsize(900, 600)

        self.loaded_path: Path | None = None
        self.model_data: dict[str, Any] | None = None
        self.text_mass_mapping: dict[int, dict[str, float]] | None = None
        self.text_editor: tk.Toplevel | None = None
        self.text_editor_widget: tk.Text | None = None
        self.text_model_path: Path | None = None
        self.input_source: str | None = None
        self.model_builder = ModelBuilder()
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

        self._build_menu()
        self._build_widgets()
        self._draw_empty_canvas()
        self._update_summary("No file loaded.")

    def _build_menu(self) -> None:
        menu_bar = tk.Menu(self.root)

        file_menu = tk.Menu(menu_bar, tearoff=False)
        file_menu.add_command(label="New Model", command=self.new_model)
        file_menu.add_command(label="Open XML Model", command=self.open_xml_model)
        file_menu.add_command(label="Open JSON Model", command=self.open_json_model)
        file_menu.add_command(label="Open Text Model", command=self.open_text_model)
        file_menu.add_command(label="Save Text Model", command=self.save_text_model)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.destroy)
        menu_bar.add_cascade(label="File", menu=file_menu)

        define_menu = tk.Menu(menu_bar, tearoff=False)
        define_menu.add_command(label="Materials", command=self.define_materials)
        define_menu.add_command(label="Sections", command=self.define_sections)
        define_menu.add_command(label="Nodes / Joints", command=self.define_nodes)
        define_menu.add_command(label="Frame Elements", command=self.define_frame_elements)
        define_menu.add_command(label="Truss Elements", command=self.define_truss_elements)
        define_menu.add_command(label="Nodal Loads", command=self.define_nodal_loads)
        define_menu.add_command(label="Modal Masses", command=self.define_modal_masses)
        define_menu.add_command(label="Analysis Options", command=self.define_analysis_options)
        define_menu.add_separator()
        define_menu.add_command(label="Show Model Summary", command=self.show_model_summary)
        menu_bar.add_cascade(label="Define", menu=define_menu)

        analyze_menu = tk.Menu(menu_bar, tearoff=False)
        analyze_menu.add_command(label="Run Static Analysis", command=self.run_analysis)
        analyze_menu.add_command(label="Run Modal Analysis", command=self.run_modal_analysis)
        menu_bar.add_cascade(label="Analyze", menu=analyze_menu)

        display_menu = tk.Menu(menu_bar, tearoff=False)
        static_menu = tk.Menu(display_menu, tearoff=False)
        for name in ("Geometry", "Deformed Shape", "Axial Force Diagram", "Shear Force Diagram", "Bending Moment Diagram"):
            static_menu.add_command(label=name, command=lambda plot=name: self.select_plot_type(plot))
        modal_menu = tk.Menu(display_menu, tearoff=False)
        for name in ("Mode 1", "Mode 2", "Mode 3", "Mode 4", "Modal Frequencies", "Modal Periods"):
            modal_menu.add_command(label=name, command=lambda plot=name: self.select_plot_type(plot))
        display_menu.add_cascade(label="Static", menu=static_menu)
        display_menu.add_cascade(label="Modal", menu=modal_menu)
        menu_bar.add_cascade(label="Display", menu=display_menu)

        help_menu = tk.Menu(menu_bar, tearoff=False)
        help_menu.add_command(label="About", command=self.show_about)
        help_menu.add_command(label="Input Workflow Help", command=self.show_input_workflow_help)
        help_menu.add_command(label="Limitations", command=self.show_limitations)
        menu_bar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menu_bar)

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

        self._load_model_from_path(Path(file_path), source="file")

    def open_xml_model(self) -> None:
        file_path = filedialog.askopenfilename(title="Open XML model", filetypes=[("XML files", "*.xml")])
        if file_path:
            self._load_model_from_path(Path(file_path), source="xml")

    def open_json_model(self) -> None:
        file_path = filedialog.askopenfilename(title="Open JSON model", filetypes=[("JSON files", "*.json")])
        if file_path:
            self._load_model_from_path(Path(file_path), source="json")

    def open_text_model(self) -> None:
        file_path = filedialog.askopenfilename(title="Open text model", filetypes=[("Text model files", "*.txt")])
        if not file_path:
            return

        path = Path(file_path)
        try:
            data, mass_mapping = load_text_model(path)
            text = path.read_text(encoding="utf-8")
        except Exception as exc:
            self._show_error("Failed to load text model", exc)
            return

        self._set_loaded_model(path, data, source="text", mass_mapping=mass_mapping)
        self.text_model_path = path
        self._open_text_editor(text)
        self._update_summary(
            f"Loaded text model: {path.name}\n"
            f"Parsed {len(data['nodes'])} nodes, {len(data['elements'])} elements, "
            f"{len(mass_mapping)} modal mass record(s)."
        )

    def _load_model_from_path(self, path: Path, source: str) -> None:
        try:
            data = load_model_data(path)
        except Exception as exc:
            self._show_error("Failed to load model", exc)
            return

        self._set_loaded_model(path, data, source=source, mass_mapping=None)
        self._update_summary(f"Loaded file: {path.name}\nRun static or modal analysis to view results.")

    def _set_loaded_model(
        self,
        path: Path | None,
        data: dict[str, Any],
        source: str,
        mass_mapping: dict[int, dict[str, float]] | None,
    ) -> None:
        self.loaded_path = path
        self.model_data = data
        self.text_mass_mapping = mass_mapping
        self.input_source = source
        self.model_builder.load_from_structure_dict(data, mass_mapping)
        self.static_result = None
        self.modal_result = None
        self._draw_empty_canvas()

    def new_model(self) -> None:
        self.model_builder.clear()
        self.loaded_path = None
        self.model_data = self.model_builder.to_structure_dict()
        self.text_mass_mapping = None
        self.input_source = "form"
        self.static_result = None
        self.modal_result = None
        self._apply_analysis_options_to_controls()
        self._draw_empty_canvas()
        self._update_summary("New form-based model created.\nUse Define menu items to add model data.")

    def new_text_model(self) -> None:
        self.text_model_path = None
        self._open_text_editor(DEFAULT_TEXT_MODEL)
        self._parse_current_text_editor(update_summary=True)

    def edit_text_model(self) -> None:
        if self.text_editor_widget is not None:
            self.text_editor.lift()
            return
        if self.input_source == "text" and self.text_model_path is not None:
            try:
                text = self.text_model_path.read_text(encoding="utf-8")
            except OSError as exc:
                self._show_error("Failed to reopen text model", exc)
                return
            self._open_text_editor(text)
        else:
            self._open_text_editor(DEFAULT_TEXT_MODEL)

    def save_text_model(self) -> None:
        if self.text_editor_widget is None:
            messagebox.showerror("No text model", "Open or create a text model before saving.")
            return

        path = self.text_model_path
        if path is None:
            file_path = filedialog.asksaveasfilename(
                title="Save text model",
                defaultextension=".txt",
                filetypes=[("Text model files", "*.txt")],
            )
            if not file_path:
                return
            path = Path(file_path)

        try:
            path.write_text(self._text_editor_contents(), encoding="utf-8")
        except OSError as exc:
            self._show_error("Failed to save text model", exc)
            return

        self.text_model_path = path
        self.loaded_path = path
        self._parse_current_text_editor(update_summary=True)

    def _open_text_editor(self, text: str) -> None:
        if self.text_editor is not None and self.text_editor.winfo_exists():
            self.text_editor.destroy()

        self.text_editor = tk.Toplevel(self.root)
        self.text_editor.title("Text Model Editor")
        self.text_editor.geometry("760x520")
        self.text_editor.protocol("WM_DELETE_WINDOW", self._close_text_editor)

        toolbar = tk.Frame(self.text_editor, padx=6, pady=6)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        tk.Button(toolbar, text="Apply / Parse Model", command=lambda: self._parse_current_text_editor(True)).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        tk.Button(toolbar, text="Save Text Model", command=self.save_text_model).pack(side=tk.LEFT)

        self.text_editor_widget = tk.Text(self.text_editor, wrap=tk.NONE)
        self.text_editor_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.text_editor_widget.insert("1.0", text)

    def _close_text_editor(self) -> None:
        if self.text_editor is not None:
            self.text_editor.destroy()
        self.text_editor = None
        self.text_editor_widget = None

    def _text_editor_contents(self) -> str:
        if self.text_editor_widget is None:
            return ""
        return self.text_editor_widget.get("1.0", tk.END)

    def _parse_current_text_editor(self, update_summary: bool = False) -> bool:
        if self.text_editor_widget is None:
            return False
        try:
            data, mass_mapping = parse_text_model(self._text_editor_contents())
        except Exception as exc:
            self._show_error("Failed to parse text model", exc)
            return False

        self._set_loaded_model(self.text_model_path, data, source="text", mass_mapping=mass_mapping)
        if update_summary:
            name = self.text_model_path.name if self.text_model_path else "(unsaved text model)"
            self._update_summary(
                f"Loaded text model: {name}\n"
                f"Parsed {len(data['nodes'])} nodes, {len(data['elements'])} elements, "
                f"{len(mass_mapping)} modal mass record(s)."
            )
        return True

    def run_analysis(self) -> None:
        if not self._sync_model_source_if_needed():
            return
        if self.model_data is None:
            messagebox.showerror("No model loaded", "Load an XML, JSON, or text model before running static analysis.")
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
        if not self._sync_model_source_if_needed():
            return
        if self.model_data is None:
            messagebox.showerror("No model loaded", "Load an XML, JSON, or text model before running modal analysis.")
            return

        try:
            n_modes = _parse_positive_int(self.num_modes.get(), "number of modes")
            structure = Structure.from_dict(self.model_data)
            mass_mapping = self.text_mass_mapping if self.text_mass_mapping else None
            if not mass_mapping:
                mass_value = _parse_positive_float(self.default_mass.get(), "default lateral mass")
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

    def _sync_model_source_if_needed(self) -> bool:
        if self.input_source == "text" and self.text_editor_widget is not None:
            return self._parse_current_text_editor(update_summary=False)
        if self.input_source == "form":
            self.model_data = self.model_builder.to_structure_dict()
            masses = self.model_builder.to_mass_mapping()
            self.text_mass_mapping = masses if masses else None
        return True

    def _apply_analysis_options_to_controls(self) -> None:
        options = self.model_builder.analysis_options
        self.default_mass.set(str(options["default_lateral_mass"]))
        self.num_modes.set(str(options["num_modes"]))
        self.mode_scale.set(str(options["mode_shape_scale"]))

    def _apply_controls_to_analysis_options(self) -> None:
        self.model_builder.update_analysis_options(
            default_lateral_mass=float(self.default_mass.get()),
            num_modes=int(self.num_modes.get()),
            mode_shape_scale=float(self.mode_scale.get()),
        )

    def select_plot_type(self, plot_name: str) -> None:
        self.plot_type.set(plot_name)
        self.on_plot_type_changed(plot_name)

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
                kwargs["scale"] = self._static_plot_scale(plot_name)
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

    def _static_plot_scale(self, plot_name: str) -> float:
        if plot_name == "Deformed Shape":
            return float(self.model_builder.analysis_options["static_deformation_scale"])
        if plot_name in {"Axial Force Diagram", "Shear Force Diagram", "Bending Moment Diagram"}:
            return float(self.model_builder.analysis_options["force_diagram_scale"])
        return PLOT_SCALES.get(plot_name, 1.0)

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

        mass_assumption = (
            "Mass assumption: using modal mass records from text/form model."
            if self.text_mass_mapping
            else "Mass assumption: default mass assigned to free ux DOFs only; uy/rz mass = 0."
        )
        lines = [
            "",
            "Modal analysis: run",
            f"Modes computed: {len(self.modal_result['frequencies_hz'])}",
            mass_assumption,
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

    def define_materials(self) -> None:
        self._ensure_form_source()
        open_materials_dialog(self.root, self.model_builder)

    def define_sections(self) -> None:
        self._ensure_form_source()
        open_sections_dialog(self.root, self.model_builder)

    def define_nodes(self) -> None:
        self._ensure_form_source()
        open_nodes_dialog(self.root, self.model_builder)

    def define_frame_elements(self) -> None:
        self._ensure_form_source()
        open_frame_elements_dialog(self.root, self.model_builder)

    def define_truss_elements(self) -> None:
        self._ensure_form_source()
        open_truss_elements_dialog(self.root, self.model_builder)

    def define_nodal_loads(self) -> None:
        self._ensure_form_source()
        open_nodal_loads_dialog(self.root, self.model_builder)

    def define_modal_masses(self) -> None:
        self._ensure_form_source()
        open_modal_masses_dialog(self.root, self.model_builder)

    def define_analysis_options(self) -> None:
        self._ensure_form_source()
        open_analysis_options_dialog(self.root, self.model_builder, on_apply=self._apply_analysis_options_to_controls)

    def _ensure_form_source(self) -> None:
        if self.input_source is None:
            self.new_model()
        elif self.input_source != "form":
            self.input_source = "form"

    def show_model_summary(self) -> None:
        if self.input_source == "form":
            self._sync_model_source_if_needed()
            messagebox.showinfo("Model Summary", "\n".join(self.model_builder.summary_lines()))
            return

        if self.model_data is None:
            messagebox.showinfo("Model Summary", "No model loaded.")
            return

        mass_count = len(self.text_mass_mapping or {})
        messagebox.showinfo(
            "Model Summary",
            "\n".join(
                [
                    f"Nodes: {len(self.model_data.get('nodes', []))}",
                    f"Materials: {len(self.model_data.get('materials', []))}",
                    f"Sections: {len(self.model_data.get('sections', []))}",
                    f"Elements: {len(self.model_data.get('elements', []))}",
                    f"Nodal loads: {len(self.model_data.get('nodal_loads', []))}",
                    f"Text MASS records: {mass_count}",
                ]
            ),
        )

    def show_input_format_help(self) -> None:
        messagebox.showinfo("Input Format Help", INPUT_FORMAT_HELP)

    def show_input_workflow_help(self) -> None:
        messagebox.showinfo(
            "Input Workflow Help",
            "Use File > New Model, then Define menu dialogs to enter materials, sections, "
            "nodes, elements, loads, modal masses, and analysis options.\n\n"
            "Alternatively, use File > Open XML Model, Open JSON Model, or Open Text Model.",
        )

    def show_limitations(self) -> None:
        messagebox.showinfo(
            "Limitations",
            "This is a simplified SAP-like postprocessor. It does not include mouse-based drawing, "
            "nonlinear analysis, staged construction, time history, P-Delta, design checks, "
            "load combinations, or full SAP2000-style tables.",
        )

    def show_about(self) -> None:
        messagebox.showinfo(
            "About",
            "CE4011 Static/Modal Postprocessor\n"
            "Lightweight SAP2000-like workflow for 2D frame-truss results.",
        )


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
