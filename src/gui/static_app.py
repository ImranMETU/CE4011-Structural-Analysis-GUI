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
from matplotlib.patches import Rectangle

SRC_ROOT = Path(__file__).resolve().parents[1]
IO_ROOT = SRC_ROOT / "io"
for path in (SRC_ROOT, IO_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from analysis.modal_solver import solve_modal_analysis  # noqa: E402
from gui.frame_generator_dialog import (  # noqa: E402
    GENERATED_DIR,
    generate_proposal_default_models,
    open_frame_generator_dialog,
)
from gui.input_dialogs import (  # noqa: E402
    open_analysis_options_dialog,
    open_frame_elements_dialog,
    open_materials_dialog,
    open_modal_masses_dialog,
    open_nodal_loads_dialog,
    open_nodes_dialog,
    open_sections_dialog,
    open_support_settlements_dialog,
    open_thermal_loads_dialog,
    open_truss_elements_dialog,
)
from gui.interactive_selection import (  # noqa: E402
    pick_element,
    pick_node,
    select_elements_in_rectangle,
    select_nodes_in_rectangle,
)
from gui.model_builder import ModelBuilder  # noqa: E402
from gui.result_tables import (  # noqa: E402
    format_member_force_rows,
    format_modal_frequency_rows,
    format_modal_participation_rows,
    format_nodal_displacement_rows,
    format_reaction_rows,
    format_static_roof_displacement_rows,
    format_static_story_drift_rows,
    open_table_window,
    write_table_csv,
)
from model.structure import Structure  # noqa: E402
from postprocessing.modal_results import package_modal_results  # noqa: E402
from postprocessing.static_results import run_static_analysis  # noqa: E402
from postprocessing.drift_results import (  # noqa: E402
    compute_floor_displacements,
    compute_roof_displacement,
    compute_story_drift,
)
from visualization.drift_plots import (  # noqa: E402
    plot_drift_ratio_profile,
    plot_floor_displacement_profile,
    plot_story_drift_profile,
)
from visualization.model_view import plot_model_view  # noqa: E402
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
    "Model View",
    "Presentation Model View",
    "Deformed Shape",
    "Axial Force Diagram",
    "Shear Force Diagram",
    "Bending Moment Diagram",
    "Story Drift Profile",
    "Drift Ratio Profile",
    "Floor Displacement Profile",
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

MODEL_VIEW_TYPES = {
    "Model View",
    "Presentation Model View",
}

DRIFT_PLOT_TYPES = {
    "Story Drift Profile",
    "Drift Ratio Profile",
    "Floor Displacement Profile",
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
# THERMAL element_id T_UNIFORM=50
# SETTLEMENT node_id UX=0 UY=-0.002 RZ=0
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
THERMAL element_id T_UNIFORM=50
THERMAL element_id T_TOP=0 T_BOTTOM=50
SETTLEMENT node_id UX=0 UY=-0.002 RZ=0
MASS node_id UX=10000 UY=0 RZ=0

Node restraints must be FIX or FREE.
Thermal loads are assigned as element member loads.
Settlements are prescribed nodal displacements and should be on restrained DOFs.
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
        self.generated_model_name: str | None = None
        self.model_builder = ModelBuilder()
        self.static_result: dict[str, Any] | None = None
        self.modal_result: dict[str, Any] | None = None
        self.current_table: dict[str, Any] | None = None
        self.selected_nodes: set[int] = set()
        self.selected_elements: set[int] = set()
        self._selection_drag_start: tuple[float, float] | None = None
        self._selection_drag_start_pixel: tuple[float, float] | None = None
        self._selection_rect_artist: Rectangle | None = None
        self._selection_artists: list[Any] = []

        self.plot_type = tk.StringVar(value=PLOT_TYPES[0])
        self.default_mass = tk.StringVar(value="10000.0")
        self.num_modes = tk.StringVar(value="4")
        self.mode_scale = tk.StringVar(value="1.0")

        self.figure = Figure(figsize=(7.0, 5.0), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas: FigureCanvasTkAgg | None = None

        self.summary_text: tk.Text | None = None
        self.selection_text: tk.Text | None = None
        self.plot_menu: tk.OptionMenu | None = None

        self._build_menu()
        self._build_widgets()
        self._draw_empty_canvas()
        self._update_summary("No file loaded.")

    def _build_menu(self) -> None:
        menu_bar = tk.Menu(self.root)

        file_menu = tk.Menu(menu_bar, tearoff=False)
        file_menu.add_command(label="New Model", command=self.new_model)
        file_menu.add_command(label="New Assignment 4 Settlement Example", command=self.new_assignment4_settlement_example)
        file_menu.add_command(label="New Assignment 4 Thermal Example", command=self.new_assignment4_thermal_example)
        file_menu.add_separator()
        file_menu.add_command(label="Open XML Model", command=self.open_xml_model)
        file_menu.add_command(label="Open JSON Model", command=self.open_json_model)
        file_menu.add_command(label="Open Text Model", command=self.open_text_model)
        file_menu.add_command(label="Open Generated Model", command=self.open_generated_model)
        file_menu.add_command(label="Save Text Model", command=self.save_text_model)
        file_menu.add_command(label="Generate Proposal Models", command=self.generate_proposal_models)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.destroy)
        menu_bar.add_cascade(label="File", menu=file_menu)

        define_menu = tk.Menu(menu_bar, tearoff=False)
        define_menu.add_command(label="Materials", command=self.define_materials)
        define_menu.add_command(label="Sections", command=self.define_sections)
        define_menu.add_command(label="Nodes / Joints", command=self.define_nodes)
        define_menu.add_command(label="Frame Elements", command=self.define_frame_elements)
        define_menu.add_command(label="Truss Elements", command=self.define_truss_elements)
        define_menu.add_command(label="Generate Frame Model", command=self.define_generate_frame_model)
        define_menu.add_command(label="Nodal Loads", command=self.define_nodal_loads)
        define_menu.add_command(label="Thermal Loads", command=self.define_thermal_loads)
        define_menu.add_command(label="Support Settlements", command=self.define_support_settlements)
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
        for name in (
            "Geometry",
            "Model View",
            "Presentation Model View",
            "Deformed Shape",
            "Axial Force Diagram",
            "Shear Force Diagram",
            "Bending Moment Diagram",
            "Story Drift Profile",
            "Drift Ratio Profile",
            "Floor Displacement Profile",
        ):
            static_menu.add_command(label=name, command=lambda plot=name: self.select_plot_type(plot))
        modal_menu = tk.Menu(display_menu, tearoff=False)
        for name in ("Mode 1", "Mode 2", "Mode 3", "Mode 4", "Modal Frequencies", "Modal Periods"):
            modal_menu.add_command(label=name, command=lambda plot=name: self.select_plot_type(plot))
        display_menu.add_cascade(label="Static", menu=static_menu)
        display_menu.add_cascade(label="Modal", menu=modal_menu)
        menu_bar.add_cascade(label="Display", menu=display_menu)

        tables_menu = tk.Menu(menu_bar, tearoff=False)
        tables_menu.add_command(label="Nodal Displacements", command=self.show_nodal_displacements_table)
        tables_menu.add_command(label="Support Reactions", command=self.show_support_reactions_table)
        tables_menu.add_command(label="Member-End Forces", command=self.show_member_end_forces_table)
        tables_menu.add_separator()
        tables_menu.add_command(label="Story Drift Table", command=self.show_story_drift_table)
        tables_menu.add_command(label="Roof Displacement", command=self.show_roof_displacement_table)
        tables_menu.add_separator()
        tables_menu.add_command(label="Modal Frequencies", command=self.show_modal_frequencies_table)
        tables_menu.add_command(label="Modal Participation Factors", command=self.show_modal_participation_table)
        tables_menu.add_separator()
        tables_menu.add_command(label="Export Current Table to CSV", command=self.export_current_table)
        menu_bar.add_cascade(label="Tables", menu=tables_menu)

        select_menu = tk.Menu(menu_bar, tearoff=False)
        select_menu.add_command(label="Clear Selection", command=self.clear_selection)
        select_menu.add_command(label="Select All Nodes", command=self.select_all_nodes)
        select_menu.add_command(label="Select All Elements", command=self.select_all_elements)
        select_menu.add_separator()
        select_menu.add_command(label="Selection Help", command=self.show_selection_help)
        menu_bar.add_cascade(label="Select", menu=select_menu)

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
        self._connect_selection_events()

        summary_frame = tk.Frame(body, width=260, padx=8, pady=8)
        body.add(summary_frame)

        tk.Label(summary_frame, text="Summary", font=("TkDefaultFont", 10, "bold")).pack(anchor=tk.W)
        self.summary_text = tk.Text(summary_frame, width=36, height=14, wrap=tk.WORD)
        self.summary_text.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.summary_text.configure(state=tk.DISABLED)

        tk.Label(summary_frame, text="Selection", font=("TkDefaultFont", 10, "bold")).pack(anchor=tk.W, pady=(8, 0))
        self.selection_text = tk.Text(summary_frame, width=36, height=14, wrap=tk.WORD)
        self.selection_text.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.selection_text.configure(state=tk.DISABLED)

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

    def open_generated_model(self) -> None:
        GENERATED_DIR.mkdir(parents=True, exist_ok=True)
        file_path = filedialog.askopenfilename(
            title="Open generated model",
            initialdir=str(GENERATED_DIR),
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not file_path:
            return

        path = Path(file_path)
        try:
            data = load_model_data(path)
            mass_mapping = _load_companion_masses(path)
        except Exception as exc:
            self._show_error("Failed to load generated model", exc)
            return

        self._set_loaded_model(path, data, source="generated", mass_mapping=mass_mapping)
        self.generated_model_name = path.stem
        self.plot_type.set("Model View")
        self._redraw_current_plot()
        self._update_summary(
            f"Loaded generated model: {path.name}\n"
            f"Nodes: {len(data.get('nodes', []))}\n"
            f"Elements: {len(data.get('elements', []))}\n"
            f"{self._generated_mass_message()}"
        )

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
        self.generated_model_name = None
        self.model_builder.load_from_structure_dict(data, mass_mapping)
        self.static_result = None
        self.modal_result = None
        self.current_table = None
        self.clear_selection(redraw=False)
        self._draw_empty_canvas()

    def new_model(self) -> None:
        self.model_builder.clear()
        self.plot_type.set("Model View")
        self._refresh_model_from_builder(source_label="New Form Model", redraw=True)
        self._update_summary("New form-based model created.\nUse Define menu items to add model data.")

    def new_assignment4_settlement_example(self) -> None:
        self._load_example_text_model("inputs/examples/a4_settlement_example.txt")

    def new_assignment4_thermal_example(self) -> None:
        self._load_example_text_model("inputs/examples/a4_thermal_example.txt")

    def generate_proposal_models(self) -> None:
        try:
            paths = generate_proposal_default_models()
        except OSError as exc:
            self._show_error("Proposal model generation failed", exc)
            return

        messagebox.showinfo(
            "Proposal models generated",
            "Generated proposal models:\n" + "\n".join(str(path) for path in paths),
        )

    def _load_generated_frame_model(
        self,
        data: dict[str, Any],
        mass_mapping: dict[int, dict[str, float]] | None,
        model_name: str,
        path: Path | None,
    ) -> None:
        self._set_loaded_model(path, data, source="generated", mass_mapping=mass_mapping)
        self.generated_model_name = model_name
        self.plot_type.set("Model View")
        self._redraw_current_plot()
        self._update_summary(
            f"Generated frame model loaded: {model_name}\n"
            f"Nodes: {len(data.get('nodes', []))}\n"
            f"Elements: {len(data.get('elements', []))}\n"
            f"{self._generated_mass_message()}\n\n"
            "Run static or modal analysis to view results."
        )

    def _load_example_text_model(self, relative_path: str) -> None:
        path = Path(__file__).resolve().parents[2] / relative_path
        try:
            data, mass_mapping = load_text_model(path)
            text = path.read_text(encoding="utf-8")
        except Exception as exc:
            self._show_error("Failed to load example model", exc)
            return

        self.text_model_path = path
        self._set_loaded_model(path, data, source="text", mass_mapping=mass_mapping)
        self._open_text_editor(text)
        self._update_summary(f"Loaded example text model: {path.name}\nRun static analysis to view results.")

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
            self.current_table = None
            if (
                self.plot_type.get() not in STATIC_PLOT_TYPES
                and self.plot_type.get() not in MODEL_VIEW_TYPES
                and self.plot_type.get() not in DRIFT_PLOT_TYPES
            ):
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
            self.current_table = None
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
            self._refresh_model_from_builder(redraw=False)
        return True

    def _refresh_model_from_builder(self, *, source_label: str = "Form Model", redraw: bool = True) -> None:
        """Synchronize GUI model state from records entered through Define dialogs."""
        data = self.model_builder.to_structure_dict()
        masses = self.model_builder.to_mass_mapping()
        previous_data = self.model_data
        previous_masses = self.text_mass_mapping or {}
        data_changed = data != previous_data
        masses_changed = masses != previous_masses

        self.loaded_path = None
        self.model_data = data
        self.text_mass_mapping = masses if masses else None
        self.input_source = "form"
        self.generated_model_name = source_label

        if data_changed:
            self.static_result = None
            self.modal_result = None
            self.current_table = None
            self.clear_selection(redraw=False)
        elif masses_changed:
            self.modal_result = None
            self.current_table = None

        self._apply_analysis_options_to_controls()
        if redraw and self.plot_type.get() in MODEL_VIEW_TYPES:
            self._redraw_current_plot()
        self._update_summary()

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
        if plot_name in MODEL_VIEW_TYPES:
            if not self._sync_model_source_if_needed():
                return
            if self._current_model_view_data() is None:
                messagebox.showerror("No model loaded", "Load or define a model before selecting Model View.")
                self.plot_type.set("Geometry")
                return
        if plot_name in STATIC_PLOT_TYPES and self.static_result is None:
            messagebox.showerror("No static results", "Run static analysis before selecting a static result plot.")
            self.plot_type.set("Geometry")
            return
        if plot_name in DRIFT_PLOT_TYPES and self.static_result is None:
            messagebox.showerror("No static results", "Run static analysis before opening drift results.")
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
        if plot_name in MODEL_VIEW_TYPES:
            model_view_data = self._current_model_view_data()
            if model_view_data is None:
                return
            options: dict[str, Any] = {"mass_mapping": self.text_mass_mapping or {}}
            if plot_name == "Presentation Model View":
                options.update({"show_axes": False, "show_grid": False, "show_legend": True})
            plot_model_view(model_view_data, ax=self.ax, options=options)
        elif plot_name in STATIC_PLOT_TYPES:
            if self.static_result is None:
                return
            plot_func = _static_plot_function(plot_name)
            kwargs: dict[str, Any] = {"ax": self.ax}
            if plot_name != "Geometry":
                kwargs["scale"] = self._static_plot_scale(plot_name)
            plot_func(self.static_result, **kwargs)
        elif plot_name in DRIFT_PLOT_TYPES:
            if self.static_result is None:
                return
            self._draw_drift_plot(plot_name)
        elif plot_name in MODAL_PLOT_TYPES:
            if self.modal_result is None:
                return
            self._draw_modal_plot(plot_name)
        else:
            raise ValueError(f"Unknown plot type: {plot_name}")

        self.figure.tight_layout()
        self._draw_selection_highlights()
        if self.canvas is not None:
            self.canvas.draw_idle()

    def _current_model_view_data(self) -> dict[str, Any] | None:
        if self.model_data is not None:
            return self.model_data
        if self.static_result is not None:
            return self.static_result
        if self.modal_result is not None and self.modal_result.get("nodes") and self.modal_result.get("elements"):
            return self.modal_result

        fallback = self.model_builder.to_structure_dict()
        if fallback.get("nodes") or fallback.get("elements"):
            return fallback
        return None

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

    def _draw_drift_plot(self, plot_name: str) -> None:
        if self.static_result is None:
            return
        if plot_name == "Story Drift Profile":
            plot_story_drift_profile(self._current_story_drift(), ax=self.ax)
        elif plot_name == "Drift Ratio Profile":
            plot_drift_ratio_profile(self._current_story_drift(), ax=self.ax)
        elif plot_name == "Floor Displacement Profile":
            plot_floor_displacement_profile(self._current_floor_displacements(), ax=self.ax)
        else:
            raise ValueError(f"Unknown drift plot type: {plot_name}")

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
        self._draw_selection_highlights()
        if self.canvas is not None:
            self.canvas.draw_idle()

    def _update_summary(self, message: str | None = None) -> None:
        if self.summary_text is None:
            return

        if message is not None:
            summary = message
        else:
            loaded_name = self.loaded_path.name if self.loaded_path is not None else "(unknown)"
            if self.loaded_path is None and self.generated_model_name:
                loaded_name = self.generated_model_name
            lines = [f"Loaded file: {loaded_name}", f"Current plot: {self.plot_type.get()}"]

            if self.static_result is not None:
                max_disp = max(abs(value) for value in self.static_result["displacement_vector"])
                lines.extend(
                    [
                        "",
                        "Static analysis: run",
                        f"Nodes: {len(self.static_result['nodes'])}",
                        f"Elements: {len(self.static_result['elements'])}",
                        f"Thermal load records: {self._thermal_load_count()}",
                        f"Support settlement records: {self._settlement_count()}",
                        f"Thermal/settlement included: {'yes' if self._thermal_load_count() or self._settlement_count() else 'no'}",
                        f"Max |displacement|: {max_disp:.6e}",
                        f"Support reaction records: {len(self.static_result['reactions'])}",
                        f"Member-force records: {len(self.static_result['member_end_forces'])}",
                    ]
                )
                lines.extend(self._drift_summary_lines())
            else:
                lines.extend(["", "Static analysis: not run"])
                if self.model_data is not None:
                    nodes = self.model_data.get("nodes", [])
                    elements = self.model_data.get("elements", [])
                    lines.extend(
                        [
                            f"Nodes: {len(nodes)}",
                            f"Elements: {len(elements)}",
                            f"Thermal load records: {self._thermal_load_count()}",
                            f"Support settlement records: {self._settlement_count()}",
                        ]
                    )
                    lines.extend(self._model_view_validation_lines())

            if self.modal_result is not None:
                lines.extend(self._modal_summary_lines())
            else:
                lines.extend(["", "Modal analysis: not run"])
                lines.append(self._pre_modal_mass_message())

            summary = "\n".join(lines)

        self.summary_text.configure(state=tk.NORMAL)
        self.summary_text.delete("1.0", tk.END)
        self.summary_text.insert(tk.END, summary)
        self.summary_text.configure(state=tk.DISABLED)
        self._update_selection_panel()

    def _show_error(self, title: str, exc: Exception) -> None:
        detail = "".join(traceback.format_exception_only(type(exc), exc)).strip()
        messagebox.showerror(title, detail)

    def _model_view_validation_lines(self) -> list[str]:
        if self.model_data is None:
            return []

        nodes = self.model_data.get("nodes", [])
        elements = self.model_data.get("elements", [])
        if not nodes:
            return ["Model View notice: no nodes defined."]

        lines: list[str] = []
        if not elements:
            lines.append("Model View notice: no elements defined yet.")

        node_ids = {int(node["id"]) for node in nodes}
        material_ids = {str(material["id"]) for material in self.model_data.get("materials", [])}
        section_ids = {str(section["id"]) for section in self.model_data.get("sections", [])}
        missing_node_refs = [
            int(element["id"])
            for element in elements
            if int(element.get("node_i", -1)) not in node_ids or int(element.get("node_j", -1)) not in node_ids
        ]
        missing_material_refs = [
            int(element["id"])
            for element in elements
            if str(element.get("material", "")) not in material_ids
        ]
        missing_section_refs = [
            int(element["id"])
            for element in elements
            if str(element.get("section", "")) not in section_ids
        ]

        if missing_node_refs:
            lines.append(f"Model View notice: missing node references in element(s) {_format_ids(missing_node_refs)}.")
        if missing_material_refs:
            lines.append(f"Model View notice: missing material references in element(s) {_format_ids(missing_material_refs)}.")
        if missing_section_refs:
            lines.append(f"Model View notice: missing section references in element(s) {_format_ids(missing_section_refs)}.")
        return lines

    def _current_floor_displacements(self) -> dict[str, Any]:
        self._validate_drift_ready()
        return compute_floor_displacements(self.static_result, direction="ux", method="mean")

    def _current_story_drift(self) -> dict[str, Any]:
        self._validate_drift_ready()
        drift = compute_story_drift(self.static_result, direction="ux", method="mean")
        if not drift.get("stories"):
            raise ValueError("At least two floor levels are required for story drift results.")
        return drift

    def _current_roof_displacement(self) -> dict[str, Any]:
        self._validate_drift_ready()
        return compute_roof_displacement(self.static_result, direction="ux", method="max_abs")

    def _validate_drift_ready(self) -> None:
        if self.static_result is None:
            raise ValueError("Run static analysis before opening drift results.")
        if not self.static_result.get("nodes"):
            raise ValueError("No node coordinates are available for drift results.")
        if not self.static_result.get("displacements"):
            raise ValueError("No displacement data are available for drift results.")

    def _drift_summary_lines(self) -> list[str]:
        if self.static_result is None or self.plot_type.get() not in DRIFT_PLOT_TYPES:
            return []
        try:
            drift = self._current_story_drift()
            roof = self._current_roof_displacement()
        except Exception as exc:
            return ["", f"Drift summary unavailable: {exc}"]

        max_story = max(drift["stories"], key=lambda story: story["abs_story_drift"])
        max_ratio = max(drift["stories"], key=lambda story: story["abs_drift_ratio"])
        return [
            "",
            "Drift summary:",
            f"Max |story drift|: {max_story['abs_story_drift']:.6e} (Story {max_story['story']})",
            f"Max |drift ratio|: {max_ratio['abs_drift_ratio']:.6e} (Story {max_ratio['story']})",
            f"Roof ux: {roof['roof_displacement']:.6e}",
        ]

    def _connect_selection_events(self) -> None:
        if self.canvas is None:
            return
        self.canvas.mpl_connect("button_press_event", self._on_canvas_press)
        self.canvas.mpl_connect("motion_notify_event", self._on_canvas_motion)
        self.canvas.mpl_connect("button_release_event", self._on_canvas_release)

    def _on_canvas_press(self, event: Any) -> None:
        if not self._selection_supported_plot():
            return
        if event.inaxes != self.ax or event.xdata is None or event.ydata is None or event.button != 1:
            return
        self._selection_drag_start = (float(event.xdata), float(event.ydata))
        self._selection_drag_start_pixel = (float(event.x), float(event.y))
        self._remove_selection_rectangle()

    def _on_canvas_motion(self, event: Any) -> None:
        if self._selection_drag_start is None or event.inaxes != self.ax or event.xdata is None or event.ydata is None:
            return
        if self._selection_drag_start_pixel is None:
            return
        if abs(float(event.x) - self._selection_drag_start_pixel[0]) < 3 and abs(float(event.y) - self._selection_drag_start_pixel[1]) < 3:
            return

        x0, y0 = self._selection_drag_start
        x1, y1 = float(event.xdata), float(event.ydata)
        crossing = x1 < x0
        edge = "tab:green" if crossing else "tab:blue"
        face = "green" if crossing else "blue"
        self._remove_selection_rectangle(draw=False)
        self._selection_rect_artist = Rectangle(
            (min(x0, x1), min(y0, y1)),
            abs(x1 - x0),
            abs(y1 - y0),
            edgecolor=edge,
            facecolor=face,
            alpha=0.18,
            linewidth=1.5,
            linestyle="-",
            zorder=50,
        )
        self.ax.add_patch(self._selection_rect_artist)
        if self.canvas is not None:
            self.canvas.draw_idle()

    def _on_canvas_release(self, event: Any) -> None:
        if self._selection_drag_start is None:
            return

        start = self._selection_drag_start
        start_pixel = self._selection_drag_start_pixel
        self._selection_drag_start = None
        self._selection_drag_start_pixel = None
        self._remove_selection_rectangle(draw=False)

        if event.inaxes != self.ax or event.xdata is None or event.ydata is None:
            self._draw_selection_highlights()
            return

        end = (float(event.xdata), float(event.ydata))
        is_click = True
        if start_pixel is not None:
            is_click = abs(float(event.x) - start_pixel[0]) < 5 and abs(float(event.y) - start_pixel[1]) < 5

        if is_click:
            self._select_by_click(end)
        else:
            self._select_by_rectangle(start, end)

    def _select_by_click(self, point: tuple[float, float]) -> None:
        nodes, elements = self._selection_geometry()
        tolerance = self._selection_tolerance()
        node_id = pick_node(nodes, point, tolerance)
        if node_id is not None:
            self.selected_nodes = {node_id}
            self.selected_elements.clear()
        else:
            element_id = pick_element(elements, nodes, point, tolerance)
            self.selected_elements = {element_id} if element_id is not None else set()
            self.selected_nodes.clear()
        self._draw_selection_highlights()

    def _select_by_rectangle(self, start: tuple[float, float], end: tuple[float, float]) -> None:
        nodes, elements = self._selection_geometry()
        rect = (start[0], start[1], end[0], end[1])
        crossing = end[0] < start[0]
        self.selected_nodes = select_nodes_in_rectangle(nodes, rect)
        self.selected_elements = select_elements_in_rectangle(elements, nodes, rect, crossing=crossing)
        self._draw_selection_highlights()

    def clear_selection(self, redraw: bool = True) -> None:
        self.selected_nodes.clear()
        self.selected_elements.clear()
        self._remove_selection_rectangle(draw=False)
        if redraw:
            self._draw_selection_highlights()
        else:
            self._clear_selection_artists()
            self._update_selection_panel()

    def select_all_nodes(self) -> None:
        nodes, _elements = self._selection_geometry()
        self.selected_nodes = set(nodes)
        self.selected_elements.clear()
        self._draw_selection_highlights()

    def select_all_elements(self) -> None:
        _nodes, elements = self._selection_geometry()
        self.selected_nodes.clear()
        self.selected_elements = set(elements)
        self._draw_selection_highlights()

    def show_selection_help(self) -> None:
        messagebox.showinfo(
            "Selection Help",
            "Click near a node or element to select it.\n\n"
            "Drag left-to-right for blue window selection: elements require both end nodes inside.\n"
            "Drag right-to-left for green crossing selection: elements are selected if they intersect the rectangle.\n\n"
            "Selection highlights are display-only and do not modify the structural model. They are shown on "
            "geometry-shaped views, not modal frequency/period bar charts.",
        )

    def _draw_selection_highlights(self) -> None:
        self._clear_selection_artists()
        if not self._selection_supported_plot():
            self._update_selection_panel()
            if self.canvas is not None:
                self.canvas.draw_idle()
            return

        nodes, elements = self._selection_geometry()

        for element_id in sorted(self.selected_elements):
            element = elements.get(element_id)
            if not element:
                continue
            node_i = nodes.get(int(element["node_i"]))
            node_j = nodes.get(int(element["node_j"]))
            if not node_i or not node_j:
                continue
            artist = self.ax.plot(
                [node_i["x"], node_j["x"]],
                [node_i["y"], node_j["y"]],
                color="tab:red",
                linewidth=4.0,
                solid_capstyle="round",
                zorder=60,
            )[0]
            self._selection_artists.append(artist)

        selected_xy = [
            (nodes[node_id]["x"], nodes[node_id]["y"])
            for node_id in sorted(self.selected_nodes)
            if node_id in nodes
        ]
        if selected_xy:
            xs, ys = zip(*selected_xy)
            artist = self.ax.scatter(
                xs,
                ys,
                s=95,
                facecolors="none",
                edgecolors="tab:red",
                linewidths=2.2,
                zorder=70,
            )
            self._selection_artists.append(artist)

        self._update_selection_panel()
        if self.canvas is not None:
            self.canvas.draw_idle()

    def _clear_selection_artists(self) -> None:
        for artist in self._selection_artists:
            try:
                artist.remove()
            except ValueError:
                pass
        self._selection_artists = []

    def _remove_selection_rectangle(self, draw: bool = True) -> None:
        if self._selection_rect_artist is not None:
            try:
                self._selection_rect_artist.remove()
            except ValueError:
                pass
        self._selection_rect_artist = None
        if draw and self.canvas is not None:
            self.canvas.draw_idle()

    def _selection_tolerance(self) -> float:
        x0, x1 = self.ax.get_xlim()
        y0, y1 = self.ax.get_ylim()
        span = max(abs(x1 - x0), abs(y1 - y0), 1.0)
        return span * 0.025

    def _selection_geometry(self) -> tuple[dict[int, dict[str, float]], dict[int, dict[str, Any]]]:
        if self.static_result is not None:
            return self.static_result.get("nodes", {}), self.static_result.get("elements", {})
        if self.modal_result is not None and self.modal_result.get("nodes") and self.modal_result.get("elements"):
            return self.modal_result.get("nodes", {}), self.modal_result.get("elements", {})
        if self.model_data is None:
            return {}, {}

        nodes = {
            int(node["id"]): {"x": float(node["x"]), "y": float(node["y"])}
            for node in self.model_data.get("nodes", [])
        }
        elements = {
            int(element["id"]): {
                "type": str(element.get("type", "")),
                "node_i": int(element["node_i"]),
                "node_j": int(element["node_j"]),
            }
            for element in self.model_data.get("elements", [])
        }
        return nodes, elements

    def _selection_supported_plot(self) -> bool:
        return self.plot_type.get() not in {"Modal Frequencies", "Modal Periods"} | DRIFT_PLOT_TYPES

    def _update_selection_panel(self) -> None:
        if self.selection_text is None:
            return
        lines = self._selection_info_lines()
        self.selection_text.configure(state=tk.NORMAL)
        self.selection_text.delete("1.0", tk.END)
        self.selection_text.insert(tk.END, "\n".join(lines))
        self.selection_text.configure(state=tk.DISABLED)

    def _selection_info_lines(self) -> list[str]:
        if not self.selected_nodes and not self.selected_elements:
            return [
                "No selection.",
                "",
                "Click nodes/elements or drag a selection box.",
                "Left-to-right: window.",
                "Right-to-left: crossing.",
            ]
        if len(self.selected_nodes) + len(self.selected_elements) > 1:
            return [
                f"Selected nodes: {len(self.selected_nodes)}",
                _compact_id_line("Node IDs", self.selected_nodes),
                f"Selected elements: {len(self.selected_elements)}",
                _compact_id_line("Element IDs", self.selected_elements),
            ]
        if self.selected_nodes:
            return self._selected_node_lines(next(iter(self.selected_nodes)))
        return self._selected_element_lines(next(iter(self.selected_elements)))

    def _selected_node_lines(self, node_id: int) -> list[str]:
        node = self._model_node(node_id)
        geometry_nodes, _elements = self._selection_geometry()
        coord = geometry_nodes.get(node_id, {})
        lines = [
            f"Node {node_id}",
            f"x: {float(coord.get('x', node.get('x', 0.0))):.6g}",
            f"y: {float(coord.get('y', node.get('y', 0.0))):.6g}",
        ]
        restraints = node.get("restraints", {})
        if restraints:
            lines.append(
                "restraints: "
                + ", ".join(f"{dof}={'FIX' if restraints.get(dof) else 'FREE'}" for dof in ("ux", "uy", "rz"))
            )
        if node.get("prescribed_displacements"):
            lines.append(f"prescribed: {node['prescribed_displacements']}")

        nodal_load = self._nodal_load(node_id)
        if nodal_load:
            lines.append(f"nodal load: Fx={nodal_load.get('fx', 0.0):.6e}, Fy={nodal_load.get('fy', 0.0):.6e}, Mz={nodal_load.get('mz', 0.0):.6e}")

        if self.static_result is not None:
            disp = self.static_result.get("displacements", {}).get(node_id)
            if disp:
                lines.append(f"disp: ux={disp.get('ux', 0.0):.6e}, uy={disp.get('uy', 0.0):.6e}, rz={disp.get('rz', 0.0):.6e}")
            reaction = self.static_result.get("reactions", {}).get(node_id)
            if reaction:
                lines.append(f"reaction: Rx={reaction.get('rx', 0.0):.6e}, Ry={reaction.get('ry', 0.0):.6e}, Mz={reaction.get('mz', 0.0):.6e}")
        return lines

    def _selected_element_lines(self, element_id: int) -> list[str]:
        element = self._model_element(element_id)
        lines = [
            f"Element {element_id}",
            f"type: {element.get('type', '')}",
            f"node_i: {element.get('node_i', '')}",
            f"node_j: {element.get('node_j', '')}",
            f"material: {element.get('material', '')}",
            f"section: {element.get('section', '')}",
        ]
        if element.get("member_loads"):
            lines.append(f"member loads: {element['member_loads']}")

        if self.static_result is not None:
            forces = self.static_result.get("member_end_forces", {}).get(element_id)
            if forces:
                i_end = forces.get("node_i", {})
                j_end = forces.get("node_j", {})
                lines.extend(
                    [
                        "member-end forces:",
                        f"  i: Nx={i_end.get('nx', 0.0):.6e}, Vy={i_end.get('vy', 0.0):.6e}, Mz={i_end.get('mz', 0.0):.6e}",
                        f"  j: Nx={j_end.get('nx', 0.0):.6e}, Vy={j_end.get('vy', 0.0):.6e}, Mz={j_end.get('mz', 0.0):.6e}",
                    ]
                )
        return lines

    def _model_node(self, node_id: int) -> dict[str, Any]:
        if self.model_data is None:
            return {}
        for node in self.model_data.get("nodes", []):
            if int(node.get("id")) == int(node_id):
                return node
        return {}

    def _model_element(self, element_id: int) -> dict[str, Any]:
        if self.model_data is None:
            return {}
        for element in self.model_data.get("elements", []):
            if int(element.get("id")) == int(element_id):
                return element
        return {}

    def _nodal_load(self, node_id: int) -> dict[str, Any] | None:
        if self.model_data is None:
            return None
        for load in self.model_data.get("nodal_loads", []):
            if int(load.get("node")) == int(node_id):
                return load
        return None

    def show_nodal_displacements_table(self) -> None:
        if self.static_result is None:
            messagebox.showerror("No static results", "Run static analysis before opening displacement results.")
            return
        headers, rows = format_nodal_displacement_rows(self.static_result)
        self._open_result_table("Nodal Displacements", headers, rows)

    def show_support_reactions_table(self) -> None:
        if self.static_result is None:
            messagebox.showerror("No static results", "Run static analysis before opening support reaction results.")
            return
        headers, rows = format_reaction_rows(self.static_result)
        self._open_result_table("Support Reactions", headers, rows)

    def show_member_end_forces_table(self) -> None:
        if self.static_result is None:
            messagebox.showerror("No static results", "Run static analysis before opening member-end force results.")
            return
        headers, rows = format_member_force_rows(self.static_result)
        self._open_result_table("Member-End Forces", headers, rows)

    def show_story_drift_table(self) -> None:
        if self.static_result is None:
            messagebox.showerror("No static results", "Run static analysis before opening drift results.")
            return
        try:
            self._current_story_drift()
            headers, rows = format_static_story_drift_rows(self.static_result)
        except Exception as exc:
            self._show_error("Story drift table failed", exc)
            return
        self._open_result_table("Story Drift Table", headers, rows)

    def show_roof_displacement_table(self) -> None:
        if self.static_result is None:
            messagebox.showerror("No static results", "Run static analysis before opening drift results.")
            return
        try:
            self._current_roof_displacement()
            headers, rows = format_static_roof_displacement_rows(self.static_result)
        except Exception as exc:
            self._show_error("Roof displacement table failed", exc)
            return
        self._open_result_table("Roof Displacement", headers, rows)

    def show_modal_frequencies_table(self) -> None:
        if self.modal_result is None:
            messagebox.showerror("No modal results", "Run modal analysis before opening modal result tables.")
            return
        headers, rows = format_modal_frequency_rows(self.modal_result)
        self._open_result_table("Modal Frequencies", headers, rows)

    def show_modal_participation_table(self) -> None:
        if self.modal_result is None:
            messagebox.showerror("No modal results", "Run modal analysis before opening modal result tables.")
            return
        headers, rows = format_modal_participation_rows(self.modal_result)
        if not rows:
            messagebox.showerror(
                "No modal participation data",
                "Modal participation data are not available for this model/result.",
            )
            return
        self._open_result_table("Modal Participation Factors", headers, rows)

    def export_current_table(self) -> None:
        if self.current_table is None:
            messagebox.showerror("No table", "No table is currently available for export.")
            return

        file_path = filedialog.asksaveasfilename(
            title="Export Current Table to CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not file_path:
            return

        try:
            write_table_csv(file_path, self.current_table["headers"], self.current_table["rows"])
        except OSError as exc:
            self._show_error("Failed to export table", exc)
            return

        messagebox.showinfo("Export complete", f"Exported {self.current_table['title']} to:\n{file_path}")

    def _open_result_table(self, title: str, headers: list[str], rows: list[list[str]]) -> None:
        self.current_table = {"title": title, "headers": headers, "rows": rows}
        open_table_window(self.root, title, headers, rows, export_command=self.export_current_table)

    def _modal_summary_lines(self) -> list[str]:
        if self.modal_result is None:
            return []

        mass_assumption = (
            self._active_mass_message()
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

    def _generated_mass_message(self) -> str:
        if self.text_mass_mapping:
            return "Generated floor masses assigned to ux DOFs."
        return "No generated mass mapping; using default mass field for modal analysis."

    def _pre_modal_mass_message(self) -> str:
        if self.input_source == "generated":
            return self._generated_mass_message()
        return "Mass assumption: default mass is assigned to free ux DOFs only."

    def _active_mass_message(self) -> str:
        if self.input_source == "generated":
            return "Mass assumption: generated floor masses assigned to ux DOFs."
        return "Mass assumption: using modal mass records from text/form model."

    def _thermal_load_count(self) -> int:
        if self.model_data is None:
            return 0
        return sum(len(element.get("member_loads", [])) for element in self.model_data.get("elements", []))

    def _settlement_count(self) -> int:
        if self.model_data is None:
            return 0
        return sum(
            1
            for node in self.model_data.get("nodes", [])
            if any(
                float(node.get("prescribed_displacements", {}).get(dof, 0.0)) != 0.0
                for dof in ("ux", "uy", "rz")
            )
        )

    def define_materials(self) -> None:
        self._ensure_form_source()
        open_materials_dialog(self.root, self.model_builder, on_change=self._refresh_model_from_builder)

    def define_sections(self) -> None:
        self._ensure_form_source()
        open_sections_dialog(self.root, self.model_builder, on_change=self._refresh_model_from_builder)

    def define_nodes(self) -> None:
        self._ensure_form_source()
        open_nodes_dialog(self.root, self.model_builder, on_change=self._refresh_model_from_builder)

    def define_frame_elements(self) -> None:
        self._ensure_form_source()
        open_frame_elements_dialog(self.root, self.model_builder, on_change=self._refresh_model_from_builder)

    def define_truss_elements(self) -> None:
        self._ensure_form_source()
        open_truss_elements_dialog(self.root, self.model_builder, on_change=self._refresh_model_from_builder)

    def define_generate_frame_model(self) -> None:
        open_frame_generator_dialog(self.root, self._load_generated_frame_model)

    def define_nodal_loads(self) -> None:
        self._ensure_form_source()
        open_nodal_loads_dialog(self.root, self.model_builder, on_change=self._refresh_model_from_builder)

    def define_thermal_loads(self) -> None:
        self._ensure_form_source()
        open_thermal_loads_dialog(self.root, self.model_builder, on_change=self._refresh_model_from_builder)

    def define_support_settlements(self) -> None:
        self._ensure_form_source()
        open_support_settlements_dialog(self.root, self.model_builder, on_change=self._refresh_model_from_builder)

    def define_modal_masses(self) -> None:
        self._ensure_form_source()
        open_modal_masses_dialog(self.root, self.model_builder, on_change=self._refresh_model_from_builder)

    def define_analysis_options(self) -> None:
        self._ensure_form_source()
        open_analysis_options_dialog(self.root, self.model_builder, on_apply=self._on_analysis_options_applied)

    def _on_analysis_options_applied(self) -> None:
        self._apply_analysis_options_to_controls()
        self._refresh_model_from_builder(redraw=True)

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
                    f"Thermal loads: {self._thermal_load_count()}",
                    f"Support settlements: {self._settlement_count()}",
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
            "load combinations, or full SAP2000-style tables. Selection highlights are available on "
            "geometry-shaped plots, not modal frequency/period bar charts.",
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


def _load_companion_masses(path: Path) -> dict[int, dict[str, float]] | None:
    mass_path = path.with_name(f"{path.stem}_masses.json")
    if not mass_path.exists():
        return None
    with mass_path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, dict):
        raise ValueError("Generated mass mapping JSON root must be an object.")
    return {
        int(node_id): {
            "ux": float(values.get("ux", 0.0)),
            "uy": float(values.get("uy", 0.0)),
            "rz": float(values.get("rz", 0.0)),
        }
        for node_id, values in raw.items()
    }


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


def _compact_id_line(label: str, ids: set[int]) -> str:
    values = ", ".join(str(item) for item in sorted(ids))
    if len(values) > 80:
        values = values[:77] + "..."
    return f"{label}: {values if values else '-'}"


def _format_ids(ids: list[int], limit: int = 8) -> str:
    values = sorted(set(int(item) for item in ids))
    text = ", ".join(str(item) for item in values[:limit])
    if len(values) > limit:
        text += ", ..."
    return text


def main() -> None:
    root = tk.Tk()
    StaticAnalysisApp(root)
    root.mainloop()
