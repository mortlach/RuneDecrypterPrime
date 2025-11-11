"""
Regression: GA tutorial-friendly path should converge to near-perfect plaintext.

We run a trimmed mono-substitution scenario (~240 characters) to keep the test
fast while still exercising the Stage-2 engine + solver polish. The ciphertext
is deterministic (seeded permutation key), and we provide a small pool of
noisy seeds derived from the ground-truth key. The solver is expected to
recover >= 97.5% of the plaintext tokens with a high language-model score.
"""

from __future__ import annotations

import random
import numpy as np
import pytest

from rune_decrypter_prime.api import run, KeySpec, SolverSpec, Direction, by_name
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext_english_string
from tests.tutorials._utils import build_mono_ciphertext, noisy_permutation_seeds

pytestmark = pytest.mark.tier_a


def test_ga_stage2_mono_runs_to_high_quality():
    # Override python.random for deterministic helper behaviour.
    random_state = random.getstate()
    random.seed(6)

    try:
        direction = Direction.RTL

        plaintext = plaintext_english_string[:240]
        ct_runes, wli, pt_idx, key_true = build_mono_ciphertext(
            plaintext, direction=direction, cipher_seed=12345
        )

        seeds = noisy_permutation_seeds(key_true, count=64, swaps=2, seed=2024)

        solver = SolverSpec.ga(
            pop_size=96,
            generations=120,
            elite_frac=0.08,
            cx_frac=0.85,
            mut_prob=0.25,
            tournament_k=4,
            plateau_gens=25,
            stop_score=0.60,
            log_interval=0,
            progress_pct=1,
            seed=1003,
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
            telemetry_on=False,
            initial_keys=seeds,
        )

        recovered = np.asarray(sol.plaintext_idx, dtype=np.uint8)
        match_rate = float(np.mean(recovered == pt_idx))

        assert match_rate >= 0.975, f"Expected >=97.5% token match, got {match_rate:.4f}"
        assert sol.score >= 0.64, f"Expected score >=0.64 for this scenario, got {sol.score:.4f}"
    finally:
        random.setstate(random_state)
