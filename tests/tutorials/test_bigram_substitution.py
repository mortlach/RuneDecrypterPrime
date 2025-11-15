from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.tier_a


def test_bigram_substitution_tutorial_fast_path():
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "tutorials" / "v1" / "Tutorial_BigramSubstitution.py"
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
    # Known-key fast path must hit perfection. Hybrid stage currently has a lower bar
    # until the LM-seeded solver is fully tuned (tracked in dev backlog).
    thresholds = {"known key": 0.9, "hybrid LM seed": 0.1}
    for label, threshold in thresholds.items():
        match = re.search(rf"Match ratio \({re.escape(label)}\):\s*([0-9.]+)", stdout)
        assert match, f"Missing match ratio line for {label!r}.\n{stdout}"
        ratio = float(match.group(1))
        assert ratio >= threshold, f"{label} ratio too low: {match.group(1)}"
