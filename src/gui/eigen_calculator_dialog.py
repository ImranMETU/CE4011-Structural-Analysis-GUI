"""Standalone Tkinter eigenanalysis calculator dialog."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import numpy as np

from analysis.eigen_calculator import (
    compute_modal_properties,
    format_eigenvalue_table,
    format_eigenvector_table,
    format_modal_property_table,
    solve_generalized_eigen,
    write_eigen_results_csv,
)
from analysis.rayleigh_damping import (
    format_rayleigh_table,
    rayleigh_coefficients,
    rayleigh_damping_ratios,
)


NORMALIZATION_OPTIONS = ("max_abs", "mass", "last_dof_positive")


def open_eigen_calculator_dialog(parent: tk.Misc) -> "EigenanalysisCalculatorDialog":
    """Open the standalone matrix eigenanalysis calculator."""
    return EigenanalysisCalculatorDialog(parent)


class EigenanalysisCalculatorDialog:
    """User-friendly matrix-based generalized eigenanalysis calculator."""

    def __init__(self, parent: tk.Misc):
        self.parent = parent
        self.window = tk.Toplevel(parent)
        self.window.title("Eigenanalysis Calculator")
        self.window.geometry("1040x720")
        self.window.minsize(860, 560)

        self.size_var = tk.IntVar(value=2)
        self.normalization_var = tk.StringVar(value="max_abs")
        self.use_damping_var = tk.BooleanVar(value=False)
        self.use_influence_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="Create matrices or load an example.")
        self.rayleigh_mode_i_var = tk.IntVar(value=1)
        self.rayleigh_mode_j_var = tk.IntVar(value=2)
        self.rayleigh_xi_i_var = tk.StringVar(value="0.05")
        self.rayleigh_xi_j_var = tk.StringVar(value="0.05")
        self.rayleigh_output_var = tk.StringVar(value="Solve eigenanalysis, then compute Rayleigh damping.")

        self.matrix_entries: dict[str, list[list[tk.Entry]]] = {}
        self.vector_entries: dict[str, list[tk.Entry]] = {}
        self.result: dict[str, Any] | None = None
        self.trees: dict[str, ttk.Treeview] = {}

        self._build_widgets()
        self.create_matrices()

    def _build_widgets(self) -> None:
        top = ttk.Frame(self.window, padding=8)
        top.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(top, text="DOFs:").pack(side=tk.LEFT)
        ttk.Spinbox(top, from_=1, to=12, textvariable=self.size_var, width=5).pack(side=tk.LEFT, padx=(4, 8))
        ttk.Button(top, text="Create Matrices", command=self.create_matrices).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(top, text="Normalize:").pack(side=tk.LEFT)
        ttk.Combobox(
            top,
            values=NORMALIZATION_OPTIONS,
            textvariable=self.normalization_var,
            state="readonly",
            width=18,
        ).pack(side=tk.LEFT, padx=(4, 10))

        ttk.Checkbutton(top, text="Use damping matrix C", variable=self.use_damping_var, command=self.create_matrices).pack(
            side=tk.LEFT,
            padx=(0, 8),
        )
        ttk.Checkbutton(top, text="Use influence vector r", variable=self.use_influence_var, command=self.create_matrices).pack(
            side=tk.LEFT,
            padx=(0, 8),
        )
        ttk.Button(top, text="Load Example 2DOF", command=self.load_example_2dof).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(top, text="Load Example 3DOF Shear Building", command=self.load_example_3dof).pack(side=tk.LEFT)

        self.matrix_area = ttk.Frame(self.window, padding=(8, 0, 8, 8))
        self.matrix_area.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        button_row = ttk.Frame(self.window, padding=(8, 0, 8, 6))
        button_row.pack(side=tk.TOP, fill=tk.X)
        ttk.Button(button_row, text="Solve", command=self.solve).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(button_row, text="Clear", command=self.clear_values).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(button_row, text="Export Results CSV", command=self.export_csv).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(button_row, text="Close", command=self.window.destroy).pack(side=tk.RIGHT)

        ttk.Label(self.window, textvariable=self.status_var, padding=(8, 0, 8, 4)).pack(side=tk.TOP, anchor=tk.W)

        self.notebook = ttk.Notebook(self.window)
        self.notebook.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        for name in ("Frequencies", "Modal Properties", "Eigenvectors"):
            frame = ttk.Frame(self.notebook, padding=4)
            self.notebook.add(frame, text=name)
            self.trees[name] = self._make_tree(frame)
        rayleigh_frame = ttk.Frame(self.notebook, padding=4)
        self.notebook.add(rayleigh_frame, text="Rayleigh Damping")
        self._build_rayleigh_tab(rayleigh_frame)

    def create_matrices(self) -> None:
        n = self._matrix_size()
        for child in self.matrix_area.winfo_children():
            child.destroy()
        self.matrix_entries = {}
        self.vector_entries = {}
        self.result = None

        if n > 6:
            ttk.Label(
                self.matrix_area,
                text="Warning: matrix entry may be cumbersome for more than 6 DOFs.",
                foreground="#B35C00",
            ).pack(side=tk.TOP, anchor=tk.W, pady=(0, 4))

        content = ttk.Frame(self.matrix_area)
        content.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        matrices = ["K", "M"]
        if self.use_damping_var.get():
            matrices.append("C")
        for name in matrices:
            frame = ttk.LabelFrame(content, text=f"{name} matrix", padding=4)
            frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))
            self.matrix_entries[name] = self._create_matrix_grid(frame, n)

        if self.use_influence_var.get():
            frame = ttk.LabelFrame(content, text="Influence vector r", padding=4)
            frame.pack(side=tk.LEFT, fill=tk.Y)
            self.vector_entries["r"] = self._create_vector_grid(frame, n)

        self._clear_result_tables()
        self.status_var.set(f"Matrix size set to {n} DOF.")

    def solve(self) -> None:
        try:
            k = self._read_matrix("K")
            m = self._read_matrix("M")
            c = self._read_matrix("C") if self.use_damping_var.get() else None
            r = self._read_vector("r") if self.use_influence_var.get() else None

            result = solve_generalized_eigen(k, m, normalize=self.normalization_var.get())
            props = compute_modal_properties(k, m, C=c, modes=result["modes"], influence_vector=r)
            result.update(props)
            self.result = result
            self._populate_result_tables(result)
            self._clear_rayleigh_result()

            message = f"Solved {len(result['eigenvalues'])} positive mode(s)."
            if c is not None:
                message += " Damping ratios use modal-compatible damping diagnostics."
            if result.get("warnings"):
                message += " " + " ".join(result["warnings"])
            self.status_var.set(message)
        except Exception as exc:
            messagebox.showerror("Eigenanalysis failed", str(exc))

    def clear_values(self) -> None:
        for rows in self.matrix_entries.values():
            for row in rows:
                for entry in row:
                    entry.delete(0, tk.END)
        for entries in self.vector_entries.values():
            for entry in entries:
                entry.delete(0, tk.END)
        self.result = None
        self._clear_result_tables()
        self.status_var.set("Input values cleared.")

    def export_csv(self) -> None:
        if self.result is None:
            messagebox.showerror("No results", "Solve the eigenanalysis problem before exporting.")
            return
        path = filedialog.asksaveasfilename(
            parent=self.window,
            title="Export eigenanalysis results",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            write_eigen_results_csv(Path(path), self.result)
        except OSError as exc:
            messagebox.showerror("Export failed", str(exc))
            return
        messagebox.showinfo("Export complete", f"Eigenanalysis results exported to:\n{path}")

    def load_example_2dof(self) -> None:
        self.size_var.set(2)
        self.use_damping_var.set(False)
        self.use_influence_var.set(True)
        self.create_matrices()
        self._set_matrix("K", [[3.0, -1.0], [-1.0, 1.0]])
        self._set_matrix("M", [[2.0, 0.0], [0.0, 1.0]])
        self._set_vector("r", [1.0, 1.0])
        self.status_var.set("Loaded stable 2DOF example.")

    def load_example_3dof(self) -> None:
        self.size_var.set(3)
        self.use_damping_var.set(False)
        self.use_influence_var.set(True)
        self.create_matrices()
        self._set_matrix(
            "K",
            1.0e5 * np.array([[2.0, -1.0, 0.0], [-1.0, 2.0, -1.0], [0.0, -1.0, 1.0]]),
        )
        self._set_matrix("M", np.diag([200.0, 200.0, 100.0]))
        self._set_vector("r", [1.0, 1.0, 1.0])
        self.status_var.set("Loaded 3DOF shear-building example.")

    def compute_rayleigh_damping(self) -> None:
        if self.result is None:
            messagebox.showerror("No eigenanalysis results", "Solve the eigenanalysis problem before computing Rayleigh damping.")
            return
        try:
            mode_i = int(self.rayleigh_mode_i_var.get())
            mode_j = int(self.rayleigh_mode_j_var.get())
            xi_i = float(self.rayleigh_xi_i_var.get())
            xi_j = float(self.rayleigh_xi_j_var.get())
            self._compute_rayleigh_for_omegas(
                self.result["omega_rad_per_s"],
                self.result["frequency_Hz"],
                self.result["period_s"],
                mode_i,
                xi_i,
                mode_j,
                xi_j,
            )
        except Exception as exc:
            messagebox.showerror("Rayleigh damping failed", str(exc))

    def load_ce586_rayleigh_check(self) -> None:
        omegas = np.array([11.57, 31.62, 43.20], dtype=float)
        frequencies = omegas / (2.0 * np.pi)
        periods = 2.0 * np.pi / omegas
        self.rayleigh_mode_i_var.set(1)
        self.rayleigh_mode_j_var.set(2)
        self.rayleigh_xi_i_var.set("0.05")
        self.rayleigh_xi_j_var.set("0.05")
        self._compute_rayleigh_for_omegas(omegas, frequencies, periods, 1, 0.05, 2, 0.05)
        self.status_var.set("Loaded CE586 Example 6.1 Rayleigh check.")

    def _create_matrix_grid(self, parent: ttk.Frame, n: int) -> list[list[tk.Entry]]:
        rows: list[list[tk.Entry]] = []
        for i in range(n):
            row = []
            for j in range(n):
                entry = tk.Entry(parent, width=10, justify=tk.RIGHT)
                entry.grid(row=i, column=j, padx=1, pady=1)
                entry.insert(0, "0" if i != j else "1")
                row.append(entry)
            rows.append(row)
        return rows

    def _create_vector_grid(self, parent: ttk.Frame, n: int) -> list[tk.Entry]:
        entries = []
        for i in range(n):
            entry = tk.Entry(parent, width=10, justify=tk.RIGHT)
            entry.grid(row=i, column=0, padx=1, pady=1)
            entry.insert(0, "1")
            entries.append(entry)
        return entries

    def _make_tree(self, parent: ttk.Frame) -> ttk.Treeview:
        tree = ttk.Treeview(parent, show="headings")
        y_scroll = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=tree.yview)
        x_scroll = ttk.Scrollbar(parent, orient=tk.HORIZONTAL, command=tree.xview)
        tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)
        return tree

    def _build_rayleigh_tab(self, parent: ttk.Frame) -> None:
        controls = ttk.Frame(parent)
        controls.pack(side=tk.TOP, fill=tk.X, pady=(0, 6))
        ttk.Label(controls, text="Target mode i:").pack(side=tk.LEFT)
        ttk.Spinbox(controls, from_=1, to=99, textvariable=self.rayleigh_mode_i_var, width=5).pack(side=tk.LEFT, padx=(4, 8))
        ttk.Label(controls, text="xi_i:").pack(side=tk.LEFT)
        ttk.Entry(controls, textvariable=self.rayleigh_xi_i_var, width=8).pack(side=tk.LEFT, padx=(4, 12))
        ttk.Label(controls, text="Target mode j:").pack(side=tk.LEFT)
        ttk.Spinbox(controls, from_=1, to=99, textvariable=self.rayleigh_mode_j_var, width=5).pack(side=tk.LEFT, padx=(4, 8))
        ttk.Label(controls, text="xi_j:").pack(side=tk.LEFT)
        ttk.Entry(controls, textvariable=self.rayleigh_xi_j_var, width=8).pack(side=tk.LEFT, padx=(4, 12))
        ttk.Button(controls, text="Compute", command=self.compute_rayleigh_damping).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(controls, text="CE586 Example 6.1 Check", command=self.load_ce586_rayleigh_check).pack(side=tk.LEFT)

        ttk.Label(parent, textvariable=self.rayleigh_output_var).pack(side=tk.TOP, anchor=tk.W, pady=(0, 6))
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.trees["Rayleigh Damping"] = self._make_tree(tree_frame)

    def _populate_result_tables(self, result: dict[str, Any]) -> None:
        tables = {
            "Frequencies": format_eigenvalue_table(result),
            "Modal Properties": format_modal_property_table(result),
            "Eigenvectors": format_eigenvector_table(result),
        }
        for name, (headers, rows) in tables.items():
            self._populate_tree(self.trees[name], headers, rows)

    def _populate_tree(self, tree: ttk.Treeview, headers: list[str], rows: list[list[str]]) -> None:
        tree.delete(*tree.get_children())
        tree["columns"] = headers
        for header in headers:
            tree.heading(header, text=header)
            tree.column(header, width=max(95, min(180, len(header) * 12)), anchor=tk.CENTER, stretch=True)
        for row in rows:
            tree.insert("", tk.END, values=row)

    def _clear_result_tables(self) -> None:
        for tree in self.trees.values():
            tree.delete(*tree.get_children())
        self._clear_rayleigh_result()

    def _clear_rayleigh_result(self) -> None:
        if "Rayleigh Damping" in self.trees:
            self.trees["Rayleigh Damping"].delete(*self.trees["Rayleigh Damping"].get_children())
        self.rayleigh_output_var.set("Solve eigenanalysis, then compute Rayleigh damping.")

    def _compute_rayleigh_for_omegas(
        self,
        omegas: Any,
        frequencies: Any,
        periods: Any,
        mode_i: int,
        xi_i: float,
        mode_j: int,
        xi_j: float,
    ) -> None:
        omega = np.asarray(omegas, dtype=float).reshape(-1)
        if mode_i == mode_j:
            raise ValueError("Rayleigh target modes must be different.")
        if mode_i < 1 or mode_j < 1 or mode_i > len(omega) or mode_j > len(omega):
            raise ValueError(f"Target modes must be between 1 and {len(omega)}.")
        a0, a1 = rayleigh_coefficients(omega[mode_i - 1], xi_i, omega[mode_j - 1], xi_j)
        xis = rayleigh_damping_ratios(omega, a0, a1)
        headers, rows = format_rayleigh_table(omega, frequencies, periods, xis)
        self._populate_tree(self.trees["Rayleigh Damping"], headers, rows)
        self.rayleigh_output_var.set(
            f"a0 = {a0:.6g}, a1 = {a1:.6g}. "
            "xi(w) = a0/(2w) + a1*w/2."
        )
        if self.result is not None:
            self.result["rayleigh_a0"] = a0
            self.result["rayleigh_a1"] = a1
            self.result["rayleigh_xi"] = xis
            self.result["rayleigh_table"] = (headers, rows)

    def _read_matrix(self, name: str) -> np.ndarray:
        entries = self.matrix_entries.get(name)
        if not entries:
            raise ValueError(f"{name} matrix is not available.")
        return np.array([[self._entry_float(entry, f"{name}[{i + 1},{j + 1}]") for j, entry in enumerate(row)] for i, row in enumerate(entries)], dtype=float)

    def _read_vector(self, name: str) -> np.ndarray:
        entries = self.vector_entries.get(name)
        if not entries:
            raise ValueError(f"{name} vector is not available.")
        return np.array([self._entry_float(entry, f"{name}[{i + 1}]") for i, entry in enumerate(entries)], dtype=float)

    def _entry_float(self, entry: tk.Entry, label: str) -> float:
        value = entry.get().strip()
        if value == "":
            raise ValueError(f"{label} must be numeric.")
        try:
            return float(value)
        except ValueError as exc:
            raise ValueError(f"{label} must be numeric.") from exc

    def _set_matrix(self, name: str, values: Any) -> None:
        matrix = np.asarray(values, dtype=float)
        for i, row in enumerate(self.matrix_entries[name]):
            for j, entry in enumerate(row):
                entry.delete(0, tk.END)
                entry.insert(0, f"{matrix[i, j]:.12g}")

    def _set_vector(self, name: str, values: Any) -> None:
        vector = np.asarray(values, dtype=float).reshape(-1)
        for i, entry in enumerate(self.vector_entries.get(name, [])):
            entry.delete(0, tk.END)
            entry.insert(0, f"{vector[i]:.12g}")

    def _matrix_size(self) -> int:
        try:
            n = int(self.size_var.get())
        except (TypeError, tk.TclError, ValueError) as exc:
            raise ValueError("DOF size must be an integer.") from exc
        if n <= 0:
            raise ValueError("DOF size must be positive.")
        return n
