"""Run non-GUI backend checks for GUI verification manifest cases."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
IO_ROOT = SRC_ROOT / "io"

for path in (SRC_ROOT, IO_ROOT, PROJECT_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from postprocessing.static_results import run_static_analysis  # noqa: E402
from text_loader import load_text_model  # noqa: E402
from visualization.static_plots import (  # noqa: E402
    plot_axial_force_diagram,
    plot_bending_moment_diagram,
    plot_deformed_shape,
    plot_geometry,
    plot_shear_force_diagram,
)
from xml_loader import load_structure_from_xml  # noqa: E402


MANIFEST_PATH = PROJECT_ROOT / "verification" / "gui_case_manifest.json"
OUTPUT_ROOT = PROJECT_ROOT / "results" / "verification" / "gui_backend"


def main() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    rows = []
    for case in manifest:
        rows.append(_run_case(case))

    _print_summary(rows)
    failed = [row for row in rows if row["status"] == "FAIL"]
    return 1 if failed else 0


def _run_case(case: dict[str, Any]) -> dict[str, str]:
    case_id = case["id"]
    expected = case["expected_behavior"]
    try:
        data = _load_case_data(case)
        if expected == "error":
            try:
                run_static_analysis(data)
            except Exception as exc:
                return _row(case_id, expected, "PASS", f"Expected error: {type(exc).__name__}: {exc}")
            return _row(case_id, expected, "FAIL", "Expected error, but case solved.")

        result = run_static_analysis(data)
        _assert_static_result(result)
        _write_plots(case_id, result)

        note = (
            f"nodes={len(result['nodes'])}, elements={len(result['elements'])}, "
            f"reactions={len(result['reactions'])}, member_forces={len(result['member_end_forces'])}"
        )
        return _row(case_id, expected, "PASS", note)
    except Exception as exc:
        if expected == "error":
            return _row(case_id, expected, "PASS", f"Expected error: {type(exc).__name__}: {exc}")
        return _row(case_id, expected, "FAIL", f"{type(exc).__name__}: {exc}")


def _load_case_data(case: dict[str, Any]) -> dict[str, Any]:
    path = PROJECT_ROOT / case["input_path"]
    input_type = case["input_type"]
    if input_type == "xml":
        return load_structure_from_xml(path)
    if input_type == "json":
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("JSON model root must be an object.")
        return data
    if input_type == "txt":
        data, _mass_mapping = load_text_model(path)
        return data
    raise ValueError(f"Unsupported input_type {input_type!r}.")


def _assert_static_result(result: dict[str, Any]) -> None:
    required = ("displacement_vector", "reactions", "member_end_forces", "nodes", "elements")
    missing = [key for key in required if key not in result]
    if missing:
        raise AssertionError(f"Missing result keys: {missing}")
    if len(result["nodes"]) == 0:
        raise AssertionError("No nodes in result package.")
    if len(result["elements"]) == 0:
        raise AssertionError("No elements in result package.")
    if len(result["reactions"]) == 0:
        raise AssertionError("No reaction records in result package.")
    if len(result["member_end_forces"]) == 0:
        raise AssertionError("No member-end force records in result package.")


def _write_plots(case_id: str, result: dict[str, Any]) -> None:
    case_dir = OUTPUT_ROOT / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    plot_specs = [
        ("geometry.png", plot_geometry, {}),
        ("deformed_shape.png", plot_deformed_shape, {"scale": 1.0}),
        ("axial_force.png", plot_axial_force_diagram, {"scale": 1.0}),
        ("shear_force.png", plot_shear_force_diagram, {"scale": 1.0}),
        ("bending_moment.png", plot_bending_moment_diagram, {"scale": 1.0}),
    ]
    for filename, plot_func, kwargs in plot_specs:
        fig, _ax = plot_func(result, **kwargs)
        fig.tight_layout()
        fig.savefig(case_dir / filename, dpi=120)
        plt.close(fig)


def _row(case_id: str, expected: str, status: str, message: str) -> dict[str, str]:
    return {"id": case_id, "expected": expected, "status": status, "message": message}


def _print_summary(rows: list[dict[str, str]]) -> None:
    print("GUI backend verification summary")
    print("-" * 100)
    print(f"{'Case ID':35} {'Expected':10} {'Status':8} Message")
    print("-" * 100)
    for row in rows:
        print(f"{row['id']:35} {row['expected']:10} {row['status']:8} {row['message']}")
    print("-" * 100)
    print(f"Total: {len(rows)}, PASS: {sum(r['status'] == 'PASS' for r in rows)}, FAIL: {sum(r['status'] == 'FAIL' for r in rows)}")
    print(f"Plot output root: {OUTPUT_ROOT}")


if __name__ == "__main__":
    raise SystemExit(main())
