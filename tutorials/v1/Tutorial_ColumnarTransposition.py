from __future__ import annotations
from rdp import api
import sys
from pathlib import Path
from typing import List, Sequence
_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / 'src'
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext_english_string
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils.tutorial_output import tutorial_debug_preview_block
from rune_decrypter_prime.utils.tutorial_utils import format_stop_summary, oracle_stop_score
'\nTutorial variant: Columnar Transposition with the standard RDP printer facade.\n\nThis file intentionally lives beside the original tutorial. The original remains\nstable while this variant proves the new display/printer contract.\n'
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
TUTORIAL_SEED = 12345
PREVIEW_RUNES = 160
PREVIEW_IDX = 32

def encrypt_columnar(pt: str, key: List[int]) -> str:
    """Row-fill, then read columns in the order given by 'key' (no spaces)."""
    K = len(key)
    rows = (len(pt) + K - 1) // K
    table = [list(pt[i * K:i * K + K]) for i in range(rows)]
    out_chars: List[str] = []
    for col in key:
        for r in range(rows):
            if col < len(table[r]):
                out_chars.append(table[r][col])
    return ''.join(out_chars)

def _preview_text(value: str, *, limit: int=PREVIEW_RUNES) -> str:
    suffix = '...' if len(value) > limit else ''
    return f'{value[:limit]}{suffix}'

def _preview_sequence(values: Sequence[int], *, limit: int=PREVIEW_IDX) -> str:
    clipped = list(values[:limit])
    suffix = ' ...' if len(values) > limit else ''
    return f'{clipped}{suffix}'

def _model_loading_rows(events: Sequence[object]) -> list[tuple[str, object]]:
    if not events:
        return [('status', 'no model assets loaded')]
    if len(events) == 1:
        event = events[0]
        return [(getattr(event, 'asset_type'), getattr(event, 'asset_id')), ('status', getattr(event, 'status'))]
    return [(f"{getattr(event, 'asset_type')} {index}", f"{getattr(event, 'asset_id')} ({getattr(event, 'status')})") for index, event in enumerate(events, start=1)]

def main() -> None:
    print('Recipe note: this concise tutorial uses a char2-only pedagogical scorer;')
    print('the qualified robustness recipe uses char2=.30 plus WLI2=.70.')
    print_options = api.display.PrintOptions.detailed()
    direction = api.TextDirection.RIGHT_TO_LEFT
    pt_en = plaintext_english_string
    _pt_idx_with_spaces, _wli_pt, pt_runes = Runeglish.encode_english_to_runes(pt_en, direction=direction.value)
    pt_runes_nosp = pt_runes.replace(' ', '')
    reference_idx = Runeglish.rune_to_pos(pt_runes_nosp)
    key_true = [3, 6, 1, 4, 2, 0, 5]
    ct_runes = encrypt_columnar(pt_runes_nosp, key_true)
    ct_idx = Runeglish.rune_to_pos(ct_runes)
    api.display.print_block(api.display.format_banner(options=print_options))
    api.display.print_block(api.display.format_key_value_block('Initialising RDP', [('display schema', 'api_display_summary.v1'), ('encoding', 'utf-8'), ('status', 'ready')], options=print_options))
    api.display.print_block(api.display.format_key_value_block('Tutorial', [('name', 'Columnar transposition'), ('cipher', 'columnar'), ('solver', 'hybrid'), ('direction', direction.value), ('expected result', 'exact solve'), ('truth/reference use', 'stop-score calibration; not supplied to solver ranking')], options=print_options))
    api.display.print_block(api.display.format_key_value_block('Problem input', [('plaintext runes length', len(pt_runes_nosp)), ('ciphertext runes length', len(ct_runes)), ('ciphertext indices length', len(ct_idx)), ('true key length', len(key_true))], options=print_options))
    api.display.print_block(api.display.format_preview_block('Plaintext preview', [('runes', _preview_text(pt_runes_nosp))], options=print_options))
    api.display.print_block(api.display.format_preview_block('Ciphertext preview', [('runes', _preview_text(ct_runes)), ('indices', _preview_sequence(ct_idx))], options=print_options))
    api.display.print_block(tutorial_debug_preview_block(label='plaintext_no_spaces', idx=reference_idx, wli=None, direction=direction, options=print_options))
    api.display.print_block(tutorial_debug_preview_block(label='ciphertext_no_spaces', idx=ct_idx, wli=None, direction=direction, options=print_options))
    cipher = api.CipherSpec.columnar(columns=len(key_true))
    key_spec = api.KeySpec.permutation(length=len(key_true))
    scorer_params = api.ScoringConfig(character_lane_enabled=True, word_length_lane_enabled=False, character_order_weights={2: 1.0}, word_length_order_weights={}, objective=api.advanced.ScoringObjective.percentile_log_probability(window_size=10))
    display_scorer_params = api.ScoringConfig(character_lane_enabled=True, word_length_lane_enabled=False, character_order_weights={2: 1.0}, objective=api.advanced.ScoringObjective.percentile_log_probability(window_size=10))
    lm_load_events: list[object] = []
    stop = oracle_stop_score(reference_idx, None, scorer_params, device='cpu', encoding_dir=direction, margin=0.02, min_score=0.45, fallback=0.503, load_reporter=lm_load_events.append)
    api.display.print_block(api.display.format_status_block('Model loading', _model_loading_rows(lm_load_events), options=print_options))
    api.display.print_block(format_stop_summary('Columnar Hybrid', stop, options=print_options))
    solve_spec = api.SolverSpec.hybrid(use_beam_search=True, beam_width=96, beam_rounds=6, beam_expansion=api.advanced.BeamExpansionMode.SAMPLE, sample_per_parent=48, top_parents_fraction=0.4, genetic_algorithm=api.SolverSpec.genetic_algorithm(population_size=96, generations=40, elite_fraction=0.1, crossover_fraction=0.85, mutation_probability=0.3, tournament_size=3, plateau_generations=12, plateau_minimum_delta=0.0001, target_score=stop.stop_score), simulated_annealing=api.SolverSpec.simulated_annealing(iterations=3000, initial_temperature=0.95, minimum_temperature=0.0001, cooling_rate=0.997, plateau_iterations=300, plateau_minimum_delta=0.0001, local_improvement_on_accept=True, target_score=stop.stop_score), seed=TUTORIAL_SEED, plateau_rounds=8, plateau_minimum_delta=0.0001, target_score=stop.stop_score)
    display_spec = api.RunSpec(problem_input=api.RawTextInput(text=ct_runes), cipher=cipher, key_space=key_spec, solver=solve_spec, scoring=display_scorer_params, text_direction=direction, telemetry_enabled=True)
    api.display.print_block(api.display.format_section('Run progress'))
    result = api.run(api.RunSpec(problem_input=api.RuneIndexInput(indices=ct_idx, word_lengths=None), cipher=cipher, key_space=key_spec, solver=solve_spec, scoring=scorer_params, telemetry_enabled=True, text_direction=direction, compute_device=api.ComputeDevice.CPU))
    print()
    api.display.print_result(
        result, spec=display_spec, options=api.display.SummaryOptions.for_tutorial()
    )


if __name__ == "__main__":
    main()
