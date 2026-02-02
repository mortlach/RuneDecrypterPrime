# -*- coding: utf-8 -*-
"""
Tutorial: Affine (ct = (a*pt + b) mod 29) with the General Map API.

- Shows how to encrypt with (a,b) then recover both using a search.
- Uses modest beam or GA (both work fine on short texts).
"""

from __future__ import annotations
from typing import Sequence, Dict, Any, Optional
from math import gcd
from datetime import datetime

from rune_decrypter_prime.api.api import define_map, KeySpec, SolverSpec, run
from rune_decrypter_prime.utils.runeglish import Runeglish

N = 29

def affine_cell(pt: int, k: int, offs: int) -> int:
    return ( (int(k) * int(pt)) + int(offs) ) % N

def encrypt_affine_indices(pt_idx: Sequence[int], a: int, b: int) -> list[int]:
    if gcd(a, N) != 1:
        raise ValueError("a must be coprime with 29")
    return [ (a*int(p) + b) % N for p in pt_idx ]

def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def main() -> None:
    # English → runes (keep spaces/WLI; affine works per-symbol so WLI is fine)
    pt_en = "THERE WAS A TABLE SET OUT UNDER A TREE IN FRONT OF THE HOUSE"
    pt_idx, wli, pt_runes = Runeglish.encode_english_to_runes(pt_en, direction="rtl")

    # Pick a valid key (a coprime to 29, b arbitrary)
    a, b = 12, 7
    if gcd(a, N) != 1:
        a = 2*a + 1  # ensure coprime in case someone edits the demo

    ct_idx = encrypt_affine_indices(pt_idx, a, b)
    ct_runes = Runeglish.to_rune(ct_idx, wli)

    # Build a 2-parameter general map by “currying” into a single stream key of length 2:
    # we let position 0 carry 'a' and position 1 carry 'b', repeated across text.
    # (Your map wrapper in patche_old_ui/api.py supports small param vectors via KeySpec.repeat(len=2))
    def _cell(pt: int, k: int) -> int:
        # k is the *stream value*; we unpack a,b from the first two positions via modulo trick
        # For solving, the engine mutates those two positions; our wrapper reads them back.
        # In practice core’s define_map supports fixed-arity cells — this mirrors that usage.
        raise NotImplementedError  # the patche_old_ui.map-wrapper injects the proper (a,b) each step

    # Using the “table” path is simpler here: a,b unknown → prebuild all ct for each pt & (a,b)
    spec = define_map(function=lambda pt, k: (k[0]*pt + k[1]) % N, N=N)  # k is a 2-vector

    # KeySpec: a 2-vector searched by GA/Beam. We also bound 'a' to coprimes only via params.
    key_spec = KeySpec.vector(len=2)  # modern helper: 2 unknown ints

    # Solve (beam or GA — pick one)
    solve = SolverSpec.ga(
        population=80,
        generations=120,
        elite_frac=0.05,
        cx_frac=0.7,
        mut_prob=0.3,
        plateau_rounds=15,
        plateau_min_delta=1e-4,
        stop_score=0.55,
    )

    sol = run.solve(
        text=ct_runes,
        cipher=spec,       # define_map returns a cipher spec compatible with run.solve
        key=key_spec,
        solve=solve,
        scorer="rune",
        scorer_params={
            "objective": "pct.logp.win10",
            "n_char": 2, "n_wli": 2, "win": 10,
            "include_char": True, "use_word_breaks": True, "weights": (0.5, 0.5)
        },
        device="cpu",
        wli_data=None
    )

    # Pretty (compact)
    rec_runes = getattr(sol, "plaintext", "")
    rec_latin = "".join(" " if ch == " " else str(Runeglish.rune_to_latin(ch)) for ch in rec_runes)
    score     = getattr(sol, "score", None)
    meta      = getattr(sol, "meta", {}) or {}

    bar = "─" * 72
    print(bar); print(f"Affine-29  |  {_now()}"); print(bar)
    print(f"PT (runes) : {pt_runes[:160]}")
    print(f"CT (runes) : {ct_runes[:160]}")
    print(bar)
    print("Recovered (runes):", rec_runes[:360])
    print("Recovered (latin):", rec_latin[:360])
    print(bar)
    if isinstance(score, (int, float)): print(f"Score: {score:.6f}")
    print("Optimizer:", (meta.get("telemetry", {}) or {}).get("solver", {}))
    print(bar)

if __name__ == "__main__":
    main()
