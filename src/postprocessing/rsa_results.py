"""Formatting helpers for per-mode RSA postprocessing results."""

from __future__ import annotations

from typing import Any


def rsa_modal_peak_response_rows(rsa_result: dict[str, Any]) -> list[dict[str, Any]]:
    """Return per-mode peak response rows in a stable table-ready shape."""
    rows = []
    for row in rsa_result.get("modal_peak_rows", []):
        rows.append(
            {
                "mode": row.get("mode", ""),
                "period_s": row.get("period_s", 0.0),
                "frequency_hz": row.get("frequency_hz", 0.0),
                "omega_rad_per_s": row.get("omega_rad_per_s", 0.0),
                "gamma": row.get("gamma", 0.0),
                "Sa": row.get("Sa_at_Tn", 0.0),
                "Sd": row.get("Sd_at_Tn", 0.0),
                "qmax": row.get("qmax", 0.0),
                "peak_roof_ux": row.get("peak_roof_ux", row.get("peak_roof_response", 0.0)),
                "controlling_roof_node": row.get("controlling_roof_node", ""),
            }
        )
    return rows


def rsa_modal_peak_story_drift_rows(rsa_result: dict[str, Any]) -> list[dict[str, Any]]:
    """Return per-mode story drift rows."""
    return [
        {
            "mode": row.get("mode", ""),
            "story": row.get("story", ""),
            "lower_elevation": row.get("lower_elevation", 0.0),
            "upper_elevation": row.get("upper_elevation", 0.0),
            "peak_story_drift": row.get("peak_story_drift", 0.0),
            "peak_drift_ratio": row.get("peak_drift_ratio", 0.0),
        }
        for row in rsa_result.get("story_drift_peak_by_mode", [])
    ]


def rsa_combined_response_rows(rsa_result: dict[str, Any]) -> list[dict[str, Any]]:
    """Return ABSSUM/SRSS/CQC rows for combined RSA responses."""
    combined = rsa_result.get("combined", {})
    rows: list[dict[str, Any]] = []

    roof = combined.get("roof_response", {})
    rows.append(
        {
            "quantity": "Roof ux",
            "location": "Roof",
            "ABSSUM": roof.get("ABSSUM", 0.0),
            "SRSS": roof.get("SRSS", 0.0),
            "CQC": roof.get("CQC", 0.0),
        }
    )

    for row in combined.get("floor_responses", []):
        rows.append(
            {
                "quantity": "Floor ux",
                "location": f"Floor {row.get('floor', '')} y={float(row.get('elevation', 0.0)):.6g}",
                "ABSSUM": row.get("ABSSUM", 0.0),
                "SRSS": row.get("SRSS", 0.0),
                "CQC": row.get("CQC", 0.0),
            }
        )

    for row in combined.get("story_drifts", []):
        rows.append(
            {
                "quantity": "Story drift",
                "location": f"Story {row.get('story', '')}",
                "ABSSUM": row.get("ABSSUM", 0.0),
                "SRSS": row.get("SRSS", 0.0),
                "CQC": row.get("CQC", 0.0),
            }
        )
        ratio = row.get("drift_ratio", {})
        rows.append(
            {
                "quantity": "Drift ratio",
                "location": f"Story {row.get('story', '')}",
                "ABSSUM": ratio.get("ABSSUM", 0.0),
                "SRSS": ratio.get("SRSS", 0.0),
                "CQC": ratio.get("CQC", 0.0),
            }
        )
    return rows
