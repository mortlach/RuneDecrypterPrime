from __future__ import annotations
from tutorials.v1.data.two_period_cribs_demo import encrypt_interruptor_fixture
from rdp import api
import sys
from pathlib import Path
import numpy as np
_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / 'src'
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils import tutorial_pretty as pretty
from rune_decrypter_prime.utils.tutorial_output import print_tutorial_debug_preview
from rune_decrypter_prime.utils.tutorial_utils import oracle_stop_score, print_stop_summary
'\nTutorial variant: smaller single-start Vigenere interruptor Beam pool search.\n\nThe original tutorial remains unchanged; this variant proves the printer facade.\n'
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
TUTORIAL_SEED = 2026
DEMO_TEXT = 'THERE WAS A TABLE SET OUT UNDER A TREE IN FRONT OF THE HOUSE AND THE MARCH HARE AND THE HATTER WERE HAVING TEA AT IT'
KEY_NUMS = [7, 0, 13, 2]

def _make_interruptor_pool(length: int) -> list[int]:
    fractions = (0.12, 0.32, 0.52, 0.72)
    pool = sorted({int(length * frac) for frac in fractions})
    pool = [p for p in pool if 0 <= p < length]
    if len(pool) < 2:
        pool = list(range(min(length, 4)))
    return pool

def _pick_interruptors(pool: list[int]) -> list[int]:
    if len(pool) < 2:
        raise ValueError('Interruptor pool must include at least two positions')
    if len(pool) >= 4:
        picks = [pool[1], pool[-2]]
    else:
        picks = [pool[0], pool[-1]]
    return sorted(set(picks))

def main() -> None:
    pretty.print_rdp_identity()
    pretty.print_initialising()
    pretty.print_tutorial_contract(name='Vigenere smaller single-start interruptor Beam pool search', cipher='vigenere interruptors', solver='beam', direction='ltr', expected_result='exact solve', uses_reference_stop_score=True)
    direction = api.TextDirection.LEFT_TO_RIGHT
    pt_idx, wli, pt_runes = Runeglish.encode_english_to_runes(DEMO_TEXT, direction=direction.value)
    pt_arr = np.asarray(pt_idx, dtype=np.uint8)
    pool = _make_interruptor_pool(len(pt_idx))
    interruptors = _pick_interruptors(pool)
    if len(interruptors) < 2:
        raise ValueError('Need at least two interruptors for this tutorial')
    key_arr = np.asarray(KEY_NUMS, dtype=np.uint8)
    encrypt_cipher = api.CipherSpec.vigenere(alphabet_size=29)
    ct_idx = encrypt_interruptor_fixture(pt_arr, cipher=encrypt_cipher, key=tuple((int(_concrete_key_value) for _concrete_key_value in key_arr)), interruptor_positions=interruptors)
    intr_values_pt = [int(pt_arr[i]) for i in interruptors]
    intr_values_ct = [int(ct_idx[i]) for i in interruptors]
    if intr_values_pt != intr_values_ct:
        raise ValueError('Interruptor symbols changed during encryption')
    ct_idx_list = [int(v) for v in ct_idx.tolist()]
    ct_runes = Runeglish.to_rune(ct_idx_list, wli)
    print('Vigenere interruptor problem')
    print(f'direction: {direction.value}')
    print('Interruptor pool:', pool)
    print('Interruptor positions:', interruptors)
    print('Interruptor symbols:', intr_values_ct)
    print('Plaintext (preview):', pt_runes[:120] + ('...' if len(pt_runes) > 120 else ''))
    print('Ciphertext (preview):', ct_runes[:120] + ('...' if len(ct_runes) > 120 else ''))
    print_tutorial_debug_preview(label='plaintext', idx=pt_idx, wli=wli, direction=direction)
    print_tutorial_debug_preview(label='ciphertext', idx=ct_idx_list, wli=wli, direction=direction)
    interrupt_cfg = api.InterruptorConfig.search(pool, minimum_count=len(interruptors), maximum_count=len(interruptors), strategy=api.advanced.InterruptorSearchStrategy.AUTO, maximum_combinations=5000)
    scorer_params = api.ScoringConfig(character_lane_enabled=True, word_length_lane_enabled=True, character_order_weights={2: 0.3}, word_length_order_weights={2: 0.7}, objective=api.advanced.ScoringObjective.percentile_log_probability(window_size=10))
    display_scorer_params = api.ScoringConfig(character_lane_enabled=True, word_length_lane_enabled=True, character_order_weights={2: 0.3}, word_length_order_weights={2: 0.7}, objective=api.advanced.ScoringObjective.percentile_log_probability(window_size=10))
    stop = oracle_stop_score(pt_idx, wli, scorer_params, device='cpu', encoding_dir=direction, margin=0.02, min_score=0.5, fallback=0.55)
    print_stop_summary('Vigenere Interruptors (solve)', stop)
    solver = api.SolverSpec.beam_search(width=32, expansion=api.advanced.BeamExpansionMode.SWEEP, plateau_rounds=6, plateau_minimum_delta=0.0001, target_score=stop.stop_score, seed=TUTORIAL_SEED, rounds=0)
    key_spec = api.KeySpec.repeating(length=len(KEY_NUMS))
    cipher_spec = api.CipherSpec.vigenere(alphabet_size=29)
    display_spec = api.RunSpec(problem_input=api.RuneIndexInput(indices=ct_idx_list, word_lengths=wli), cipher=cipher_spec, key_space=key_spec, solver=solver, scoring=display_scorer_params, text_direction=direction, telemetry_enabled=True)
    result = api.run(api.RunSpec(problem_input=api.RuneIndexInput(indices=ct_idx_list, word_lengths=wli), cipher=cipher_spec, key_space=key_spec, solver=solver, scoring=scorer_params, telemetry_enabled=True, text_direction=direction, interruptors=interrupt_cfg))
    found_key = (result.key or []) or []
    found_core = found_key[:len(KEY_NUMS)]
    found_intr = [int(v) for v in found_key[len(KEY_NUMS):] if int(v) >= 0]
    if found_key:
        print('Found key (core):', found_core)
        print('Found interruptors:', found_intr)
    pretty.print_summary_spacer()
    api.display.print_result(
        result, spec=display_spec, options=api.display.SummaryOptions.for_tutorial()
    )


if __name__ == "__main__":
    main()
