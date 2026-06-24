from __future__ import annotations

"""Run the final V1 pretty-print tutorial review list.

The tutorial list, thresholds, console-output policy, and output-log location are
constants in this file. Public V1 tutorial runners do not use environment
variables, CLI switches, or separate config files for normal control.
"""

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TUTORIAL_DIR = Path(__file__).resolve().parent

TITLE = "V1 pretty-print tutorial review"
SHOW_OUTPUT = False
STOP_ON_FIRST_FAILURE = False
WRITE_LOGS = True
OUTPUT_DIR = Path("output/tutorial_pretty_print_logs")
TAIL_LINES = 80


@dataclass(frozen=True)
class PrettyTutorial:
    path: str
    min_match_ratio: float


TUTORIALS: tuple[PrettyTutorial, ...] = (
    PrettyTutorial("Start_Here.py", 1.0),
    PrettyTutorial("Tutorial_Autokey.py", 1.0),
    PrettyTutorial("Tutorial_Railfence.py", 1.0),
    PrettyTutorial("Tutorial_Vigenere_Interruptors_Exact.py", 1.0),
    PrettyTutorial("Tutorial_ColumnarTransposition.py", 1.0),
    PrettyTutorial("Tutorial_Vigenere_GeneralMap.py", 1.0),
    PrettyTutorial("Tutorial_Vigenere_Interruptors_Solve.py", 1.0),
    PrettyTutorial("Tutorial_MonoSubstitution_GA_RTL.py", 0.97),
    PrettyTutorial("Tutorial_MonoSubstitution_GA_LTR.py", 0.97),
    PrettyTutorial("Tutorial_Repeating_multiply.py", 1.0),
    PrettyTutorial("Tutorial_MonoSubstitution_HYBRID_RTL.py", 0.995),
    PrettyTutorial("Tutorial_Vigenere_Interruptors_NonTrivial.py", 1.0),
    PrettyTutorial("Tutorial_ScheduledStreamLookup_RealSolve_P13Sequence.py", 1.0),
    PrettyTutorial("Tutorial_ScheduledStreamLookup_RealSolve_P13Primes.py", 1.0),
    PrettyTutorial("Tutorial_ScheduledStreamLookup_RealSolve_P13P31Segmented.py", 0.9),
    PrettyTutorial("Tutorial_LP_Welcome_Pilgrim_Solve.py", 1.0),
    PrettyTutorial("Tutorial_MonoSubstitution_SA_LTR.py", 0.995),
    PrettyTutorial("Tutorial_PeriodicSubstitution.py", 1.0),
    PrettyTutorial("Tutorial_PeriodicSubstitution_Simple_P7.py", 1.0),
    PrettyTutorial("Tutorial_PeriodicColumnar.py", 1.0),
    PrettyTutorial("Tutorial_PeriodicColumnar_Simple_P7_ColThenSub.py", 1.0),
)


@dataclass(frozen=True)
class PrettyResult:
    path: str
    returncode: int
    match_ratio: float | None
    passed: bool
    output_path: Path | None


def _validate_tutorials() -> None:
    if not TUTORIALS:
        raise ValueError("TUTORIALS must contain at least one tutorial.")
    for index, entry in enumerate(TUTORIALS, start=1):
        script_path = TUTORIAL_DIR / entry.path
        if script_path.name != entry.path or not entry.path.endswith(".py"):
            raise ValueError(f"TUTORIALS[{index}] path must be a simple Python filename.")
        if not 0.0 <= float(entry.min_match_ratio) <= 1.0:
            raise ValueError(f"TUTORIALS[{index}] min_match_ratio must be between 0.0 and 1.0.")
        if not script_path.is_file():
            raise FileNotFoundError(f"TUTORIALS[{index}] does not exist: {script_path}")


def _output_dir() -> Path:
    if OUTPUT_DIR.is_absolute():
        raise ValueError("OUTPUT_DIR must be repo-relative, not absolute.")
    return ROOT / OUTPUT_DIR


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


def _tail(text: str, *, lines: int) -> str:
    chunks = text.rstrip().splitlines()
    return "\n".join(chunks[-lines:])


def _relpath(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _write_output_log(entry: PrettyTutorial, output: str) -> Path | None:
    if not WRITE_LOGS:
        return None
    output_dir = _output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / (Path(entry.path).stem + ".txt")
    output_path.write_text(output, encoding="utf-8")
    return output_path


def _run_one(entry: PrettyTutorial) -> PrettyResult:
    script = TUTORIAL_DIR / entry.path
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", str(script)],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    output = (proc.stdout or "") + (proc.stderr or "")
    output_path = _write_output_log(entry, output)
    if SHOW_OUTPUT or proc.returncode != 0:
        print(f"\n--- output: {entry.path} ---")
        print(output.rstrip())
    match_ratio = _parse_match_ratio(output)
    passed = proc.returncode == 0 and match_ratio is not None and match_ratio >= entry.min_match_ratio
    if not passed and not SHOW_OUTPUT:
        print(f"\n--- tail: {entry.path} ---")
        print(_tail(output, lines=TAIL_LINES))
    return PrettyResult(entry.path, proc.returncode, match_ratio, passed, output_path)


def main() -> int:
    _validate_tutorials()

    print("RDP pretty-print tutorial runner")
    print(f"title : {TITLE}")
    print(f"selected: {len(TUTORIALS)}")
    if WRITE_LOGS:
        print(f"output logs: {_relpath(_output_dir())}")

    results: list[PrettyResult] = []
    for entry in TUTORIALS:
        print(f"[RUN ] {entry.path}")
        result = _run_one(entry)
        results.append(result)
        status = "PASS" if result.passed else "FAIL"
        match_text = "none" if result.match_ratio is None else f"{result.match_ratio:.3f}"
        log_text = "" if result.output_path is None else f" log={_relpath(result.output_path)}"
        print(f"[{status}] {entry.path} match_ratio={match_text} min={entry.min_match_ratio:.3f}{log_text}")
        if not result.passed and STOP_ON_FIRST_FAILURE:
            break

    passed = sum(1 for result in results if result.passed)
    failed = len(results) - passed
    print("\nPretty-print summary")
    print(f"selected={len(TUTORIALS)} run={len(results)} passed={passed} failed={failed}")
    return 0 if failed == 0 and len(results) == len(TUTORIALS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
