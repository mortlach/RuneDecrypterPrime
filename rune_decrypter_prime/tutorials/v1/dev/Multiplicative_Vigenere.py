# -*- coding: utf-8 -*-
"""
Tutorial: Multiplicative Vigenère (ct = pt * k mod 29), with periodic key.
"""

from __future__ import annotations
from typing import List, Sequence
from rune_decrypter_prime.ui.api import define_map, KeySpec, SolveSpec, run
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.tutorials.v1 import pretty

N = 29
def mult_vigenere(pt: int, k: int) -> int:
    return (int(pt) * int(k)) % N

def repeat_to_length(key: Sequence[int], L: int) -> List[int]:
    return [int(key[i % len(key)]) for i in range(L)]

def main():
    pt_en = "USING IT AS A CUSHION RESTING THEIR ELBOWS ON IT"
    pt_idx, wli, pt_runes = Runeglish.encode_english_to_runes(pt_en, direction="rev")

    cipher = define_map(function=mult_vigenere, N=N)
    key_nums = [3, 7, 5]
    stream   = repeat_to_length(key_nums, len(pt_idx))
    ct_idx   = [(p * k) % N for p, k in zip(pt_idx, stream)]
    ct_runes = Runeglish.to_rune(ct_idx, wli)

    key_spec = KeySpec.repeat(len=len(key_nums))
    solve    = SolveSpec.beam(beam_width=48)

    sol = run.solve(
        text=ct_runes, cipher=cipher, key=key_spec, solve=solve,
        device="cpu", scorer="rune",
        scorer_params=dict(objective="pct.logp.win10", n_char=2, n_wli=2, win=10,
                           include_char=True, use_word_breaks=True, weights=(0.5, 0.5)),
        wli_data=wli
    )

    pretty.print_run_report(
        title="Multiplicative Vigenère",
        cipher=cipher.kind,
        key_idx=key_nums,
        ct_idx=[Runeglish.rune_to_pos(c) for c in ct_runes],
        ct_rune=ct_runes,
        solution=sol,
        match_ok=None,
        app_version="tutorial-1.0",
        key_len=len(key_nums),
        wli=wli,
        pt_rune_ref=pt_runes,
        pt_idx_ref=pt_idx,
    )

if __name__ == "__main__":
    main()
