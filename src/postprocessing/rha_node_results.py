"""Selected-node response-history extraction for modal RHA results."""

from __future__ import annotations

from typing import Any

import numpy as np


SUPPORTED_DOFS = ("ux", "uy", "rz")


def get_available_rha_nodes(rha_result: dict[str, Any]) -> list[int]:
    """Return node ids with available RHA displacement histories."""
    histories = rha_result.get("node_displacement_histories", {})
    return sorted(int(node_id) for node_id in histories)


def extract_node_response_history(
    rha_result: dict[str, Any],
    node_id: int,
    dof: str = "ux",
) -> dict[str, Any]:
    """Extract a selected node/DOF response history from an RHA result."""
    dof = str(dof).lower()
    if dof not in SUPPORTED_DOFS:
        raise ValueError("dof must be ux, uy, or rz.")
    histories = rha_result.get("node_displacement_histories", {})
    node_key = int(node_id)
    if node_key not in histories:
        raise ValueError(f"Node {node_id} is not available in RHA node histories.")
    history = _history_for_dof(histories[node_key], dof)
    time = np.asarray(rha_result.get("time", []), dtype=float)
    if time.size != history.size:
        raise ValueError("RHA time vector and node response history have different lengths.")
    peaks = _response_peaks(time, history)
    return {"node": node_key, "dof": dof, "time": time, "response": history, **peaks}


def compute_node_response_peaks(
    rha_result: dict[str, Any],
    node_ids: list[int] | None = None,
    dofs: tuple[str, ...] = ("ux",),
) -> list[dict[str, Any]]:
    """Return peak response summaries for selected nodes and DOFs."""
    nodes = get_available_rha_nodes(rha_result) if node_ids is None else [int(node_id) for node_id in node_ids]
    rows = []
    for node_id in nodes:
        for dof in dofs:
            try:
                rows.append(extract_node_response_history(rha_result, node_id, dof))
            except ValueError:
                continue
    return rows


def format_node_response_rows(rows: list[dict[str, Any]]) -> tuple[list[str], list[list[str]]]:
    """Return display rows for node response peaks."""
    headers = [
        "Node",
        "DOF",
        "Peak Positive",
        "Time of Peak Positive",
        "Peak Negative",
        "Time of Peak Negative",
        "Peak Absolute",
        "Time of Peak Absolute",
    ]
    table = []
    for row in rows:
        table.append(
            [
                str(row.get("node", "")),
                str(row.get("dof", "")),
                _fmt(row.get("peak_positive", 0.0)),
                _fmt(row.get("time_peak_positive", 0.0)),
                _fmt(row.get("peak_negative", 0.0)),
                _fmt(row.get("time_peak_negative", 0.0)),
                _fmt(row.get("peak_absolute", 0.0)),
                _fmt(row.get("time_peak_absolute", 0.0)),
            ]
        )
    return headers, table


def _history_for_dof(raw_history: Any, dof: str) -> np.ndarray:
    if isinstance(raw_history, dict):
        if dof not in raw_history:
            raise ValueError(f"DOF {dof} is not available for this RHA node history.")
        return np.asarray(raw_history[dof], dtype=float)
    if dof != "ux":
        raise ValueError(f"DOF {dof} is not available; current RHA result stores ux histories.")
    return np.asarray(raw_history, dtype=float)


def _response_peaks(time: np.ndarray, response: np.ndarray) -> dict[str, float]:
    if response.size == 0:
        return {
            "peak_positive": 0.0,
            "time_peak_positive": 0.0,
            "peak_negative": 0.0,
            "time_peak_negative": 0.0,
            "peak_absolute": 0.0,
            "time_peak_absolute": 0.0,
        }
    pos_idx = int(np.argmax(response))
    neg_idx = int(np.argmin(response))
    abs_idx = int(np.argmax(np.abs(response)))
    return {
        "peak_positive": float(response[pos_idx]),
        "time_peak_positive": float(time[pos_idx]),
        "peak_negative": float(response[neg_idx]),
        "time_peak_negative": float(time[neg_idx]),
        "peak_absolute": float(abs(response[abs_idx])),
        "time_peak_absolute": float(time[abs_idx]),
    }


def _fmt(value: Any) -> str:
    return f"{float(value):.6e}"
