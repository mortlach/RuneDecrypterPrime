# # # ============================================================
# # # rune_decrypter_prime/optimizers/hybrid_optimizer.py
# # # Hybrid orchestrator: Beam → GA → SA
# # # ============================================================
# -*- coding: utf-8 -*-
"""
Mono Substitution (29 runes) — HYBRID walkthrough (Beam → GA → SA)

What you’ll see
---------------
1) English → runes (single direction).
2) Random key → encrypt → ciphertext.
3) HYBRID optimiser runs: Beam warm-start (if available) → GA explore → SA polish.
4) We deliberately start from **noise** (no seeds) to show robustness.
5) A short, friendly report at the end.

You can tweak GA/SA knobs inside the Hybrid params.
"""
from __future__ import annotations
from typing import Tuple
import numpy as np

from rune_decrypter_prime.ui.api import by_name, cipher_instance, KeySpec, SolveSpec, run
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.tutorials.v1 import pretty
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext_english_string


def preview(s: str, n: int = 120) -> str:
    return s if len(s) <= n else s[:n] + "…"


def _invert_perm(pt_to_ct: np.ndarray) -> np.ndarray:
    inv = np.empty_like(pt_to_ct)
    inv[pt_to_ct] = np.arange(pt_to_ct.size, dtype=np.uint8)
    return inv


def _build_ciphertext(pt_en: str, *, direction: str = "rev", seed: int = 42):
    pt_idx, wli, _ = Runeglish.encode_english_to_runes(pt_en, direction=direction)
    rng = np.random.default_rng(seed)
    key_fwd = rng.permutation(29).astype(np.uint8)            # pt→ct
    ciph = cipher_instance(by_name.cipher("mono"))
    ct_idx = ciph.encrypt(plaintext=np.asarray(pt_idx, np.uint8), key=key_fwd)
    ct_runes = Runeglish.to_rune(ct_idx.tolist(), wli)
    key_inv = _invert_perm(key_fwd)                            # ct→pt
    return ct_runes, wli, key_fwd.tolist(), key_inv.tolist()


def main():
    direction = "rev"

    # 1) English → ciphertext
    pt_en = plaintext_english_string
    ct_runes, wli, _key_fwd, _key_inv = _build_ciphertext(pt_en, direction=direction, seed=42)

    # 2) Hybrid config (Beam → GA → SA), **start from noise**: no initial_keys here.
    #    NOTE: Hybrid expects nested dicts: ga={...}, sa={...}.
    hybrid = SolveSpec.hybrid(
        use_beam=True,
        beam_width=16,          # short beam so GA & SA get time
        ga=dict(                # GA explore (short)
            pop=120,
            gens=60,
            elite_frac=0.06,
            cx_frac=0.80,
            mut_prob=0.30,
            tournament_k=3,
            plateau_gens=12,
            stop_score=0.52,  # early success exit
        ),
        sa=dict(                # SA polish (short)
            iters=6000,
            T0=0.7,
            Tmin=1e-3,
            auto_cooling=True,
            cooling=0.998,
            elitism=True,       # keep best-so-far during SA
            reseed_interval=2000,
            rescue_drop_abs=0.02,
            rescue_drop_ratio=0.5,
            local_improve_on_accept=True,
            stop_score=0.52,  # early success exit
        ),
        # Common
        seed=123,
        verbose=True,
        log_interval=10,
        stop_score=0.52,
    )

    # 3) Run solver (no seeds passed → genuine noise start)
    sol = run.solve(
        text=ct_runes,
        cipher=by_name.cipher("mono"),
        key=KeySpec.permutation(len=29),
        solve=hybrid,
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
        # initial_keys=None,
    )

    # 4) Report
    print("─" * 72)
    print("Mono Substitution — HYBRID (Beam → GA → SA)")
    print("Recovered plaintext:", preview(sol.plaintext))
    print("Score:", round(sol.score, 6))

    pretty.print_run_report(
        title="mono-hybrid",
        cipher="mono",
        key_idx=None,
        ct_idx=Runeglish.rune_to_pos(ct_runes.replace(" ","")),
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

