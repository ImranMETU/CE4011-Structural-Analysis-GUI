"""Braced/unbraced comparison helpers for generated proposal models."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from analysis.modal_solver import solve_modal_analysis
from model.structure import Structure
from postprocessing.drift_results import compute_roof_displacement, compute_story_drift
from postprocessing.modal_results import package_modal_results
from postprocessing.static_results import run_static_analysis


def load_model_and_mass_mapping(
    model_path: str | Path,
    mass_path: str | Path | None = None,
) -> tuple[dict[str, Any], dict[int, dict[str, float]] | None]:
    """Load model JSON and optional companion modal mass mapping."""
    model_path = Path(model_path)
    with model_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("Model JSON root must be an object.")

    path = Path(mass_path) if mass_path is not None else model_path.with_name(f"{model_path.stem}_masses.json")
    if not path.exists():
        return data, None

    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, dict):
        raise ValueError("Mass mapping JSON root must be an object.")
    masses = {
        int(node_id): {
            "ux": float(values.get("ux", 0.0)),
            "uy": float(values.get("uy", 0.0)),
            "rz": float(values.get("rz", 0.0)),
        }
        for node_id, values in raw.items()
    }
    return data, masses


def analyze_static_response(model_path: str | Path) -> dict[str, Any]:
    """Run static analysis and compute drift/roof postprocessing."""
    data, _masses = load_model_and_mass_mapping(model_path, mass_path=None)
    static_result = run_static_analysis(data)
    drift_result = compute_story_drift(static_result, direction="ux", method="mean")
    roof_result = compute_roof_displacement(static_result, direction="ux", method="max_abs")
    return {
        "data": data,
        "static_result": static_result,
        "drift_result": drift_result,
        "roof_result": roof_result,
    }


def analyze_modal_response(
    model_path: str | Path,
    mass_path: str | Path | None = None,
    num_modes: int = 4,
) -> dict[str, Any] | None:
    """Run modal analysis using companion/generated masses when available."""
    data, masses = load_model_and_mass_mapping(model_path, mass_path=mass_path)
    if not masses:
        return None
    structure = Structure.from_dict(data)
    modal = solve_modal_analysis(structure, masses, n_modes=num_modes)
    return package_modal_results(modal, structure)


def compute_model_summary(
    model_name: str,
    model_path: str | Path,
    mass_path: str | Path | None = None,
    num_modes: int = 4,
) -> dict[str, Any]:
    """Compute static, drift, roof, and modal summary values for one model."""
    warnings: list[str] = []
    model_path = Path(model_path)
    data, masses = load_model_and_mass_mapping(model_path, mass_path=mass_path)
    structure = Structure.from_dict(data)

    element_types = [str(element.get("type", "")).lower() for element in data.get("elements", [])]
    static_result = run_static_analysis(data)
    drift_result = compute_story_drift(static_result, direction="ux", method="mean")
    roof_result = compute_roof_displacement(static_result, direction="ux", method="max_abs")

    max_drift_story = _max_or_none(drift_result.get("stories", []), "abs_story_drift")
    max_ratio_story = _max_or_none(drift_result.get("stories", []), "abs_drift_ratio")

    modal_result = None
    if masses:
        try:
            modal = solve_modal_analysis(Structure.from_dict(data), masses, n_modes=num_modes)
            modal_result = package_modal_results(modal, structure)
        except Exception as exc:  # pragma: no cover - exercised by defensive runtime path
            warnings.append(f"Modal analysis failed for {model_name}: {type(exc).__name__}: {exc}")
    else:
        warnings.append(f"No modal mass mapping available for {model_name}.")

    mode_1_participation = None
    if modal_result and modal_result.get("participation"):
        mode_1_participation = modal_result["participation"][0].get("effective_modal_mass_ratio")

    return {
        "model_name": model_name,
        "model_path": str(model_path),
        "mass_path": str(mass_path) if mass_path is not None else None,
        "node_count": len(data.get("nodes", [])),
        "element_count": len(data.get("elements", [])),
        "frame_element_count": element_types.count("frame"),
        "truss_element_count": element_types.count("truss"),
        "active_dofs": structure.n_active_dofs,
        "roof_displacement_ux": roof_result.get("roof_displacement"),
        "max_story_drift": None if max_drift_story is None else max_drift_story["abs_story_drift"],
        "controlling_drift_story": None if max_drift_story is None else max_drift_story["story"],
        "max_drift_ratio": None if max_ratio_story is None else max_ratio_story["abs_drift_ratio"],
        "controlling_drift_ratio_story": None if max_ratio_story is None else max_ratio_story["story"],
        "omega_1": _first(modal_result, "omega"),
        "f1_Hz": _first(modal_result, "frequencies_hz"),
        "T1_s": _first(modal_result, "periods"),
        "frequencies_hz": [] if modal_result is None else [float(value) for value in modal_result["frequencies_hz"][:num_modes]],
        "periods": [] if modal_result is None else [float(value) for value in modal_result["periods"][:num_modes]],
        "mode_1_effective_mass_ratio": mode_1_participation,
        "static_result": static_result,
        "drift_result": drift_result,
        "roof_result": roof_result,
        "modal_result": modal_result,
        "warnings": warnings,
    }


def compare_two_models(unbraced_summary: dict[str, Any], braced_summary: dict[str, Any]) -> dict[str, Any]:
    """Compare summary dictionaries and return metrics plus warnings."""
    warnings = list(unbraced_summary.get("warnings", [])) + list(braced_summary.get("warnings", []))
    metrics = {
        "roof_displacement_reduction_percent": percent_reduction(
            abs(unbraced_summary.get("roof_displacement_ux", 0.0)),
            abs(braced_summary.get("roof_displacement_ux", 0.0)),
            "roof displacement reduction",
            warnings,
        ),
        "max_story_drift_reduction_percent": percent_reduction(
            unbraced_summary.get("max_story_drift"),
            braced_summary.get("max_story_drift"),
            "max story drift reduction",
            warnings,
        ),
        "max_drift_ratio_reduction_percent": percent_reduction(
            unbraced_summary.get("max_drift_ratio"),
            braced_summary.get("max_drift_ratio"),
            "max drift ratio reduction",
            warnings,
        ),
        "fundamental_frequency_increase_percent": percent_change(
            unbraced_summary.get("f1_Hz"),
            braced_summary.get("f1_Hz"),
            "fundamental frequency increase",
            warnings,
        ),
        "fundamental_period_reduction_percent": percent_reduction(
            unbraced_summary.get("T1_s"),
            braced_summary.get("T1_s"),
            "fundamental period reduction",
            warnings,
        ),
    }
    _add_trend_warnings(unbraced_summary, braced_summary, warnings)
    return {
        "unbraced": unbraced_summary,
        "braced": braced_summary,
        "metrics": metrics,
        "warnings": warnings,
    }


def percent_change(
    baseline: float | None,
    comparison: float | None,
    label: str = "percent change",
    warnings: list[str] | None = None,
) -> float | None:
    """Return ``(comparison - baseline) / abs(baseline) * 100`` safely."""
    if baseline is None or comparison is None or abs(float(baseline)) == 0.0:
        if warnings is not None:
            warnings.append(f"Cannot compute {label}: missing or zero baseline.")
        return None
    return (float(comparison) - float(baseline)) / abs(float(baseline)) * 100.0


def percent_reduction(
    baseline: float | None,
    comparison: float | None,
    label: str = "percent reduction",
    warnings: list[str] | None = None,
) -> float | None:
    """Return ``(baseline - comparison) / abs(baseline) * 100`` safely."""
    if baseline is None or comparison is None or abs(float(baseline)) == 0.0:
        if warnings is not None:
            warnings.append(f"Cannot compute {label}: missing or zero baseline.")
        return None
    return (float(baseline) - float(comparison)) / abs(float(baseline)) * 100.0


def _add_trend_warnings(unbraced: dict[str, Any], braced: dict[str, Any], warnings: list[str]) -> None:
    if _abs_value(braced.get("roof_displacement_ux")) >= _abs_value(unbraced.get("roof_displacement_ux")):
        warnings.append("Expected braced roof displacement to be lower than unbraced, but trend was not observed.")
    if _value(braced.get("max_story_drift")) >= _value(unbraced.get("max_story_drift")):
        warnings.append("Expected braced max story drift to be lower than unbraced, but trend was not observed.")
    if _value(braced.get("f1_Hz")) <= _value(unbraced.get("f1_Hz")):
        warnings.append("Expected braced fundamental frequency to be higher than unbraced, but trend was not observed.")
    if _value(braced.get("T1_s")) >= _value(unbraced.get("T1_s")):
        warnings.append("Expected braced fundamental period to be lower than unbraced, but trend was not observed.")


def _max_or_none(rows: list[dict[str, Any]], key: str) -> dict[str, Any] | None:
    return None if not rows else max(rows, key=lambda row: float(row.get(key, 0.0)))


def _first(modal_result: dict[str, Any] | None, key: str) -> float | None:
    if modal_result is None or key not in modal_result or len(modal_result[key]) == 0:
        return None
    return float(modal_result[key][0])


def _value(value: Any) -> float:
    return float("-inf") if value is None else float(value)


def _abs_value(value: Any) -> float:
    return float("-inf") if value is None else abs(float(value))
