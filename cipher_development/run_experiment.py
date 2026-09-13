from __future__ import annotations

"""Single local entry point for retained cipher-development experiments."""

import contextlib
import json
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, TextIO

EXPERIMENT = "autokey"
MODE = "smoke"
SEED = 20260822
REPO_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = REPO_ROOT.parents[1]
OUTPUT_LOCATION = WORKSPACE_ROOT / "run_outputs" / "cipher_development"
TRANSCRIPT_LOCATION = WORKSPACE_ROOT / "run_outputs" / "tests" / "cipher_development"

for import_root in (REPO_ROOT, REPO_ROOT / "src"):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))


@dataclass(frozen=True, slots=True)
class ExperimentDefinition:
    recipe_profile: str
    smoke_assets: str
    development_assets: str
    run: Callable[[str, int, Path], Path]


class Tee:
    def __init__(self, *streams: TextIO) -> None:
        self.streams = streams

    def write(self, value: str) -> int:
        for stream in self.streams:
            stream.write(value)
            stream.flush()
        return len(value)

    def flush(self) -> None:
        for stream in self.streams:
            stream.flush()

    def isatty(self) -> bool:
        return any(stream.isatty() for stream in self.streams)

    @property
    def encoding(self) -> str:
        return str(getattr(self.streams[0], "encoding", "utf-8") or "utf-8")


def _run_autokey(mode: str, seed: int, output_root: Path) -> Path:
    from cipher_development.autokey_search.experiment import run_experiment

    return run_experiment(mode=mode, seed=seed, output_root=output_root)


def _run_two_period(mode: str, seed: int, output_root: Path) -> Path:
    from cipher_development.two_period_overlay.pack09 import run_experiment

    return run_experiment(mode=mode, seed=seed, output_root=output_root)


def _run_periodic_columnar_staged(mode: str, seed: int, output_root: Path) -> Path:
    from cipher_development.periodic_columnar_staged.qualification import (
        run_qualification,
    )

    return run_qualification(mode=mode, seed=seed, output_root=output_root)


EXPERIMENTS = {
    "autokey": ExperimentDefinition(
        recipe_profile="autokey_wli12_beam_v1",
        smoke_assets="ci_light",
        development_assets="ci_light",
        run=_run_autokey,
    ),
    "two_period_pack09": ExperimentDefinition(
        recipe_profile="S2 scout / F1 static rank",
        smoke_assets="ci_light",
        development_assets="full_v1",
        run=_run_two_period,
    ),
    "periodic_columnar_staged": ExperimentDefinition(
        recipe_profile="periodic_columnar_decomposed_v2",
        smoke_assets="full_v1",
        development_assets="full_v1",
        run=_run_periodic_columnar_staged,
    ),
}


def selected_definition(name: str) -> ExperimentDefinition:
    try:
        return EXPERIMENTS[name]
    except KeyError as exc:
        raise ValueError(
            f"unknown experiment {name!r}; choose one of {sorted(EXPERIMENTS)}"
        ) from exc


def run_selected(
    *,
    experiment: str = EXPERIMENT,
    mode: str = MODE,
    seed: int = SEED,
    output_location: Path = OUTPUT_LOCATION,
) -> Path:
    if mode not in {"smoke", "diagnostic", "development"}:
        raise ValueError("MODE must be 'smoke', 'diagnostic', or 'development'")
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("SEED must be a non-negative integer")
    if not output_location.is_absolute():
        raise ValueError("OUTPUT_LOCATION must be an absolute external path")
    output_root = output_location.resolve()
    if output_root == REPO_ROOT or output_root.is_relative_to(REPO_ROOT):
        raise ValueError("OUTPUT_LOCATION must remain outside the repository")
    definition = selected_definition(experiment)
    asset_profile = (
        definition.smoke_assets
        if mode == "smoke"
        else definition.development_assets
    )
    print(f"experiment: {experiment}")
    print(f"mode: {mode}")
    print(f"recipe/profile: {definition.recipe_profile}")
    print(f"seed: {seed}")
    print(f"asset profile: {asset_profile}")
    print(f"output: {output_root}")
    result = definition.run(mode, seed, output_root)
    print("result: " + json.dumps({"path": str(result)}, sort_keys=True))
    return result


def _transcript_path() -> Path:
    timestamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    return TRANSCRIPT_LOCATION / f"{EXPERIMENT}_{MODE}_{timestamp}.log"


def main() -> int:
    TRANSCRIPT_LOCATION.mkdir(parents=True, exist_ok=True)
    transcript = _transcript_path()
    with transcript.open("w", encoding="utf-8", newline="\n", buffering=1) as handle:
        stdout = Tee(sys.__stdout__, handle)
        stderr = Tee(sys.__stderr__, handle)
        with (
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
            contextlib.chdir(REPO_ROOT),
        ):
            print(f"transcript: {transcript}")
            try:
                run_selected()
            except BaseException:
                traceback.print_exc()
                print(f"transcript retained after execution failure: {transcript}")
                return 1
            print(f"transcript retained: {transcript}")
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
