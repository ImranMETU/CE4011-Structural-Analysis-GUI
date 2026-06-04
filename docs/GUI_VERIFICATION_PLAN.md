# GUI Verification Plan

## Purpose

This plan verifies that the final CE4011 GUI workflow can load, solve, package, and display cases that were already validated through the Assignment 2-4 backend work.

The intent is not to re-prove the Direct Stiffness Method solver mathematics. Those checks are covered by backend unit and regression tests. The current goal is GUI integration verification: file loading, menu workflow, analysis execution, result packaging, plotting, and graceful handling of unsupported/legacy inputs.

## Verification Scope

Backend tests verify numerical behavior directly through Python APIs. GUI verification cases verify that the same cases can pass through the user-facing workflow:

1. Open XML, JSON, or text model.
2. Run static analysis.
3. Confirm displacements, reactions, and member-end forces are available.
4. Display required plots in the Matplotlib canvas.
5. Confirm invalid or legacy inputs fail with a clear error instead of crashing.

## Available Case Inventory

The repository currently contains these GUI-loadable model formats:

- XML: `inputs/q2/*.xml`, `inputs/regression/xml/*.xml`
- JSON: `inputs/*.json`, `settlement/test_settlement_input.json`
- Text deck: `inputs/simple_portal_frame.txt`
- Assignment 4 text examples: `inputs/examples/a4_settlement_example.txt`, `inputs/examples/a4_thermal_example.txt`

Ftool `.ftl` files and ground-motion `.THF` files are not static GUI model inputs and are not included in the automated GUI manifest.

Assignment 3 Q3 samples a-e were not found in the current project input folders during this audit.

## Manual GUI Workflow

Use:

```powershell
C:\Users\Imran\anaconda3\envs\CE4011\python.exe scripts\run_static_gui.py
```

For each valid case:

1. Use `File > Open XML Model`, `File > Open JSON Model`, or `File > Open Text Model`.
2. Run `Analyze > Run Static Analysis`.
3. Check the summary panel for node/element counts and result records.
4. Use `Display` menu entries to check the required views.
5. Capture screenshots for cases marked as screenshot priority.

For Assignment 4 form-created cases, use `Define > Thermal Loads` or `Define > Support Settlements` after defining the base model. These dialogs write to the same backend schema as XML/JSON/text inputs: thermal records become element `member_loads`, and settlement records become node `prescribed_displacements`.

For invalid or legacy-schema cases:

1. Open the file through the appropriate File menu.
2. Run analysis if loading succeeds.
3. Confirm a clear message box appears and the GUI does not crash.

## Expected Behavior

- `solve`: the case should run static analysis and produce displacements, reactions, member-end forces, and requested plots.
- `warning`: the case is useful for manual review but may be incomplete, duplicated, or not directly part of the current GUI input scope.
- `error`: the case should fail gracefully due to unsupported or legacy input schema.

## Automated Non-GUI Check

The script `scripts/run_gui_backend_verification.py` reads `verification/gui_case_manifest.json`, uses the same XML/JSON/text loading paths as the GUI, runs static analysis for `solve` cases, and records expected failures for `error` cases. It does not launch Tkinter or call `mainloop()`.
