from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _run_tutorial(path: str) -> str:
    proc = subprocess.run(
        [sys.executable, str(ROOT / path)],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=True,
    )
    return proc.stdout


def test_generic_sequence_tutorial_runs() -> None:
    out = _run_tutorial("tutorials/v1/Tutorial_ScheduledStreamLookup_GenericSequence.py")
    assert "generic P13 plus supplied sequence" in out
    assert "periodic_plus_sequence preset" in out
    assert out.count("PASS/OK") >= 2


def test_periodic_plus_primes_tutorial_runs() -> None:
    out = _run_tutorial("tutorials/v1/Tutorial_PeriodicPlusPrimes.py")
    assert "P13 plus generated primes preset" in out
    assert "PASS/OK" in out


def test_overlay_tutorial_runs() -> None:
    out = _run_tutorial("tutorials/v1/Tutorial_ScheduledStreamLookup_Overlay.py")
    assert "overlaid P13 + P31 preset" in out
    assert "PASS/OK" in out


def test_segmented_tutorial_runs() -> None:
    out = _run_tutorial("tutorials/v1/Tutorial_ScheduledStreamLookup_Segmented.py")
    assert "segmented P13/P31/P13 preset" in out
    assert "segmented P31/P13/P31 preset" in out
    assert out.count("PASS/OK") >= 2
