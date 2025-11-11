# -*- coding: utf-8 -*-
"""
Tutorial: Bigram (digraph) substitution with an optional plaintext crib.
- Alphabet: 29-runeglish; pairs encoded as base-29 bigrams: code = 29*a + b.
- Key: a permutation over 29*29 positions.
- Crib: optional rune/latin phrase to seed the solver (soft bias).
"""

from __future__ import annotations
from typing import List, Tuple, Optional
import random

from rune_decrypter_prime.api.api import by_name, KeySpec, SolverSpec, run
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils import pretty

N = 29
NBIG = N * N

def pair_idx(a: int, b: int) -> int:
    return a * N + b

def unpair_idx(x: int) -> Tuple[int, int]:
    return divmod(int(x), N)

def text_to_bigrams(idx: List[int]) -> List[int]:
    # pad odd length with last symbol to keep pairs well-formed
    src = idx if (len(idx) % 2 == 0) else (idx + [idx[-1]])
    return [pair_idx(src[i], src[i+1]) for i in range(0, len(src), 2)]

def bigrams_to_text(bi: List[int]) -> List[int]:
    out: List[int] = []
    for x in bi:
        a, b = unpair_idx(x)
        out.extend([a, b])
    return out

def encrypt_bigram_sub(pt_idx: List[int], perm: List[int]) -> List[int]:
    pairs = text_to_bigrams(pt_idx)
    subd  = [perm[p] for p in pairs]
    return bigrams_to_text(subd)

def main(crib: Optional[str] = "HARE"):
    # 1) demo plaintext
    pt_en = (
        "THERE WAS A TABLE SET OUT UNDER A TREE IN FRONT OF THE HOUSE "
        "AND THE MARCH HARE AND THE HATTER WERE HAVING TEA AT IT"
    )
    pt_idx, wli, pt_runes = Runeglish.encode_english_to_runes(pt_en, direction="rtl")

    # 2) build a random bigram substitution key (permutation over 29*29)
    perm = list(range(NBIG)); random.Random(7).shuffle(perm)

    # 3) encrypt
    ct_idx = encrypt_bigram_sub(pt_idx, perm)
    ct_runes = Runeglish.to_rune(ct_idx, wli)

    # 4) cipher + key + solve spec
    #    (Your bigram-sub class exposes kind="bigram_sub"; key=PermutationOps(N*N))
    cipher   = by_name.cipher("bigram_sub", key_len=NBIG)
    key_spec = KeySpec.permutation(len=NBIG)
    solve    = SolverSpec.hybrid(pop_size=250, generations=150,
                                 sa_iters=3000, sa_init_temp=1.0, sa_min_temp=0.001, sa_cooling=0.999)

    # 5) scorer config (use word-breaks; bigrams benefit a lot)
    scorer_params = dict(
        objective="pct.logp.win10",
        n_char=2, n_wli=2, win=10,
        include_char=True, use_word_breaks=True, weights=(0.5, 0.5),
    )

    # 6) optional crib (soft bias at scoring layer)
    #    Pass as UI arg; your core can read this from run_cfg.scorer_params["crib"]
    if crib:
        # allow latin or runes; convert to rune string (no spaces)
        if any(ch.isalpha() for ch in crib):
            c_idx, c_wli, c_runes = Runeglish.encode_english_to_runes(crib, direction="rtl")
            scorer_params["crib"] = c_runes.replace(" ", "")
        else:
            scorer_params["crib"] = crib.replace(" ", "")

    # 7) solve
    sol = run.solve(
        text=ct_runes, cipher=cipher, key=key_spec, solve=solve,
        device="cpu", scorer="rune", scorer_params=scorer_params, wli_data=wli
    )

    # 8) pretty
    pretty.print_run_report(
        title="Bigram Substitution",
        cipher="bigram_sub",
        key_idx=list(range(NBIG)),  # (we don’t reveal the perm here; just show length)
        ct_idx=[Runeglish.rune_to_pos(ch) for ch in ct_runes],
        ct_rune=ct_runes,
        solution=sol,
        match_ok=None,
        app_version="tutorial-1.0",
        key_len=NBIG,
        wli=wli,
        pt_rune_ref=pt_runes,
        pt_idx_ref=pt_idx,
    )

if __name__ == "__main__":
    main()
