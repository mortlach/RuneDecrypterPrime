from __future__ import annotations
from rdp import api
'Periodic substitution simple P7 pretty-print tutorial.'
import sys
from pathlib import Path
from typing import Sequence, Tuple
_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / 'src'
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
import numpy as np
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext_english_string
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils import tutorial_pretty as pretty
from rune_decrypter_prime.utils.tutorial_output import print_tutorial_debug_preview
from rune_decrypter_prime.utils.seed_utils import make_periodic_seed_pool, make_periodic_structured_key
from rune_decrypter_prime.utils.tutorial_utils import oracle_stop_score, print_stop_summary
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
ALPHABET = 29
PERIOD = 7
TUTORIAL_SEED = 12345
CIPHERTEXT_SEED = 12345
USE_SEEDS = True
BLOCK_SEEDS = 8
SEED_KEYS = 48
SEED_SWAPS = 2
SOLVER_STEPS = 1200
SOLVER_RESTARTS = 3
SOLVER_INNER_BATCH = 96
SOLVER_SLIP_EVERY = 80
SOLVER_SLIP_BLOCKS = 1
SOLVER_STALL_ROUNDS = 140
SOLVER_STALL_SLIP_LIMIT = 3
SOLVER_SLIP_SWAPS = 30
MIN_MATCH_RATIO = 0.995

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

def _build_ciphertext(pt_idx: np.ndarray, wli: Sequence[Sequence[int]], *, period: int, alphabet_size: int, seed: int) -> Tuple[np.ndarray, str, np.ndarray]:
    key = np.asarray(make_periodic_structured_key(period=period, alphabet_size=alphabet_size, seed=seed), dtype=np.int16)
    cipher_spec = api.CipherSpec.periodic_substitution(period=period, alphabet_size=alphabet_size)
    cipher = cipher_spec
    ct_idx = api.encrypt(tuple(int(value) for value in pt_idx), cipher=cipher, key=tuple(int(value) for value in key))
    ct_runes = Runeglish.to_rune(list(ct_idx), wli)
    return (ct_idx, ct_runes, key)

def main() -> None:
    pretty.print_rdp_identity()
    pretty.print_initialising()
    pretty.print_tutorial_contract(name='Periodic substitution simple P7', cipher='periodic substitution', solver='hybrid', direction='rtl', expected_result='near-exact solve', uses_reference_stop_score=True)
    print('Runtime class: LONG-RUNNING KAEDING QUALIFICATION (may take several hours)')
    encoding_dir = api.TextDirection.RIGHT_TO_LEFT
    pt_idx, wli, pt_runes = Runeglish.encode_english_to_runes(plaintext_english_string, direction=encoding_dir)
    pt_idx_arr = np.asarray(pt_idx, dtype=np.uint8)
    print('Periodic substitution simple problem')
    print(f'encoding direction: {encoding_dir.value}')
    print(f'period: {PERIOD}')
    print('Plaintext preview:', _preview(pt_runes))
    ct_idx, ct_runes, key = _build_ciphertext(pt_idx_arr, wli, period=PERIOD, alphabet_size=ALPHABET, seed=CIPHERTEXT_SEED + PERIOD)
    ct_idx_list = [int(v) for v in list(ct_idx)]
    print('Ciphertext preview:', _preview(ct_runes))
    print_tutorial_debug_preview(label='plaintext', idx=pt_idx, wli=wli, direction=encoding_dir)
    print_tutorial_debug_preview(label='ciphertext', idx=[int(v) for v in list(ct_idx)], wli=wli, direction=encoding_dir)
    seed_keys = None
    if USE_SEEDS:
        seed_keys = make_periodic_seed_pool(ct_idx, period=PERIOD, direction=encoding_dir, seed=TUTORIAL_SEED + PERIOD, n_block_seeds=BLOCK_SEEDS, total_seeds=SEED_KEYS, swaps_per_block=SEED_SWAPS, alphabet_size=ALPHABET)
        print(f'Seed pool: {len(seed_keys)} keys')
    cipher_spec = api.CipherSpec.periodic_substitution(period=PERIOD, alphabet_size=ALPHABET)
    key_spec = api.KeySpec.periodic_substitution(period=PERIOD, alphabet_size=ALPHABET)
    scorer_params = api.ScoringConfig(character_lane_enabled=True, word_length_lane_enabled=True, character_order_weights={3: 0.3, 4: 0.7}, word_length_order_weights={3: 0.4, 4: 0.6}, objective=api.advanced.ScoringObjective.percentile_log_probability(window_size=10))
    display_scorer_params = api.ScoringConfig(character_lane_enabled=True, word_length_lane_enabled=True, objective=api.advanced.ScoringObjective.percentile_log_probability(window_size=10))
    stop = oracle_stop_score(pt_idx, wli, scorer_params, device='cpu', encoding_dir=encoding_dir, margin=0.02, min_score=0.5, fallback=0.55)
    print_stop_summary('PeriodicSub simple P7', stop)
    plateau_rounds = max(10, int(SOLVER_STEPS * 0.1))
    solver = api.SolverSpec.kaeding(steps=SOLVER_STEPS, restarts=SOLVER_RESTARTS, inner_batch_size=SOLVER_INNER_BATCH, slip_interval=SOLVER_SLIP_EVERY, slip_blocks=SOLVER_SLIP_BLOCKS, block_schedule=api.advanced.KaedingBlockSchedule.ROUND_ROBIN, plateau_rounds=plateau_rounds, plateau_minimum_delta=0.0001, target_score=stop.stop_score, seed=TUTORIAL_SEED, slip_policy=api.advanced.KaedingSlipPolicy.ON_STALL, stall_rounds=SOLVER_STALL_ROUNDS, stall_slip_limit=SOLVER_STALL_SLIP_LIMIT, slip_swaps=SOLVER_SLIP_SWAPS, stop_after_stall_slip_limit=True)
    display_spec = api.RunSpec(problem_input=api.RuneIndexInput(indices=ct_idx_list, word_lengths=wli), cipher=cipher_spec, key_space=key_spec, solver=solver, scoring=display_scorer_params, text_direction=encoding_dir, telemetry_enabled=True)
    initial_keys = (
        None
        if seed_keys is None
        else tuple(tuple(int(value) for value in seed) for seed in seed_keys)
    )
    result = api.run(api.RunSpec(problem_input=api.RuneIndexInput(indices=ct_idx, word_lengths=wli), cipher=cipher_spec, key_space=key_spec, solver=solver, scoring=scorer_params, initial_keys=initial_keys, telemetry_enabled=True, text_direction=encoding_dir))
    ratio = _match_ratio(result, pt_idx)
    print(f'Match ratio: {ratio:.3f}')
    if ratio < MIN_MATCH_RATIO:
        raise RuntimeError(f'Solve failed: match_ratio={ratio:.4f}')
    recovered = (result.plaintext_text or '') or (result.plaintext_text or '')
    print('Recovered preview:', _preview(str(recovered)))
    pretty.print_summary_spacer()
    api.display.print_result(
        result, spec=display_spec, options=api.display.SummaryOptions.for_tutorial()
    )
    print(f"True key length: {int(key.size)}")


if __name__ == "__main__":
    main()
