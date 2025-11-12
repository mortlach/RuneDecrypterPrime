# # # ============================================================
# # # rune_decrypter_prime/solver/hybrid_solver.py
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
import sys
from pathlib import Path

# Ensure repo root on sys.path before importing project modules
_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from rune_decrypter_prime.api import run, KeySpec, SolverSpec, Direction, by_name, cipher_instance
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils.pretty import print_run_report
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext_english_string
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

TUTORIAL_SEED = 12345
CIPHERTEXT_SEED = 12345



def preview(s: str, n: int = 120) -> str:
    return s if len(s) <= n else s[:n] + "…"

def _invert_perm(pt_to_ct: np.ndarray) -> np.ndarray:
    inv = np.empty_like(pt_to_ct)
    inv[pt_to_ct] = np.arange(pt_to_ct.size, dtype=np.uint8)
    return inv


def _build_ciphertext(pt_en: str, *, encoding_dir: Direction = Direction.RTL, seed: int = 42):
    pt_idx, wli, _ = Runeglish.encode_english_to_runes(pt_en, direction=encoding_dir.value)
    rng = np.random.default_rng(seed)
    key_fwd = rng.permutation(29).astype(np.uint8)            # pt→ct
    ciph = cipher_instance(by_name.cipher("mono"))
    ct_idx = ciph.encrypt(plaintext=np.asarray(pt_idx, np.uint8), key=key_fwd)
    ct_runes = Runeglish.to_rune(ct_idx.tolist(), wli)
    key_inv = _invert_perm(key_fwd)                            # ct→pt
    return ct_runes, wli, key_fwd.tolist(), key_inv.tolist(), pt_idx


def main():
    # english words encoded right-to-left or left-to-right
    encoding_dir = Direction.RTL

    # 1) English → ciphertext
    pt_en = plaintext_english_string
    ct_runes, wli, _key_fwd, _key_inv, pt_idx = _build_ciphertext(
        pt_en, encoding_dir=encoding_dir, seed=CIPHERTEXT_SEED
    )

    # 2) Hybrid Solver config (hybrid is a combination of Beam → GA → SA solvers), for demo use random noise starting keys
    hybrid = SolverSpec.hybrid(
        use_beam=True,
        beam_width=12,
        rounds=6,
        expand_mode="sample",
        sample_per_parent=16,
        top_parents_factor=0.5,
        progress_pct=2,
        print_progress=True,

        ga=dict(
            pop_size=60,
            generations=15,
            elite_frac=0.08,
            cx_frac=0.85,
            mut_prob=0.35,
            tournament_k=3,
            plateau_gens=8,
            stop_score=0.150,
            auto_cooling=False,
            print_progress=True,
        ),
        sa=dict(
            sa_iters=1500,
            sa_init_temp=0.8,
            sa_min_temp=1e-3,
            sa_auto_cooling=True,
            sa_cooling=0.996,
            sa_elitism=True,
            sa_reseed_interval=2000,
            sa_rescue_drop_abs=0.02,
            sa_rescue_drop_ratio=0.5,
            local_improve_on_accept=False,
            stop_score=0.150,
            print_progress=True,
        ),


        seed=TUTORIAL_SEED,
        verbose=True,
        log_interval=10,
        stop_score=0.150,
    )

    # 3) Run solver
    sol = run(
        text=ct_runes,
        cipher=by_name.cipher("mono"),
        key=KeySpec.permutation(len=29),
        solver=hybrid,
        device="cpu",
        scorer_params=dict(
            char_weights={2: 0.3},
            wli_weights={2: 0.7},
            include_char=True,
            use_word_breaks=True,
            encoding_dir=encoding_dir,
        ),
        wli_data=wli,
        encoding_dir=encoding_dir,
        telemetry_on=True,
    )

    # 4) Report
    print("-" * 72)
    print("Mono Substitution — HYBRID (Beam → GA → SA)")
    recovered = getattr(sol, "plaintext_rune", "") or getattr(sol, "plaintext_str", "")
    print("Recovered plaintext:", preview(str(recovered)))
    print("Score:", round(sol.score, 6))
    # Keep reference for pretty printer (auto match ratio)
    pt_ref = Runeglish.to_rune(list(pt_idx), wli)

    print_run_report(
        title="mono-hybrid",
        cipher="mono",
        solution=sol,
        match_ok=None,
        app_version="tutorial-1.3",
        pt_rune_ref=pt_ref,
        pt_idx_ref=pt_idx,
    )

if __name__ == "__main__":
    main()
