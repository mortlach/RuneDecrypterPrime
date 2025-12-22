"""
Regression: SA tutorial preset must converge to near-perfect plaintext.

We encrypt a short mono substitution sample, seed the SA solver with noisy
variants of the true decrypt key, then assert that Stage-2 recovers >=96%
of the plaintext tokens with a strong score.
"""

from __future__ import annotations

import numpy as np
import pytest

from rune_decrypter_prime.api import run, KeySpec, SolverSpec, Direction, by_name
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext_english_string
from tests.tutorials._utils import (
    build_mono_ciphertext,
    invert_permutation,
    noisy_permutation_seeds,
)

pytestmark = pytest.mark.tier_a


def test_sa_stage2_mono_regression():
    direction = Direction.LTR
    plaintext = plaintext_english_string[:200]
    ct_runes, wli, pt_idx, key_fwd = build_mono_ciphertext(
        plaintext, direction=direction, cipher_seed=12345
    )

    key_inv = invert_permutation(key_fwd)
    seeds = noisy_permutation_seeds(key_inv, swaps=2, count=32, seed=2024, include_true=True)

    solver = SolverSpec.sa(
        sa_iters=400,
        sa_init_temp=0.8,
        sa_min_temp=1e-3,
        sa_cooling=0.998,
        sa_auto_cooling=True,
        sa_elitism=True,
        sa_reseed_interval=0,
        sa_rescue_drop_abs=0.02,
        sa_rescue_drop_ratio=0.5,
        local_improve_on_accept=True,
        log_interval=0,
        plateau_rounds=30,
        plateau_min_delta=1e-4,
        stop_score=0.65,
        progress_pct=1,
        seed=321,
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
            encoding_dir=direction,
        ),
        wli_data=wli,
        encoding_dir=direction,
        initial_keys=seeds,
        telemetry_on=False,
    )

    recovered = np.asarray(sol.plaintext_idx, dtype=np.uint8)
    match_rate = float(np.mean(recovered == pt_idx))

    assert match_rate >= 0.96, f"Expected >=96% token match, got {match_rate:.4f}"
    assert sol.score >= 0.68, f"Expected score >=0.68, got {sol.score:.4f}"

