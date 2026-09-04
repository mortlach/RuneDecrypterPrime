from __future__ import annotations
'Older Autokey GA and crib-assisted comparison.\n\nThis lighter alternative keeps the historical teaching shape: first a no-crib GA\nsolve, then a crib-assisted GA solve. It prints compact problem context, solver\ncalibration/progress, and a standard RDP summary for each solve. The qualified\nrobust Beam/WLI1+2 recipe is shown in ``Tutorial_Autokey_Robust.py``.\n'
import sys
from pathlib import Path
from typing import List, Sequence
_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / 'src'
for _import_root in (_ROOT, _SRC):
    if str(_import_root) not in sys.path:
        sys.path.insert(0, str(_import_root))
from rdp import api
import numpy as np
from rdp.data.runeglish import Runeglish
from tutorials.v1.support import tutorial_pretty as pretty
from tutorials.v1.support.tutorial_output import print_tutorial_debug_preview
from tutorials.v1.support.tutorial_utils import oracle_stop_score, print_stop_summary
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
SEED = [6, 1, 4]
SEED_LEN = len(SEED)
ALPHABET_SIZE = 29
MATCH_THRESHOLD = 1.0
CRIB_TEXT = 'WHITE RABBIT'
TUTORIAL_SEED_BASELINE = 2024
TUTORIAL_SEED_CRIB = 4242

def _match_ratio(found: Sequence[int], reference: Sequence[int]) -> float:
    n = min(len(found), len(reference))
    if n == 0:
        return 0.0
    matches = sum((1 for i in range(n) if int(found[i]) == int(reference[i])))
    return matches / float(n)


def _preview_text(label: str, value: str, *, limit: int = 160) -> None:
    suffix = "..." if len(value) > limit else ""
    print(f"{label} length: {len(value)}")
    print(f"{label} preview: {value[:limit]}{suffix}")


def _crib_seeds_from_prefix(
    ct_idx: Sequence[int],
    crib_text: str,
    *,
    direction: api.TextDirection,
    seed_len: int,
    alphabet: int,
) -> List[List[int]]:
    crib_idx, _, _ = Runeglish.encode_english_to_runes(
        crib_text,
        direction=("ltr" if direction is api.TextDirection.LEFT_TO_RIGHT else "rtl"),
    )
    crib_idx = [int(v) for v in crib_idx if v >= 0]
    if len(crib_idx) < seed_len or len(ct_idx) < seed_len:
        return []
    base = [int((int(ct_idx[i]) - crib_idx[i]) % alphabet) for i in range(seed_len)]
    seeds: List[List[int]] = [base]
    for delta in (-1, 1):
        seeds.append([(val + delta) % alphabet for val in base])
    return seeds

def main() -> None:
    pretty.print_rdp_identity()
    pretty.print_initialising()
    pretty.print_tutorial_contract(name='Autokey older GA/crib-assisted comparison', cipher='autokey', solver='ga', direction='rtl', expected_result='exact solve', uses_reference_stop_score=True)
    direction = api.TextDirection.RIGHT_TO_LEFT
    plaintext = "WHEN THE WHITE RABBIT READ THESE WORDS HE SEEMED SUDDENLY ALARMED FOR A SHOWER OF LITTLE GLASS BOXES CAME TUMBLING UPON HIM"
    pt_idx, wli, pt_runes = Runeglish.encode_english_to_runes(
        plaintext,
        direction=("ltr" if direction is api.TextDirection.LEFT_TO_RIGHT else "rtl"),
    )
    pt_idx_arr = np.asarray(pt_idx, dtype=np.uint8)
    autokey_cipher = api.CipherSpec.autokey(alphabet_size=ALPHABET_SIZE)
    seed_arr = np.asarray(SEED, dtype=np.uint8)
    ct_idx = api.encrypt(tuple(int(value) for value in pt_idx_arr), cipher=autokey_cipher, key=tuple(int(value) for value in seed_arr))
    ct_idx_list = [int(v) for v in list(ct_idx)]
    ct_runes = Runeglish.to_rune(ct_idx_list, wli)
    print('Autokey older GA/crib-assisted comparison (not the robust recipe)')
    print(f'encoding direction: {direction.value}')
    print(f'seed length: {SEED_LEN}')
    print(f'crib text used only for second run: {CRIB_TEXT}')
    _preview_text('plaintext runes', pt_runes)
    _preview_text('ciphertext runes', ct_runes)
    print_tutorial_debug_preview(label='plaintext', idx=pt_idx, wli=wli, direction=direction)
    print_tutorial_debug_preview(label='ciphertext', idx=ct_idx_list, wli=wli, direction=direction)
    cipher_spec = api.CipherSpec.autokey(alphabet_size=ALPHABET_SIZE)
    key_spec = api.KeySpec.repeating(length=SEED_LEN)
    scorer_params = api.ScoringConfig(character_lane_enabled=True, word_length_lane_enabled=True, character_order_weights={2: 0.3}, word_length_order_weights={2: 0.7}, objective=api.advanced.ScoringObjective.percentile_log_probability(window_size=10))
    display_scorer_params = api.ScoringConfig(character_lane_enabled=True, word_length_lane_enabled=True, character_order_weights={2: 0.3}, word_length_order_weights={2: 0.7}, objective=api.advanced.ScoringObjective.percentile_log_probability(window_size=10))
    stop = oracle_stop_score(pt_idx, wli, scorer_params, device='cpu', encoding_dir=direction, margin=0.02, min_score=0.5, fallback=0.54)
    print_stop_summary('Autokey GA', stop)

    def _run(label: str, solver: api.SolverSpec, initial_keys: Sequence[Sequence[int]] | None):
        print(f'\n=== Autokey solve: {label} ===')
        display_spec = api.RunSpec(problem_input=api.RuneIndexInput(indices=ct_idx_list, word_lengths=wli), cipher=cipher_spec, key_space=key_spec, solver=solver, scoring=display_scorer_params, text_direction=direction, telemetry_enabled=True)
        typed_initial_keys = None if initial_keys is None else tuple(tuple(int(value) for value in key) for key in initial_keys)
        result = api.run(api.RunSpec(problem_input=api.RuneIndexInput(indices=ct_idx, word_lengths=wli), cipher=cipher_spec, key_space=key_spec, solver=solver, scoring=scorer_params, initial_keys=typed_initial_keys, telemetry_enabled=True, text_direction=direction, compute_device=api.ComputeDevice.CPU))
        ratio = _match_ratio(result.plaintext, pt_idx)
        print(f'Match ratio ({label}): {ratio:.3f}')
        pretty.print_summary_spacer()
        api.display.print_result(
            result, spec=display_spec, options=api.display.SummaryOptions.for_tutorial()
        )
        return ratio
    baseline_solver = api.SolverSpec.genetic_algorithm(population_size=144, generations=120, elite_fraction=0.08, crossover_fraction=0.9, mutation_probability=0.25, tournament_size=4, plateau_generations=25, plateau_minimum_delta=0.0001, target_score=stop.stop_score, seed=TUTORIAL_SEED_BASELINE)
    baseline_ratio = _run('no crib', baseline_solver, initial_keys=None)
    crib_seeds = _crib_seeds_from_prefix(ct_idx_list, CRIB_TEXT, direction=direction, seed_len=SEED_LEN, alphabet=ALPHABET_SIZE)
    print(f'crib seed candidates: {len(crib_seeds)}')
    crib_solver = api.SolverSpec.genetic_algorithm(population_size=144, generations=120, elite_fraction=0.08, crossover_fraction=0.9, mutation_probability=0.25, tournament_size=4, plateau_generations=25, plateau_minimum_delta=0.0001, target_score=stop.stop_score, seed=TUTORIAL_SEED_CRIB)
    _run('crib assisted', crib_solver, initial_keys=crib_seeds or None)
    print(f'\nBaseline ratio: {baseline_ratio:.3f}')
if __name__ == '__main__':
    main()
