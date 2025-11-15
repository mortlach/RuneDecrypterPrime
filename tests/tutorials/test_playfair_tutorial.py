from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.tier_a


def test_playfair_tutorial_runs_both_modes():
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "tutorials" / "v1" / "Tutorial_Playfair29.py"
    assert script.is_file()

    env = os.environ.copy()
    src_path = repo_root / "src"
    env["PYTHONPATH"] = f"{src_path}{os.pathsep}{env.get('PYTHONPATH','')}".rstrip(os.pathsep)

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
    ratios = [float(m) for m in re.findall(r"Match ratio .*?:\s*([0-9.]+)", stdout)]
    assert len(ratios) >= 2, stdout
    assert all(r >= 0.90 for r in ratios), stdout
    recovered = re.findall(r"Recovered\?\s*:\s*(\w+)", stdout)
    assert recovered.count("Yes") >= 2, stdout
