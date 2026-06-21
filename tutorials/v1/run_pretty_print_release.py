from __future__ import annotations

"""Run V1 pretty-print tutorial variants from the adjacent config file.

The tutorial list, thresholds, console-output policy, and output-log location live
in ``pretty_print_release_config.toml`` next to this runner. That keeps the runner
stable and makes review settings visible without environment variables or CLI
switches.
"""

import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
TUTORIAL_DIR = Path(__file__).resolve().parent
CONFIG_PATH = TUTORIAL_DIR / "pretty_print_release_config.toml"


@dataclass(frozen=True)
class PrettyTutorial:
    path: str
    min_match_ratio: float


@dataclass(frozen=True)
class PrettyRunnerConfig:
    title: str
    tutorials: tuple[PrettyTutorial, ...]
    show_output: bool
    stop_on_first_failure: bool
    write_logs: bool
    output_dir: Path
    tail_lines: int


@dataclass(frozen=True)
class PrettyResult:
    path: str
    returncode: int
    match_ratio: float | None
    passed: bool
    output_path: Path | None


def _read_toml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Pretty-print runner config not found: {path}")
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _as_bool(value: Any, *, key: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"Config key {key!r} must be true or false.")
    return value


def _as_non_empty_str(value: Any, *, key: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TypeError(f"Config key {key!r} must be a non-empty string.")
    return value.strip()


def _as_positive_int(value: Any, *, key: str) -> int:
    if not isinstance(value, int) or value <= 0:
        raise TypeError(f"Config key {key!r} must be a positive integer.")
    return value


def _as_min_match_ratio(value: Any, *, key: str) -> float:
    if not isinstance(value, (int, float)):
        raise TypeError(f"Config key {key!r} must be numeric.")
    ratio = float(value)
    if not 0.0 <= ratio <= 1.0:
        raise ValueError(f"Config key {key!r} must be between 0.0 and 1.0.")
    return ratio


def _repo_relative_dir(raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        raise ValueError("Pretty-print output_dir must be repo-relative, not absolute.")
    return ROOT / path


def _load_config(path: Path = CONFIG_PATH) -> PrettyRunnerConfig:
    payload = _read_toml(path)
    runner = payload.get("runner")
    if not isinstance(runner, dict):
        raise TypeError("Pretty-print config must contain a [runner] table.")

    raw_tutorials = payload.get("tutorials")
    if not isinstance(raw_tutorials, list) or not raw_tutorials:
        raise TypeError("Pretty-print config must contain at least one [[tutorials]] entry.")

    tutorials: list[PrettyTutorial] = []
    for index, item in enumerate(raw_tutorials, start=1):
        if not isinstance(item, dict):
            raise TypeError(f"Tutorial entry {index} must be a table.")
        tutorial_path = _as_non_empty_str(item.get("path"), key=f"tutorials[{index}].path")
        script_path = TUTORIAL_DIR / tutorial_path
        if script_path.name != tutorial_path or not tutorial_path.endswith(".py"):
            raise ValueError(f"Tutorial entry {index} path must be a simple Python filename.")
        if not script_path.is_file():
            raise FileNotFoundError(f"Tutorial entry {index} does not exist: {script_path}")
        tutorials.append(
            PrettyTutorial(
                path=tutorial_path,
                min_match_ratio=_as_min_match_ratio(item.get("min_match_ratio"), key=f"tutorials[{index}].min_match_ratio"),
            )
        )

    output_dir = _repo_relative_dir(_as_non_empty_str(runner.get("output_dir"), key="runner.output_dir"))
    return PrettyRunnerConfig(
        title=_as_non_empty_str(runner.get("title"), key="runner.title"),
        tutorials=tuple(tutorials),
        show_output=_as_bool(runner.get("show_output"), key="runner.show_output"),
        stop_on_first_failure=_as_bool(runner.get("stop_on_first_failure"), key="runner.stop_on_first_failure"),
        write_logs=_as_bool(runner.get("write_logs"), key="runner.write_logs"),
        output_dir=output_dir,
        tail_lines=_as_positive_int(runner.get("tail_lines"), key="runner.tail_lines"),
    )


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


def _write_output_log(config: PrettyRunnerConfig, entry: PrettyTutorial, output: str) -> Path | None:
    if not config.write_logs:
        return None
    config.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = config.output_dir / (Path(entry.path).stem + ".txt")
    output_path.write_text(output, encoding="utf-8")
    return output_path


def _run_one(entry: PrettyTutorial, config: PrettyRunnerConfig) -> PrettyResult:
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
    output_path = _write_output_log(config, entry, output)
    if config.show_output or proc.returncode != 0:
        print(f"\n--- output: {entry.path} ---")
        print(output.rstrip())
    match_ratio = _parse_match_ratio(output)
    passed = proc.returncode == 0 and match_ratio is not None and match_ratio >= entry.min_match_ratio
    if not passed and not config.show_output:
        print(f"\n--- tail: {entry.path} ---")
        print(_tail(output, lines=config.tail_lines))
    return PrettyResult(entry.path, proc.returncode, match_ratio, passed, output_path)


def main() -> int:
    config = _load_config()

    print("RDP pretty-print tutorial runner")
    print(f"config: {_relpath(CONFIG_PATH)}")
    print(f"title : {config.title}")
    print(f"selected: {len(config.tutorials)}")
    if config.write_logs:
        print(f"output logs: {_relpath(config.output_dir)}")

    results: list[PrettyResult] = []
    for entry in config.tutorials:
        print(f"[RUN ] {entry.path}")
        result = _run_one(entry, config)
        results.append(result)
        status = "PASS" if result.passed else "FAIL"
        match_text = "none" if result.match_ratio is None else f"{result.match_ratio:.3f}"
        log_text = "" if result.output_path is None else f" log={_relpath(result.output_path)}"
        print(f"[{status}] {entry.path} match_ratio={match_text} min={entry.min_match_ratio:.3f}{log_text}")
        if not result.passed and config.stop_on_first_failure:
            break

    passed = sum(1 for result in results if result.passed)
    failed = len(results) - passed
    print("\nPretty-print summary")
    print(f"selected={len(config.tutorials)} run={len(results)} passed={passed} failed={failed}")
    return 0 if failed == 0 and len(results) == len(config.tutorials) else 1


if __name__ == "__main__":
    raise SystemExit(main())
