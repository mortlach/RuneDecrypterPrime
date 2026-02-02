# -*- coding: utf-8 -*-
"""
Tutorial: Columnar Transposition via permutation keys.

- Ciphertext is formed by writing plaintext into rows, then reading columns in permuted order.
- Key = permutation of column indices.
"""

from __future__ import annotations
from typing import List
from rune_decrypter_prime.api.api import by_name, KeySpec, SolverSpec, run
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils import pretty
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext_english_string

def encrypt_columnar(pt: str, key: List[int]) -> str:
    """Simple columnar transposition (spaces preserved)."""
    N = len(key)
    rows = (len(pt) + N - 1) // N
    table = [list(pt[i * N : i * N + N]) for i in range(rows)]
    ct = ""
    for col in key:
        for r in range(rows):
            if col < len(table[r]):
                ct += table[r][col]
    return ct

def main():
    # English plaintext
    # pt_en = ("THERE WAS A TABLE SET OUT UNDER A TREE IN FRONT OF THE HOUSE "
    #          "AND THE MARCH HARE AND THE HATTER WERE HAVING TEA AT IT")
    pt_en = plaintext_english_string[0:220]

    # Encode to runes, get WLI
    pt_idx, wli, pt_runes = Runeglish.encode_english_to_runes(pt_en, direction="rtl")
    # for this test we do not know word spaces
    wli = None
    pt_runes= pt_runes.replace(" ", "")
    print(f"pt_runes = {pt_runes}")
    # True key
    key = [3, 1, 4, 2,0, 5, 6]

    # Plaintext (Latin preview)
    pt_lat = "".join(" " if c == " " else Runeglish.rune_to_latin(c) for c in pt_runes)

    # Encrypt (remove spaces, no WLI for this cipher)
    ct_runes = encrypt_columnar(pt_runes, key)
    print(f"ct_runes = {ct_runes}")

    # Build cipher + key spec
    cipher = by_name.cipher("columnar", key_len=len(key))
    key_spec = KeySpec.permutation(len=len(key))
    solve_spec = SolverSpec.hybrid(
        pop_size=200,
        generations=100,
        sa_iters=2000,
        sa_init_temp=1.0,
        sa_min_temp=0.001,
        sa_cooling=0.999,
        plateau_rounds=20,
        plateau_min_delta=1e-4,
        stop_score=0.55,
    )
    # solve_spec = SolveSpec.ga(population=50, generations=300, mut_prob=0.4,cx_frac=0.5,elite_frac=0.01)
    # solve_spec_2 = SolveSpec.sa(sa_iters = 200000)

    # Solve 1,
    sol = run.solve(
        text=ct_runes,
        cipher=cipher,
        key=key_spec,
        solve=solve_spec,
        device="cpu",
        scorer="rune",
        # todo add to api and have defaults with scoring with wli and without
        scorer_params={
            "objective": "pct.logp.win10",
            "n_char": 2,
            "n_wli": None,
            "win": 10,
            "include_char": True,
            "use_word_breaks": False,
            "weights": (1),
        },
        wli_data=None,
        force_no_wli=True,
    )
    # Pretty report
    pretty.print_run_report(
        title="Columnar Transposition",
        cipher="columnar",
        key_idx=key,
        ct_idx=[Runeglish.rune_to_pos(ch) for ch in ct_runes],  # indices for preview
        ct_rune=ct_runes,
        solution=sol,
        match_ok=(list(sol.key) == key),
        app_version="tutorial-1.0",
        key_len=len(key),
        wli=wli,
        pt_rune_ref=pt_runes,
        pt_idx_ref=pt_idx,
    )


if __name__ == "__main__":
    main()
