"""Station-based frame element postprocessing.

This module is postprocessing-only. It uses the existing static result package,
recovered local member-end forces, and member load metadata to evaluate frame
quantities at stations along each element.

Force sign convention follows ``postprocessing.force_diagrams``: the i-end
force is the left station value and the j-end value is sign-flipped so diagrams
are expressed in one local i-to-j member convention. Supported member-load
corrections currently cover full-span local-y UDLs, local-y point loads, and
simple local-x axial loads.
"""

from __future__ import annotations

import math
from typing import Any


DEFAULT_STATION_COUNT = 11


def hermite_shape_values(length: float, xi: float) -> dict[str, float]:
    """Return cubic Hermite shape functions and derivatives for a 2D frame."""
    if length <= 0.0:
        raise ValueError("length must be positive.")
    xi = _clamp_xi(xi)
    h1 = 1.0 - 3.0 * xi**2 + 2.0 * xi**3
    h2 = length * (xi - 2.0 * xi**2 + xi**3)
    h3 = 3.0 * xi**2 - 2.0 * xi**3
    h4 = length * (-xi**2 + xi**3)
    dh1 = (-6.0 * xi + 6.0 * xi**2) / length
    dh2 = 1.0 - 4.0 * xi + 3.0 * xi**2
    dh3 = (6.0 * xi - 6.0 * xi**2) / length
    dh4 = -2.0 * xi + 3.0 * xi**2
    d2h1 = (-6.0 + 12.0 * xi) / (length * length)
    d2h2 = (-4.0 + 6.0 * xi) / length
    d2h3 = (6.0 - 12.0 * xi) / (length * length)
    d2h4 = (-2.0 + 6.0 * xi) / length
    return {
        "H1": h1,
        "H2": h2,
        "H3": h3,
        "H4": h4,
        "dH1_dx": dh1,
        "dH2_dx": dh2,
        "dH3_dx": dh3,
        "dH4_dx": dh4,
        "d2H1_dx2": d2h1,
        "d2H2_dx2": d2h2,
        "d2H3_dx2": d2h3,
        "d2H4_dx2": d2h4,
    }


def interpolate_frame_displacement(length: float, local_dofs: list[float], xi: float) -> dict[str, float]:
    """Interpolate local frame displacement, slope, and curvature at ``xi``."""
    if len(local_dofs) != 6:
        raise ValueError("local_dofs must contain [ui, vi, thi, uj, vj, thj].")
    ui, vi, thi, uj, vj, thj = [float(value) for value in local_dofs]
    shapes = hermite_shape_values(length, xi)
    axial = (1.0 - _clamp_xi(xi)) * ui + _clamp_xi(xi) * uj
    transverse = shapes["H1"] * vi + shapes["H2"] * thi + shapes["H3"] * vj + shapes["H4"] * thj
    slope = (
        shapes["dH1_dx"] * vi
        + shapes["dH2_dx"] * thi
        + shapes["dH3_dx"] * vj
        + shapes["dH4_dx"] * thj
    )
    curvature = (
        shapes["d2H1_dx2"] * vi
        + shapes["d2H2_dx2"] * thi
        + shapes["d2H3_dx2"] * vj
        + shapes["d2H4_dx2"] * thj
    )
    return {"u": axial, "v": transverse, "slope": slope, "curvature": curvature}


def frame_local_displacement_dofs(result: dict[str, Any], element: dict[str, Any]) -> list[float]:
    """Return element displacement DOFs in local coordinates."""
    disp_i = result["displacements"][element["node_i"]]
    disp_j = result["displacements"][element["node_j"]]
    c = math.cos(float(element["angle"]))
    s = math.sin(float(element["angle"]))
    ux_i, uy_i, rz_i = float(disp_i["ux"]), float(disp_i["uy"]), float(disp_i["rz"])
    ux_j, uy_j, rz_j = float(disp_j["ux"]), float(disp_j["uy"]), float(disp_j["rz"])
    return [
        c * ux_i + s * uy_i,
        -s * ux_i + c * uy_i,
        rz_i,
        c * ux_j + s * uy_j,
        -s * ux_j + c * uy_j,
        rz_j,
    ]


def station_xis(n_stations: int = DEFAULT_STATION_COUNT) -> list[float]:
    """Return normalized station coordinates including both endpoints."""
    if n_stations < 2:
        raise ValueError("n_stations must be at least 2.")
    return [i / (n_stations - 1) for i in range(n_stations)]


def frame_station_results(
    result: dict[str, Any],
    element_id: int,
    n_stations: int = DEFAULT_STATION_COUNT,
) -> list[dict[str, Any]]:
    """Return station postprocessing rows for one frame element."""
    element = result["elements"][element_id]
    if str(element.get("type", "")).lower() != "frame":
        return []
    length = float(element["length"])
    local_dofs = frame_local_displacement_dofs(result, element)
    member_force = result["member_end_forces"][element_id]
    rows = []
    for station, xi in enumerate(station_xis(n_stations), start=1):
        x_local = xi * length
        global_x, global_y = local_to_global_station(result, element, x_local)
        disp = interpolate_frame_displacement(length, local_dofs, xi)
        force = section_force_at_x(member_force, element, x_local)
        rows.append(
            {
                "element": element_id,
                "type": "frame",
                "station": station,
                "xi": xi,
                "x_local": x_local,
                "global_x": global_x,
                "global_y": global_y,
                "N": force["N"],
                "V": force["V"],
                "M": force["M"],
                "u_local": disp["u"],
                "v_local": disp["v"],
                "slope": disp["slope"],
                "curvature": disp["curvature"],
            }
        )
    return rows


def all_frame_station_results(result: dict[str, Any], n_stations: int = DEFAULT_STATION_COUNT) -> list[dict[str, Any]]:
    """Return station rows for all frame elements in a static result package."""
    rows: list[dict[str, Any]] = []
    for element_id, element in sorted(result.get("elements", {}).items()):
        if str(element.get("type", "")).lower() == "frame":
            rows.extend(frame_station_results(result, int(element_id), n_stations=n_stations))
    return rows


def section_force_at_x(member_force: dict[str, Any], element: dict[str, Any], x_local: float) -> dict[str, float]:
    """Return N, V, M at local station ``x_local`` using existing diagram convention."""
    length = float(element["length"])
    if length <= 0.0:
        raise ValueError("element length must be positive.")
    x = max(0.0, min(length, float(x_local)))
    i_end = member_force.get("node_i", {})
    j_end = member_force.get("node_j", {})
    n0 = float(i_end.get("nx", 0.0))
    n1 = -float(j_end.get("nx", 0.0))
    v0 = float(i_end.get("vy", 0.0))
    m0 = float(i_end.get("mz", 0.0))
    axial = n0 + (n1 - n0) * x / length
    shear = v0
    moment = m0 + v0 * x

    for load in element.get("member_loads", []):
        load_type = str(load.get("type", "")).lower()
        direction = str(load.get("direction", "local_y")).lower()
        if load_type == "udl" and direction == "local_y":
            w = float(load.get("w", 0.0))
            shear += w * x
            moment += 0.5 * w * x * x
        elif load_type == "point" and direction == "local_y":
            p = float(load.get("p", 0.0))
            a = float(load.get("a", 0.0))
            if x >= a:
                shear += p
                moment += p * (x - a)
        elif load_type == "udl" and direction == "local_x":
            w = float(load.get("w", 0.0))
            axial += w * x
        elif load_type == "point" and direction == "local_x":
            p = float(load.get("p", 0.0))
            a = float(load.get("a", 0.0))
            if x >= a:
                axial += p

    return {"N": axial, "V": shear, "M": moment}


def hermite_deformed_polyline(
    result: dict[str, Any],
    element_id: int,
    scale: float = 1.0,
    n_stations: int = DEFAULT_STATION_COUNT,
) -> dict[str, list[float]]:
    """Return global undeformed/deformed station coordinates for one element."""
    element = result["elements"][element_id]
    length = float(element["length"])
    c = math.cos(float(element["angle"]))
    s = math.sin(float(element["angle"]))
    if str(element.get("type", "")).lower() == "frame":
        local_dofs = frame_local_displacement_dofs(result, element)
    else:
        local_dofs = _truss_like_local_dofs(result, element)

    x_base: list[float] = []
    y_base: list[float] = []
    x_def: list[float] = []
    y_def: list[float] = []
    for xi in station_xis(n_stations):
        x_local = xi * length
        gx, gy = local_to_global_station(result, element, x_local)
        disp = interpolate_frame_displacement(length, local_dofs, xi)
        x_base.append(gx)
        y_base.append(gy)
        x_def.append(gx + scale * (disp["u"] * c - disp["v"] * s))
        y_def.append(gy + scale * (disp["u"] * s + disp["v"] * c))
    return {"x": x_base, "y": y_base, "x_deformed": x_def, "y_deformed": y_def}


def local_to_global_station(result: dict[str, Any], element: dict[str, Any], x_local: float) -> tuple[float, float]:
    node_i = result["nodes"][element["node_i"]]
    c = math.cos(float(element["angle"]))
    s = math.sin(float(element["angle"]))
    return float(node_i["x"]) + float(x_local) * c, float(node_i["y"]) + float(x_local) * s


def project_point_to_element_station(
    point_x: float,
    point_y: float,
    node_i: dict[str, Any],
    node_j: dict[str, Any],
) -> dict[str, Any]:
    """Project a point to the nearest station on a straight element chord."""
    xi, yi = float(node_i["x"]), float(node_i["y"])
    xj, yj = float(node_j["x"]), float(node_j["y"])
    dx = xj - xi
    dy = yj - yi
    length2 = dx * dx + dy * dy
    if length2 <= 0.0:
        raise ValueError("element length must be positive.")
    t = ((float(point_x) - xi) * dx + (float(point_y) - yi) * dy) / length2
    t = max(0.0, min(1.0, t))
    cx = xi + t * dx
    cy = yi + t * dy
    distance = ((float(point_x) - cx) ** 2 + (float(point_y) - cy) ** 2) ** 0.5
    return {"xi": t, "closest_point": (cx, cy), "distance": distance}


def find_nearest_element_station(result_or_model: dict[str, Any], point_x: float, point_y: float) -> dict[str, Any] | None:
    """Find the nearest straight-chord element station to a point."""
    nodes = _normalize_node_mapping(result_or_model.get("nodes", {}))
    elements = _normalize_element_mapping(result_or_model.get("elements", {}))
    best: dict[str, Any] | None = None
    for element_id, element in elements.items():
        node_i = nodes.get(int(element["node_i"]))
        node_j = nodes.get(int(element["node_j"]))
        if node_i is None or node_j is None:
            continue
        projected = project_point_to_element_station(point_x, point_y, node_i, node_j)
        candidate = {"element": element_id, **projected}
        if best is None or candidate["distance"] < best["distance"]:
            best = candidate
    return best


def _truss_like_local_dofs(result: dict[str, Any], element: dict[str, Any]) -> list[float]:
    disp_i = result["displacements"][element["node_i"]]
    disp_j = result["displacements"][element["node_j"]]
    c = math.cos(float(element["angle"]))
    s = math.sin(float(element["angle"]))
    ui = c * float(disp_i["ux"]) + s * float(disp_i["uy"])
    vi = -s * float(disp_i["ux"]) + c * float(disp_i["uy"])
    uj = c * float(disp_j["ux"]) + s * float(disp_j["uy"])
    vj = -s * float(disp_j["ux"]) + c * float(disp_j["uy"])
    return [ui, vi, 0.0, uj, vj, 0.0]


def _normalize_node_mapping(raw_nodes: Any) -> dict[int, dict[str, Any]]:
    if isinstance(raw_nodes, dict):
        return {int(node_id): dict(node) for node_id, node in raw_nodes.items()}
    return {int(node["id"]): dict(node) for node in raw_nodes}


def _normalize_element_mapping(raw_elements: Any) -> dict[int, dict[str, Any]]:
    if isinstance(raw_elements, dict):
        return {int(element_id): dict(element) for element_id, element in raw_elements.items()}
    return {int(element["id"]): dict(element) for element in raw_elements}


def _clamp_xi(xi: float) -> float:
    return max(0.0, min(1.0, float(xi)))
