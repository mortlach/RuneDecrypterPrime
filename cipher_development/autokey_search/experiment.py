from __future__ import annotations

"""Small, fixed Autokey experiments using the permanent robustness cases."""

import json
import sys
import time
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
for import_root in (REPO_ROOT, REPO_ROOT / "src"):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from tools.robustness import cipher_solver_campaign as campaign


EXPERIMENT = "solver_trials"  # "profile_probe" or "solver_trials"
TRIALS = tuple(range(20))
ALPHABET = 29
SOLVER_SCORER_PROFILE = "wli12"

SCORER_PROFILES = {
    "current": {
        "objective": "pct.logp.win10",
        "include_char": True,
        "use_word_breaks": True,
        "char_weights": {2: 0.3},
        "wli_weights": {2: 0.7},
    },
    "char2": {
        "objective": "pct.logp.win10",
        "include_char": True,
        "use_word_breaks": False,
        "char_weights": {2: 1.0},
        "wli_weights": {},
    },
    "wli2": {
        "objective": "pct.logp.win10",
        "include_char": False,
        "use_word_breaks": True,
        "char_weights": {},
        "wli_weights": {2: 1.0},
    },
    "char12": {
        "objective": "pct.logp.win10",
        "include_char": True,
        "use_word_breaks": False,
        "char_weights": {1: 0.3, 2: 0.7},
        "wli_weights": {},
    },
    "wli12": {
        "objective": "pct.logp.win10",
        "include_char": False,
        "use_word_breaks": True,
        "char_weights": {},
        "wli_weights": {1: 0.3, 2: 0.7},
    },
    "combined12": {
        "objective": "pct.logp.win10",
        "include_char": True,
        "use_word_breaks": True,
        "char_weights": {1: 0.1, 2: 0.2},
        "wli_weights": {1: 0.2, 2: 0.5},
    },
}

BEAM_PARAMS = {
    "beam_width": 96,
    "rounds": 32,
    "restarts": 3,
    "expand_mode": "sweep",
    "plateau_rounds": 0,
}


def _single_change_neighbourhood(key: list[int]) -> np.ndarray:
    truth = np.asarray(key, dtype=np.uint8)
    rows = [truth.copy()]
    for position, current in enumerate(truth.tolist()):
        for value in range(ALPHABET):
            if value == current:
                continue
            candidate = truth.copy()
            candidate[position] = value
            rows.append(candidate)
    return np.asarray(rows, dtype=np.uint8)


def profile_probe() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for trial in TRIALS:
        for profile_name, scorer in SCORER_PROFILES.items():
            case = campaign.build_case("autokey_beam", trial)
            case.scorer = dict(scorer)
            case.initial_keys = _single_change_neighbourhood(case.expected_key or [])
            population = len(case.initial_keys)
            case.solver = campaign.api.SolverSpec.ga(
                pop_size=population,
                generations=1,
                elite_frac=0.0,
                cx_frac=0.0,
                mut_prob=0.0,
                tournament_k=2,
                plateau_rounds=0,
            )
            started = time.perf_counter()
            assessment = campaign.assess_result(case, campaign.execute_case(case))
            row = {
                "trial": trial,
                "direction": case.direction.value,
                "seed_length": case.key_length,
                "profile": profile_name,
                "truth_is_best_local_key": (
                    assessment["recovered_key"] == assessment["expected_key"]
                ),
                "best_local_match_ratio": assessment["match_ratio"],
                "best_local_score": assessment["best_score"],
                "runtime_seconds": time.perf_counter() - started,
            }
            rows.append(row)
            print(json.dumps(row, sort_keys=True), flush=True)
    return rows


def solver_trials() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for trial in TRIALS:
        case = campaign.build_case("autokey_beam", trial)
        case.scorer = dict(SCORER_PROFILES[SOLVER_SCORER_PROFILE])
        case.solver = campaign.api.SolverSpec.beam(**BEAM_PARAMS)
        started = time.perf_counter()
        assessment = campaign.assess_result(case, campaign.execute_case(case))
        row = {
            "trial": trial,
            "direction": case.direction.value,
            "seed_length": case.key_length,
            "classification": assessment["classification"],
            "match_ratio": assessment["match_ratio"],
            "key_match": assessment["recovered_key"] == assessment["expected_key"],
            "best_score": assessment["best_score"],
            "runtime_seconds": time.perf_counter() - started,
        }
        rows.append(row)
        print(json.dumps(row, sort_keys=True), flush=True)
    return rows


def main() -> int:
    rows = profile_probe() if EXPERIMENT == "profile_probe" else solver_trials()
    print(json.dumps(rows, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
