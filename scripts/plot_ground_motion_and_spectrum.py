"""Generate ground-motion and elastic response-spectrum plots."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
IO_ROOT = SRC_ROOT / "io"

for path in (SRC_ROOT, IO_ROOT, PROJECT_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from analysis.response_spectrum_generator import generate_elastic_response_spectrum  # noqa: E402
from ground_motion_loader import load_ground_motion  # noqa: E402
from visualization.ground_motion_plots import (  # noqa: E402
    plot_acceleration_history,
    plot_response_spectrum_sa,
    plot_response_spectrum_sd,
)


def main() -> int:
    if len(sys.argv) > 1:
        record_path = Path(sys.argv[1]).expanduser()
    else:
        record_path = PROJECT_ROOT / "DIN95Y01.THF"
        if not record_path.exists():
            print(
                "Usage: python scripts/plot_ground_motion_and_spectrum.py <record_path> [unit]\n"
                "Default unit is cm/s2. If no path is provided, the script looks for DIN95Y01.THF "
                "in the project root."
            )
            return 1

    input_unit = sys.argv[2] if len(sys.argv) > 2 else "cm/s2"
    output_dir = PROJECT_ROOT / "results" / "ground_motion"
    output_dir.mkdir(parents=True, exist_ok=True)

    record = load_ground_motion(record_path, input_unit=input_unit, output_unit="m/s2")
    periods = np.linspace(0.05, 4.0, 100)
    spectrum = generate_elastic_response_spectrum(record["time"], record["acceleration"], periods)

    plots = [
        ("acceleration_history.png", plot_acceleration_history, (record["time"], record["acceleration"])),
        ("response_spectrum_Sa.png", plot_response_spectrum_sa, (spectrum,)),
        ("response_spectrum_Sd.png", plot_response_spectrum_sd, (spectrum,)),
    ]
    for filename, plot_func, args in plots:
        fig, _ = plot_func(*args)
        fig.tight_layout()
        fig.savefig(output_dir / filename, dpi=150)
        plt.close(fig)

    print(f"Saved ground-motion plots to: {output_dir}")
    print(
        f"Record: n={record['n_points']}, dt={record['dt']:.6g}s, "
        f"duration={record['duration']:.6g}s, PGA={record['pga']:.6g} m/s2"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
