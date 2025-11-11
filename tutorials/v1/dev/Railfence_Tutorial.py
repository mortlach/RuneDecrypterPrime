# -*- coding: utf-8 -*-
"""
Tutorial: Railfence transposition (no word breaks at solve time).
"""

from __future__ import annotations
from rune_decrypter_prime.api.api import by_name, KeySpec, SolverSpec, run
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils import pretty


def encrypt_railfence(pt: str, rails: int) -> str:
    rows = [""] * rails
    r, step = 0, 1
    for ch in pt:
        rows[r] += ch
        if r == 0:   step = 1
        if r == rails-1: step = -1
        r += step
    return "".join(rows)

def main():
    pt_en = "THERE WAS A TABLE SET OUT UNDER A TREE IN FRONT OF THE HOUSE"
    pt_idx, wli, pt_runes = Runeglish.encode_english_to_runes(pt_en, direction="rtl")
    rails = 3
    pt_nosp = pt_runes.replace(" ", "")
    ct_runes = encrypt_railfence(pt_nosp, rails)

    cipher = by_name.cipher("railfence", rails=rails)
    key    = KeySpec.fixed([])  # parameterized by rails; no variable key
    solve  = SolverSpec.beam(beam_width=64)

    sol = run.solve(
        text=ct_runes, cipher=cipher, key=key, solve=solve,
        device="cpu", scorer="rune",
        scorer_params=dict(objective="pct.logp.win10", n_char=2, n_wli=None,
                           win=10, include_char=True, use_word_breaks=False, weights=(1.0,)),
        wli_data=None, force_no_wli=True
    )

    pretty.print_run_report(
        title="Railfence",
        cipher="railfence",
        key_idx=[rails],
        ct_idx=[Runeglish.rune_to_pos(c) for c in ct_runes],
        ct_rune=ct_runes,
        solution=sol,
        match_ok=None,
        app_version="tutorial-1.0",
        key_len=rails,
        wli=None,
        pt_rune_ref=pt_nosp,
        pt_idx_ref=pt_idx,
    )

if __name__ == "__main__":
    main()
