from __future__ import annotations

import os
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

    env = os.environ.copy()
    src_path = repo_root / "src"
    current = env.get("PYTHONPATH")
    env["PYTHONPATH"] = f"{src_path}{os.pathsep}{current}" if current else str(src_path)

    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(repo_root),
        env=env,
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
    recovered_flags = re.findall(r"Recovered\?\s*:\s*(\w+)", stdout)
    assert recovered_flags.count("Yes") >= 2, stdout
