"""Periodic substitution.

See the example catalogue for assets, runtime and reference use.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from rdp import api
from rdp.data.runeglish import Runeglish
from rdp.solvers.seed_generation import make_seeds_from_freq
from tutorials.v1.data.plaintext_fixtures import plaintext_english_string
from tutorials.v1.support import tutorial_pretty as pretty
from tutorials.v1.support.tutorial_output import print_tutorial_debug_preview
from tutorials.v1.support.tutorial_utils import oracle_stop_score, print_stop_summary

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
ALPHABET = 29
TUTORIAL_SEED = 12345
CIPHERTEXT_SEED = 12345
USE_SEEDS = True
BLOCK_SEEDS = 6
SEED_KEYS = 32
SEED_SWAPS = 2
MIN_MATCH_RATIO = 0.995


@dataclass(frozen=True, slots=True)
class TutorialScenario:
    label: str
    period: int
    steps: int
    restarts: int
    inner_batch_size: int
    slip_interval: int
    slip_blocks: int
    block_seeds: int = BLOCK_SEEDS
    seed_keys: int = SEED_KEYS
    seed_swaps: int = SEED_SWAPS
    retry_steps: int = 1400
    retry_restarts: int = 4
    retry_inner_batch_size: int = 96
    retry_slip_interval: int = 60
    retry_slip_blocks: int = 2
    retry_block_seeds: int = 10
    retry_seed_keys: int = 64
    retry_seed_swaps: int = 3

    def solver(self, *, target_score: float, retry: bool = False) -> api.SolverSpec:
        steps = self.retry_steps if retry else self.steps
        return api.SolverSpec.kaeding(
            steps=steps,
            restarts=self.retry_restarts if retry else self.restarts,
            inner_batch_size=self.retry_inner_batch_size
            if retry
            else self.inner_batch_size,
            block_schedule=api.advanced.KaedingBlockSchedule.RANDOM,
            slip_blocks=self.retry_slip_blocks if retry else self.slip_blocks,
            slip_interval=self.retry_slip_interval if retry else self.slip_interval,
            slip_policy=api.advanced.KaedingSlipPolicy.ON_STALL
            if retry
            else api.advanced.KaedingSlipPolicy.FIXED_INTERVAL,
            slip_swaps=40 if retry else 0,
            stall_rounds=120 if retry else 0,
            stall_slip_limit=4 if retry else 0,
            plateau_rounds=max(10, int(steps * 0.1)),
            plateau_minimum_delta=1e-06 if retry else 0.0001,
            target_score=target_score,
            seed=TUTORIAL_SEED,
        )


SCENARIOS: tuple[TutorialScenario, ...] = (
    TutorialScenario("easy", 2, 400, 1, 48, 0, 1),
    TutorialScenario("medium", 3, 700, 2, 64, 80, 1),
)


def _preview(text: str, n: int = 160) -> str:
    return text if len(text) <= n else text[:n] + "..."


def _match_ratio(solution, pt_idx: list[int]) -> float:
    guess = solution.plaintext or None
    if not guess:
        return 0.0
    a = np.asarray(guess, dtype=np.int64).reshape(-1)
    b = np.asarray(pt_idx, dtype=np.int64).reshape(-1)
    n = min(a.size, b.size)
    return float(np.mean(a[:n] == b[:n])) if n > 0 else 0.0


def _make_periodic_key(period: int, alphabet_size: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    blocks = [rng.permutation(alphabet_size).astype(np.int16) for _ in range(period)]
    return np.concatenate(blocks, axis=0).astype(np.int16, copy=False)


def _build_ciphertext(
    pt_idx: np.ndarray,
    wli: list[list[int]],
    *,
    period: int,
    alphabet_size: int,
    seed: int,
):
    key = _make_periodic_key(period, alphabet_size, seed)
    cipher_spec = api.CipherSpec.periodic_substitution(
        period=period, alphabet_size=alphabet_size
    )
    cipher = cipher_spec
    ct_idx = api.encrypt(
        tuple(int(value) for value in pt_idx),
        cipher=cipher,
        key=tuple(int(value) for value in key),
    )
    ct_runes = Runeglish.to_rune(list(ct_idx), wli)
    return (ct_idx, ct_runes, key)


def _make_periodic_seeds(
    ct_idx: Sequence[int],
    *,
    period: int,
    direction: api.TextDirection,
    seed: int,
    n_block_seeds: int,
    total_seeds: int,
    swaps_per_block: int,
) -> list[list[int]]:
    rng = np.random.default_rng(seed)
    block_seeds: list[list[list[int]]] = []
    for r in range(period):
        phase_idx = ct_idx[r::period]
        phase_runes = Runeglish.to_rune([int(value) for value in phase_idx], wli=None)
        seeds = make_seeds_from_freq(
            phase_runes,
            n_keys=n_block_seeds,
            swaps_per_key=swaps_per_block,
            seed=seed + r,
            A=ALPHABET,
            direction=direction,
        )
        block_seeds.append(seeds)

    def _concat(blocks: list[list[int]]) -> list[int]:
        out: list[int] = []
        for block in blocks:
            out.extend(block)
        return out

    keys: list[list[int]] = [_concat([seeds[0] for seeds in block_seeds])]
    for _ in range(max(0, total_seeds - 1)):
        pick = [_s[int(rng.integers(0, len(_s)))] for _s in block_seeds]
        keys.append(_concat(pick))
    return keys


def main() -> None:
    pretty.print_rdp_identity()
    pretty.print_initialising()
    pretty.print_tutorial_contract(
        name="Periodic substitution",
        cipher="periodic substitution",
        solver="hybrid",
        direction="rtl",
        expected_result="near-exact solve",
        uses_reference_stop_score=True,
    )
    print("Runtime class: LONG-RUNNING KAEDING QUALIFICATION (may take several hours)")
    direction = api.TextDirection.RIGHT_TO_LEFT
    pt_idx, wli, pt_runes = Runeglish.encode_english_to_runes(
        plaintext_english_string, direction=direction
    )
    pt_idx_arr = np.asarray(pt_idx, dtype=np.uint8)
    print("Periodic substitution problem")
    print(f"encoding direction: {direction.value}")
    print("Plaintext preview:", _preview(pt_runes))
    display_scorer_params = api.ScoringConfig(
        character_lane_enabled=True,
        word_length_lane_enabled=True,
        objective=api.advanced.ScoringObjective.percentile_log_probability(
            window_size=10
        ),
    )
    for scenario in SCENARIOS:
        label = scenario.label
        period = scenario.period
        ct_idx, ct_runes, key = _build_ciphertext(
            pt_idx_arr,
            wli,
            period=period,
            alphabet_size=ALPHABET,
            seed=CIPHERTEXT_SEED + period,
        )
        ct_idx_list = [int(v) for v in list(ct_idx)]
        print("=" * 72)
        print(f"Scenario: {label} (period={period})")
        print("Ciphertext preview:", _preview(ct_runes))
        print_tutorial_debug_preview(
            label=f"plaintext_{label}", idx=pt_idx, wli=wli, direction=direction
        )
        print_tutorial_debug_preview(
            label=f"ciphertext_{label}", idx=ct_idx_list, wli=wli, direction=direction
        )
        seed_keys = None
        if USE_SEEDS:
            seed_keys = _make_periodic_seeds(
                ct_idx,
                period=period,
                direction=direction,
                seed=TUTORIAL_SEED + period,
                n_block_seeds=scenario.block_seeds,
                total_seeds=scenario.seed_keys,
                swaps_per_block=scenario.seed_swaps,
            )
            print(f"Seed pool: {len(seed_keys)} keys")
        cipher_spec = api.CipherSpec.periodic_substitution(
            period=period, alphabet_size=ALPHABET
        )
        key_spec = api.KeySpec.periodic_substitution(
            period=period, alphabet_size=ALPHABET
        )
        scorer_params = api.ScoringConfig(
            character_lane_enabled=True,
            word_length_lane_enabled=True,
            character_order_weights={3: 0.3, 4: 0.7},
            word_length_order_weights={3: 0.4, 4: 0.6},
            objective=api.advanced.ScoringObjective.percentile_log_probability(
                window_size=10
            ),
        )
        stop = oracle_stop_score(
            pt_idx,
            wli,
            scorer_params,
            device="cpu",
            encoding_dir=direction,
            margin=0.02,
            min_score=0.5,
            fallback=0.55,
        )
        print_stop_summary(f"PeriodicSub {label}", stop)
        solver = scenario.solver(target_score=stop.stop_score)
        initial_keys = (
            None
            if seed_keys is None
            else tuple(tuple(int(value) for value in seed) for seed in seed_keys)
        )
        result = api.run(
            api.RunSpec(
                problem_input=api.RuneIndexInput(indices=ct_idx, word_lengths=wli),
                cipher=cipher_spec,
                key_space=key_spec,
                solver=solver,
                scoring=scorer_params,
                initial_keys=initial_keys,
                telemetry_enabled=True,
                text_direction=direction,
            )
        )
        if _match_ratio(result, pt_idx) < 0.999:
            print("Retrying with stronger Kaeding settings...")
            seed_keys = None
            if USE_SEEDS:
                seed_keys = _make_periodic_seeds(
                    ct_idx,
                    period=period,
                    direction=direction,
                    seed=TUTORIAL_SEED + period + 99,
                    n_block_seeds=scenario.retry_block_seeds,
                    total_seeds=scenario.retry_seed_keys,
                    swaps_per_block=scenario.retry_seed_swaps,
                )
                print(f"Seed pool (retry): {len(seed_keys)} keys")
            solver = scenario.solver(target_score=stop.stop_score, retry=True)
            retry_initial_keys = (
                None
                if seed_keys is None
                else tuple(tuple(int(value) for value in seed) for seed in seed_keys)
            )
            result = api.run(
                api.RunSpec(
                    problem_input=api.RuneIndexInput(indices=ct_idx, word_lengths=wli),
                    cipher=cipher_spec,
                    key_space=key_spec,
                    solver=solver,
                    scoring=scorer_params,
                    initial_keys=retry_initial_keys,
                    telemetry_enabled=True,
                    text_direction=direction,
                )
            )
        ratio = _match_ratio(result, pt_idx)
        recovered = (result.plaintext_text or "") or (result.plaintext_text or "")
        print("Recovered preview:", _preview(str(recovered)))
        print(f"Match ratio: {ratio:.3f}")
        display_spec = api.RunSpec(
            problem_input=api.RuneIndexInput(indices=ct_idx_list, word_lengths=wli),
            cipher=cipher_spec,
            key_space=key_spec,
            solver=solver,
            scoring=display_scorer_params,
            text_direction=direction,
            telemetry_enabled=True,
        )
        pretty.print_summary_spacer()
        api.display.print_result(
            result, spec=display_spec, options=api.display.SummaryOptions.for_tutorial()
        )
        print(f"True key length ({label}): {int(key.size)}")
        if ratio < MIN_MATCH_RATIO:
            raise AssertionError(
                f"{label} periodic substitution solve below acceptance threshold: "
                f"{ratio:.3f}"
            )


if __name__ == "__main__":
    main()
