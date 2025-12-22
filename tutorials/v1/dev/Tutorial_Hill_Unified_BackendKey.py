# -*- coding: utf-8 -*-
"""
Tutorial: Hill (NxN) — backend-key version.
- Uses backend MatrixKey to materialize a known invertible key.
- Encrypts a toy plaintext, sanity-checks decrypt, then solves.

Why this version?
- You need an actual key object (e.g., to encrypt locally or unit test).
- You’re okay importing backend keyops.
"""

from __future__ import annotations
import numpy as np

from rune_decrypter_prime.api.api import by_name, CipherSpec, KeySpec, SolverSpec, run  # UI front door
from rune_decrypter_prime.keyops import MatrixKey, MatrixKeyConfig          # backend key object
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext1

A = 29  # alphabet size (rune set)

def make_tiny_plaintext() -> np.ndarray:
    base = np.array(plaintext1, dtype=np.uint8)
    pt = np.tile(base, 12)  # 16*12 = 192 symbols
    return pt

def encrypt_hill(pt_u8: np.ndarray, key_flat_u8: np.ndarray, mod: int = A) -> np.ndarray:
    n = int(np.sqrt(key_flat_u8.size))
    assert n*n == key_flat_u8.size, "Square key required"
    N = int(pt_u8.size)
    pad = (-N) % n
    if pad:
        w = np.empty(N+pad, dtype=np.uint8); w[:N] = pt_u8; w[N:] = 0
    else:
        w = pt_u8
    X = w.reshape(-1, n).astype(np.int64)
    M = key_flat_u8.reshape(n, n).astype(np.int64)
    ct = (X @ M.T) % mod
    return ct.reshape(-1)[:N].astype(np.uint8)

def main():
    rng = np.random.default_rng(12345)
    pt = make_tiny_plaintext()

    # 1) Build an invertible 2x2 key (backend)
    keyop = MatrixKey(MatrixKeyConfig(rows=2, cols=2, mod=A, require_invertible=True))
    key   = keyop.materialize(seed=777)  # deterministic

    # 2) Encrypt with known key
    ct = encrypt_hill(pt, key, mod=A)

    # 3) Build a CipherSpec (UI object) — no direct instantiation
    cipher = CipherSpec._wrapper(name="hill", core_name="hill", N=A)

    # (Optional) sanity: decrypt with known key via cipher’s batch path happens inside run.solve anyway

    # 4) Solve via UI
    # 4) Solve via the UI. For Hill-2×2, use the provided matrix2x2 plan.
    key_plan = KeySpec.matrix(n=2,A=A)
    # make the plaintext longer (you already tiled; great)
    # solve = SolveSpec.ga(
    #     generations=200,
    #     pop=512,
    #     seed=123,
    #     params={"elite": 8, "cx_frac": 0.7, "mut_prob": 0.5}
    # )

    # Replace 'solve = SolveSpec.beam(...)' with:
    solve = SolverSpec.sa(
        sa_iters=30000,  # 20-50k is typical for 2x2
        sa_init_temp=1.5,  # gentle cooling
        sa_min_temp=1e-3,
        sa_cooling=0.96,
        plateau_rounds=3000,  # stop if no improvement for a while
        seed=123,
        sa_elitism=True,
        sa_reseed_interval=3000,
        sa_rescue_drop_abs=0.01,
        sa_rescue_drop_ratio=0.6,
        verbose=True,
    )

    key_plan = KeySpec.matrix(n=2, A=A)

    result = run.solve(
        text=ct,
        cipher=cipher,
        key=key_plan,
        solve=solve,
        device="cpu",
        scorer="rune",
        scorer_params=dict(
            objective="pct.logp.win10",
            char_weights={2: 0.3, 3: 0.7},
            wli_weights={2: 0.7, 3: 0.7},
            include_char=True,
            use_word_breaks=True,
            direction="ltr",
        ),
    )

    # 5) Prints
    print("=== Hill (NxN) — backend-key ===")
    print("device:", "cpu")
    print("N (key size):", 2)
    print("known key (flat):", key.tolist())
    print("pt[:16]:", pt[:16].tolist())
    print("ct[:16]:", ct[:16].tolist())
    # Solution is an object with fields: key (list), plaintext (str), score (float), meta (dict)
    print("solver.best_score:", getattr(result, "score", None))

    best_text = getattr(result, "plaintext", "")
    # If some pipeline returns indices, convert to runes defensively
    if not isinstance(best_text, str):
        try:
            from rune_decrypter_prime.utils.runeglish import Runeglish
            best_text = Runeglish.to_rune(best_text, None)
        except Exception:
            best_text = str(best_text)

    print("solver.best_preview:", best_text[:120])
    print("solver.best_key:", getattr(result, "key", None))
    # Optional: telemetry snapshot
    meta = getattr(result, "meta", {}) or {}
    print("telemetry.device:", meta.get("run_meta", {}).get("device") or meta.get("telemetry", {}).get("device"))
    print("telemetry.score_time:", (meta.get("run_meta", {}) or {}).get("score_time"))


if __name__ == "__main__":
    main()

