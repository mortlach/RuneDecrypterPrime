from __future__ import annotations
from rdp import api
'Railfence pretty-print tutorial.\n\nThis variant keeps the original railfence teaching path but reports through the\nstandard RDP printer contract.\n'
import sys
from pathlib import Path
from typing import Sequence
_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / 'src'
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext_english_string
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils import tutorial_pretty as pretty
from rune_decrypter_prime.utils.tutorial_output import print_tutorial_debug_preview
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
TUTORIAL_SEED = 4242
MIN_RAILS = 4
MAX_RAILS = 10
TRUE_RAILS = 7
MIN_MATCH_RATIO = 1.0

def _match_ratio(recovered: Sequence[int], reference: Sequence[int]) -> float:
    limit = min(len(recovered), len(reference))
    if limit == 0:
        return 0.0
    matches = sum((1 for i in range(limit) if int(recovered[i]) == int(reference[i])))
    return matches / float(limit)

def _preview_text(label: str, value: str, *, limit: int=160) -> None:
    suffix = '...' if len(value) > limit else ''
    print(f'{label} length: {len(value)}')
    print(f'{label} preview: {value[:limit]}{suffix}')

def main() -> None:
    pretty.print_rdp_identity()
    pretty.print_initialising()
    pretty.print_tutorial_contract(name='Railfence beam solve', cipher='railfence', solver='beam', direction='rtl', expected_result='exact solve', uses_reference_stop_score=False)
    direction = api.TextDirection.RIGHT_TO_LEFT
    pt_latin = plaintext_english_string
    reference_idx, wli, pt_runes = Runeglish.encode_english_to_runes(pt_latin, direction=direction)
    cipher_spec = api.CipherSpec.rail_fence(minimum_rails=MIN_RAILS, maximum_rails=MAX_RAILS, alphabet_size=29)
    rail_key = (TRUE_RAILS,)
    ct = api.encrypt(tuple(int(value) for value in reference_idx), cipher=api.CipherSpec.rail_fence(minimum_rails=MIN_RAILS, maximum_rails=MAX_RAILS, alphabet_size=29), key=(int(rail_key[0]),))
    ct_idx = [int(v) for v in list(ct)]
    ct_runes = Runeglish.to_rune(ct_idx, wli)
    print('Railfence problem')
    print(f'encoding direction: {direction.value}')
    print(f'true rails: {TRUE_RAILS}')
    print(f'qualified rail range: {MIN_RAILS}..{MAX_RAILS}')
    _preview_text('plaintext runes', pt_runes)
    _preview_text('ciphertext runes', ct_runes)
    print_tutorial_debug_preview(label='plaintext', idx=reference_idx, wli=wli, direction=direction)
    print_tutorial_debug_preview(label='ciphertext', idx=ct_idx, wli=wli, direction=direction)
    key_spec = api.KeySpec.scalar(minimum=MIN_RAILS, maximum=MAX_RAILS)
    scorer_params = api.ScoringConfig(character_lane_enabled=True, word_length_lane_enabled=True, character_order_weights={2: 0.3}, word_length_order_weights={2: 0.7}, objective=api.advanced.ScoringObjective.percentile_log_probability(window_size=10))
    display_scorer_params = api.ScoringConfig(character_lane_enabled=True, word_length_lane_enabled=True, character_order_weights={2: 0.3}, word_length_order_weights={2: 0.7}, objective=api.advanced.ScoringObjective.percentile_log_probability(window_size=10))
    solver_spec = api.SolverSpec.beam_search(width=64, plateau_rounds=40, seed=TUTORIAL_SEED, rounds=0)
    display_spec = api.RunSpec(problem_input=api.RuneIndexInput(indices=ct_idx, word_lengths=wli), cipher=cipher_spec, key_space=key_spec, solver=solver_spec, scoring=display_scorer_params, text_direction=direction, telemetry_enabled=True)
    result = api.run(api.RunSpec(problem_input=api.RuneIndexInput(indices=ct_idx, word_lengths=wli), cipher=cipher_spec, key_space=key_spec, solver=solver_spec, scoring=scorer_params, telemetry_enabled=True, text_direction=direction, compute_device=api.ComputeDevice.CPU))
    recovered = (result.plaintext_text or '') or (result.plaintext_text or '')
    print('Recovered plaintext preview:', recovered[:120] + ('...' if len(recovered) > 120 else ''))
    match_ratio = _match_ratio(result.plaintext, reference_idx)
    print(f'Match ratio: {match_ratio:.3f}')
    pretty.print_summary_spacer()
    api.display.print_result(
        result, spec=display_spec, options=api.display.SummaryOptions.for_tutorial()
    )


if __name__ == "__main__":
    main()
