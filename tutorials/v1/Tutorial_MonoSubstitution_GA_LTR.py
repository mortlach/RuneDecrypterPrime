from __future__ import annotations
'Lighter single-attempt Mono-substitution GA tutorial for LTR encoding.\n\nThis is an independently generated LTR-encoded mono-substitution example. It is\nnot the same ciphertext as the RTL tutorial solved under a different assumption.\nThe purpose is to show that RDP can solve this cipher shape in LTR rune encoding\nwhile preserving the standard printer/report contract. It uses the earlier\nchar2/WLI2 scorer, not the qualified three-attempt recipe.\n'
import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / 'src'
for _import_root in (_ROOT, _SRC):
    if str(_import_root) not in sys.path:
        sys.path.insert(0, str(_import_root))
from rdp import api
import numpy as np
from tutorials.v1.data.plaintext_fixtures import plaintext_english_string
from rdp.data.runeglish import Runeglish
from tutorials.v1.support import tutorial_pretty as pretty
from tutorials.v1.support.tutorial_output import print_tutorial_debug_preview
from rdp.solvers.seed_generation import make_seeds_from_freq
from tutorials.v1.support.tutorial_utils import oracle_stop_score, print_stop_summary
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
DIRECTION = api.TextDirection.LEFT_TO_RIGHT
START_MODE = 'seeded'
STOP_SCORE = 0.55
TUTORIAL_SEED = 12345
CIPHERTEXT_SEED = 12345
SEED_KEYS = 240
SEED_SWAPS = 3
POPULATION = 144
GENERATIONS = 160
MIN_MATCH_RATIO = 0.97
TUTORIAL_PATH = 'Tutorial_MonoSubstitution_GA_LTR.py'
TUTORIAL_TITLE = 'Mono-substitution lighter single-attempt GA LTR demonstration'

def preview(s: str, n: int=120) -> str:
    return s if len(s) <= n else s[:n] + '...'

def _invert_perm(pt_to_ct: np.ndarray) -> np.ndarray:
    inv = np.empty_like(pt_to_ct)
    inv[pt_to_ct] = np.arange(pt_to_ct.size, dtype=np.uint8)
    return inv

def _build_ciphertext(pt_en: str, *, encoding_direction: api.TextDirection, seed: int):
    pt_idx, wli, _ = Runeglish.encode_english_to_runes(pt_en, direction="ltr")
    rng = np.random.default_rng(seed)
    key_fwd = rng.permutation(29).astype(np.uint8)
    ciph = api.CipherSpec.substitution(alphabet_size=29)
    ct_idx = api.encrypt(tuple(int(value) for value in pt_idx), cipher=ciph, key=tuple(int(value) for value in key_fwd))
    ct_runes = Runeglish.to_rune(list(ct_idx), wli)
    key_inv = _invert_perm(key_fwd)
    return (ct_idx, ct_runes, wli, key_fwd.tolist(), key_inv.tolist(), pt_idx)

def main() -> None:
    pretty.print_rdp_identity()
    pretty.print_initialising()
    pretty.print_tutorial_contract(name='Mono-substitution lighter single-attempt GA LTR', cipher='mono substitution', solver='ga', direction='ltr', expected_result='human-readable solve', uses_reference_stop_score=True)
    pt_en = plaintext_english_string
    ct_idx, ct_runes, wli, _key_fwd, _key_inv, pt_idx = _build_ciphertext(pt_en, encoding_direction=DIRECTION, seed=CIPHERTEXT_SEED)
    ct_idx_list = [int(v) for v in list(ct_idx)]
    print('Mono-substitution lighter single-attempt GA problem')
    print('recipe status: earlier scorer demonstration; not the qualified robust recipe')
    print(f'encoding direction: {DIRECTION.value}')
    print('example relation: independent generated LTR ciphertext, not paired with the RTL tutorial')
    print(f'ciphertext length: {len(ct_idx_list)}')
    print(f'ciphertext preview: {preview(ct_runes, 160)}')
    print_tutorial_debug_preview(label='plaintext', idx=pt_idx, wli=wli, direction=DIRECTION)
    print_tutorial_debug_preview(label='ciphertext', idx=ct_idx_list, wli=wli, direction=DIRECTION)
    seeds = None
    if START_MODE == "seeded":
        seeds = make_seeds_from_freq(
            ct_runes.replace(" ", ""),
            n_keys=SEED_KEYS,
            swaps_per_key=SEED_SWAPS,
            seed=TUTORIAL_SEED,
            direction="ltr",
        )
    print(f"seeded starts: {(0 if seeds is None else len(seeds))}")
    print(f"GA population: {POPULATION}")
    print(f"GA generations: {GENERATIONS}")
    scorer_params = api.ScoringConfig(
        word_length_lane_enabled=True,
        character_order_weights={2: 0.3},
        word_length_order_weights={2: 0.7},
    )
    display_scorer_params = api.ScoringConfig(
        character_lane_enabled=True,
        word_length_lane_enabled=True,
        character_order_weights={2: 0.3},
        word_length_order_weights={2: 0.7},
        objective=api.advanced.ScoringObjective.percentile_log_probability(
            window_size=10
        ),
    )
    stop = oracle_stop_score(
        pt_idx,
        wli,
        scorer_params,
        device="cpu",
        encoding_dir=DIRECTION,
        margin=0.02,
        min_score=0.5,
        fallback=STOP_SCORE,
    )
    print_stop_summary(f"Mono GA {DIRECTION.value}", stop)
    solver = api.SolverSpec.genetic_algorithm(
        population_size=POPULATION,
        generations=GENERATIONS,
        target_score=stop.stop_score,
        elite_fraction=0.08,
        crossover_fraction=0.85,
        mutation_probability=0.25,
        tournament_size=4,
        plateau_generations=20,
        plateau_minimum_delta=0.0001,
        seed=TUTORIAL_SEED,
    )
    key_spec = api.KeySpec.permutation(length=29)
    cipher_spec = api.CipherSpec.substitution(alphabet_size=29)
    display_spec = api.RunSpec(problem_input=api.RuneIndexInput(indices=ct_idx_list, word_lengths=wli), cipher=cipher_spec, key_space=key_spec, solver=solver, scoring=display_scorer_params, text_direction=DIRECTION, telemetry_enabled=True)
    initial_keys = (
        None
        if seeds is None
        else tuple(tuple(int(value) for value in key) for key in seeds)
    )
    result = api.run(api.RunSpec(problem_input=api.RuneIndexInput(indices=ct_idx, word_lengths=wli), cipher=cipher_spec, key_space=key_spec, solver=solver, scoring=scorer_params, initial_keys=initial_keys, telemetry_enabled=True, text_direction=DIRECTION))
    mode_label = 'GA (seeded start)' if seeds is not None else 'GA (noise start)'
    print(f'Mode: {mode_label}')
    rec = (result.plaintext_text or '') or (result.plaintext_text or '')
    print('Recovered plaintext:', preview(str(rec)))
    print('Score:', round(result.score, 6))
    pipeline = getattr(result.solver_report.details, 'value', {}) or {}
    print('Pipeline block:', pipeline)
    has_tel = bool((result.telemetry or {}).get('telemetry'))
    print('Telemetry attached:', has_tel)
    recovered_idx = [int(value) for value in result.plaintext]
    expected_idx = [int(value) for value in pt_idx]
    match_ratio = (
        sum(a == b for a, b in zip(recovered_idx, expected_idx, strict=True))
        / len(expected_idx)
    )
    print(f'Match ratio: {match_ratio:.3f}')
    pretty.print_summary_spacer()
    api.display.print_result(
        result, spec=display_spec, options=api.display.SummaryOptions.for_tutorial()
    )
    if match_ratio < MIN_MATCH_RATIO:
        raise AssertionError(f'GA LTR solve below acceptance threshold: {match_ratio:.3f}')


if __name__ == "__main__":
    main()
