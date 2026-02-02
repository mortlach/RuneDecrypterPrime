# -*- coding: utf-8 -*-
# File: Tutorial_Playsquare25.py

from __future__ import annotations
from typing import List, Tuple
from rune_decrypter_prime.api.api import by_name, KeySpec, SolverSpec, run
from rune_decrypter_prime.utils.runeglish import Runeglish

# --- helpers -------------------------------------------------------------

# Reduce 29→25 by merging rarely used tokens.
_reduce = {
    "X": "S",
    "AE": "A",
    "EO": "E",
    "IO": "I",
}
def reduce_token(tok: str) -> str:
    return _reduce.get(tok, tok)

def reduce_runes(runes: str) -> str:
    # map rune→latin token, normalize, map back to rune
    out: List[str] = []
    for ch in runes:
        if ch == " ":
            continue
        latin = Runeglish.rune_to_latin(ch)
        latin = reduce_token(latin)
        out.append(Runeglish.latin_to_rune(latin))
    return "".join(out)

def chunk_pairs(s: str) -> List[Tuple[str,str]]:
    pairs = []
    i = 0
    while i < len(s):
        a = s[i]
        b = s[i+1] if i+1 < len(s) else s[0]  # wrap last (classic demo trick)
        pairs.append((a,b))
        i += 2
    return pairs

# --- demo text -----------------------------------------------------------

PT_EN = (
    "THERE WAS A TABLE SET OUT UNDER A TREE IN FRONT OF THE HOUSE "
    "AND THE MARCH HARE AND THE HATTER WERE HAVING TEA AT IT "
    "A DORMOUSE WAS SITTING BETWEEN THEM FAST ASLEEP"
)

def main() -> None:
    # Encode english → (idx, wli, runes)
    pt_idx, wli, pt_runes = Runeglish.encode_english_to_runes(PT_EN, direction="rtl")

    # Playsquare demo: drop spaces & reduce to 25-alphabet runes
    pt_runes25 = reduce_runes(pt_runes)   # no spaces, 25 symbols
    wli = None

    # Build cipher spec: name “playsquare25” (you already added the class in core)
    # Key = permutation of 25 entries (the square’s linearized order)
    K = 25
    cipher = by_name.cipher("playsquare25", key_len=K)
    key_spec = KeySpec.permutation(len=K)

    # Make a toy key to encrypt (so we have a CT to solve)
    true_key = list(range(K))
    true_key = true_key[7:]+true_key[:7]      # rotate for a demo
    # Encrypt via cipher wrapper’s helper (all in core); or do a simple local impl if you prefer
    # We’ll call the API’s “known key fastpath” by passing key=(known, None) to encrypt:
    ct = run.encrypt(text=pt_runes25, cipher=cipher, key=true_key, wli_data=None).ciphertext

    # Solve with GA+SA hybrid (permutation key)
    solve = SolverSpec.hybrid(
        pop_size=150,
        generations=200,
        sa_iters=2000,
        sa_init_temp=1.0,
        sa_min_temp=0.001,
        sa_cooling=0.999,
        plateau_rounds=20,
        plateau_min_delta=1e-4,
        stop_score=0.55,
    )

    # Scoring without word breaks
    scorer_params = dict(objective="pct.logp.win10", n_char=2, n_wli=None, win=10, include_char=True, use_word_breaks=False, weights=(1.0,))

    sol = run.solve(
        text=ct, cipher=cipher, key=key_spec, solve=solve,
        device="cpu", scorer="rune", scorer_params=scorer_params,
        wli_data=None, force_no_wli=True
    )

    # Pretty summary
    rec_runes = getattr(sol, "plaintext", "")
    key_found = getattr(sol, "key", None)
    score     = getattr(sol, "score", None)

    print("─"*60)
    print("Play-Square (25) Demo")
    print("PT (25-runes):", pt_runes25[:180])
    print("CT (25-runes):", str(ct)[:180] if isinstance(ct, str) else "")
    print("Recovered     :", rec_runes[:180])
    print("Key(found)    :", list(key_found) if key_found is not None else None)
    if isinstance(score, (int, float)):
        print("Score         :", f"{score:.6f}")
    print("─"*60)

if __name__ == "__main__":
    main()
