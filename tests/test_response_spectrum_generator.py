from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"

for path in (SRC_ROOT, ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from analysis.response_spectrum_generator import generate_elastic_response_spectrum  # noqa: E402
from visualization.ground_motion_plots import (  # noqa: E402
    plot_acceleration_history,
    plot_response_spectrum_sa,
    plot_response_spectrum_sd,
)


def test_response_spectrum_positive_finite_values():
    time = np.linspace(0.0, 2.0, 201)
    ag = 0.3 * np.sin(2.0 * np.pi * 2.0 * time)
    periods = np.array([0.2, 0.5, 1.0])

    spectrum = generate_elastic_response_spectrum(time, ag, periods, damping_ratio=0.05)

    assert np.all(np.isfinite(spectrum["Sa"]))
    assert np.all(np.isfinite(spectrum["Sv"]))
    assert np.all(np.isfinite(spectrum["Sd"]))
    assert np.any(spectrum["Sa"] > 0.0)
    assert np.any(spectrum["Sv"] > 0.0)
    assert np.any(spectrum["Sd"] > 0.0)


def test_zero_acceleration_gives_near_zero_spectrum():
    time = np.linspace(0.0, 1.0, 101)
    ag = np.zeros_like(time)
    periods = np.array([0.2, 0.5, 1.0])

    spectrum = generate_elastic_response_spectrum(time, ag, periods)

    assert np.max(np.abs(spectrum["Sa"])) < 1e-12
    assert np.max(np.abs(spectrum["Sv"])) < 1e-12
    assert np.max(np.abs(spectrum["Sd"])) < 1e-12


def test_ground_motion_plot_functions_save_figures(tmp_path):
    time = np.linspace(0.0, 1.0, 101)
    ag = 0.1 * np.sin(2.0 * np.pi * time)
    periods = np.array([0.2, 0.5, 1.0])
    spectrum = generate_elastic_response_spectrum(time, ag, periods)

    plot_cases = [
        ("acceleration_history.png", plot_acceleration_history, (time, ag)),
        ("response_spectrum_Sa.png", plot_response_spectrum_sa, (spectrum,)),
        ("response_spectrum_Sd.png", plot_response_spectrum_sd, (spectrum,)),
    ]
    for filename, plot_func, args in plot_cases:
        fig, _ax = plot_func(*args)
        output_path = tmp_path / filename
        fig.savefig(output_path)

        assert output_path.exists()
        assert output_path.stat().st_size > 0
