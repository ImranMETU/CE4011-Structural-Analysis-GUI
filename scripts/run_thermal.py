"""Run thermal load cases by reusing the Assignment3 solver core."""

import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
IO_ROOT = SRC_ROOT / "io"
COURSE_ROOT = PROJECT_ROOT.parent
A3_ROOT = COURSE_ROOT / "Assignment3"
A3_Q2_ROOT = COURSE_ROOT / "Assignment3" / "q2_frame_analysis"

# Ensure both extension package and Assignment3 solver are importable.
for path in (SRC_ROOT, IO_ROOT, PROJECT_ROOT, A3_ROOT, A3_Q2_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from model.structure import Structure  # noqa: E402


# THERMAL RUNNER EXTENSION START
def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def _index_by_id(items: list[dict[str, Any]]) -> dict[Any, dict[str, Any]]:
    index: dict[Any, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        item_id = item.get("id")
        if item_id is not None:
            index[item_id] = item
    return index


def _looks_like_thermal_load(load: dict[str, Any]) -> bool:
    if load.get("type") == "thermal":
        return True
    thermal_keys = {"T_uniform", "delta_T", "T_top", "T_bottom"}
    return any(k in load for k in thermal_keys)


def _classify_thermal_load(load: dict[str, Any]) -> tuple[str, float | None, float | None]:
    t_uniform = load.get("T_uniform")
    delta_t = load.get("delta_T")
    t_top = load.get("T_top")
    t_bottom = load.get("T_bottom")

    if isinstance(t_top, (int, float)) and isinstance(t_bottom, (int, float)):
        t_uniform = (float(t_top) + float(t_bottom)) / 2.0
        delta_t = float(t_top) - float(t_bottom)

    has_uniform = isinstance(t_uniform, (int, float)) and abs(float(t_uniform)) > 0.0
    has_gradient = isinstance(delta_t, (int, float)) and abs(float(delta_t)) > 0.0

    if has_uniform and has_gradient:
        return "combined", float(t_uniform), float(delta_t)
    if has_gradient:
        return "gradient", float(t_uniform) if isinstance(t_uniform, (int, float)) else None, float(delta_t)
    if has_uniform:
        return "uniform", float(t_uniform), float(delta_t) if isinstance(delta_t, (int, float)) else None
    return "invalid", None, None


def _find_thermal_member_loads(data: dict[str, Any]) -> list[dict[str, Any]]:
    elements = _as_list(data.get("elements"))
    thermal_entries: list[dict[str, Any]] = []

    for elem in elements:
        if not isinstance(elem, dict):
            continue
        elem_id = elem.get("id")
        member_loads = _as_list(elem.get("member_loads"))
        for load_idx, load in enumerate(member_loads, start=1):
            if not isinstance(load, dict):
                continue
            if _looks_like_thermal_load(load):
                has_t_top = "T_top" in load
                has_t_bottom = "T_bottom" in load
                if has_t_top ^ has_t_bottom:
                    print(
                        "WARNING: Partial thermal gradient definition on "
                        f"element {elem_id} load #{load_idx}; both T_top and T_bottom are required "
                        "to derive gradient from top/bottom temperatures."
                    )
                kind, t_uniform, delta_t = _classify_thermal_load(load)
                thermal_entries.append(
                    {
                        "element_id": elem_id,
                        "load": load,
                        "kind": kind,
                        "T_uniform": t_uniform,
                        "delta_T": delta_t,
                    }
                )

    return thermal_entries


def _warn_thermal_metadata(data: dict[str, Any], thermal_entries: list[dict[str, Any]]) -> None:
    if not thermal_entries:
        return

    materials_by_id = _index_by_id(_as_list(data.get("materials")))
    sections_by_id = _index_by_id(_as_list(data.get("sections")))
    elements = {e.get("id"): e for e in _as_list(data.get("elements")) if isinstance(e, dict)}

    warned_alpha: set[Any] = set()
    warned_depth: set[Any] = set()
    warned_material_ref: set[Any] = set()
    warned_section_ref: set[Any] = set()

    for entry in thermal_entries:
        elem_id = entry.get("element_id")
        elem = elements.get(elem_id, {}) if isinstance(elem_id, (int, str)) else {}
        if not isinstance(elem, dict):
            elem = {}

        material_ref = elem.get("material_id", elem.get("material", elem.get("mat_id")))
        section_ref = elem.get("section_id", elem.get("section", elem.get("sec_id")))

        if material_ref is None and elem_id not in warned_material_ref:
            print(
                "WARNING: Element "
                f"{elem_id} has thermal loading but no material reference key was found."
            )
            warned_material_ref.add(elem_id)
        if section_ref is None and elem_id not in warned_section_ref:
            print(
                "WARNING: Element "
                f"{elem_id} has thermal loading but no section reference key was found."
            )
            warned_section_ref.add(elem_id)

        if material_ref is not None and material_ref not in materials_by_id and elem_id not in warned_material_ref:
            print(
                "WARNING: Element "
                f"{elem_id} references material '{material_ref}', but it was not found in materials."
            )
            warned_material_ref.add(elem_id)
        if section_ref is not None and section_ref not in sections_by_id and elem_id not in warned_section_ref:
            print(
                "WARNING: Element "
                f"{elem_id} references section '{section_ref}', but it was not found in sections."
            )
            warned_section_ref.add(elem_id)

        material = materials_by_id.get(material_ref, {}) if material_ref is not None else {}
        section = sections_by_id.get(section_ref, {}) if section_ref is not None else {}

        if not isinstance(material, dict):
            material = {}
        if not isinstance(section, dict):
            section = {}

        alpha_value = material.get("alpha")
        if alpha_value is None and elem_id not in warned_alpha:
            print(
                "WARNING: Thermal load requested on "
                f"element {elem_id}, but material alpha is missing."
            )
            warned_alpha.add(elem_id)

        kind = entry.get("kind")
        depth_value = section.get("d", section.get("depth"))
        if kind in {"gradient", "combined"} and depth_value is None and elem_id not in warned_depth:
            print(
                "WARNING: Thermal gradient requested on "
                f"element {elem_id}, but section depth is missing."
            )
            warned_depth.add(elem_id)


def _print_thermal_summary(data: dict[str, Any], case_path: Path) -> list[dict[str, Any]]:
    thermal_entries = _find_thermal_member_loads(data)
    count = len(thermal_entries)

    print("\nThermal load inspection:")
    print(f"  Count: {count}")

    if count == 0:
        # If a case looks thermal by name, highlight likely modeling/input mismatch.
        if "thermal" in case_path.stem.lower():
            print(
                "WARNING: No thermal member loads were detected, "
                "but this case file name suggests a thermal case."
            )
        return thermal_entries

    element_ids = sorted({entry.get("element_id") for entry in thermal_entries if entry.get("element_id") is not None})
    print(f"  Elements with thermal loads: {element_ids}")

    for i, entry in enumerate(thermal_entries, start=1):
        elem_id = entry.get("element_id")
        kind = entry.get("kind")
        t_uniform = entry.get("T_uniform")
        delta_t = entry.get("delta_T")
        print(
            f"  [{i}] element={elem_id}, resolved={kind}, "
            f"T_u={t_uniform}, delta_T={delta_t}"
        )

    # Sign convention note for solver-core implementation:
    # Expected local restrained thermal vector often written as
    # [-N_t, 0, -M_t, N_t, 0, M_t], but verify against existing solver sign conventions.
    _warn_thermal_metadata(data, thermal_entries)
    return thermal_entries


# THERMAL RUNNER EXTENSION END
def load_input(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Case file not found: {path}")

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse JSON in case file: {path}\n{exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"Input JSON root must be an object/dict: {path}")

    return data


def run_case(case_path: Path, tol: float = 1e-8, max_iter: int = 2000) -> None:
    data = load_input(case_path)
    _print_thermal_summary(data, case_path)

    structure = Structure.from_dict(data)

    print(f"Case: {case_path.name}")
    print(f"Active DOFs: {structure.n_active_dofs}")
    # For fully restrained models (zero active DOFs), still run solve/recovery so
    # thermal fixed-end effects appear in reactions/member-end forces.
    if structure.n_active_dofs > 0:
        structure.assemble_global_stiffness()
        structure.assemble_global_load_vector()
    D = structure.solve(tol=tol, max_iter=max_iter)
    reactions = structure.compute_reactions()
    member_forces = structure.compute_member_end_forces()

    if structure.n_active_dofs > 0:
        print(f"||F|| = {structure.F.norm():.6e}")
    else:
        print("||F|| = 0.000000e+00 (no active DOFs)")
    print(f"||D|| = {D.norm():.6e}")

    print("\nSupport reactions:")
    for node_id in sorted(reactions):
        r = reactions[node_id]
        print(f"  Node {node_id}: Rx={r['rx']:.6e}, Ry={r['ry']:.6e}, Mz={r['mz']:.6e}")

    print("\nMember end forces (local):")
    for elem_id in sorted(member_forces):
        q = member_forces[elem_id]
        print(
            f"  Element {elem_id}: "
            f"i(N,V,M)=({q['node_i']['nx']:.6e}, {q['node_i']['vy']:.6e}, {q['node_i']['mz']:.6e}), "
            f"j(N,V,M)=({q['node_j']['nx']:.6e}, {q['node_j']['vy']:.6e}, {q['node_j']['mz']:.6e})"
        )


def main() -> None:
    if len(sys.argv) > 1:
        case_file = Path(sys.argv[1]).expanduser()
    else:
        case_file = PROJECT_ROOT / "inputs" / "thermal_frame_combined.json"

    case_file = case_file.resolve()

    # TODO: Add optional CLI flags (e.g., tol/max_iter/verbose) if needed later.
    try:
        run_case(case_file)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
    except Exception as exc:
        print(f"ERROR: Failed to run case '{case_file}': {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
