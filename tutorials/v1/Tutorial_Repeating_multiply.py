from __future__ import annotations
from rdp import api
'Repeating multiply pretty-print tutorial.\n\nThis variant demonstrates a custom user map, ct = pt * k mod 29, and reports the\nreal solve through the standard RDP printer contract.\n'
import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / 'src'
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
import numpy as np
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext1_rev, word_breaks1_rev
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils import tutorial_pretty as pretty
from rune_decrypter_prime.utils.tutorial_output import print_tutorial_debug_preview
from rune_decrypter_prime.utils.tutorial_utils import oracle_stop_score, print_stop_summary
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
N = 29
TUTORIAL_SEED = 12345
KEY_LEN = 13
MIN_MATCH_RATIO = 1.0
DIRECTION = api.TextDirection.RIGHT_TO_LEFT

def mult_map(pt: int, k: int) -> int:
    return pt * k % N

def _preview(label: str, text: str, limit: int=160) -> None:
    suffix = '...' if len(text) > limit else ''
    print(f'{label} length: {len(text)}')
    print(f'{label} preview: {text[:limit]}{suffix}')

def main() -> None:
    pretty.print_rdp_identity()
    pretty.print_initialising()
    pretty.print_tutorial_contract(name='Repeating multiply mod 29', cipher='repeating multiply', solver='beam', direction='rtl', expected_result='exact solve', uses_reference_stop_score=True)
    rng = np.random.default_rng(TUTORIAL_SEED)
    key_nums = rng.integers(1, N, size=KEY_LEN).tolist()
    pt_idx = [int(v) for v in plaintext1_rev]
    wli = [list(pair) for pair in word_breaks1_rev]
    pt_runes = Runeglish.to_rune(pt_idx, wli)
    stream = [key_nums[i % KEY_LEN] for i in range(len(pt_idx))]
    ct_idx = [int(p * k % N) for p, k in zip(pt_idx, stream)]
    ct_runes = Runeglish.to_rune(ct_idx, wli)
    print('Repeating multiply problem')
    print(f'encoding direction: {DIRECTION.value}')
    print(f'map: ct = pt * k mod {N}')
    print(f'key length: {KEY_LEN}')
    _preview('plaintext runes', pt_runes)
    _preview('ciphertext runes', ct_runes)
    print_tutorial_debug_preview(label='plaintext', idx=pt_idx, wli=wli, direction=DIRECTION)
    print_tutorial_debug_preview(label='ciphertext', idx=ct_idx, wli=wli, direction=DIRECTION)
    cipher = api.experimental.define_cipher_map(mult_map, alphabet_size=N)
    key_spec = api.KeySpec.repeating(length=KEY_LEN)
    scorer_params = api.ScoringConfig(character_lane_enabled=True, word_length_lane_enabled=True, character_order_weights={2: 0.3}, word_length_order_weights={2: 0.7})
    display_scorer_params = api.ScoringConfig(character_lane_enabled=True, word_length_lane_enabled=True, character_order_weights={2: 0.3}, word_length_order_weights={2: 0.7}, objective=api.advanced.ScoringObjective.percentile_log_probability(window_size=10))
    stop = oracle_stop_score(pt_idx, wli, scorer_params, device='cpu', encoding_dir=DIRECTION, margin=0.02, min_score=0.5, fallback=0.55)
    print_stop_summary('Repeating Multiply Beam', stop)
    solve_spec = api.SolverSpec.beam_search(width=32, maximum_children_per_parent=24, plateau_rounds=8, plateau_minimum_delta=0.0001, target_score=stop.stop_score, seed=TUTORIAL_SEED, rounds=0)
    display_spec = api.RunSpec(problem_input=api.RuneIndexInput(indices=ct_idx, word_lengths=wli), cipher=cipher, key_space=key_spec, solver=solve_spec, scoring=display_scorer_params, text_direction=DIRECTION, telemetry_enabled=True)
    result = api.run(api.RunSpec(problem_input=api.RuneIndexInput(indices=ct_idx, word_lengths=wli), cipher=cipher, key_space=key_spec, solver=solve_spec, scoring=scorer_params, telemetry_enabled=True, text_direction=DIRECTION))
    recovered = (result.plaintext_text or '') or (result.plaintext_text or '')
    print('Recovered plaintext preview:', str(recovered)[:120] + ('...' if len(str(recovered)) > 120 else ''))
    pretty.print_summary_spacer()
    api.display.print_result(
        result, spec=display_spec, options=api.display.SummaryOptions.for_tutorial()
    )


if __name__ == "__main__":
    main()
