from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"

for path in (SRC_ROOT, ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from gui.result_tables import format_rsa_modal_peak_response_rows, format_rsa_modal_peak_story_drift_rows  # noqa: E402
from postprocessing.rsa_results import rsa_modal_peak_response_rows  # noqa: E402


def _rsa_result() -> dict:
    return {
        "modal_peak_rows": [
            {
                "mode": 1,
                "period_s": 1.0,
                "frequency_hz": 0.159,
                "omega_rad_per_s": 1.0,
                "gamma": 2.0,
                "Sa_at_Tn": 3.0,
                "Sd_at_Tn": 0.1,
                "qmax": 0.2,
                "peak_roof_ux": 0.4,
                "controlling_roof_node": 5,
            }
        ],
        "story_drift_peak_by_mode": [
            {"mode": 1, "story": 1, "lower_elevation": 0.0, "upper_elevation": 3.0, "peak_story_drift": 0.2, "peak_drift_ratio": 0.0667}
        ],
    }


def test_rsa_result_rows_contain_expected_keys():
    rows = rsa_modal_peak_response_rows(_rsa_result())

    assert {"mode", "period_s", "frequency_hz", "omega_rad_per_s", "gamma", "Sa", "Sd", "qmax"} <= set(rows[0])


def test_rsa_gui_table_formatters_return_expected_headers():
    headers, rows = format_rsa_modal_peak_response_rows(_rsa_result())
    drift_headers, drift_rows = format_rsa_modal_peak_story_drift_rows(_rsa_result())

    assert headers[:4] == ["Mode", "Period s", "Frequency Hz", "Omega rad/s"]
    assert drift_headers == ["Mode", "Story", "Lower Elevation", "Upper Elevation", "Peak Story Drift", "Peak Drift Ratio"]
    assert len(rows) == 1
    assert len(drift_rows) == 1
