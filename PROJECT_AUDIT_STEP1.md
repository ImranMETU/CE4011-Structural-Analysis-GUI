# CE4011 Final Project - Step 1 Project Audit

Date: 2026-06-02

## Current directory structure

Project root: `C:\DDrive\Imran\METU\Coursework\CE4011\Project`

- `src/`: current solver source code.
  - `src/model/`: structural model classes and DSM workflow.
  - `src/io/`: XML input loader.
  - `src/matrixlib/`: compatibility exports for the Assignment 1 matrix library.
  - `src/q1_matrix_library/`: matrix, vector, sparse matrix, and conjugate-gradient solver.
  - `src/thermal/`: thermal load helper implementation.
- `tests/`: pytest tests, with root-level duplicates plus `unit/`, `interface/`, and `regression/` subfolders.
- `inputs/`: JSON and XML model inputs.
  - `inputs/json/`: thermal JSON cases.
  - `inputs/q2/`: Model A/B XML inputs.
  - `inputs/regression/xml/`: XML regression cases for thermal and settlement behavior.
- `scripts/`: runnable helper scripts for thermal cases, XML regression cases, validation, reports, and migration.
- `results/`: previous generated solver and benchmark output.
- `ftool/`: Ftool model and benchmark files.
- `report/`, `docs/`: Assignment 4 report and documentation artifacts.
- `thermal/`, `settlement/`: legacy/top-level package or test artifacts.

No `.git` directory was found in the project root or nested below it.

## Main solver entry points

- `scripts/run_thermal.py`: JSON thermal-case runner. Reads a JSON case, builds `Structure`, solves, and prints displacement norm, reactions, and member-end forces.
- `scripts/run_regression_case.py`: XML regression runner. Reads one XML case from `inputs/regression/xml/`, builds `Structure`, solves, and prints post-processing output.
- `tests/regression/test_xml_regression.py` and `tests/test_xml_regression.py`: pytest execution path for XML regression cases.
- Core programmatic entry point: `Structure.from_dict(data)` followed by assembly, solve, and post-processing methods.

## Main classes/modules

- `src/model/structure.py`
  - `Structure`: model container and main DSM coordinator.
  - Stores `nodes`, `materials`, `sections`, `elements`, `node_index`, `n_active_dofs`, `K`, `F`, and `D`.
  - Main methods include `assign_dofs`, `assemble_global_stiffness`, `assemble_global_load_vector`, `solve`, `full_displacement_vector`, `compute_reactions`, `compute_member_end_forces`, and `from_dict`.
- `src/model/node.py`
  - `Node`: 2D node with `ux`, `uy`, `rz` DOFs, restraints, nodal loads, equation numbers, and prescribed support settlements.
- `src/model/element.py`
  - `Element`: abstract base class for geometry, transformation, global stiffness, equivalent nodal load, and local member-end force recovery.
- `src/model/frame_element.py`
  - `FrameElement`: 2D frame element with axial and bending stiffness, member loads, thermal loads, and optional end releases.
- `src/model/truss_element.py`
  - `TrussElement`: axial-only 2D truss element embedded in the 3-DOF-per-node formulation.
- `src/model/material.py`
  - `Material`: Young's modulus `E` and thermal expansion coefficient `alpha`.
- `src/model/section.py`
  - `Section`: area `A`, moment of inertia `I`, and optional depth `d`.
- `src/matrixlib/__init__.py` and `src/q1_matrix_library/`
  - Re-export and implement `Vector`, `SymmetricSparseMatrix`, and `ConjugateGradientSolver`.
- `src/io/xml_loader.py`
  - XML-to-dictionary loader compatible with `Structure.from_dict`.
- `src/thermal/thermal_load.py`
  - Thermal fixed-end/equivalent nodal load helper logic.

## Existing static-analysis workflow

The current static workflow is:

1. Read input into a Python dictionary, either directly from JSON or via XML conversion.
2. Build the model with `Structure.from_dict(data)`.
3. Add nodes, materials, sections, nodal loads, elements, member loads, releases, thermal loads, and prescribed settlements.
4. Assign global DOF numbers with restrained DOFs numbered as `0`.
5. If active DOFs exist, assemble global stiffness `K` and load vector `F`.
6. Call `Structure.solve()`.
   - Uses `ConjugateGradientSolver`.
   - Handles fully restrained zero-active-DOF cases with empty vectors.
   - Applies support-settlement correction before solving.
   - Performs basic instability/zero-stiffness checks.
7. Recover post-processing results:
   - `Structure.full_displacement_vector()`
   - `Structure.compute_reactions()`
   - `Structure.compute_member_end_forces()`

## Existing input/output workflow

### JSON

- `scripts/run_thermal.py` reads JSON through `json.load`.
- Default JSON case: `inputs/thermal_frame_combined.json`.
- Additional JSON cases exist under `inputs/json/`.
- JSON root must be a dictionary compatible with `Structure.from_dict`.
- Expected sections include `nodes`, `materials`, `sections`, `elements`, and `nodal_loads`.

### XML

- `src/io/xml_loader.py` parses XML with `xml.etree.ElementTree`.
- `load_structure_from_xml(xml_path)` returns a `Structure.from_dict` compatible dictionary.
- XML parser handles:
  - `nodes/node` with coordinates, restraints, and optional prescribed displacements.
  - `materials/material` with `E` and optional `alpha`.
  - `sections/section` with `A`, `I`, and optional `d` or `depth`.
  - `elements/element` with type, end nodes, material, section, releases, and member loads.
  - `nodal_loads/load` or `nodalLoads/load`.
  - `nodal_loads/settlement` or `nodalLoads/settlement`.

### Stored/printed output

- Active displacement solution is stored as `Structure.D`.
- Full nodal displacement vector is returned by `Structure.full_displacement_vector()`.
  - Order is sorted node IDs, three DOFs per node: `[ux, uy, rz]`.
  - Restrained DOFs use prescribed displacement values for settlement support.
- Support reactions are returned by `Structure.compute_reactions()` as:
  - `{node_id: {"rx": value, "ry": value, "mz": value}}`
- Member-end forces are returned by `Structure.compute_member_end_forces()` as:
  - `{element_id: {"node_i": {"nx", "vy", "mz"}, "node_j": {"nx", "vy", "mz"}}}`
- Runner scripts print results to stdout. Existing historical text outputs are present under `results/solver/`, but no current centralized result-object or file writer was identified.

## Existing test commands and test status

Environment identified from user note and local path:

- CE4011 interpreter: `C:\Users\Imran\anaconda3\envs\CE4011\python.exe`
- Version: Python 3.11.15

Commands tried:

- `C:\Users\Imran\anaconda3\envs\CE4011\python.exe -m pytest -q`
  - Status: failed during collection.
  - Reason: pytest attempted to collect `results/solver/TEST_RESULTS.txt`, which is not UTF-8 text for pytest collection.
- `C:\Users\Imran\anaconda3\envs\CE4011\python.exe -m pytest tests -q`
  - Status: passed.
  - Result: `14 passed in 0.14s`.
- `C:\Users\Imran\anaconda3\envs\CE4011\python.exe scripts\run_regression_case.py regression_thermal_uniform_truss.xml`
  - Status: passed as a smoke run.
  - Produced zero active DOFs, expected thermal reactions, and local member-end forces.

Recommended current test command:

```powershell
C:\Users\Imran\anaconda3\envs\CE4011\python.exe -m pytest tests -q
```

## Git status and branch setup

- `git status --short --branch` from the project root failed with: `fatal: not a git repository (or any of the parent directories): .git`
- Recursive `.git` directory check found no nested Git repository metadata.
- Branch `final-static-modal-gui` was not created because this folder is not currently a Git repository.

## Missing dependencies or environment notes

- In the CE4011 Python 3.11 environment, pytest is available and the scoped `tests/` suite passes.
- The system default `python` on PATH is Python 3.14.5 and does not have pytest installed. It should not be used for this project.
- `conda` is not available on the current PowerShell PATH, so the CE4011 interpreter was invoked directly by absolute path.
- No `requirements.txt`, `pyproject.toml`, or environment lock file was identified during the audit.
- Broad root-level pytest collection should be adjusted later, likely by adding pytest configuration that limits collection to `tests/`.

## Immediate next steps for Step 2: static post-processing backend

- Add a small static post-processing API around existing solver outputs without changing solver math.
- Define a stable result object or dictionary containing nodal displacements, support reactions, and member-end forces.
- Preserve existing `Structure` behavior and tests while adding adapter/helper functions for GUI consumption.
- Add focused tests for the new result packaging using existing XML/JSON cases.
- Consider pytest configuration to prevent accidental collection of historical files under `results/`.
- Do not begin GUI implementation or modal analysis until the static post-processing backend contract is stable.
