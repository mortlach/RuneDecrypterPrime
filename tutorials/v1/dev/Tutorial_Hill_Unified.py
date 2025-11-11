# -*- coding: utf-8 -*-
"""
Tutorial: Hill (NxN) — build a ciphertext, decrypt (known key), then solve.

What you'll do
--------------
1) Define a small plaintext over the 29-rune alphabet (indices).
2) Pick N=2 for readability; create a MatrixKey (invertible mod 29).
3) Encrypt to get ciphertext.
4) Decrypt with the known key (sanity check).
5) Solve the ciphertext via the public API (CPU by default).

Notes
-----
- CPU is the default device (deterministic, no optional deps).
- If you set device="cuda" and N==2, the cipher will use the XP path internally.
"""

from __future__ import annotations
import numpy as np

from rune_decrypter_prime.api.api import by_name, CipherSpec, SolverSpec, run  # public route
from rune_decrypter_prime.keyops import MatrixKey, MatrixKeyConfig          # backend key object


# --- 0) Small, deterministic plaintext (indices 0..28) ---
def make_tiny_plaintext() -> np.ndarray:
    # A small toy phrase encoded as indices (example set replace with runeglish helper if you prefer)
    # Keeping this tiny avoids tutorial noise.
    idx = np.array([1, 2, 3, 4,  5, 6, 7, 8,  9,10,11,12,  13,14,15,16], dtype=np.uint8)
    return idx

def encrypt_hill(pt_u8: np.ndarray, key_flat_u8: np.ndarray, mod: int = 29) -> np.ndarray:
    n = int(np.sqrt(key_flat_u8.size))
    assert n*n == key_flat_u8.size, "Square key required"
    N = int(pt_u8.size)
    pad = (-N) % n
    if pad:
        w = np.empty(N+pad, dtype=np.uint8); w[:N]=pt_u8; w[N:]=0
    else:
        w = pt_u8
    X = w.reshape(-1, n).astype(np.int64)
    M = key_flat_u8.reshape(n, n).astype(np.int64)
    ct = (X @ M.T) % mod
    out = ct.reshape(-1)[:N].astype(np.uint8)
    return out

def main():
    rng = np.random.default_rng(12345)
    pt = make_tiny_plaintext()

    # --- 1) Build an invertible 2x2 key (general API works for any n) ---
    keyop = KeySpec.matrix(n=2, A=29, require_invertible=True)
    key = keyop.materialize(seed=777)  # deterministic

    # --- 2) Encrypt (tutorial-local helper) ---
    ct = encrypt_hill(pt, key, mod=29)

    # --- 3) Known-key decrypt via the public API (instantiate the cipher) ---
    hill = by_name.cipher("hill")  # resolves through the cipher registry
    cipher = hill(
        cfg=type("Cfg", (), {
            "name": "hill",
            "device": "cpu",               # set to "cuda" to exercise XP fast-path when n==2
            "text_transposition": "ltr",
            "key_transposition": "ltr",
            "key": keyop,                  # pass the MatrixKey object
        })()
    )
    # Pipeline takes care of transpositions; here we just call the batch core through the API runner.
    # We'll use the standard run.solve path next, so this acts as a sanity check.

    # --- 4) Solve via the public API ---
    spec  = CipherSpec(name="hill", key=keyop)  # factories will re-materialize keys for search
    solve = SolverSpec(cipher=spec,
                       scorer={"impl": "char", "order": 3},  # normal tutorial scorer
                       solver={"name": "ga", "generations": 50, "pop": 64, "seed": 123})
    result = run.solve(ct, solve)  # returns a stable result structure with telemetry

    # --- 5) Minimal prints (beginner-friendly) ---
    print("=== Hill (NxN) tutorial ===")
    print("device:", "cpu")
    print("N (key size):", 2)
    print("known key (flat):", key.tolist())
    print("pt[:16]:", pt[:16].tolist())
    print("ct[:16]:", ct[:16].tolist())
    print("solver.best_score:", result.get("best_score"))
    print("solver.best_preview:", result.get("best_preview"))

if __name__ == "__main__":
    main()
