# ============================================================
# Tutorial_Railfence.py
# ============================================================
# -*- coding: utf-8 -*-
"""
Tutorial: Railfence cipher (zig-zag transposition).
"""

from __future__ import annotations
from typing import List, Dict, Any, Sequence
from datetime import datetime
from rune_decrypter_prime.ui.api import by_name, KeySpec, SolveSpec, run
from rune_decrypter_prime.utils.runeglish import Runeglish

def _now(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
def _preview(s: str, n: int = 200) -> str: return s if len(s) <= n else s[:n] + "…"

def encrypt_railfence(pt: str, rails: int) -> str:
    if rails <= 1: return pt
    fence = [[] for _ in range(rails)]
    rail, step = 0, 1
    for ch in pt:
        fence[rail].append(ch)
        rail += step
        if rail == 0 or rail == rails-1:
            step = -step
    return "".join("".join(row) for row in fence)

def main():
    pt_en = "AND THE OTHER TWO WERE USING IT AS A CUSHION RESTING THEIR ELBOWS ON IT"
    pt_idx, wli, pt_runes = Runeglish.encode_english_to_runes(pt_en, direction="rev")
    rails = 3
    ct_runes = encrypt_railfence(pt_runes.replace(" ",""), rails)

    cipher = by_name.cipher("railfence")
    key_spec = KeySpec.scalar(max_val=10)  # rails count
    solve_spec = SolveSpec.beam(beam_width=10)

    sol = run.solve(text=ct_runes, cipher=cipher, key=key_spec,
                    solve=solve_spec, device="cpu", scorer="rune",
                    scorer_params={"objective":"pct.logp.win10","n_char":2,"n_wli":2,"win":10,
                                   "include_char":True,"use_word_breaks":True,"weights":(0.5,0.5)})

    print("─"*72)
    print(f"Railfence | {_now()}")
    print("─"*72)
    print("Rails(true):", rails)
    print("Rails(found):", sol.key)
    print("CT:", _preview(ct_runes))
    print("Recovered:", _preview(sol.plaintext))
    print("Score:", sol.score)

if __name__=="__main__": main()


