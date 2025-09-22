# -*- coding: utf-8 -*-
"""
Mono Substitution (29 runes) — GA tutorial (friendly version)

What this does
--------------
1) Turn a short English text into runes (one direction, kept consistent).
2) Make ciphertext by encrypting with a random key.
3) EITHER start GA from **noise** OR from **seeded keys** (your choice).
4) GA searches for a key that makes the text look like real language.
5) Stop early if we hit a good score (stop_score).

How to use
---------
• Set START_MODE = "seeded" (fast) or "noise" (pure random start).
• You can also pick a run profile: "short", "medium", "long".
• We keep parameter names the same as your GA optimizer.
"""

from __future__ import annotations
from typing import Tuple
import numpy as np

from rune_decrypter_prime.ui.api import by_name, cipher_instance, KeySpec, SolveSpec, run
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.tutorials.v1 import pretty
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext_english_string
from rune_decrypter_prime.utils.seed_utils import make_seeds_from_freq


# -------------------------- knobs you can tweak --------------------------

# Start mode: "seeded" (use freq-based seeds) or "noise" (no seeds)
START_MODE = "seeded"    # "seeded" | "noise"
START_MODE = "noise"    # "seeded" | "noise"

# Consistent direction everywhere ("rev" is typical in your examples)
DIRECTION = "rev"

# Choose a run length
RUN_PROFILE = "medium"   # "short" | "medium" | "long"

# Early stop target (set on SolveSpec, not inside params)
STOP_SCORE = 0.52

# Randomness (for repeatability). Set to None for true entropy.
TUTORIAL_SEED = 12345     # affects seeds & GA rng
CIPHERTEXT_SEED = 42      # makes a reproducible random key for the demo


# -------------------------- small helpers --------------------------

def preview(s: str, n: int = 120) -> str:
    """Shorten long strings so prints stay readable."""
    return s if len(s) <= n else s[:n] + "…"


def _invert_perm(pt_to_ct: np.ndarray) -> np.ndarray:
    """Return the inverse permutation (ct->pt) of a pt->ct key."""
    inv = np.empty_like(pt_to_ct)
    inv[pt_to_ct] = np.arange(pt_to_ct.size, dtype=np.uint8)
    return inv


def _build_ciphertext(pt_en: str, *, direction: str = "rev", seed: int = 42):
    """
    1) English -> rune indices
    2) Random pt->ct permutation
    3) Encrypt using the cipher's API
    4) Return ciphertext as runes (with spaces) and WLI metadata
    """
    pt_idx, wli, _ = Runeglish.encode_english_to_runes(pt_en, direction=direction)
    rng = np.random.default_rng(seed)
    key_fwd = rng.permutation(29).astype(np.uint8)           # pt->ct
    ciph = cipher_instance(by_name.cipher("mono"))
    ct_idx = ciph.encrypt(plaintext=np.asarray(pt_idx, np.uint8), key=key_fwd)
    ct_runes = Runeglish.to_rune(ct_idx.tolist(), wli)
    key_inv = _invert_perm(key_fwd)                          # ct->pt
    return ct_runes, wli, key_fwd.tolist(), key_inv.tolist()


# -------------------------- main tutorial --------------------------

def main():
    # 1) Make a demo ciphertext (so the tutorial is self-contained)
    pt_en = plaintext_english_string
    ct_runes, wli, _key_fwd, _key_inv = _build_ciphertext(
        pt_en, direction=DIRECTION, seed=CIPHERTEXT_SEED
    )

    # 2) (Optional) seeds from ciphertext + LM frequency
    #    We only build them if START_MODE == "seeded".
    seeds = None
    if START_MODE == "seeded":
        # NOTE: seed_utils works over runes (with spaces preserved)
        # and figures out ct->pt guesses internally.
        seeds = make_seeds_from_freq(
            ct_runes,
            n_keys=120,          # number of starting keys
            swaps_per_key=2,     # small random jitter per key
            seed=TUTORIAL_SEED,
            direction=DIRECTION,
        )

    # 3) Pick a run profile (just population/generations)
    if RUN_PROFILE == "short":
        population, generations = 120, 140
    elif RUN_PROFILE == "long":
        population, generations = 240, 450
    else:  # "medium"
        population, generations = 160, 300

    # 4) Build the GA SolveSpec
    #    IMPORTANT: stop_score is set on SolveSpec (top level),
    #    while everything else goes in params=dict(...).
    ga = SolveSpec.ga(
        population=population,
        generations=generations,
        stop_score=STOP_SCORE,   # early success exit
        verbose=True,
        params=dict(
            # If we want a pure-noise start, DON'T pass initial_keys.
            # If we want a seeded start, DO pass initial_keys.
            **({} if seeds is None else {"initial_keys": seeds}),

            elite_frac=0.06,
            cx_frac=0.80,
            mut_prob=0.30,
            tournament_k=3,

            # friendly logging
            log_interval=20,
            # make it repeatable
            seed=TUTORIAL_SEED,
        ),
    )

    # 5) Run the solver
    sol = run.solve(
        text=ct_runes,
        cipher=by_name.cipher("mono"),
        key=KeySpec.permutation(len=29),
        solve=ga,
        device="cpu",
        scorer="rune",
        scorer_params=dict(
            objective="pct.logp.win10",
            char_weights={2: 0.3},
            wli_weights={2: 0.7},
            include_char=True,
            use_word_breaks=True,
            direction=DIRECTION,
        ),
        wli_data=wli,
    )

    # 6) Friendly prints + pretty report
    print("─" * 72)
    mode_label = "GA (seeded start)" if seeds is not None else "GA (noise start)"
    print(f"Mono Substitution — {mode_label}")
    print("Recovered plaintext:", preview(sol.plaintext))
    print("Score:", round(sol.score, 6))

    pretty.print_run_report(
        title="mono-ga-friendly",
        cipher="mono",
        key_idx=None,
        ct_idx=Runeglish.rune_to_pos(ct_runes.replace(" ", "")),
        ct_rune=ct_runes,
        solution=sol,
        match_ok=None,
        app_version="tutorial-1.3",
        key_len=None,
        wli=wli,
        pt_rune_ref=pt_en,
        pt_idx_ref="",
    )


if __name__ == "__main__":
    main()
