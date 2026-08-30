from __future__ import annotations
from rdp import api
'Periodic columnar simple P7 col-then-sub pretty-print tutorial.'
import sys
from pathlib import Path
from typing import Sequence
_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / 'src'
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
import numpy as np
from rune_decrypter_prime.data.cipher_tests.plaintext import long_plaintext_string
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils import tutorial_pretty as pretty
from rune_decrypter_prime.utils.seed_utils_periodic_columnar import SeedPlan, generate_seed_keys_periodic_columnar
from rune_decrypter_prime.utils.tutorial_output import print_tutorial_debug_preview
from rune_decrypter_prime.utils.tutorial_utils import oracle_stop_score, print_stop_summary
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
ALPHABET = 29
PERIOD = 7
COLUMNS = 7
ORDER = 'col_then_sub'
TUTORIAL_SEED = 12345
CIPHERTEXT_SEED = 54321
USE_SEEDS = True
SEED_KEYS = 128
SEED_STARTS = 48
SEED_REFINE_STEPS = 600
SEED_TEMP_START = 0.4
SEED_TEMP_END = 0.04
STAGE1_STEPS = 20000
STAGE1_RESTARTS = 10
STAGE1_INNER_BATCH = 192
STAGE1_SLIP_EVERY = 60
STAGE1_SLIP_BLOCKS = 1
STAGE1_COL_EVERY = 1
STAGE1_COL_BATCH = 512
STAGE1_STALL_ROUNDS = 260
STAGE1_STALL_SLIP_LIMIT = 4
STAGE1_SLIP_SWAPS = 50
STAGE2_STEPS = 18000
STAGE2_RESTARTS = 8
STAGE2_INNER_BATCH = 192
STAGE2_SLIP_EVERY = 60
STAGE2_SLIP_BLOCKS = 1
STAGE2_COL_EVERY = 1
STAGE2_COL_BATCH = 512
STAGE2_STALL_ROUNDS = 260
STAGE2_STALL_SLIP_LIMIT = 4
STAGE2_SLIP_SWAPS = 50
MIN_MATCH_RATIO = 1.0

def _preview(text: str, n: int=160) -> str:
    return text if len(text) <= n else text[:n] + '...'

def _match_ratio(solution, pt_idx: Sequence[int]) -> float:
    guess = solution.plaintext or None
    if guess is None:
        return 0.0
    a = np.asarray(guess, dtype=np.int64).reshape(-1)
    b = np.asarray(pt_idx, dtype=np.int64).reshape(-1)
    n = min(a.size, b.size)
    return float(np.mean(a[:n] == b[:n])) if n > 0 else 0.0

def main() -> None:
    pretty.print_rdp_identity()
    pretty.print_initialising()
    pretty.print_tutorial_contract(name='Periodic columnar simple P7 col-then-sub', cipher='periodic columnar', solver='hybrid', direction='rtl', expected_result='exact solve', uses_reference_stop_score=True)
    print('Runtime class: LONG-RUNNING KAEDING QUALIFICATION (may take several hours)')
    encoding_dir = api.TextDirection.RIGHT_TO_LEFT
    pt_idx, wli, pt_runes = Runeglish.encode_english_to_runes(long_plaintext_string, direction=encoding_dir)
    pt_arr = np.asarray(pt_idx, dtype=np.uint8)
    print('Periodic columnar simple problem')
    print(f'encoding direction: {encoding_dir.value}')
    print(f'period={PERIOD}, columns={COLUMNS}, order={ORDER}')
    print('stages: raw char34 seed generation -> char-only Kaeding -> full scorer Kaeding')
    print('Plaintext preview:', _preview(pt_runes))
    cipher_spec = api.CipherSpec.periodic_columnar(
        period=PERIOD,
        columns=COLUMNS,
        order=api.advanced.PeriodicColumnarOrder.COLUMNAR_THEN_SUBSTITUTION,
        alphabet_size=ALPHABET,
    )
    key_spec = api.KeySpec.periodic_columnar(period=PERIOD, alphabet_size=ALPHABET, columns=COLUMNS)
    cipher = cipher_spec
    rng_key = np.random.default_rng(CIPHERTEXT_SEED)
    true_key = np.concatenate(
        [
            *(rng_key.permutation(ALPHABET) for _ in range(PERIOD)),
            rng_key.permutation(COLUMNS),
        ]
    ).astype(np.uint8, copy=False)
    ct_idx = api.encrypt(tuple(int(value) for value in pt_arr), cipher=cipher, key=tuple(int(value) for value in true_key))
    ct_idx_list = [int(v) for v in list(ct_idx)]
    ct_runes = Runeglish.to_rune(ct_idx_list, wli)
    print('Ciphertext preview:', _preview(ct_runes))
    print_tutorial_debug_preview(label='plaintext', idx=pt_idx, wli=wli, direction=encoding_dir)
    print_tutorial_debug_preview(label='ciphertext', idx=ct_idx_list, wli=wli, direction=encoding_dir)
    scorer_stage1 = api.ScoringConfig(character_lane_enabled=True, word_length_lane_enabled=False, character_order_weights={3: 0.5, 4: 0.5}, word_length_order_weights={}, objective=api.advanced.ScoringObjective.percentile_log_probability(window_size=10))
    seed_keys = None
    if USE_SEEDS:
        seed_plan = SeedPlan(
            n_starts=SEED_STARTS,
            refine_steps=SEED_REFINE_STEPS,
            temp_start=SEED_TEMP_START,
            temp_end=SEED_TEMP_END,
        )
        seed_keys = generate_seed_keys_periodic_columnar(
            ct_idx_list,
            period=PERIOD,
            columns=COLUMNS,
            order=ORDER,
            direction=encoding_dir,
            seed=TUTORIAL_SEED,
            scoring_cfg=scorer_stage1,
            n_keys=SEED_KEYS,
            plan=seed_plan,
            refine=True,
        )
        print(f'Seed pool: {len(seed_keys)} keys')
    stop1 = oracle_stop_score(pt_idx, wli, scorer_stage1, device='cpu', encoding_dir=encoding_dir, margin=0.02, min_score=0.45, fallback=0.5)
    print_stop_summary('PeriodicColumnar simple P7 (Stage 1: char-only)', stop1)
    solver1 = api.SolverSpec.kaeding(steps=STAGE1_STEPS, restarts=STAGE1_RESTARTS, inner_batch_size=STAGE1_INNER_BATCH, slip_interval=STAGE1_SLIP_EVERY, slip_blocks=STAGE1_SLIP_BLOCKS, column_interval=STAGE1_COL_EVERY, column_batch_size=STAGE1_COL_BATCH, block_schedule=api.advanced.KaedingBlockSchedule.ROUND_ROBIN, target_score=stop1.stop_score, seed=TUTORIAL_SEED, slip_policy=api.advanced.KaedingSlipPolicy.ON_STALL, stall_rounds=STAGE1_STALL_ROUNDS, stall_slip_limit=STAGE1_STALL_SLIP_LIMIT, slip_swaps=STAGE1_SLIP_SWAPS, stop_after_stall_slip_limit=False)
    stage1_initial_keys = (
        None
        if seed_keys is None
        else tuple(tuple(int(value) for value in seed) for seed in seed_keys)
    )
    stage1 = api.run(api.RunSpec(problem_input=api.RuneIndexInput(indices=ct_idx_list, word_lengths=wli), cipher=cipher_spec, key_space=key_spec, solver=solver1, scoring=scorer_stage1, initial_keys=stage1_initial_keys, telemetry_enabled=True, text_direction=encoding_dir))
    print(f'[Stage 1] best_score={float(stage1.score):.6f}')
    warm_keys: list[tuple[int, ...]] = []
    if stage1.key:
        warm_keys.append(tuple(int(value) for value in stage1.key))
    if seed_keys:
        warm_keys.extend(
            tuple(int(value) for value in seed)
            for seed in seed_keys[:min(48, len(seed_keys))]
        )
    scorer_stage2 = api.ScoringConfig(character_lane_enabled=True, word_length_lane_enabled=True, character_order_weights={3: 0.3, 4: 0.7}, word_length_order_weights={3: 0.4, 4: 0.6}, objective=api.advanced.ScoringObjective.percentile_log_probability(window_size=10))
    display_scorer_params = api.ScoringConfig(character_lane_enabled=True, word_length_lane_enabled=True, objective=api.advanced.ScoringObjective.percentile_log_probability(window_size=10))
    stop2 = oracle_stop_score(pt_idx, wli, scorer_stage2, device='cpu', encoding_dir=encoding_dir, margin=0.02, min_score=0.5, fallback=0.55)
    print_stop_summary('PeriodicColumnar simple P7 (Stage 2: full scorer)', stop2)
    solver2 = api.SolverSpec.kaeding(steps=STAGE2_STEPS, restarts=STAGE2_RESTARTS, inner_batch_size=STAGE2_INNER_BATCH, slip_interval=STAGE2_SLIP_EVERY, slip_blocks=STAGE2_SLIP_BLOCKS, column_interval=STAGE2_COL_EVERY, column_batch_size=STAGE2_COL_BATCH, block_schedule=api.advanced.KaedingBlockSchedule.ROUND_ROBIN, target_score=stop2.stop_score, seed=TUTORIAL_SEED, slip_policy=api.advanced.KaedingSlipPolicy.ON_STALL, stall_rounds=STAGE2_STALL_ROUNDS, stall_slip_limit=STAGE2_STALL_SLIP_LIMIT, slip_swaps=STAGE2_SLIP_SWAPS, stop_after_stall_slip_limit=False)
    result = api.run(api.RunSpec(problem_input=api.RuneIndexInput(indices=ct_idx_list, word_lengths=wli), cipher=cipher_spec, key_space=key_spec, solver=solver2, scoring=scorer_stage2, initial_keys=tuple(warm_keys) if warm_keys else None, telemetry_enabled=True, text_direction=encoding_dir))
    ratio = _match_ratio(result, pt_idx)
    recovered = (result.plaintext_text or '') or (result.plaintext_text or '')
    print('Recovered preview:', _preview(str(recovered)))
    print(f'Match ratio: {ratio:.3f}')
    if ratio < MIN_MATCH_RATIO:
        raise RuntimeError(f'Solve failed: match_ratio={ratio:.4f}')
    display_spec = api.RunSpec(problem_input=api.RuneIndexInput(indices=ct_idx_list, word_lengths=wli), cipher=cipher_spec, key_space=key_spec, solver=solver2, scoring=display_scorer_params, text_direction=encoding_dir, telemetry_enabled=True)
    pretty.print_summary_spacer()
    api.display.print_result(
        result, spec=display_spec, options=api.display.SummaryOptions.for_tutorial()
    )
    print(f"True key length: {int(len(true_key))}")


if __name__ == "__main__":
    main()
