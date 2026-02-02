# -*- coding: utf-8 -*-
"""
Tutorial: Hill (NxN) — UI-only version.
- Uses only the UI front door (KeySpec/CipherSpec/SolveSpec/run).
- Focus: solving an existing ciphertext with no backend imports.

Why this version?
- Keeps tutorials decoupled from backend key classes.
- Great for reader-facing examples and CI smoke (no key materialization).
- If you also want to *encrypt* locally, use the backend-key variant.
"""

from __future__ import annotations
import numpy as np

from rune_decrypter_prime.api.api import KeySpec, by_name, CipherSpec, SolverSpec, run  # UI only

A = 29  # alphabet size (rune set)

def load_or_make_demo_ciphertext() -> np.ndarray:
    """
    Replace this with real ciphertext indices for a demo.
    For now we synthesize a small length-16 array to exercise the path.
    (This is NOT encryption; just a placeholder demo vector.)
    """
    return np.array([7, 12, 3, 25,  1, 18, 22, 9,  6, 14, 0, 27,  4, 16, 8, 10], dtype=np.uint8)

def main():
    ct = load_or_make_demo_ciphertext()

    # 1) Declare a matrix key space (n x n) for the solver (no backend object here)
    key_plan = KeySpec.matrix(n=2, A=A)  # plan only; solver will search in length n*n

    # 2) Get the unified Hill cipher
    Hill = by_name.cipher("hill")
    cipher = Hill(cfg=type("Cfg", (), {
        "name": "hill", "device": "cpu",
        "text_transposition": "ltr", "key_transposition": "ltr",
        # NOTE: no backend key object here — we’re using a plan and letting the solver search
    })())

    # 3) Solve via UI
    spec  = CipherSpec(name="hill", key=key_plan)
    solve = SolverSpec(
        cipher=spec,
        scorer={"impl": "char", "order": 3},
        solver={
            "name": "ga",
            "generations": 50,
            "pop": 64,
            "seed": 123,
            "plateau_rounds": 10,
            "plateau_min_delta": 1e-4,
            "stop_score": 0.5,
        },
    )
    result = run.solve(ct, solve)

    # 4) Prints
    print("=== Hill (NxN) — UI-only ===")
    print("device:", "cpu")
    print("N (key size):", 2)
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
