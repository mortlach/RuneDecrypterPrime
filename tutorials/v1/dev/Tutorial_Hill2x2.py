# ============================================================
# Tutorial_Hill2x2.py
# ============================================================
# -*- coding: utf-8 -*-
"""
Tutorial: Hill cipher with 2x2 key matrix mod 29.
"""

from __future__ import annotations
from typing import List
from datetime import datetime
from rune_decrypter_prime.api.api import define_map, KeySpec, SolverSpec, run
from rune_decrypter_prime.utils.runeglish import Runeglish

N=29
def hill2x2_map(p1:int,p2:int,a:int,b:int,c:int,d:int)->tuple[int,int]:
    return ((a*p1+b*p2)%N, (c*p1+d*p2)%N)

def main():
    pt_en = "A DORMOUSE WAS SITTING BETWEEN THEM FAST ASLEEP"
    pt_idx, wli, pt_runes = Runeglish.encode_english_to_runes(pt_en, direction="rtl")
    key = [3,3,2,5]  # 2x2 matrix
    ct_idx=[]
    for i in range(0,len(pt_idx)-1,2):
        p1,p2=pt_idx[i],pt_idx[i+1]
        c1,c2=hill2x2_map(p1,p2,*key)
        ct_idx.extend([c1,c2])
    ct_runes = Runeglish.to_rune(ct_idx,wli[:len(ct_idx)])

    cipher = define_map(function=hill2x2_map,N=N)
    key_spec = KeySpec.matrix2x2(N)
    solve_spec = SolverSpec.ga(population=100, generations=500)

    sol = run.solve(text=ct_runes,cipher=cipher,key=key_spec,solve=solve_spec,
                    device="cpu",scorer="rune",
                    scorer_params={"objective":"pct.logp.win10","n_char":2,"n_wli":2,"win":10,
                                   "include_char":True,"use_word_breaks":True,"weights":(0.5,0.5)})

    print("─"*72)
    print("Hill 2x2 cipher")
    print("─"*72)
    print("Key(true):",key)
    print("Key(found):",sol.key)
    print("Recovered:",sol.plaintext)
    print("Score:",sol.score)

if __name__=="__main__":
    main()