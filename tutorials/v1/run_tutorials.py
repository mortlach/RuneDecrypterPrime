"""Run RDP V1 tutorials and worked examples from a source checkout.

The runner makes ``src/`` importable for itself and its child processes, so the
RDP package does not have to be installed just to use this source-tree runner.
Python dependencies and any native extensions required by the selected examples
still need to be available.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import uuid
from enum import StrEnum
from pathlib import Path
from collections.abc import Sequence


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
TUTORIAL_ROOT = Path(__file__).resolve().parent
GETTING_STARTED_DIR = TUTORIAL_ROOT / "getting_started"
EXAMPLES_DIR = TUTORIAL_ROOT / "examples"

# Prefer the checkout when an installed RDP also exists.
while str(SRC) in sys.path:
    sys.path.remove(str(SRC))
sys.path.insert(0, str(SRC))

from rdp.core.config.output_paths import path_from, resolve_output_root


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
OUTPUT_DIR: Path | None = None
_ACTIVE_OUTPUT: Path | None = None
FAILURE_TAIL_LINES = 80

GROUPS: dict[str, TutorialRunSet] = {
    "getting-started": TutorialRunSet.GETTING_STARTED,
    "release": TutorialRunSet.RELEASE,
    "bundled": TutorialRunSet.BUNDLED_EXAMPLES,
    "full-assets": TutorialRunSet.FULL_ASSET_EXAMPLES,
    "qualification": TutorialRunSet.QUALIFICATION,
}

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


def _getting_started() -> tuple[Path, ...]:
    paths = _discover(GETTING_STARTED_DIR, "[0-9][0-9]_*.py")
    if not paths:
        raise FileNotFoundError("no getting-started files were discovered")
    return paths


def _examples() -> tuple[Path, ...]:
    paths = tuple(
        path
        for path in _discover(EXAMPLES_DIR, "*.py")
        if path.name != "__init__.py"
    )
    if not paths:
        raise FileNotFoundError("no V1 examples were discovered")
    return paths


def _named_examples(names: tuple[str, ...]) -> tuple[Path, ...]:
    paths = tuple(EXAMPLES_DIR / name for name in names)
    missing = [path.name for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing V1 examples: {', '.join(missing)}")
    return paths


def _selected_tutorials(
    run_set: TutorialRunSet | None = None,
) -> tuple[Path, ...]:
    selected_set = RUN_SET if run_set is None else run_set
    getting_started = _getting_started()
    examples = _examples()

    if selected_set is TutorialRunSet.GETTING_STARTED:
        return getting_started
    if selected_set is TutorialRunSet.RELEASE:
        return getting_started + _named_examples(RELEASE_EXAMPLE_NAMES)
    if selected_set is TutorialRunSet.BUNDLED_EXAMPLES:
        return tuple(
            path for path in examples if path.name not in FULL_ASSET_ONLY_NAMES
        )
    if selected_set is TutorialRunSet.FULL_ASSET_EXAMPLES:
        return _named_examples(FULL_ASSET_EXAMPLE_NAMES)
    if selected_set is TutorialRunSet.QUALIFICATION:
        return _named_examples(QUALIFICATION_NAMES)
    raise ValueError(f"unsupported tutorial run set: {selected_set!r}")


def _all_runnable_material() -> tuple[Path, ...]:
    return _getting_started() + _examples()


def _match_one(name: str, paths: Sequence[Path]) -> Path:
    token = name.strip()
    if not token:
        raise ValueError("empty tutorial name")

    exact = [
        path
        for path in paths
        if token in {path.name, path.stem, _relative(path)}
    ]
    if len(exact) == 1:
        return exact[0]

    if token.isdigit():
        prefix = f"{int(token):02d}_"
        numbered = [path for path in _getting_started() if path.stem.startswith(prefix)]
        if len(numbered) == 1:
            return numbered[0]

    by_stem_prefix = [path for path in paths if path.stem.startswith(token)]
    if len(by_stem_prefix) == 1:
        return by_stem_prefix[0]
    if len(by_stem_prefix) > 1:
        choices = ", ".join(path.stem for path in by_stem_prefix)
        raise ValueError(f"{name!r} is ambiguous; matches: {choices}")

    raise ValueError(f"no tutorial/example matched {name!r}; use --list")


def _resolve_only(names: Sequence[str]) -> tuple[Path, ...]:
    all_paths = _all_runnable_material()
    resolved: list[Path] = []
    seen: set[Path] = set()
    for name in names:
        path = _match_one(name, all_paths)
        if path not in seen:
            resolved.append(path)
            seen.add(path)
    return tuple(resolved)


def _print_catalogue() -> None:
    print("Runner groups")
    for name in GROUPS:
        print(f"  {name}")

    print("\nGetting started")
    for path in _getting_started():
        print(f"  {path.stem}")

    print("\nWorked examples")
    for path in _examples():
        tags: list[str] = []
        if path.name in FULL_ASSET_ONLY_NAMES:
            tags.append("full-assets")
        if path.name in QUALIFICATION_NAMES:
            tags.append("qualification")
        suffix = "" if not tags else f"  [{', '.join(tags)}]"
        print(f"  {path.stem}{suffix}")


def _output_dir() -> Path:
    if _ACTIVE_OUTPUT is None:
        raise RuntimeError("Tutorial output has not been initialized")
    return _ACTIVE_OUTPUT


def _prepare_output_dir() -> None:
    global _ACTIVE_OUTPUT
    _ACTIVE_OUTPUT = resolve_output_root(OUTPUT_DIR) / "tutorial_logs" / uuid.uuid4().hex
    _ACTIVE_OUTPUT.mkdir(parents=True)


def _relative(path: Path) -> str:
    return path_from(path, ROOT).replace(os.sep, "/")


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


def _child_environment(script: Path) -> dict[str, str]:
    existing = os.environ.get("PYTHONPATH")
    pythonpath = str(SRC) if not existing else os.pathsep.join((str(SRC), existing))
    return {
        **os.environ,
        "PYTHONPATH": pythonpath,
        "RDP_OUTPUT_ROOT": str(_output_dir() / script.stem),
    }


def _run_one(script: Path) -> tuple[bool, Path | None]:
    completed = subprocess.run(
        [sys.executable, "-X", "utf8", "-m", _module_name(script)],
        cwd=ROOT,
        env=_child_environment(script),
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


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run RDP V1 tutorials/examples from this checkout."
    )
    parser.add_argument(
        "group",
        nargs="?",
        choices=tuple(GROUPS),
        default=None,
        help="runner group (default: release)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="list groups and runnable tutorial/example names, then exit",
    )
    parser.add_argument(
        "--only",
        nargs="+",
        metavar="NAME",
        help="run only named items; accepts a stem, filename, path, or 01..10",
    )
    parser.add_argument(
        "--full-output",
        action="store_true",
        help="show each script's complete console output",
    )
    parser.add_argument(
        "--stop-on-first-failure",
        action="store_true",
        help="stop after the first failed script",
    )
    parser.add_argument(
        "--no-logs",
        action="store_true",
        help="do not save per-script tutorial logs",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] = ()) -> int:
    global CONSOLE_OUTPUT, STOP_ON_FIRST_FAILURE, WRITE_OUTPUT_LOGS

    args = _parse_args(argv)
    if args.list:
        try:
            _print_catalogue()
        except (FileNotFoundError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        return 0

    if args.full_output:
        CONSOLE_OUTPUT = ConsoleOutput.FULL
    if args.stop_on_first_failure:
        STOP_ON_FIRST_FAILURE = True
    if args.no_logs:
        WRITE_OUTPUT_LOGS = False

    try:
        selected = (
            _resolve_only(args.only)
            if args.only
            else _selected_tutorials(GROUPS[args.group] if args.group else RUN_SET)
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    _prepare_output_dir()
    label = "selected" if args.only else (args.group or RUN_SET.value)
    print("Rune Decrypter Prime V1 runnable material")
    print(f"run set: {label}")
    print(f"selected: {len(selected)}")
    print("acceptance: every script must complete its own semantic assertions")

    selected_names = {path.name for path in selected}
    if selected_names & FULL_ASSET_ONLY_NAMES:
        print("NOTICE: this selection requires the full V1 asset profile")
    if selected_names & set(QUALIFICATION_NAMES):
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
    raise SystemExit(main(sys.argv[1:]))
