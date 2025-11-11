# -*- coding: utf-8 -*-
"""
Tutorial: Monoalphabetic substitution (permutation of 29 symbols).
"""

from __future__ import annotations
from typing import List
import random

from rune_decrypter_prime.api.api import by_name, KeySpec, SolverSpec, run
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils import pretty

N = 29

def encrypt_mono(pt_idx: List[int], perm: List[int]) -> List[int]:
    return [perm[x] for x in pt_idx]

def main():
    pt_en = "THE HATTER WERE HAVING TEA AT IT AND THE MARCH HARE"
    pt_idx, wli, pt_runes = Runeglish.encode_english_to_runes(pt_en, direction="rtl")

    perm = list(range(N)); random.Random(11).shuffle(perm)
    ct_idx   = encrypt_mono(pt_idx, perm)
    ct_runes = Runeglish.to_rune(ct_idx, wli)

    cipher = by_name.cipher("mono", alphabet=N)
    key    = KeySpec.permutation(len=N)
    solve  = SolverSpec.ga(population=300, generations=400, elite_frac=0.05, cx_frac=0.7, mut_prob=0.3)

    sol = run.solve(
        text=ct_runes, cipher=cipher, key=key, solve=solve,
        device="cpu", scorer="rune",
        scorer_params=dict(objective="pct.logp.win10", n_char=2, n_wli=2, win=10,
                           include_char=True, use_word_breaks=True, weights=(0.6, 0.4)),
        wli_data=wli
    )

    pretty.print_run_report(
        title="Monoalphabetic Substitution",
        cipher="mono",
        key_idx=perm,
        ct_idx=[Runeglish.rune_to_pos(c) for c in ct_runes],
        ct_rune=ct_runes,
        solution=sol,
        match_ok=None,
        app_version="tutorial-1.0",
        key_len=len(perm),
        wli=wli,
        pt_rune_ref=pt_runes,
        pt_idx_ref=pt_idx,
    )

if __name__ == "__main__":
    main()
