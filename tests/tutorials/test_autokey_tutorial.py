from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.tier_a


def test_autokey_tutorial_runs_both_modes():
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "tutorials" / "v1" / "Tutorial_Autokey.py"
    assert script.is_file(), "Tutorial script missing"
    src_path = repo_root / "src"
    launch = (
        "import runpy, sys; "
        f"sys.path.insert(0, {str(src_path)!r}); "
        f"runpy.run_path({str(script)!r}, run_name='__main__')"
    )

    result = subprocess.run(
        [sys.executable, "-c", launch],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )

    stdout = result.stdout
    matches = [float(m) for m in re.findall(r"Match ratio.*?:\s*([0-9.]+)", stdout)]
    assert len(matches) >= 2, f"expected two match ratios in output:\n{stdout}"
    assert all(m >= 0.90 for m in matches), stdout
    assert stdout.count("RDP standard summary") >= 2, stdout
    assert stdout.count("match_ratio: 1.0") >= 2, stdout
    assert stdout.count("stop_category: success") >= 2, stdout
