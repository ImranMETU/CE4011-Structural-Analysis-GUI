"""Tkinter dialog for parametric frame-model generation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from generators.frame_generator import generate_floor_mass_mapping, generate_frame_model
from gui.runtime_paths import resource_root


PROJECT_ROOT = resource_root()
GENERATED_DIR = PROJECT_ROOT / "inputs" / "generated"

PROPOSAL_SPECS = [
    ("model_a_5story_unbraced", {"n_stories": 5, "n_bays": 1, "braced": False}),
    ("model_b_10story_unbraced", {"n_stories": 10, "n_bays": 2, "braced": False}),
    ("model_c_10story_braced", {"n_stories": 10, "n_bays": 2, "braced": True}),
]

DEFAULT_RAW_VALUES = {
    "model_name": "generated_frame_model",
    "n_stories": "5",
    "n_bays": "1",
    "story_height": "3.0",
    "bay_width": "6.0",
    "braced": False,
    "brace_pattern": "single_diagonal",
    "E_frame": "30000000000",
    "E_brace": "200000000000",
    "column_A": "0.25",
    "column_I": "0.00521",
    "beam_A": "0.32",
    "beam_I": "0.01707",
    "brace_A": "0.001",
    "lateral_load_per_floor": "10000.0",
    "floor_mass": "100000.0",
}


def open_frame_generator_dialog(
    parent: tk.Misc,
    on_generate_load: Callable[[dict[str, Any], dict[int, dict[str, float]] | None, str, Path | None], None],
) -> None:
    """Open the parametric frame generator dialog."""
    FrameGeneratorDialog(parent, on_generate_load)


class FrameGeneratorDialog:
    """Small SAP-like dialog for generated frame models."""

    def __init__(
        self,
        parent: tk.Misc,
        on_generate_load: Callable[[dict[str, Any], dict[int, dict[str, float]] | None, str, Path | None], None],
    ):
        self.parent = parent
        self.on_generate_load = on_generate_load
        self.window = tk.Toplevel(parent)
        self.window.title("Generate Frame Model")
        self.window.geometry("520x620")
        self.vars: dict[str, tk.Variable] = {}
        self._build()

    def _build(self) -> None:
        frame = ttk.Frame(self.window, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        fields = [
            ("Model name", "model_name"),
            ("Number of stories", "n_stories"),
            ("Number of bays", "n_bays"),
            ("Story height", "story_height"),
            ("Bay width", "bay_width"),
            ("Brace pattern", "brace_pattern"),
            ("Frame E", "E_frame"),
            ("Brace E", "E_brace"),
            ("Column area", "column_A"),
            ("Column I", "column_I"),
            ("Beam area", "beam_A"),
            ("Beam I", "beam_I"),
            ("Brace area", "brace_A"),
            ("Lateral load / floor", "lateral_load_per_floor"),
            ("Floor mass for modal", "floor_mass"),
        ]

        self.vars["braced"] = tk.BooleanVar(value=bool(DEFAULT_RAW_VALUES["braced"]))
        row = 0
        for label, key in fields:
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=3)
            var = tk.StringVar(value=str(DEFAULT_RAW_VALUES[key]))
            self.vars[key] = var
            ttk.Entry(frame, textvariable=var, width=28).grid(row=row, column=1, sticky="ew", pady=3)
            row += 1

        ttk.Checkbutton(frame, text="Braced", variable=self.vars["braced"]).grid(
            row=row, column=1, sticky="w", pady=5
        )
        row += 1

        frame.columnconfigure(1, weight=1)

        buttons = ttk.Frame(frame)
        buttons.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        ttk.Button(buttons, text="Generate and Load", command=self._generate_and_load).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(buttons, text="Save JSON", command=self._save_json).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(buttons, text="Generate Proposal Defaults", command=self._generate_defaults).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(buttons, text="Cancel", command=self.window.destroy).pack(side=tk.RIGHT)

    def _generate_and_load(self) -> None:
        try:
            data, masses, name = build_generated_model_from_raw(self._raw_values())
        except ValueError as exc:
            messagebox.showerror("Invalid frame generator input", str(exc))
            return

        self.on_generate_load(data, masses, name, None)
        self.window.destroy()

    def _save_json(self) -> None:
        try:
            data, masses, name = build_generated_model_from_raw(self._raw_values())
        except ValueError as exc:
            messagebox.showerror("Invalid frame generator input", str(exc))
            return

        GENERATED_DIR.mkdir(parents=True, exist_ok=True)
        file_path = filedialog.asksaveasfilename(
            title="Save generated frame model",
            initialdir=str(GENERATED_DIR),
            initialfile=f"{name}.json",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not file_path:
            return

        path = Path(file_path)
        try:
            save_generated_model(path, data, masses)
        except OSError as exc:
            messagebox.showerror("Save failed", str(exc))
            return

        messagebox.showinfo("Generated model saved", f"Saved model to:\n{path}")

    def _generate_defaults(self) -> None:
        try:
            paths = generate_proposal_default_models()
        except OSError as exc:
            messagebox.showerror("Generation failed", str(exc))
            return

        messagebox.showinfo(
            "Proposal models generated",
            "Generated proposal models:\n" + "\n".join(str(path) for path in paths),
        )

    def _raw_values(self) -> dict[str, Any]:
        return {key: var.get() for key, var in self.vars.items()}


def build_generated_model_from_raw(
    raw_values: dict[str, Any],
) -> tuple[dict[str, Any], dict[int, dict[str, float]] | None, str]:
    """Parse dialog values, generate model data, and optionally generate masses."""
    parsed = parse_frame_generator_options(raw_values)
    floor_mass = parsed.pop("floor_mass")
    name = parsed.pop("model_name")
    data = generate_frame_model(**parsed)
    masses = generate_floor_mass_mapping(data, floor_mass) if floor_mass and floor_mass > 0.0 else None
    return data, masses, name


def parse_frame_generator_options(raw_values: dict[str, Any]) -> dict[str, Any]:
    """Convert raw dialog values into validated generator kwargs."""
    name = str(raw_values.get("model_name", "")).strip()
    if not name:
        raise ValueError("Model name must not be empty.")

    n_stories = _positive_int(raw_values.get("n_stories"), "number of stories")
    n_bays = _positive_int(raw_values.get("n_bays"), "number of bays")
    braced = bool(raw_values.get("braced", False))
    brace_area = _positive_float(raw_values.get("brace_A"), "brace area")
    floor_mass = _nonnegative_float(raw_values.get("floor_mass"), "floor mass")

    if braced and brace_area <= 0.0:
        raise ValueError("Brace area must be positive for braced models.")

    return {
        "model_name": name,
        "n_stories": n_stories,
        "n_bays": n_bays,
        "story_height": _positive_float(raw_values.get("story_height"), "story height"),
        "bay_width": _positive_float(raw_values.get("bay_width"), "bay width"),
        "braced": braced,
        "brace_pattern": str(raw_values.get("brace_pattern", "single_diagonal")).strip() or "single_diagonal",
        "E_frame": _positive_float(raw_values.get("E_frame"), "frame elastic modulus"),
        "E_brace": _positive_float(raw_values.get("E_brace"), "brace elastic modulus"),
        "column_A": _positive_float(raw_values.get("column_A"), "column area"),
        "column_I": _positive_float(raw_values.get("column_I"), "column moment of inertia"),
        "beam_A": _positive_float(raw_values.get("beam_A"), "beam area"),
        "beam_I": _positive_float(raw_values.get("beam_I"), "beam moment of inertia"),
        "brace_A": brace_area,
        "lateral_load_per_floor": _float(raw_values.get("lateral_load_per_floor"), "lateral load per floor"),
        "floor_mass": floor_mass,
    }


def save_generated_model(
    path: Path,
    data: dict[str, Any],
    masses: dict[int, dict[str, float]] | None = None,
) -> list[Path]:
    """Save generated structural JSON and optional companion mass mapping."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    written = [path]
    if masses:
        mass_path = path.with_name(f"{path.stem}_masses.json")
        mass_path.write_text(json.dumps(masses, indent=2), encoding="utf-8")
        written.append(mass_path)
    return written


def generate_proposal_default_models(output_dir: Path | None = None) -> list[Path]:
    """Generate the three proposal default models and mass companions."""
    output_dir = GENERATED_DIR if output_dir is None else Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name, spec in PROPOSAL_SPECS:
        data = generate_frame_model(
            story_height=3.0,
            bay_width=6.0,
            lateral_load_per_floor=10000.0,
            **spec,
        )
        masses = generate_floor_mass_mapping(data, floor_mass=100000.0)
        written.extend(save_generated_model(output_dir / f"{name}.json", data, masses))
    return written


def _positive_int(value: Any, label: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a positive integer.") from exc
    if number <= 0:
        raise ValueError(f"{label} must be a positive integer.")
    return number


def _positive_float(value: Any, label: str) -> float:
    number = _float(value, label)
    if number <= 0.0:
        raise ValueError(f"{label} must be positive.")
    return number


def _nonnegative_float(value: Any, label: str) -> float:
    if value is None or str(value).strip() == "":
        return 0.0
    number = _float(value, label)
    if number < 0.0:
        raise ValueError(f"{label} must be zero or positive.")
    return number


def _float(value: Any, label: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric.") from exc
