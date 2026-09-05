"""Compare three starts on a substitution problem.

We select the highest-scoring result before comparing it with the original
message. This shows how the recipe behaves across several attempts.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass

import numpy as np

from rdp import api
from rdp.data.runeglish import Runeglish
from rdp.solvers.seed_generation import make_seeds_from_freq
from tutorials.v1.data.plaintext_fixtures import plaintext_english_string
from tutorials.v1.support import tutorial_pretty as pretty

DIRECTION = api.TextDirection.LEFT_TO_RIGHT
CIPHERTEXT_SEED = 20260822
ATTEMPT_SEEDS = (20260831, 20260832, 20260833)
SEED_KEYS = 160
SEED_SWAPS = 2
POP_SIZE = 128
GENERATIONS = 160
ELITE_FRAC = 0.08
CX_FRAC = 0.85
MUT_PROB = 0.25
TOURNAMENT_K = 4
PLATEAU_ROUNDS = 30
MIN_MATCH_RATIO = 0.97
SCORER_PARAMS = api.ScoringConfig(
    character_lane_enabled=True,
    word_length_lane_enabled=True,
    character_order_weights={2: 0.3},
    word_length_order_weights={1: 0.21, 2: 0.49},
    objective=api.advanced.ScoringObjective.percentile_log_probability(window_size=10),
)


def _display_scorer_params() -> api.ScoringConfig:
    return api.ScoringConfig(
        character_lane_enabled=True,
        word_length_lane_enabled=True,
        character_order_weights={2: 0.3},
        word_length_order_weights={1: 0.21, 2: 0.49},
        objective=api.advanced.ScoringObjective.percentile_log_probability(
            window_size=10
        ),
    )


@dataclass(frozen=True)
class Attempt:
    index: int
    seed: int
    result: api.RunResult
    solver: api.SolverSpec
    score: float
    runtime_seconds: float
    stop_reason: str
    valid: bool


def _ints(value: object) -> list[int]:
    if hasattr(value, "tolist"):
        value = value.tolist()
    return [int(item) for item in value]


def select_attempt(attempts: list[Attempt]) -> Attempt:
    """Select by validity and solver score only; earliest attempt breaks ties."""
    return max(attempts, key=lambda item: (item.valid, item.score, -item.index))


def _execution_completed(report: api.advanced.SolverReport) -> bool:
    return report.status.execution_status is api.advanced.ExecutionStatus.COMPLETED


def enforce_acceptance(match_ratio: float) -> None:
    """Make direct execution enforce the tutorial's declared threshold."""
    if match_ratio < MIN_MATCH_RATIO:
        raise AssertionError(
            f"robust Mono tutorial below acceptance threshold: match_ratio={match_ratio:.3f} < {MIN_MATCH_RATIO:.2f}"
        )


def main() -> None:
    pretty.print_rdp_identity()
    pretty.print_initialising()
    pretty.print_tutorial_contract(
        name="Mono-substitution robust three-attempt GA",
        cipher="mono substitution",
        solver="ga",
        direction=DIRECTION.value,
        expected_result="human-readable solve",
        uses_reference_stop_score=False,
    )
    pt_idx, wli, _ = Runeglish.encode_english_to_runes(
        plaintext_english_string, direction=DIRECTION
    )
    rng = np.random.default_rng(CIPHERTEXT_SEED)
    true_key = rng.permutation(29).astype(np.uint8)
    cipher_spec = api.CipherSpec.substitution(alphabet_size=29)
    ciphertext = api.encrypt(
        tuple(int(value) for value in pt_idx),
        cipher=cipher_spec,
        key=tuple(int(value) for value in true_key),
    )
    ct_idx = _ints(ciphertext)
    ct_runes = Runeglish.to_rune(ct_idx, wli)
    print("Robust Mono-substitution qualification-derived tutorial")
    print("recipe: mono_char2_wli12_3start_v1")
    print(f"direction: {DIRECTION.value}")
    print("scorer: char2=0.30, WLI1=0.21, WLI2=0.49")
    print(f"attempt seeds: {ATTEMPT_SEEDS}")
    print("selection: highest valid solver score; earliest attempt breaks ties")
    print("truth used for selection: no")
    attempts: list[Attempt] = []
    for index, seed in enumerate(ATTEMPT_SEEDS):
        initial_keys = make_seeds_from_freq(
            ct_runes.replace(" ", ""),
            n_keys=SEED_KEYS,
            swaps_per_key=SEED_SWAPS,
            seed=seed,
            direction=DIRECTION,
        )
        solver = api.SolverSpec.genetic_algorithm(
            seed=seed,
            population_size=POP_SIZE,
            generations=GENERATIONS,
            elite_fraction=ELITE_FRAC,
            crossover_fraction=CX_FRAC,
            mutation_probability=MUT_PROB,
            tournament_size=TOURNAMENT_K,
            plateau_generations=PLATEAU_ROUNDS,
        )
        started = time.perf_counter()
        result = api.run(
            api.RunSpec(
                problem_input=api.RuneIndexInput(indices=ct_idx, word_lengths=wli),
                cipher=cipher_spec,
                key_space=api.KeySpec.permutation(length=29),
                solver=solver,
                scoring=SCORER_PARAMS,
                initial_keys=tuple(
                    tuple(int(value) for value in key) for key in initial_keys
                ),
                telemetry_enabled=True,
                text_direction=DIRECTION,
            )
        )
        elapsed = time.perf_counter() - started
        score = float(result.score)
        stop_reason = str(result.solver_report.status.stop_reason)
        valid = (
            math.isfinite(score)
            and bool(stop_reason)
            and _execution_completed(result.solver_report)
        )
        attempts.append(
            Attempt(index, seed, result, solver, score, elapsed, stop_reason, valid)
        )
        print(
            f"attempt {index + 1}: seed={seed} score={score:.6f} runtime={elapsed:.3f}s stop_reason={stop_reason} valid={valid}"
        )
    winner = select_attempt(attempts)
    recovered = _ints(winner.result.plaintext)
    expected = [int(v) for v in pt_idx]
    match_ratio = sum((a == b for a, b in zip(recovered, expected, strict=True))) / len(
        expected
    )
    classification = "PASS" if match_ratio >= MIN_MATCH_RATIO else "REVIEW"
    recovered_text = winner.result.plaintext_text or ""
    recovered_key = _ints(winner.result.key)[:29]
    print(f"selected attempt: {winner.index + 1} (seed={winner.seed})")
    print(f"selected score: {winner.score:.6f}")
    print(
        f"recovered plaintext: {recovered_text[:240]}{('...' if len(recovered_text) > 240 else '')}"
    )
    print(f"recovered key: {recovered_key}")
    print(f"plaintext match: {match_ratio:.3f}")
    print(f"qualification threshold: {MIN_MATCH_RATIO:.2f}")
    print(f"result: {classification}")
    print(f"Match ratio: {match_ratio:.3f}")
    print("The frozen 20-case qualification produced 19 PASS and 1 REVIEW; this")
    print("recipe is robust evidence, not a claim of universal exact recovery.")
    pretty.print_summary_spacer()
    api.display.print_result(
        winner.result, options=api.display.SummaryOptions.for_tutorial()
    )
    if not winner.valid:
        raise AssertionError("all Mono attempts were invalid")
    enforce_acceptance(match_ratio)


if __name__ == "__main__":
    main()
