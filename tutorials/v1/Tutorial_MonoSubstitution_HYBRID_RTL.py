from __future__ import annotations
from rdp import api
'Mono-substitution HYBRID pretty-print tutorial for RTL rune encoding.'
import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / 'src'
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
import numpy as np
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext_english_string
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils import tutorial_pretty as pretty
from rune_decrypter_prime.utils.tutorial_output import print_tutorial_debug_preview
from rune_decrypter_prime.utils.tutorial_utils import oracle_stop_score, print_stop_summary
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
DIRECTION = api.TextDirection.RIGHT_TO_LEFT
TUTORIAL_SEED = 12345
CIPHERTEXT_SEED = 12345
MIN_MATCH_RATIO = 0.995

def preview(s: str, n: int=120) -> str:
    return s if len(s) <= n else s[:n] + '...'

def _invert_perm(pt_to_ct: np.ndarray) -> np.ndarray:
    inv = np.empty_like(pt_to_ct)
    inv[pt_to_ct] = np.arange(pt_to_ct.size, dtype=np.uint8)
    return inv

def _build_ciphertext(pt_en: str, *, seed: int):
    pt_idx, wli, _ = Runeglish.encode_english_to_runes(pt_en, direction=DIRECTION.value)
    rng = np.random.default_rng(seed)
    key_fwd = rng.permutation(29).astype(np.uint8)
    ciph = api.CipherSpec.substitution(alphabet_size=29)
    ct_idx = api.encrypt(tuple(int(value) for value in pt_idx), cipher=ciph, key=tuple(int(value) for value in key_fwd))
    ct_runes = Runeglish.to_rune(list(ct_idx), wli)
    key_inv = _invert_perm(key_fwd)
    return ([int(v) for v in list(ct_idx)], ct_runes, wli, key_fwd.tolist(), key_inv.tolist(), pt_idx)

def main() -> None:
    pretty.print_rdp_identity()
    pretty.print_initialising()
    pretty.print_tutorial_contract(name='Mono-substitution hybrid RTL', cipher='mono substitution', solver='hybrid', direction='rtl', expected_result='near-exact solve', uses_reference_stop_score=True)
    ct_idx, ct_runes, wli, _key_fwd, _key_inv, pt_idx = _build_ciphertext(plaintext_english_string, seed=CIPHERTEXT_SEED)
    print('Mono-substitution HYBRID problem')
    print(f'encoding direction: {DIRECTION.value}')
    print('solver path: Beam warm-start -> GA explore -> SA polish')
    print('start condition: no true-key seed supplied')
    print(f'ciphertext length: {len(ct_idx)}')
    print(f'ciphertext preview: {preview(ct_runes, 160)}')
    print_tutorial_debug_preview(label='plaintext', idx=pt_idx, wli=wli, direction=DIRECTION)
    print_tutorial_debug_preview(label='ciphertext', idx=ct_idx, wli=wli, direction=DIRECTION)
    scorer_params = api.ScoringConfig(character_lane_enabled=True, word_length_lane_enabled=True, character_order_weights={2: 0.3}, word_length_order_weights={2: 0.7})
    display_scorer_params = api.ScoringConfig(character_lane_enabled=True, word_length_lane_enabled=True, character_order_weights={2: 0.3}, word_length_order_weights={2: 0.7}, objective=api.advanced.ScoringObjective.percentile_log_probability(window_size=10))
    stop = oracle_stop_score(pt_idx, wli, scorer_params, device='cpu', encoding_dir=DIRECTION, margin=0.02, min_score=0.5, fallback=0.55)
    print_stop_summary('Mono Hybrid', stop)
    solver = api.SolverSpec.hybrid(use_beam_search=True, beam_width=12, beam_rounds=6, beam_expansion=api.advanced.BeamExpansionMode.SAMPLE, sample_per_parent=16, top_parents_fraction=0.5, genetic_algorithm=api.SolverSpec.genetic_algorithm(population_size=60, generations=15, elite_fraction=0.08, crossover_fraction=0.85, mutation_probability=0.35, tournament_size=3, plateau_generations=8, plateau_minimum_delta=0.0001, target_score=stop.stop_score), simulated_annealing=api.SolverSpec.simulated_annealing(iterations=1500, initial_temperature=0.8, minimum_temperature=0.001, automatic_cooling=True, cooling_rate=0.996, reseed_interval=2000, rescue_drop_absolute=0.02, rescue_drop_ratio=0.5, local_improvement_on_accept=False, plateau_iterations=80, plateau_minimum_delta=0.0001, target_score=stop.stop_score), seed=TUTORIAL_SEED, plateau_rounds=8, plateau_minimum_delta=0.0001, target_score=stop.stop_score)
    cipher_spec = api.CipherSpec.substitution(alphabet_size=29)
    key_spec = api.KeySpec.permutation(length=29)
    display_spec = api.RunSpec(problem_input=api.RuneIndexInput(indices=ct_idx, word_lengths=wli), cipher=cipher_spec, key_space=key_spec, solver=solver, scoring=display_scorer_params, text_direction=DIRECTION, telemetry_enabled=True)
    result = api.run(api.RunSpec(problem_input=api.RuneIndexInput(indices=ct_idx, word_lengths=wli), cipher=cipher_spec, key_space=key_spec, solver=solver, scoring=scorer_params, telemetry_enabled=True, text_direction=DIRECTION, compute_device=api.ComputeDevice.CPU))
    recovered = (result.plaintext_text or '') or (result.plaintext_text or '')
    print('Recovered plaintext:', preview(str(recovered)))
    print('Score:', round(result.score, 6))
    pretty.print_summary_spacer()
    api.display.print_result(result, options=api.display.SummaryOptions.tutorial())
if __name__ == '__main__':
    main()
