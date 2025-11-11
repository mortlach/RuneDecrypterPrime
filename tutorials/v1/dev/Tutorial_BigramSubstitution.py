# ============================================================
# Tutorial_BigramSubstitution.py
# ============================================================
# -*- coding: utf-8 -*-
"""
Tutorial: Bigram substitution cipher with crib-assisted solving.
"""

from __future__ import annotations
import random
from datetime import datetime
from rune_decrypter_prime.api.api import define_map, KeySpec, SolverSpec, run
from rune_decrypter_prime.utils.runeglish import Runeglish

N=29
def bigram_map(p1:int,p2:int,k:int)->tuple[int,int]:
    return ((p1+k)%N,(p2+k)%N)  # toy bigram substitution

def main():
    pt_en="IT WAS THE AGE OF WISDOM IT WAS THE AGE OF FOOLISHNESS"
    pt_idx,wli,pt_runes=Runeglish.encode_english_to_runes(pt_en,direction="rtl")
    key=7
    ct_idx=[]
    for i in range(0,len(pt_idx)-1,2):
        c1,c2=bigram_map(pt_idx[i],pt_idx[i+1],key)
        ct_idx.extend([c1,c2])
    ct_runes=Runeglish.to_rune(ct_idx,wli[:len(ct_idx)])

    cipher=define_map(function=bigram_map,N=N)
    key_spec=KeySpec.scalar(max_val=N)
    solve_spec=SolverSpec.beam(beam_width=N)

    sol=run.solve(text=ct_runes,cipher=cipher,key=key_spec,
                  solve=solve_spec,device="cpu",scorer="rune",
                  scorer_params={"objective":"pct.logp.win10","n_char":2,"n_wli":2,"win":10,
                                 "include_char":True,"use_word_breaks":True,"weights":(0.5,0.5)})

    print("─"*72)
    print("Bigram substitution")
    print("─"*72)
    print("Key(true):",key)
    print("Key(found):",sol.key)
    print("Recovered:",sol.plaintext)
    print("Score:",sol.score)

if __name__=="__main__":
    main()