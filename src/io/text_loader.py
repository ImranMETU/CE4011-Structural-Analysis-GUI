"""Text input-deck loader for CE4011 structural models."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def load_text_model(path: str | Path) -> tuple[dict[str, Any], dict[int, dict[str, float]]]:
    """Load a text model file into Structure.from_dict data and modal masses."""
    with Path(path).open("r", encoding="utf-8") as f:
        return parse_text_model(f.read())


def parse_text_model(text: str) -> tuple[dict[str, Any], dict[int, dict[str, float]]]:
    """Parse a simple engineering text input deck."""
    data: dict[str, Any] = {
        "nodes": [],
        "materials": [],
        "sections": [],
        "elements": [],
        "nodal_loads": [],
    }
    mass_mapping: dict[int, dict[str, float]] = {}

    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        tokens = line.split()
        keyword = tokens[0].upper()
        args = tokens[1:]

        if keyword == "MATERIAL":
            data["materials"].append(_parse_material(args, line_no))
        elif keyword == "SECTION":
            data["sections"].append(_parse_section(args, line_no))
        elif keyword == "NODE":
            data["nodes"].append(_parse_node(args, line_no))
        elif keyword in {"FRAME", "TRUSS"}:
            data["elements"].append(_parse_element(keyword, args, line_no))
        elif keyword == "LOAD":
            data["nodal_loads"].append(_parse_load(args, line_no))
        elif keyword == "MASS":
            node_id, masses = _parse_mass(args, line_no)
            mass_mapping[node_id] = masses
        elif keyword == "THERMAL":
            element_id, load = _parse_thermal(args, line_no)
            _attach_thermal_load(data["elements"], element_id, load, line_no)
        elif keyword == "SETTLEMENT":
            node_id, prescribed = _parse_settlement(args, line_no)
            _attach_settlement(data["nodes"], node_id, prescribed, line_no)
        else:
            raise ValueError(f"Line {line_no}: unknown keyword {tokens[0]!r}.")

    return data, mass_mapping


def _parse_material(args: list[str], line_no: int) -> dict[str, Any]:
    _require_len(args, 2, line_no, "MATERIAL name E=...")
    props = _key_values(args[1:], line_no)
    return {
        "id": args[0],
        "E": _required_float(props, "E", line_no),
        "alpha": float(props.get("ALPHA", 0.0)),
    }


def _parse_section(args: list[str], line_no: int) -> dict[str, Any]:
    _require_len(args, 3, line_no, "SECTION name A=... I=...")
    props = _key_values(args[1:], line_no)
    section = {
        "id": args[0],
        "A": _required_float(props, "A", line_no),
        "I": _required_float(props, "I", line_no),
    }
    if "D" in props:
        section["d"] = float(props["D"])
    return section


def _parse_node(args: list[str], line_no: int) -> dict[str, Any]:
    _require_exact_len(args, 6, line_no, "NODE id x y ux uy rz")
    return {
        "id": int(args[0]),
        "x": float(args[1]),
        "y": float(args[2]),
        "restraints": {
            "ux": _restraint_flag(args[3], line_no),
            "uy": _restraint_flag(args[4], line_no),
            "rz": _restraint_flag(args[5], line_no),
        },
    }


def _parse_element(keyword: str, args: list[str], line_no: int) -> dict[str, Any]:
    _require_exact_len(args, 5, line_no, f"{keyword} id node_i node_j material section")
    return {
        "id": int(args[0]),
        "type": keyword.lower(),
        "node_i": int(args[1]),
        "node_j": int(args[2]),
        "material": args[3],
        "section": args[4],
    }


def _parse_load(args: list[str], line_no: int) -> dict[str, Any]:
    _require_len(args, 1, line_no, "LOAD node_id FX=... FY=... MZ=...")
    props = _key_values(args[1:], line_no)
    return {
        "node": int(args[0]),
        "fx": float(props.get("FX", 0.0)),
        "fy": float(props.get("FY", 0.0)),
        "mz": float(props.get("MZ", 0.0)),
    }


def _parse_mass(args: list[str], line_no: int) -> tuple[int, dict[str, float]]:
    _require_len(args, 1, line_no, "MASS node_id UX=... UY=... RZ=...")
    props = _key_values(args[1:], line_no)
    return int(args[0]), {
        "ux": float(props.get("UX", 0.0)),
        "uy": float(props.get("UY", 0.0)),
        "rz": float(props.get("RZ", 0.0)),
    }


def _parse_thermal(args: list[str], line_no: int) -> tuple[int, dict[str, float | str]]:
    _require_len(args, 1, line_no, "THERMAL element_id T_UNIFORM=... or T_TOP=... T_BOTTOM=...")
    props = _key_values(args[1:], line_no)
    load: dict[str, float | str] = {"type": "thermal"}

    has_uniform = "T_UNIFORM" in props
    has_top = "T_TOP" in props
    has_bottom = "T_BOTTOM" in props

    if not has_uniform and not (has_top or has_bottom):
        raise ValueError(f"Line {line_no}: THERMAL requires T_UNIFORM or T_TOP/T_BOTTOM values.")
    if has_top != has_bottom:
        raise ValueError(f"Line {line_no}: THERMAL T_TOP/T_BOTTOM must be provided together.")

    if has_uniform:
        load["T_uniform"] = float(props["T_UNIFORM"])
    if has_top and has_bottom:
        load["T_top"] = float(props["T_TOP"])
        load["T_bottom"] = float(props["T_BOTTOM"])

    return int(args[0]), load


def _parse_settlement(args: list[str], line_no: int) -> tuple[int, dict[str, float]]:
    _require_len(args, 1, line_no, "SETTLEMENT node_id UX=... UY=... RZ=...")
    props = _key_values(args[1:], line_no)
    return int(args[0]), {
        "ux": float(props.get("UX", 0.0)),
        "uy": float(props.get("UY", 0.0)),
        "rz": float(props.get("RZ", 0.0)),
    }


def _attach_thermal_load(elements: list[dict[str, Any]], element_id: int, load: dict[str, Any], line_no: int) -> None:
    for element in elements:
        if int(element["id"]) == int(element_id):
            element.setdefault("member_loads", []).append(load)
            return
    raise ValueError(f"Line {line_no}: THERMAL references unknown element id {element_id}.")


def _attach_settlement(nodes: list[dict[str, Any]], node_id: int, prescribed: dict[str, float], line_no: int) -> None:
    for node in nodes:
        if int(node["id"]) == int(node_id):
            node["prescribed_displacements"] = prescribed
            return
    raise ValueError(f"Line {line_no}: SETTLEMENT references unknown node id {node_id}.")


def _key_values(tokens: list[str], line_no: int) -> dict[str, str]:
    out = {}
    for token in tokens:
        if "=" not in token:
            raise ValueError(f"Line {line_no}: expected KEY=value token, got {token!r}.")
        key, value = token.split("=", 1)
        if not key or not value:
            raise ValueError(f"Line {line_no}: malformed KEY=value token {token!r}.")
        out[key.upper()] = value
    return out


def _required_float(props: dict[str, str], key: str, line_no: int) -> float:
    if key not in props:
        raise ValueError(f"Line {line_no}: missing required {key}= value.")
    return float(props[key])


def _restraint_flag(value: str, line_no: int) -> bool:
    upper = value.upper()
    if upper == "FIX":
        return True
    if upper == "FREE":
        return False
    raise ValueError(f"Line {line_no}: restraint must be FIX or FREE, got {value!r}.")


def _require_len(args: list[str], minimum: int, line_no: int, usage: str) -> None:
    if len(args) < minimum:
        raise ValueError(f"Line {line_no}: expected {usage}.")


def _require_exact_len(args: list[str], expected: int, line_no: int, usage: str) -> None:
    if len(args) != expected:
        raise ValueError(f"Line {line_no}: expected {usage}.")
