"""
Regression: Hybrid tutorial preset should hit the V1 quality bar on trimmed mono text.
"""

from __future__ import annotations

import pytest

from rune_decrypter_prime.api import run, KeySpec, SolverSpec, Direction, by_name
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext_english_string
from tests.tutorials._utils import (
    build_mono_ciphertext,
    invert_permutation,
    noisy_permutation_seeds,
    plaintext_match_rate,
)

pytestmark = pytest.mark.tier_a


def test_hybrid_stage2_trimmed_mono_regression():
    plaintext = plaintext_english_string[:220]
    ct_runes, wli, pt_idx, key_fwd = build_mono_ciphertext(
        plaintext, direction=Direction.RTL, cipher_seed=12345
    )

    key_inv = invert_permutation(key_fwd)
    seeds = noisy_permutation_seeds(
        key_inv, swaps=1, count=64, seed=2024, include_true=True
    )

    solver = SolverSpec.hybrid(
        use_beam=True,
        beam_width=16,
        rounds=6,
        expand_mode="sample",
        sample_per_parent=24,
        top_parents_factor=0.5,
        progress_pct=1,
        ga=dict(
            pop_size=80,
            generations=20,
            elite_frac=0.10,
            cx_frac=0.85,
            mut_prob=0.25,
            tournament_k=4,
            plateau_rounds=8,
            stop_score=0.64,
            log_interval=0,
        ),
        sa=dict(
            sa_iters=1800,
            sa_init_temp=0.8,
            sa_min_temp=1e-3,
            sa_auto_cooling=True,
            sa_cooling=0.997,
            sa_elitism=True,
            sa_rescue_drop_abs=0.02,
            sa_rescue_drop_ratio=0.5,
            local_improve_on_accept=True,
            stop_score=0.66,
        ),
        seed=2025,
        verbose=False,
        log_interval=0,
        stop_score=0.66,
    )

    sol = run(
        text=ct_runes,
        cipher=by_name.cipher("mono"),
        key=KeySpec.permutation(len=29),
        solver=solver,
        scorer_params=dict(
            char_weights={2: 0.3},
            wli_weights={2: 0.7},
            use_word_breaks=True,
            encoding_dir=Direction.RTL,
        ),
        wli_data=wli,
        encoding_dir=Direction.RTL,
        telemetry_on=False,
        initial_keys=seeds,
    )

    match_rate = plaintext_match_rate(sol.plaintext_idx, pt_idx)
    assert match_rate >= 0.98, f"Expected >=98% match, got {match_rate:.4f}"
    assert sol.score >= 0.62, f"Expected score >=0.62, got {sol.score:.4f}"

