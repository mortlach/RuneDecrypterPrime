from __future__ import annotations

"""Opt-in runner for v1_release pretty-print tutorial variants.

This runner deliberately does not replace tutorials/v1/run_all.py or the normal
release manifest. It exercises only the new ``*_PrettyPrint.py`` variants so the
original tutorials can remain stable until the new variants are reviewed.
"""

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TUTORIAL_DIR = Path(__file__).resolve().parent
STOP_ON_FIRST_FAILURE = os.environ.get("RDP_PRETTY_STOP_ON_FIRST_FAILURE", "0").strip().lower() in {"1", "true", "yes", "on"}
ECHO_OUTPUT = os.environ.get("RDP_PRETTY_ECHO_OUTPUT", "0").strip().lower() in {"1", "true", "yes", "on"}
TAIL_LINES = 80


@dataclass(frozen=True)
class PrettyTutorial:
    path: str
    min_match_ratio: float


PRETTY_RELEASE_TUTORIALS: tuple[PrettyTutorial, ...] = (
    PrettyTutorial("Tutorial_ColumnarTransposition_PrettyPrint.py", 1.0),
    PrettyTutorial("Tutorial_Vigenere_GeneralMap_PrettyPrint.py", 1.0),
    PrettyTutorial("Tutorial_Vigenere_Interruptors_Solve_PrettyPrint.py", 1.0),
    PrettyTutorial("Tutorial_MonoSubstitution_GA_PrettyPrint.py", 0.97),
    PrettyTutorial("Tutorial_ScheduledStreamLookup_RealSolve_P13Sequence_PrettyPrint.py", 1.0),
    PrettyTutorial("Tutorial_LP_Welcome_Pilgrim_Solve_PrettyPrint.py", 1.0),
)


@dataclass(frozen=True)
class PrettyResult:
    path: str
    returncode: int
    match_ratio: float | None
    passed: bool


def _parse_last_float(pattern: str, text: str) -> float | None:
    vals = re.findall(pattern, text, flags=re.IGNORECASE)
    if not vals:
        return None
    try:
        return float(vals[-1])
    except ValueError:
        return None


def _parse_match_ratio(text: str) -> float | None:
    return _parse_last_float(r"(?:Match ratio(?:\s*\([^)]*\))?|match_ratio)\s*:?\s*([0-9]+(?:\.[0-9]+)?)", text)


def _tail(text: str, *, lines: int = TAIL_LINES) -> str:
    chunks = text.rstrip().splitlines()
    return "\n".join(chunks[-lines:])


def _run_one(entry: PrettyTutorial) -> PrettyResult:
    script = TUTORIAL_DIR / entry.path
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        env={**os.environ, "PYTHONUTF8": "1"},
    )
    output = (proc.stdout or "") + (proc.stderr or "")
    if ECHO_OUTPUT or proc.returncode != 0:
        print(f"\n--- output: {entry.path} ---")
        print(output.rstrip())
    match_ratio = _parse_match_ratio(output)
    passed = proc.returncode == 0 and match_ratio is not None and match_ratio >= entry.min_match_ratio
    if not passed and not ECHO_OUTPUT:
        print(f"\n--- tail: {entry.path} ---")
        print(_tail(output))
    return PrettyResult(entry.path, proc.returncode, match_ratio, passed)


def main() -> int:
    print("RDP pretty-print release tutorial runner")
    print(f"selected: {len(PRETTY_RELEASE_TUTORIALS)}")
    results: list[PrettyResult] = []
    for entry in PRETTY_RELEASE_TUTORIALS:
        print(f"[RUN ] {entry.path}")
        result = _run_one(entry)
        results.append(result)
        status = "PASS" if result.passed else "FAIL"
        match_text = "none" if result.match_ratio is None else f"{result.match_ratio:.3f}"
        print(f"[{status}] {entry.path} match_ratio={match_text} min={entry.min_match_ratio:.3f}")
        if not result.passed and STOP_ON_FIRST_FAILURE:
            break

    passed = sum(1 for result in results if result.passed)
    failed = len(results) - passed
    print("\nPretty-print release summary")
    print(f"selected={len(PRETTY_RELEASE_TUTORIALS)} run={len(results)} passed={passed} failed={failed}")
    return 0 if failed == 0 and len(results) == len(PRETTY_RELEASE_TUTORIALS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
