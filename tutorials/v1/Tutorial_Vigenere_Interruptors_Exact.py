from __future__ import annotations
from tutorials.v1.data.two_period_cribs_demo import encrypt_interruptor_fixture
from rdp import api
'Known-position Vigenere interruptor interface demonstration.\n\nThis is the tiny, explicit-position interruptor example. It demonstrates the\nmechanics of removing/reinserting interruptors and prints the final run through\nthe standard RDP printer facade.\n'
import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / 'src'
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
import numpy as np
from rune_decrypter_prime.utils.interrupter import InterruptorManager
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils import tutorial_pretty as pretty
from rune_decrypter_prime.utils.tutorial_output import print_tutorial_debug_preview
from rune_decrypter_prime.utils.tutorial_utils import oracle_stop_score, print_stop_summary
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
ALPHABET = 29
KEY = [7, 0, 13, 2, 0]
INTERRUPTORS = [2, 7, 13]
TUTORIAL_SEED = 2025
MIN_MATCH_RATIO = 1.0

def _make_wli(length: int, word_len: int=5) -> list[list[int]]:
    return [[i % word_len, word_len] for i in range(length)]

def main() -> None:
    pretty.print_rdp_identity()
    pretty.print_initialising()
    pretty.print_tutorial_contract(name='Vigenere known-position interruptor interface demonstration', cipher='vigenere interruptors', solver='beam', direction='ltr', expected_result='exact solve', uses_reference_stop_score=True)
    direction = api.TextDirection.LEFT_TO_RIGHT
    pt_idx = np.array([4, 20, 1, 3, 14, 25, 6, 8, 9, 10, 12, 17, 18, 2, 5, 7, 11, 13, 15, 19], dtype=np.uint8)
    pt_idx_list = [int(v) for v in pt_idx.tolist()]
    wli = _make_wli(int(pt_idx.size), word_len=5)
    pt_runes = Runeglish.to_rune(pt_idx_list, wli)
    key_arr = np.asarray(KEY, dtype=np.uint8)
    key_len = int(key_arr.size)
    encrypt_cipher = api.CipherSpec.vigenere(alphabet_size=29)
    ct_idx = encrypt_interruptor_fixture(pt_idx, cipher=encrypt_cipher, key=tuple((int(_concrete_key_value) for _concrete_key_value in key_arr)), interruptor_positions=INTERRUPTORS)
    ct_idx_list = [int(v) for v in ct_idx.tolist()]
    ct_runes = Runeglish.to_rune(ct_idx_list, wli)
    intr_values_pt = [int(pt_idx[i]) for i in INTERRUPTORS]
    intr_values_ct = [int(ct_idx[i]) for i in INTERRUPTORS]
    if intr_values_pt != intr_values_ct:
        raise ValueError('Interruptor symbols changed during encryption')
    intr_mgr = InterruptorManager()
    pt_core, info = intr_mgr.remove_from(pt_idx, possible_idx=INTERRUPTORS)
    ct_core, _ = intr_mgr.remove_from(ct_idx, possible_idx=INTERRUPTORS)
    print('Vigenere known-position interruptor interface demonstration')
    print('This is not unknown-position solver qualification.')
    print(f'encoding direction: {direction.value}')
    print('Interruptor positions:', INTERRUPTORS)
    print('Interruptor symbols:', intr_values_ct)
    print('Plaintext (runes):', pt_runes)
    print('Ciphertext (runes):', ct_runes)
    print('Core length:', int(pt_core.size), '->', int(ct_core.size))
    print_tutorial_debug_preview(label='plaintext', idx=pt_idx_list, wli=wli, direction=direction)
    print_tutorial_debug_preview(label='ciphertext', idx=ct_idx_list, wli=wli, direction=direction)
    print('Core interruptors removed:', info.idx.tolist())
    scorer_params = api.ScoringConfig(character_lane_enabled=True, word_length_lane_enabled=True, character_order_weights={2: 0.3}, word_length_order_weights={2: 0.7}, objective=api.advanced.ScoringObjective.percentile_log_probability(window_size=10))
    display_scorer_params = api.ScoringConfig(character_lane_enabled=True, word_length_lane_enabled=True, character_order_weights={2: 0.3}, word_length_order_weights={2: 0.7}, objective=api.advanced.ScoringObjective.percentile_log_probability(window_size=10))
    stop = oracle_stop_score(pt_idx_list, wli, scorer_params, device='cpu', encoding_dir=direction, margin=0.02, min_score=0.45, fallback=0.5)
    print_stop_summary('Vigenere Interruptors exact', stop)
    solver = api.SolverSpec.beam_search(width=1, target_score=stop.stop_score, plateau_rounds=4, plateau_minimum_delta=0.0001, seed=TUTORIAL_SEED, rounds=0)
    cipher_spec = api.CipherSpec.vigenere(alphabet_size=29)
    key_spec = api.KeySpec.repeating(length=key_len)
    display_spec = api.RunSpec(problem_input=api.RuneIndexInput(indices=ct_idx_list, word_lengths=wli), cipher=cipher_spec, key_space=key_spec, solver=solver, scoring=display_scorer_params, text_direction=direction, telemetry_enabled=True)
    result = api.run(api.RunSpec(problem_input=api.RuneIndexInput(indices=ct_idx_list, word_lengths=wli), cipher=cipher_spec, key_space=key_spec, solver=solver, scoring=scorer_params, telemetry_enabled=True, text_direction=direction, interruptors=api.InterruptorConfig.exact(INTERRUPTORS)))
    pretty.print_summary_spacer()
    api.display.print_result(result, options=api.display.SummaryOptions.tutorial())
if __name__ == '__main__':
    main()
