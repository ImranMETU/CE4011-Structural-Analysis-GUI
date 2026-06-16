from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
IO_ROOT = SRC_ROOT / "io"

for path in (SRC_ROOT, IO_ROOT, ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


def test_core_imports_do_not_create_circular_imports():
    import model.structure  # noqa: F401
    import model.frame_element  # noqa: F401
    import analysis.axis_transformation  # noqa: F401
    import analysis.modal_rha  # noqa: F401
    import postprocessing.comparison_results  # noqa: F401


def test_generate_proposal_models_script_runs():
    script = ROOT / "scripts" / "generate_proposal_models.py"

    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stdout + result.stderr
