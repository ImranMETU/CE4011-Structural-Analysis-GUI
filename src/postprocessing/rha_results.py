"""Post-processing table helpers for modal response-history analysis."""

from __future__ import annotations

from typing import Any


def format_rha_summary_rows(rha_result: dict[str, Any]) -> tuple[list[str], list[list[str]]]:
    """Return one-row RHA summary table."""
    peak_story = _max_by(rha_result.get("peak_story_drifts", []), "peak_absolute")
    peak_ratio = _max_by(rha_result.get("peak_story_drifts", []), "peak_drift_ratio")
    roof = rha_result.get("peak_roof_displacement", {})
    headers = [
        "record name",
        "dt",
        "duration",
        "PGA m/s2",
        "PGA g",
        "damping ratio",
        "modes used",
        "peak roof displacement",
        "controlling roof node",
        "max story drift",
        "controlling story",
        "max drift ratio",
        "controlling story",
    ]
    rows = [
        [
            str(rha_result.get("record_name", "")),
            _fmt(rha_result.get("dt", 0.0)),
            _fmt(rha_result.get("duration", 0.0)),
            _fmt(rha_result.get("pga_mps2", 0.0)),
            _fmt(rha_result.get("pga_g", 0.0)),
            _damping_text(rha_result.get("damping_ratio", "")),
            str(rha_result.get("modes_used", "")),
            _fmt(roof.get("value", 0.0)),
            "" if roof.get("node") is None else str(roof.get("node")),
            _fmt(peak_story.get("peak_absolute", 0.0)),
            "" if not peak_story else str(peak_story.get("story", "")),
            _fmt(peak_ratio.get("peak_drift_ratio", 0.0)),
            "" if not peak_ratio else str(peak_ratio.get("story", "")),
        ]
    ]
    return headers, rows


def format_peak_floor_response_rows(rha_result: dict[str, Any]) -> tuple[list[str], list[list[str]]]:
    """Return peak floor response rows."""
    headers = ["floor", "elevation", "peak positive ux", "peak negative ux", "peak absolute ux", "controlling time"]
    rows = []
    for row in rha_result.get("peak_floor_responses", []):
        rows.append(
            [
                str(row.get("floor", "")),
                _fmt(row.get("elevation", 0.0)),
                _fmt(row.get("peak_positive", 0.0)),
                _fmt(row.get("peak_negative", 0.0)),
                _fmt(row.get("peak_absolute", 0.0)),
                _fmt(row.get("controlling_time", 0.0)),
            ]
        )
    return headers, rows


def format_peak_story_drift_rows(rha_result: dict[str, Any]) -> tuple[list[str], list[list[str]]]:
    """Return peak story drift rows."""
    headers = [
        "story",
        "lower elevation",
        "upper elevation",
        "peak positive drift",
        "peak negative drift",
        "peak absolute drift",
        "peak drift ratio",
        "controlling time",
    ]
    rows = []
    for row in rha_result.get("peak_story_drifts", []):
        rows.append(
            [
                str(row.get("story", "")),
                _fmt(row.get("lower_elevation", 0.0)),
                _fmt(row.get("upper_elevation", 0.0)),
                _fmt(row.get("peak_positive", 0.0)),
                _fmt(row.get("peak_negative", 0.0)),
                _fmt(row.get("peak_absolute", 0.0)),
                _fmt(row.get("peak_drift_ratio", 0.0)),
                _fmt(row.get("controlling_time", 0.0)),
            ]
        )
    return headers, rows


def _max_by(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    if not rows:
        return {}
    return max(rows, key=lambda row: abs(float(row.get(key, 0.0))))


def _damping_text(value: Any) -> str:
    try:
        return _fmt(float(value))
    except (TypeError, ValueError):
        return str(value)


def _fmt(value: Any) -> str:
    return f"{float(value):.6e}"
