from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_real_solve_tutorial_entrypoint_imports_and_runs() -> None:
    """This is a tutorial regression check.

    It runs the real-solve entry point. If this is too slow for the normal suite,
    move this test into a slower/manual test lane, but keep the tutorial itself.
    """
    proc = subprocess.run(
        [sys.executable, str(ROOT / "tutorials/v1/Tutorial_ScheduledStreamLookup_RealSolve_P13Sequence.py")],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=True,
    )
    assert "MODE: real key-recovery tutorial" in proc.stdout
    assert "DOES NOT SUPPLY: true key as initial_keys" in proc.stdout
