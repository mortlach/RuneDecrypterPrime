from __future__ import annotations
from rdp import api
import re
import pytest
import numpy as np
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils.seed_utils import make_seeds_from_freq
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext_english_string
from tests.tutorials._utils import plaintext_match_rate
from tests.scoring._helpers.lm_test_guard import require_full_lm_assets

pytestmark = pytest.mark.tier_a


@pytest.mark.parametrize("optimizer", ["sa", "ga"])
def test_tutorial_mono_runs(optimizer):
    """Check that SA/GA tutorials recover text above a minimum score."""
    require_full_lm_assets(
        models=("char", "wli"),
        modes=("rtl",),
        poses=("nose",),
        ns=(2,),
        ecdf_stats=("logp",),
    )
    pt_en = plaintext_english_string
    pt_idx, wli, _ = Runeglish.encode_english_to_runes(pt_en, direction="rtl")
    mono = api.CipherSpec.substitution(alphabet_size=29)
    rng = np.random.default_rng(12345)
    key_fwd = rng.permutation(29).astype(np.uint8)
    ct_idx = api.encrypt(
        tuple(int(value) for value in pt_idx),
        cipher=mono,
        key=tuple(int(value) for value in key_fwd),
    )
    ct_runes = Runeglish.to_rune(list(ct_idx), wli)
    seeds = make_seeds_from_freq(
        ct_runes.replace(" ", ""),
        n_keys=120,
        swaps_per_key=2 if optimizer == "ga" else 1,
        seed=12345,
        direction="rtl",
    )
    if optimizer == "sa":
        solver = api.SolverSpec.simulated_annealing(
            iterations=1200,
            initial_temperature=0.8,
            minimum_temperature=0.001,
            cooling_rate=0.998,
            automatic_cooling=True,
            reseed_interval=0,
            rescue_drop_absolute=0.02,
            rescue_drop_ratio=0.5,
            local_improvement_on_accept=True,
            plateau_iterations=60,
            plateau_minimum_delta=0.0001,
            target_score=0.555,
            seed=12345,
        )
    else:
        solver = api.SolverSpec.genetic_algorithm(
            population_size=144,
            generations=160,
            target_score=0.56,
            elite_fraction=0.08,
            crossover_fraction=0.85,
            mutation_probability=0.25,
            tournament_size=4,
            plateau_generations=20,
            seed=12345,
        )
    sol = api.run(
        api.RunSpec(
            problem_input=api.RuneIndexInput(indices=ct_idx, word_lengths=wli),
            cipher=api.CipherSpec.substitution(alphabet_size=29),
            key_space=api.KeySpec.permutation(length=29),
            solver=solver,
            scoring=api.ScoringConfig(
                character_lane_enabled=True,
                word_length_lane_enabled=True,
                character_order_weights={2: 0.3},
                word_length_order_weights={2: 0.7},
                objective=api.advanced.ScoringObjective.percentile_log_probability(
                    window_size=10
                ),
            ),
            initial_keys=tuple(tuple(int(value) for value in key) for key in seeds),
            text_direction=api.TextDirection.RIGHT_TO_LEFT,
            compute_device=api.ComputeDevice.CPU,
        )
    )
    recovered_rune = sol.plaintext_text or None
    if not recovered_rune:
        pt_arr = getattr(sol, "plaintext", [])
        recovered_rune = Runeglish.to_rune(pt_arr, wli)
    assert isinstance(recovered_rune, str)
    match_rate = plaintext_match_rate(sol.plaintext, pt_idx)
    assert (
        match_rate >= 0.9
    ), f"{optimizer} tutorial must reach >=90% match (got {match_rate:.3f})"
    latin_text = None
    if hasattr(Runeglish, "runes_to_latin"):
        try:
            latin_text = Runeglish.rune_to_latin(recovered_rune)
        except Exception:
            latin_text = None
    target_text = latin_text if latin_text else recovered_rune
    rx = "[A-Z]{3,}" if latin_text else "[\\u16A0-\\u16FF]{3,}"
    assert re.search(rx, target_text), "Recovered plaintext looks too random"
