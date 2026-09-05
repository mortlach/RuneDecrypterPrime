from __future__ import annotations
'Larger single-start Vigenere interruptor Beam-search tutorial.'
import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[3]
_SRC = _ROOT / 'src'
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
import numpy as np
from rdp import api
from tutorials.v1.data.two_period_cribs_demo import encrypt_interruptor_fixture
from tutorials.v1.data.plaintext_fixtures import plaintext1, word_breaks1
from rdp.data.runeglish import Runeglish
from tutorials.v1.support import tutorial_pretty as pretty
from tutorials.v1.support.tutorial_output import print_tutorial_debug_preview
from tutorials.v1.support.tutorial_utils import oracle_stop_score, print_stop_summary
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
TUTORIAL_SEED = 2027
INTERRUPTOR_SYMBOL = 27
INTERRUPTOR_TRUE_COUNT = 2
INTERRUPTOR_MIN = 0
INTERRUPTOR_MAX = 3
KEY_NUMS = [7, 0, 13, 2, 5, 21, 8]
MIN_MATCH_RATIO = 1.0

def _preview(text: str, limit: int=160) -> str:
    return text[:limit] + ('...' if len(text) > limit else '')

def main() -> None:
    pretty.print_rdp_identity()
    pretty.print_initialising()
    pretty.print_tutorial_contract(name='Vigenere larger single-start interruptor Beam search', cipher='vigenere interruptors', solver='beam', direction='ltr', expected_result='exact solve', uses_reference_stop_score=True)
    direction = api.TextDirection.LEFT_TO_RIGHT
    pt_idx = [int(v) for v in plaintext1]
    wli = [list(pair) for pair in word_breaks1]
    interruptors = [i for i, v in enumerate(pt_idx) if v == INTERRUPTOR_SYMBOL]
    if len(interruptors) != INTERRUPTOR_TRUE_COUNT:
        raise ValueError(f'Expected {INTERRUPTOR_TRUE_COUNT} interruptors with symbol {INTERRUPTOR_SYMBOL}, found {len(interruptors)}')
    pt_arr = np.asarray(pt_idx, dtype=np.uint8)
    key_arr = np.asarray(KEY_NUMS, dtype=np.uint8)
    encrypt_cipher = api.CipherSpec.vigenere(alphabet_size=29)
    ct_idx = encrypt_interruptor_fixture(pt_arr, cipher=encrypt_cipher, key=tuple((int(_concrete_key_value) for _concrete_key_value in key_arr)), interruptor_positions=interruptors)
    ct_idx_list = [int(v) for v in ct_idx.tolist()]
    pool = sorted({i for i, v in enumerate(ct_idx_list) if v == INTERRUPTOR_SYMBOL})
    if not set(interruptors).issubset(set(pool)):
        raise ValueError('Interruptor positions not found in symbol-derived pool')
    pt_runes = Runeglish.to_rune(pt_idx, wli)
    ct_runes = Runeglish.to_rune(ct_idx_list, wli)
    print('Vigenere non-trivial interruptor problem')
    print(f'encoding direction: {direction.value}')
    print('Interruptor symbol:', INTERRUPTOR_SYMBOL)
    print('Interruptor positions (true):', interruptors)
    print('Interruptor count range:', f'{INTERRUPTOR_MIN}..{INTERRUPTOR_MAX}')
    print('Interruptor pool size:', len(pool))
    print('Interruptor pool preview:', pool[:12])
    print('Plaintext preview:', _preview(pt_runes))
    print('Ciphertext preview:', _preview(ct_runes))
    print_tutorial_debug_preview(label='plaintext', idx=pt_idx, wli=wli, direction=direction)
    print_tutorial_debug_preview(label='ciphertext', idx=ct_idx_list, wli=wli, direction=direction)
    interrupt_cfg = api.InterruptorConfig.search(pool, minimum_count=INTERRUPTOR_MIN, maximum_count=INTERRUPTOR_MAX, strategy=api.advanced.InterruptorSearchStrategy.AUTO, maximum_combinations=5000)
    scorer_params = api.ScoringConfig(character_lane_enabled=True, word_length_lane_enabled=True, character_order_weights={2: 0.3}, word_length_order_weights={2: 0.7}, objective=api.advanced.ScoringObjective.percentile_log_probability(window_size=10))
    display_scorer_params = api.ScoringConfig(character_lane_enabled=True, word_length_lane_enabled=True, character_order_weights={2: 0.3}, word_length_order_weights={2: 0.7}, objective=api.advanced.ScoringObjective.percentile_log_probability(window_size=10))
    stop = oracle_stop_score(pt_idx, wli, scorer_params, device='cpu', encoding_dir=direction, margin=0.02, min_score=0.5, fallback=0.55)
    print_stop_summary('Vigenere Interruptors (non-trivial)', stop)
    solver = api.SolverSpec.beam_search(width=64, expansion=api.advanced.BeamExpansionMode.SWEEP, plateau_rounds=8, plateau_minimum_delta=0.0001, target_score=stop.stop_score, seed=TUTORIAL_SEED, rounds=0)
    cipher_spec = api.CipherSpec.vigenere(alphabet_size=29)
    key_spec = api.KeySpec.repeating(length=len(KEY_NUMS))
    display_spec = api.RunSpec(problem_input=api.RuneIndexInput(indices=ct_idx_list, word_lengths=wli), cipher=cipher_spec, key_space=key_spec, solver=solver, scoring=display_scorer_params, text_direction=direction, telemetry_enabled=True)
    result = api.run(api.RunSpec(problem_input=api.RuneIndexInput(indices=ct_idx_list, word_lengths=wli), cipher=cipher_spec, key_space=key_spec, solver=solver, scoring=scorer_params, telemetry_enabled=True, text_direction=direction, interruptors=interrupt_cfg))
    recovered = [int(value) for value in result.plaintext]
    match_ratio = (
        sum(a == b for a, b in zip(recovered, pt_idx, strict=True)) / len(pt_idx)
    )
    print(f'Match ratio: {match_ratio:.3f}')
    pretty.print_summary_spacer()
    api.display.print_result(
        result, spec=display_spec, options=api.display.SummaryOptions.for_tutorial()
    )
    if match_ratio < MIN_MATCH_RATIO:
        raise AssertionError('non-trivial interruptor tutorial did not recover exact plaintext')


if __name__ == "__main__":
    main()
