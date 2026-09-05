"""Run the ordered V1 route or one explicit group of retained examples.

The scripts own their semantic assertions.  This runner selects files, starts
each one in a subprocess and reports whether it exited cleanly.  Edit RUN_SET
below; there is deliberately no second configuration surface.
"""

from __future__ import annotations

import subprocess
import sys
from enum import StrEnum
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TUTORIAL_ROOT = Path(__file__).resolve().parent
GETTING_STARTED_DIR = TUTORIAL_ROOT / "getting_started"
EXAMPLES_DIR = TUTORIAL_ROOT / "examples"


class TutorialRunSet(StrEnum):
    GETTING_STARTED = "getting_started"
    RELEASE = "release"
    BUNDLED_EXAMPLES = "bundled_examples"
    FULL_ASSET_EXAMPLES = "full_asset_examples"
    QUALIFICATION = "qualification"


class ConsoleOutput(StrEnum):
    COMPACT = "compact"
    FULL = "full"


RUN_SET = TutorialRunSet.RELEASE
CONSOLE_OUTPUT = ConsoleOutput.COMPACT
STOP_ON_FIRST_FAILURE = False
WRITE_OUTPUT_LOGS = True
CLEAN_OUTPUT_LOGS = True
OUTPUT_DIR = Path("output/tutorial_logs")
FAILURE_TAIL_LINES = 80

# RELEASE adds three different cipher/problem shapes to the complete short
# route. The expanded selection has not been timed as a whole.
RELEASE_EXAMPLE_NAMES = (
    "columnar_transposition.py",
    "repeating_multiply.py",
    "scheduled_stream_lookup_p13_sequence.py",
)
FULL_ASSET_EXAMPLE_NAMES = (
    "two_period_cribs.py",
    "two_period_cribs_interruptors.py",
)
QUALIFICATION_NAMES = (
    "periodic_substitution.py",
    "periodic_substitution_p7.py",
    "periodic_columnar_p7_column_then_substitution.py",
)
FULL_ASSET_ONLY_NAMES = frozenset(
    {
        *FULL_ASSET_EXAMPLE_NAMES,
        "two_period_cribs_p13_p31_search.py",
        *QUALIFICATION_NAMES,
    }
)


def _discover(directory: Path, pattern: str) -> tuple[Path, ...]:
    return tuple(sorted(path for path in directory.glob(pattern) if path.is_file()))


def _named_examples(names: tuple[str, ...]) -> tuple[Path, ...]:
    paths = tuple(EXAMPLES_DIR / name for name in names)
    missing = [path.name for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing V1 examples: {', '.join(missing)}")
    return paths


def _selected_tutorials() -> tuple[Path, ...]:
    getting_started = _discover(GETTING_STARTED_DIR, "[0-9][0-9]_*.py")
    examples = _discover(EXAMPLES_DIR, "*.py")
    examples = tuple(path for path in examples if path.name != "__init__.py")
    if not getting_started:
        raise FileNotFoundError("no getting-started files were discovered")
    if not examples:
        raise FileNotFoundError("no V1 examples were discovered")

    if RUN_SET is TutorialRunSet.GETTING_STARTED:
        return getting_started
    if RUN_SET is TutorialRunSet.RELEASE:
        return getting_started + _named_examples(RELEASE_EXAMPLE_NAMES)
    if RUN_SET is TutorialRunSet.BUNDLED_EXAMPLES:
        return tuple(
            path for path in examples if path.name not in FULL_ASSET_ONLY_NAMES
        )
    if RUN_SET is TutorialRunSet.FULL_ASSET_EXAMPLES:
        return _named_examples(FULL_ASSET_EXAMPLE_NAMES)
    if RUN_SET is TutorialRunSet.QUALIFICATION:
        return _named_examples(QUALIFICATION_NAMES)
    raise ValueError(f"unsupported tutorial run set: {RUN_SET!r}")


def _output_dir() -> Path:
    if OUTPUT_DIR.is_absolute():
        raise ValueError("OUTPUT_DIR must be repo-relative, not absolute")
    output_dir = (ROOT / OUTPUT_DIR).resolve()
    output_root = (ROOT / "output").resolve()
    if output_root not in output_dir.parents:
        raise ValueError("OUTPUT_DIR must stay under output/")
    return output_dir


def _prepare_output_dir() -> None:
    if not WRITE_OUTPUT_LOGS:
        return
    output_dir = _output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    if CLEAN_OUTPUT_LOGS:
        for path in output_dir.glob("*.txt"):
            if path.is_file():
                path.unlink()


def _relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _module_name(script: Path) -> str:
    """Return the repository module name for one selected Python file."""
    return ".".join(script.relative_to(ROOT).with_suffix("").parts)


def _write_output_log(script: Path, output: str) -> Path | None:
    if not WRITE_OUTPUT_LOGS:
        return None
    path = _output_dir() / f"{script.parent.name}_{script.stem}.txt"
    path.write_text(output, encoding="utf-8")
    return path


def _tail(text: str) -> str:
    return "\n".join(text.rstrip().splitlines()[-FAILURE_TAIL_LINES:])


def _run_one(script: Path) -> tuple[bool, Path | None]:
    completed = subprocess.run(
        [sys.executable, "-X", "utf8", "-m", _module_name(script)],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    output = (completed.stdout or "") + (completed.stderr or "")
    output_path = _write_output_log(script, output)
    passed = completed.returncode == 0
    if CONSOLE_OUTPUT is ConsoleOutput.FULL:
        print(f"\n--- output: {_relative(script)} ---")
        print(output.rstrip())
    elif not passed:
        print(f"\n--- failure: {_relative(script)} ---")
        print(_tail(output))
    return passed, output_path


def main() -> int:
    selected = _selected_tutorials()
    _prepare_output_dir()
    print("Rune Decrypter Prime V1 runnable material")
    print(f"run set: {RUN_SET.value}")
    print(f"selected: {len(selected)}")
    print("acceptance: every script must complete its own semantic assertions")

    if RUN_SET in {
        TutorialRunSet.FULL_ASSET_EXAMPLES,
        TutorialRunSet.QUALIFICATION,
    }:
        print("NOTICE: this selection requires the full V1 asset profile")
    if RUN_SET is TutorialRunSet.QUALIFICATION:
        print("WARNING: qualification programs may take several hours each")

    results: list[bool] = []
    for script in selected:
        relative = _relative(script)
        print(f"[RUN ] {relative}")
        passed, output_path = _run_one(script)
        results.append(passed)
        log = "" if output_path is None else f" log={_relative(output_path)}"
        print(f"[{'PASS' if passed else 'FAIL'}] {relative}{log}")
        if not passed and STOP_ON_FIRST_FAILURE:
            break

    passed_count = sum(results)
    failed_count = len(results) - passed_count
    print("\nRun summary")
    print(
        f"selected={len(selected)} run={len(results)} "
        f"passed={passed_count} failed={failed_count}"
    )
    return 0 if failed_count == 0 and len(results) == len(selected) else 1


if __name__ == "__main__":
    raise SystemExit(main())
