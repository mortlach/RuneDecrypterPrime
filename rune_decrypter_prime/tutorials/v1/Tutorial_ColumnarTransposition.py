# -*- coding: utf-8 -*-
"""
Tutorial: Columnar Transposition (permutation key, no WLI)

- Classic row-fill / column-read transposition.
- Ciphertext has NO word-break info; the solver must work without WLI.
- Key is a permutation of column indices indicating READ ORDER of columns.
"""

from __future__ import annotations
from typing import List
from rune_decrypter_prime.ui.api import by_name, KeySpec, SolveSpec, run
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.tutorials.v1 import pretty
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext_english_string

def encrypt_columnar(pt: str, key: List[int]) -> str:
    """Row-fill, then read columns in the order given by 'key' (no spaces)."""
    K = len(key)
    rows = (len(pt) + K - 1) // K
    # build the row table
    table = [list(pt[i * K : i * K + K]) for i in range(rows)]
    # read columns in key order
    out_chars: List[str] = []
    for col in key:
        for r in range(rows):
            if col < len(table[r]):
                out_chars.append(table[r][col])
    return "".join(out_chars)

def main():
    # English plaintext → runes (then strip spaces for columnar)
    pt_en = plaintext_english_string
    pt_idx, wli_pt, pt_runes = Runeglish.encode_english_to_runes(pt_en, direction="rev")
    pt_runes_nosp = pt_runes.replace(" ", "")
    wli = None  # IMPORTANT: no WLI for this cipher

    print(f"pt_runes = {pt_runes_nosp}")

    # True key (read-order permutation)
    key_true = [3,  1, 4, 2, 0, 5]

    # Encrypt (no spaces)
    ct_runes = encrypt_columnar(pt_runes_nosp, key_true)
    print(f"ct_runes = {ct_runes}")

    # Build cipher + key spec
    cipher   = by_name.cipher("columnar", key_len=len(key_true))
    key_spec = KeySpec.permutation(len=len(key_true))

    # A robust hybrid budget for demos (GA explore + SA polish)
    solve_spec = SolveSpec.hybrid(
        beam_width=None,                  # no beam stage for pure permutation here
        pop_size=200, generations=120,    # GA
        elite_frac=0.05, cx_frac=0.7, mut_prob=0.35,
        sa_iters=2500, sa_init_temp=1.0, sa_min_temp=0.001, sa_cooling=0.998,stop_score=0.55,patience=7000
    )

    # Scorer tuned for NO word-breaks
    scorer_params = {
        "objective": "pct.logp.win10",
        "n_char": 2,
        "n_wli": None,
        "win": 10,
        "include_char": True,
        "use_word_breaks": False,
        "weights": (1.0,),
    }

    # Solve. Pass the rune string with no spaces; force the UI to run WITHOUT WLI.
    sol = run.solve(
        text=ct_runes,
        cipher=cipher,
        key=key_spec,
        solve=solve_spec,
        device="cpu",
        scorer="rune",
        scorer_params=scorer_params,
        logging=None,
        wli_data=None,
        force_no_wli=True,    # <- your UI flag: do not infer WLI even if spaces existed
    )

    # Pretty report (uses your Runeglish-aware pretty printer)
    pretty.print_run_report(
        title="Columnar Transposition",
        cipher="columnar",
        key_idx=key_true,
        ct_idx=[Runeglish.rune_to_pos(ch) for ch in ct_runes],
        ct_rune=ct_runes,
        solution=sol,
        match_ok=(list(getattr(sol, "key", [])) == key_true),
        app_version="tutorial-1.0",
        key_len=len(key_true),
        wli=wli,
        pt_rune_ref=pt_runes_nosp,
        pt_idx_ref=pt_idx,
    )

if __name__ == "__main__":
    main()
