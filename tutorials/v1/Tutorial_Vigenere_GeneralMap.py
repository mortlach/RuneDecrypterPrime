from __future__ import annotations
from rdp import api
import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / 'src'
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext_english_string
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils import tutorial_pretty as pretty
from rune_decrypter_prime.utils.tutorial_output import print_tutorial_debug_preview
from rune_decrypter_prime.utils.tutorial_utils import oracle_stop_score, print_stop_summary
'\nTutorial variant: Vigenere via the General Map API with the standard RDP printer.\n\nThe original tutorial remains unchanged; this variant proves the printer facade.\n'
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
N = 29
TUTORIAL_SEED = 12345
MIN_MATCH_RATIO = 1.0

def vigenere_map(pt: int, k: int) -> int:
    return (pt + k) % N

def main() -> None:
    pretty.print_rdp_identity()
    pretty.print_initialising()
    pretty.print_tutorial_contract(name='Vigenere via General Map API', cipher='vigenere general map', solver='beam', direction='rtl', expected_result='exact solve', uses_reference_stop_score=True)
    pt_en = plaintext_english_string
    encoding_dir = api.TextDirection.RIGHT_TO_LEFT
    pt_idx, wli, _pt_runes = Runeglish.encode_english_to_runes(pt_en, direction=encoding_dir)
    cipher = api.experimental.define_cipher_map(vigenere_map, alphabet_size=N)
    key_nums = [3, 1, 4, 1, 5, 6]
    stream = [key_nums[i % len(key_nums)] for i in range(len(pt_idx))]
    ct_idx = [vigenere_map(p, k) for p, k in zip(pt_idx, stream)]
    ct_runes = Runeglish.to_rune(ct_idx, wli)
    print('Vigenere general-map problem')
    print(f'direction: {encoding_dir.value}')
    print(f'ciphertext length: {len(ct_idx)}')
    print(f'key period: {len(key_nums)}')
    print(f"ciphertext preview: {ct_runes[:160]}{('...' if len(ct_runes) > 160 else '')}")
    print_tutorial_debug_preview(label='plaintext', idx=pt_idx, wli=wli, direction=encoding_dir)
    print_tutorial_debug_preview(label='ciphertext', idx=ct_idx, wli=wli, direction=encoding_dir)
    scorer_params = api.ScoringConfig(character_lane_enabled=True, word_length_lane_enabled=True, character_order_weights={2: 0.3}, word_length_order_weights={2: 0.7})
    display_scorer_params = api.ScoringConfig(character_lane_enabled=True, word_length_lane_enabled=True, character_order_weights={2: 0.3}, word_length_order_weights={2: 0.7}, objective=api.advanced.ScoringObjective.percentile_log_probability(window_size=10))
    stop = oracle_stop_score(pt_idx, wli, scorer_params, device='cpu', encoding_dir=encoding_dir, margin=0.02, min_score=0.5, fallback=0.54)
    print_stop_summary('Vigenere Beam', stop)
    key_spec = api.KeySpec.repeating(length=len(key_nums))
    solve_spec = api.SolverSpec.beam_search(width=24, target_score=stop.stop_score, plateau_rounds=6, plateau_minimum_delta=0.0001, maximum_children_per_parent=16, seed=TUTORIAL_SEED, rounds=0)
    display_spec = api.RunSpec(problem_input=api.RuneIndexInput(indices=ct_idx, word_lengths=wli), cipher=cipher, key_space=key_spec, solver=solve_spec, scoring=display_scorer_params, text_direction=encoding_dir, telemetry_enabled=True)
    result = api.run(api.RunSpec(problem_input=api.RuneIndexInput(indices=ct_idx, word_lengths=wli), cipher=cipher, key_space=key_spec, solver=solve_spec, scoring=scorer_params, telemetry_enabled=True, text_direction=encoding_dir))
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
        raise AssertionError('general-map tutorial did not recover exact plaintext')


if __name__ == "__main__":
    main()
