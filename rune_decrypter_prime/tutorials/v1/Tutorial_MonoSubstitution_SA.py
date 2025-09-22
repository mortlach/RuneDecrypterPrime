# # -*- coding: utf-8 -*-
# """
# Tutorial: Monoalphabetic substitution (29-rune alphabet) with SA
# ----------------------------------------------------------------
# -*- coding: utf-8 -*-
"""
Mono Substitution (29 runes) — SA walkthrough

What you’ll see
---------------
1) English → runes (one direction, kept consistent).
2) Random key → encrypt → ciphertext.
3) Simple frequency-based seed guesses (optional but helpful).
4) Simulated Annealing (SA) recovers readable plaintext.
5) A short report at the end.

You can tweak the SA knobs below.
"""
from __future__ import annotations
from typing import Tuple
import numpy as np

from rune_decrypter_prime.ui.api import by_name, cipher_instance, KeySpec, SolveSpec, run
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.tutorials.v1 import pretty
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext_english_string
from rune_decrypter_prime.utils.seed_utils import make_seeds_from_freq


def preview(s: str, n: int = 120) -> str:
    return s if len(s) <= n else s[:n] + "…"


def _invert_perm(pt_to_ct: np.ndarray) -> np.ndarray:
    inv = np.empty_like(pt_to_ct)
    inv[pt_to_ct] = np.arange(pt_to_ct.size, dtype=np.uint8)
    return inv


def _build_ciphertext(pt_en: str, *, direction: str = "rev", seed: int = 42):
    pt_idx, wli, _ = Runeglish.encode_english_to_runes(pt_en, direction=direction)
    rng = np.random.default_rng(seed)
    key_fwd = rng.permutation(29).astype(np.uint8)
    ciph = cipher_instance(by_name.cipher("mono"))
    ct_idx = ciph.encrypt(plaintext=np.asarray(pt_idx, np.uint8), key=key_fwd)
    ct_runes = Runeglish.to_rune(ct_idx.tolist(), wli)
    key_inv = _invert_perm(key_fwd)
    return ct_runes, wli, key_fwd.tolist(), key_inv.tolist()


def main():
    direction = "rev"

    # 1) English → ciphertext
    pt_en = plaintext_english_string
    ct_runes, wli, _key_fwd, _key_inv = _build_ciphertext(pt_en, direction=direction, seed=42)

    # 2) Simple seeds from ciphertext (comment out to start from pure noise)
    seeds = make_seeds_from_freq(ct_runes.replace(" ",""), n_keys=120, swaps_per_key=2, seed=12345, direction=direction)

      # 3) SA config (kept readable) — pass kwargs directly
    sa = SolveSpec.sa(
           sa_iters = 30000,
        sa_init_temp = 0.8,
        sa_min_temp = 1e-3,
        sa_cooling = 0.998,
        sa_auto_cooling = True,
        sa_elitism = True,
        sa_reseed_interval = 5000,
        sa_rescue_drop_abs = 0.02,
        sa_rescue_drop_ratio = 0.5,
        local_improve_on_accept = True,
        log_interval = 500,
        verbose = True,
        seed = 123,
        stop_score = 0.52,
        patience=7000,
        tol=1e-6,
    )

    # 4) Run solver
    sol = run.solve(
        text=ct_runes,
        cipher=by_name.cipher("mono"),
        key=KeySpec.permutation(len=29),
        solve=sa,
        device="cpu",
        scorer="rune",
        scorer_params=dict(
            objective="pct.logp.win10",
            char_weights={2: 0.3},
            wli_weights={2: 0.7},
            include_char=True,
            use_word_breaks=True,
            direction=direction,
        ),
        wli_data=wli,
        initial_keys=seeds
    )

    # 5) Report
    print("─" * 72)
    print("Mono Substitution — SA")
    print("Recovered plaintext:", preview(sol.plaintext))
    print("Score:", round(sol.score, 6))

    pretty.print_run_report(
        title="mono-sa",
        cipher="mono",
        key_idx=None,
        ct_idx=Runeglish.rune_to_pos(ct_runes.replace(" ","")),
        ct_rune=ct_runes,
        solution=sol,
        match_ok=None,
        app_version="tutorial-1.2",
        key_len=None,
        wli=wli,
        pt_rune_ref=pt_en,
        pt_idx_ref="",
    )

if __name__ == "__main__":
    main()
