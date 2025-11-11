# -*- coding: utf-8 -*-
# File: Tutorial_RouteCipher.py

from __future__ import annotations
from typing import List
from rune_decrypter_prime.api.api import by_name, KeySpec, SolverSpec, run
from rune_decrypter_prime.utils.runeglish import Runeglish

def zebra_snake_encrypt(pt: str, cols: int) -> str:
    """Row-fill, then alternate L→R / R→L reading by row (a.k.a. rail/zigzag rectangle)."""
    rows = (len(pt) + cols - 1) // cols
    table = [list(pt[i*cols : i*cols+cols]) for i in range(rows)]
    out = []
    for r in range(rows):
        row = table[r]
        out.extend(row if r % 2 == 0 else row[::-1])
    return "".join(out)

def main() -> None:
    pt_en = "ALICE WAS BEGINNING TO GET VERY TIRED OF SITTING BY HER SISTER ON THE BANK"
    pt_idx, wli, pt_runes = Runeglish.encode_english_to_runes(pt_en, direction="ltr")
    pt_runes = pt_runes.replace(" ", "")
    wli = None

    C = 7
    ct_runes = zebra_snake_encrypt(pt=pt_runes, cols=C)

    # Cipher by name: “route-snake” (you added the modernized class)
    cipher = by_name.cipher("route-snake", key_len=C)     # key is a column permutation per snake pass
    key_spec = KeySpec.permutation(len=C)
    solve = SolverSpec.ga(population=120, generations=300, cx_frac=0.7, mut_prob=0.3, elite_frac=0.05)

    scorer_params = dict(objective="pct.logp.win10", n_char=2, n_wli=None, win=10, include_char=True, use_word_breaks=False, weights=(1.0,))

    sol = run.solve(
        text=ct_runes, cipher=cipher, key=key_spec, solve=solve,
        device="cpu", scorer="rune", scorer_params=scorer_params,
        wli_data=None, force_no_wli=True
    )

    print("─"*60)
    print("Route (Zebra-Snake) Demo")
    print("PT:", pt_runes[:160])
    print("CT:", ct_runes[:160])
    print("REC:", getattr(sol, "plaintext", "")[:160])
    print("Key(found):", getattr(sol, "key", None))
    print("Score:", getattr(sol, "score", None))
    print("─"*60)

if __name__ == "__main__":
    main()
