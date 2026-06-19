# CE4011 Structural Analysis GUI

GUI-based static and modal postprocessing extension of a 2D frame-truss Direct Stiffness Method solver.

This project is an educational structural-analysis program for linear elastic two-dimensional frame and truss systems. It combines a Python computational backend with a Tkinter/Matplotlib graphical interface for model input, static analysis, modal analysis, result visualization, result tables, generated frame examples, verification cases, and selected linear modal response-history/response-spectrum utilities.

The software is intended for learning, verification, and structural-analysis software development. It is not a commercial design package and does not perform design-code checks.

---

## Main Features

### Model input

The program supports several input routes:

- JSON model files
- XML model files
- text-deck model files
- form-based GUI model creation
- generated parametric frame models

All input routes are converted into a common backend model dictionary before analysis, so file-loaded, generated, and GUI-defined models use the same solver path.

### Structural model

Supported modeling components include:

- nodes and nodal degrees of freedom
- materials
- sections
- frame elements
- truss elements
- supports/restraints
- nodal loads
- supported member loads
- thermal loads
- support settlements
- modal masses
- companion modal mass files
- generated multi-story frame examples
- unit metadata and display labels

### Static analysis

The static solver uses the Direct Stiffness Method for 2D frame-truss systems. It assembles the global stiffness matrix, applies boundary conditions, solves for active nodal displacements, and recovers reactions and member forces.

Static outputs include:

- nodal displacement tables
- support reaction tables
- member-end force tables
- static deformed-shape plots
- axial force diagrams
- shear force diagrams
- bending moment diagrams
- station-force tables
- story drift and roof displacement outputs for frame examples

### Modal analysis

The modal module supports lumped modal mass assembly and massless-DOF static condensation. This is useful for frame models where translational DOFs may have mass but rotational or vertical DOFs may be massless.

Modal outputs include:

- circular frequency, `omega`, in rad/s
- frequency, `f`, in Hz
- period, `T`, in seconds
- mode shapes
- modal participation factors
- effective modal masses
- modal mass ratios
- cumulative modal mass ratios
- massive/massless DOF classification data

### Linear modal dynamic utilities

The project also includes selected educational modal postprocessing tools:

- ground-motion record loading
- elastic response-spectrum generation
- Rayleigh damping diagnostics
- linear modal response-history analysis
- response-spectrum analysis with ABSSUM, SRSS, and CQC modal combination

These utilities are linear modal postprocessing extensions. They are not nonlinear response-history analysis tools and are not full commercial seismic design workflows.

### Verification and diagnostics

The project includes automated tests and verification examples, including:

- cantilever beam static verification
- simply supported beam static verification
- CE586 modal benchmark examples
- five-story generated frame validation
- Autodesk Robot modal comparison
- ten-story braced/unbraced generated-frame comparison
- RHA/RSA supplementary examples
- GUI-backend consistency checks
- solver diagnostics, sparsity, bandwidth, and DOF-count information

The cleaned project version passes **344 meaningful pytest cases**. Earlier project snapshots contained 347 tests; three duplicate placeholder tests were removed during cleanup without changing solver mathematics or numerical behavior.

---

## Quick Start: Windows ZIP Executable

This is the simplest option for users who only want to run the GUI.

### Option A: Download from GitHub

Download the Windows ZIP executable package from the project repository or release/download area:

```text
https://github.com/ImranMETU/CE4011-Structural-Analysis-GUI
```

### Option B: Download from Google Drive

A ZIP/executable distribution is also available here:

```text
https://drive.google.com/file/d/153He7D_wZ2FF9whGVxrezIJhlzXqVhss/
```

### Run the executable

1. Download the ZIP file.
2. Extract it to a normal local folder, for example:

```text
C:\CE4011_Solver_Windows_x64
```

3. Run:

```text
C:\CE4011_Solver_Windows_x64\CE4011_Solver\CE4011_Solver.exe
```

4. Keep the full `CE4011_Solver` folder together. Do not move `CE4011_Solver.exe` away from the adjacent `_internal` folder.

The `_internal` folder contains Python, Tcl/Tk, NumPy, SciPy, Matplotlib, and bundled data required by the executable. Copying only the `.exe` file will cause a `Failed to load Python DLL` error.

---

## Source-Code Installation

Use this option if you want to run the project from Python, inspect the code, run tests, or rebuild the executable.

### Requirements

Recommended environment:

- Windows 10 or Windows 11
- Anaconda or Miniconda
- Python 3.11
- Tkinter support
- packages listed in `requirements.txt`

Core dependencies:

```text
numpy>=1.24
scipy>=1.10
matplotlib>=3.7
pytest>=7.0
```

### Clone the repository

```powershell
git clone https://github.com/ImranMETU/CE4011-Structural-Analysis-GUI.git
cd CE4011-Structural-Analysis-GUI
```

Alternatively, download the repository as a ZIP file from GitHub and extract it.

### Create and activate the Conda environment

```powershell
conda create -n CE4011 python=3.11 -y
conda activate CE4011
```

### Install dependencies

```powershell
python -m pip install -r requirements.txt
```

If `requirements.txt` is not available, install the essential packages manually:

```powershell
python -m pip install numpy scipy matplotlib pytest
```

Tkinter is normally included with standard Windows/Anaconda Python distributions. If the GUI does not launch and the error mentions Tkinter, install a Python distribution that includes Tcl/Tk support.

---

## Launching the GUI from Source

Run from the repository root:

```powershell
conda activate CE4011
python scripts\run_static_gui.py
```

The main window should open with a title similar to:

```text
CE4011 Static/Modal Result Viewer
```

Run the script from the repository root. Running from inside `scripts/`, `src/`, or another folder may break relative paths for inputs, examples, generated models, companion mass files, or result folders.

---

## Typical GUI Workflow

A normal analysis workflow is:

1. Launch the GUI.
2. Open or define a model.
3. Inspect the model view.
4. Run static analysis.
5. View deformed shape, reactions, member forces, and N/V/M diagrams.
6. Run modal analysis if modal masses are available.
7. View mode shapes, frequencies, periods, participation factors, and effective modal masses.
8. Export tables or plots if needed.

A recommended first example is:

```text
model_a_5story_unbraced.json
model_a_5story_unbraced_masses.json
```

Keep companion mass files together with the main model file. Modal analysis may fail or produce incomplete results if the required mass file is missing.

---

## Verification Commands

Run these commands from the repository root:

```powershell
conda activate CE4011
python -m pytest -q
python scripts\run_gui_backend_verification.py
python scripts\run_final_core_smoke.py
```

Expected cleaned-project status:

```text
344 passed
GUI backend verification: PASS
Final core smoke: PASS
```

Minor Windows temporary-directory cleanup warnings after pytest are not treated as solver failures if the tests themselves pass.

---

## Optional Example and Result Scripts

The following scripts generate selected result files and figures under `results/`:

```powershell
python scripts\generate_proposal_models.py
python scripts\run_member_load_examples.py
python scripts\run_station_postprocessing_case.py
python scripts\run_solver_diagnostics_case.py
python scripts\compare_braced_unbraced.py
python scripts\run_modal_rha_case.py
python scripts\run_modal_rsa_case.py
```

Generated outputs are normally treated as reproducible output rather than source code. They may be excluded from Git unless selected figures or CSV files are intentionally preserved.

---

## Rebuilding the Windows Executable

A PyInstaller spec and build script are included for rebuilding the executable distribution.

From the repository root:

```powershell
conda activate CE4011
.\build_exe.ps1
```

or manually:

```powershell
conda activate CE4011
python -m PyInstaller --clean --noconfirm CE4011_Solver.spec
```

The finished application is created at:

```text
dist\CE4011_Solver\CE4011_Solver.exe
```

Important packaging rules:

- Run the application from `dist\CE4011_Solver\CE4011_Solver.exe`.
- Do not run it from `build\`.
- Do not move the `.exe` away from `_internal`.
- Distribute the whole `dist\CE4011_Solver` folder, preferably as a ZIP archive.

---

## Project Structure

Representative repository layout:

```text
CE4011-Structural-Analysis-GUI/
├── src/
│   ├── analysis/
│   ├── generators/
│   ├── gui/
│   ├── io/
│   ├── model/
│   ├── postprocessing/
│   ├── units/
│   └── visualization/
├── scripts/
├── tests/
├── inputs/
├── verification/
├── benchmarks/
├── docs/
├── requirements.txt
├── README.md
├── USER_MANUAL.pdf
├── INSTALLATION_MANUAL.pdf
├── CE4011_Solver.spec
└── build_exe.ps1
```

The exact folder list may vary slightly between source snapshots, but the GUI launcher, source package, tests, inputs, and verification examples should remain in the repository.

---

## Documentation

Read these first:

- `INSTALLATION_MANUAL.pdf` — installation, executable, Python environment, verification, and troubleshooting.
- `USER_MANUAL.pdf` — GUI workflow, input routes, menus, analysis options, outputs, examples, warnings, and limitations.
- `INSTALLER_README.txt` — short notes for the packaged Windows executable.

---

## Common Problems

### GUI does not launch

Check that you are using the correct environment and running from the repository root:

```powershell
conda activate CE4011
python scripts\run_static_gui.py
```

### `ModuleNotFoundError: No module named 'gui'`

Run from the repository root, not from inside `scripts/` or `src/`.

### Executable says `Failed to load Python DLL`

You probably moved the `.exe` without `_internal`, or you are running from `build\`. Use the full extracted folder:

```text
C:\CE4011_Solver_Windows_x64\CE4011_Solver\CE4011_Solver.exe
```

### Modal analysis fails

Check that the model has modal mass data. If the model uses a companion mass file, keep it in the expected location beside the main model file.

### Force diagram sign differs from Ftool

This is usually a display-convention difference. Numerical internal-force values are separated from the plotted side/sign convention.

### Units appear wrong

The unit system is metadata and labeling only. Changing the displayed unit convention does not rescale existing numerical input values.

---

## Limitations

The software is limited to linear elastic 2D frame-truss analysis. It does not include:

- full 3D frame analysis
- shell or slab elements
- rigid diaphragm constraints
- nonlinear material behavior
- geometric nonlinearity or P-Delta effects
- staged construction
- design-code checks
- complete commercial load-combination workflows
- nonlinear response-history analysis

Future extensions may include 3D frame elements, shell/slab elements, diaphragm constraints, partial-span member-load formulas, nonlinear analysis, and code-based design checks.

---

## Author

Imran Shahriar  
CE4011 Structural Analysis Software Development  
Middle East Technical University

---

## License / Use

This repository is provided as an educational structural-analysis software development project. Users should verify all engineering results independently before using them for any decision-making purpose.
