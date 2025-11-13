from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.tier_a


def test_railfence_tutorial_script_recovers_plaintext():
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "tutorials" / "v1" / "Tutorial_Railfence.py"
    assert script.is_file(), "tutorial script is missing"

    env = os.environ.copy()
    src_path = repo_root / "src"
    py_path = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        f"{src_path}{os.pathsep}{py_path}" if py_path else str(src_path)
    )

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
    assert "Recovered? : Yes" in stdout, stdout
    match = re.search(r"Match ratio:\s*([0-9.]+)", stdout)
    assert match, f"match ratio not found in output:\n{stdout}"
    assert float(match.group(1)) >= 0.95
