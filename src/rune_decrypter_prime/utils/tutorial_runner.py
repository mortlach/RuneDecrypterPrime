from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from rune_decrypter_prime.utils.tutorial_benchmark import TutorialAcceptanceKind


class TutorialRunSet(StrEnum):
    FAST = "fast"
    RELEASE = "release"
    EXTENDED = "extended"
    PARTIAL_RECOVERY = "partial_recovery"
    CI_LIGHT = "ci_light"
    FULL_ASSETS = "full_assets"
    ALL_WORKING = "all_working"


class ConsoleOutput(StrEnum):
    COMPACT = "compact"
    FULL = "full"


@dataclass(frozen=True)
class TutorialEntry:
    path: str
    min_match_ratio: float
    acceptance: TutorialAcceptanceKind = TutorialAcceptanceKind.EXACT
    run_sets: tuple[TutorialRunSet, ...] = (TutorialRunSet.RELEASE,)
    required_asset_profile: str = "ci_light"


@dataclass(frozen=True)
class TutorialResult:
    path: str
    acceptance: TutorialAcceptanceKind
    returncode: int
    match_ratio: float | None
    passed: bool
    output_path: Path | None


def select_tutorials(
    entries: tuple[TutorialEntry, ...],
    run_set: TutorialRunSet,
) -> tuple[TutorialEntry, ...]:
    if run_set == TutorialRunSet.ALL_WORKING:
        return entries
    return tuple(entry for entry in entries if run_set in entry.run_sets)


def validate_tutorial_entries(
    entries: tuple[TutorialEntry, ...],
    *,
    tutorial_dir: Path,
    run_set: TutorialRunSet,
) -> None:
    if not entries:
        raise ValueError(f"RUN_SET {run_set.value!r} did not select any tutorials.")
    for index, entry in enumerate(entries, start=1):
        script_path = tutorial_dir / entry.path
        if script_path.name != entry.path or not entry.path.endswith(".py"):
            raise ValueError(f"TUTORIALS[{index}] path must be a simple Python filename.")
        if not 0.0 <= float(entry.min_match_ratio) <= 1.0:
            raise ValueError(f"TUTORIALS[{index}] min_match_ratio must be between 0.0 and 1.0.")
        if not isinstance(entry.acceptance, TutorialAcceptanceKind):
            raise TypeError(f"TUTORIALS[{index}] acceptance must be TutorialAcceptanceKind.")
        if not all(isinstance(item, TutorialRunSet) for item in entry.run_sets):
            raise TypeError(f"TUTORIALS[{index}] run_sets must be TutorialRunSet values.")
        if entry.required_asset_profile not in {"ci_light", "full_v1"}:
            raise ValueError(
                f"TUTORIALS[{index}] required_asset_profile must be ci_light or full_v1."
            )
        if not script_path.is_file():
            raise FileNotFoundError(f"TUTORIALS[{index}] does not exist: {script_path}")


def parse_last_float(pattern: str, text: str) -> float | None:
    vals = re.findall(pattern, text, flags=re.IGNORECASE)
    if not vals:
        return None
    try:
        return float(vals[-1])
    except ValueError:
        return None


def parse_match_ratio(text: str) -> float | None:
    return parse_last_float(r"(?:Match ratio(?:\s*\([^)]*\))?|match_ratio)\s*:?\s*([0-9]+(?:\.[0-9]+)?)", text)


def tail_text(text: str, *, lines: int) -> str:
    chunks = text.rstrip().splitlines()
    return "\n".join(chunks[-lines:])


def repo_relpath(path: Path, *, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


__all__ = [
    "ConsoleOutput",
    "TutorialEntry",
    "TutorialResult",
    "TutorialRunSet",
    "parse_last_float",
    "parse_match_ratio",
    "repo_relpath",
    "select_tutorials",
    "tail_text",
    "validate_tutorial_entries",
]
