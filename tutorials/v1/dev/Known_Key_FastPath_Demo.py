# -*- coding: utf-8 -*-
"""
Tutorial: Known-key decrypt harness (demonstrates “fast path”).
"""

from __future__ import annotations
from rune_decrypter_prime.api.api import by_name, KeySpec, SolverSpec, run
from rune_decrypter_prime.utils.runeglish import Runeglish

def main():
    pt_en = "TABLE SET OUT UNDER A TREE"
    pt_idx, wli, pt_runes = Runeglish.encode_english_to_runes(pt_en, direction="rtl")

    # simple vigenere add with key [3,1,4]
    key_nums = [3,1,4]
    ct_idx = [ (p + key_nums[i % len(key_nums)]) % 29 for i, p in enumerate(pt_idx) ]
    ct_runes = Runeglish.to_rune(ct_idx, wli)

    cipher   = by_name.cipher("vigenere_add", alphabet=29)
    key_spec = KeySpec.fixed(key_nums)          # known key
    solve    = SolverSpec.none()                 # no search

    sol = run.solve(text=ct_runes, cipher=cipher, key=key_spec, solve=solve,
                    device="cpu", scorer="rune", scorer_params=None, wli_data=wli)

    print("Recovered runes:", sol.plaintext)

if __name__ == "__main__":
    main()
