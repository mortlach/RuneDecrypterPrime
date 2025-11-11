# -*- coding: utf-8 -*-
"""
Tutorial: Hill cipher (2×2) over Runeglish mod 29.
"""

from __future__ import annotations
from typing import List
from rune_decrypter_prime.api.api import by_name, KeySpec, SolverSpec, run
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils import pretty

N = 29

def blocks2(pt_idx: List[int]) -> List[List[int]]:
    src = pt_idx if len(pt_idx) % 2 == 0 else (pt_idx + [pt_idx[-1]])
    return [src[i:i+2] for i in range(0, len(src), 2)]

def mul2(A, v):
    return [ (A[0]*v[0] + A[1]*v[1]) % N,
             (A[2]*v[0] + A[3]*v[1]) % N ]

def encrypt_hill2(pt_idx: List[int], A: List[int]) -> List[int]:
    out = []
    for b in blocks2(pt_idx):
        out.extend(mul2(A, b))
    return out

def main():
    pt_en = "A DORMOUSE WAS SITTING BETWEEN THEM FAST ASLEEP"
    pt_idx, wli, pt_runes = Runeglish.encode_english_to_runes(pt_en, direction="rtl")

    # invertible 2×2 over mod 29 (det coprime with 29)
    A = [5, 8,
         7, 3]
    ct_idx = encrypt_hill2(pt_idx, A)
    ct_runes = Runeglish.to_rune(ct_idx, wli)

    cipher = by_name.cipher("hill2", modulus=N)
    key    = KeySpec.matrix2x2(modulus=N)    # your new keyops wrapper
    solve  = SolverSpec.sa(
        sa_iters=8000,
        sa_init_temp=1.0,
        sa_min_temp=0.001,
        sa_cooling=0.997,
    )

    sol = run.solve(
        text=ct_runes, cipher=cipher, key=key, solve=solve,
        device="cpu", scorer="rune",
        scorer_params=dict(objective="pct.logp.win10", n_char=2, n_wli=2, win=10,
                           include_char=True, use_word_breaks=True, weights=(0.5, 0.5)),
        wli_data=wli
    )

    pretty.print_run_report(
        title="Hill 2x2",
        cipher="hill2",
        key_idx=A,
        ct_idx=[Runeglish.rune_to_pos(c) for c in ct_runes],
        ct_rune=ct_runes,
        solution=sol,
        match_ok=None,
        app_version="tutorial-1.0",
        key_len=4,
        wli=wli,
        pt_rune_ref=pt_runes,
        pt_idx_ref=pt_idx,
    )

if __name__ == "__main__":
    main()
