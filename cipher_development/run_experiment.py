from __future__ import annotations

"Single local entry point for retained cipher-development experiments."
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

EXPERIMENT = "autokey"
MODE = "smoke"
SEED = 20260822
REPO_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = REPO_ROOT.parents[1]
OUTPUT_LOCATION = WORKSPACE_ROOT / "run_outputs" / "cipher_development"
for import_root in (REPO_ROOT, REPO_ROOT / "src"):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))


@dataclass(frozen=True, slots=True)
class ExperimentDefinition:
    recipe_profile: str
    smoke_assets: str
    development_assets: str
    run: Callable[[str, int, Path], Path]


def _run_autokey(mode: str, seed: int, output_root: Path) -> Path:
    from cipher_development.autokey_search.experiment import run_experiment

    return run_experiment(mode=mode, seed=seed, output_root=output_root)


def _run_two_period(mode: str, seed: int, output_root: Path) -> Path:
    from cipher_development.two_period_overlay.pack09 import run_experiment

    return run_experiment(mode=mode, seed=seed, output_root=output_root)


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
    if mode not in {"smoke", "development"}:
        raise ValueError("MODE must be 'smoke' or 'development'")
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("SEED must be a non-negative integer")
    if not output_location.is_absolute():
        raise ValueError("OUTPUT_LOCATION must be an absolute external path")
    output_root = output_location.resolve()
    if output_root == REPO_ROOT or output_root.is_relative_to(REPO_ROOT):
        raise ValueError("OUTPUT_LOCATION must remain outside the repository")
    definition = selected_definition(experiment)
    asset_profile = (
        definition.smoke_assets if mode == "smoke" else definition.development_assets
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


def main() -> int:
    run_selected()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
