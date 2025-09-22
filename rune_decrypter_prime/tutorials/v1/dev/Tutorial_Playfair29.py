# -*- coding: utf-8 -*-
"""
Tutorial: Playfair-29 (Runeglish) — solve with a permutation key + optional crib.

What this shows:
1) Build a 29-symbol square from a keyword (for encryption demo only).
2) Encrypt a normal paragraph (Runeglish, spaces removed for Playfair).
3) Solve by searching a permutation of 29 symbols (hybrid GA+SA).
4) (Optional) Provide a crib to help the optimizer lock on sooner.
"""

from __future__ import annotations
from typing import List, Sequence, Dict, Any, Optional
from datetime import datetime

from rune_decrypter_prime.ui.api import by_name, KeySpec, SolveSpec, run
from rune_decrypter_prime.utils.runeglish import Runeglish

# ---------- helpers (list-only, no numpy) ----------
def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _preview(s: str, n: int = 160) -> str:
    return s if len(s) <= n else (s[:n] + "…")

def print_report(
    *,
    title: str,
    key_found: Optional[Sequence[int]],
    score: Optional[float],
    pt_runes_head: str,
    ct_runes_head: str,
    rec_runes_head: str,
    rec_latin_head: str,
    meta: Dict[str, Any],
) -> None:
    bar = "─" * 72
    print(bar); print(f"{title}  |  {_now()}"); print(bar)
    if key_found is not None:
        print(f"Key(found) : (permutation of 29)  len={len(key_found)}")
    print(f"PT runes   : {_preview(pt_runes_head)}")
    print(f"CT runes   : {_preview(ct_runes_head)}")
    print(bar)
    print("Recovered plaintext (runes):")
    print(_preview(rec_runes_head, 360))
    print("Recovered plaintext (latin):")
    print(_preview(rec_latin_head, 360))
    print(bar)
    if isinstance(score, (int, float)):
        print(f"Score      : {score:.6f}")
    tel = (meta or {}).get("telemetry", {})
    print("Optimizer  :", (tel.get("optimizer") or {}))
    print("Timings    :", {"elapsed_sec": tel.get("optimizer", {}).get("elapsed_sec")})
    print(bar)
    print("Note: Higher scores ≈ more language-like (n-gram log-probabilities).")
    print(bar)

# ---------- tiny Playfair encrypt (29-runeglish square) ----------
def make_square_from_keyword(keyword_runes: str) -> List[str]:
    """Return a 29-length symbol order (unique) in row-major for the square."""
    seen = set()
    order: List[str] = []
    # 1) keyword characters (runes) first
    for ch in keyword_runes:
        if ch != " " and ch not in seen:
            seen.add(ch); order.append(ch)
    # 2) remaining runes in canonical Runeglish order
    for r in Runeglish.runes:
        if r not in seen:
            seen.add(r); order.append(r)
    return order  # length 29

def playfair29_encrypt(pt_runes: str, order: Sequence[str]) -> str:
    """Standard Playfair digram rules, 29×29 square, spaces removed."""
    # row/col maps
    pos: Dict[str, int] = {r: i for i, r in enumerate(order)}
    # row = i//29, col = i%29
    def enc_pair(a: str, b: str) -> str:
        i, j = pos[a], pos[b]
        ra, ca = divmod(i, 29)
        rb, cb = divmod(j, 29)
        if ra == rb:  # same row → shift right
            return order[ra*29 + ((ca+1) % 29)] + order[rb*29 + ((cb+1) % 29)]
        if ca == cb:  # same col → shift down
            return order[((ra+1) % 29)*29 + ca] + order[((rb+1) % 29)*29 + cb]
        # rectangle swap columns
        return order[ra*29 + cb] + order[rb*29 + ca]

    # strip spaces; split to digrams with filler if needed
    s = pt_runes.replace(" ", "")
    out: List[str] = []
    i = 0
    filler = Runeglish.latin_to_rune("X")  # common filler
    while i < len(s):
        a = s[i]
        if i+1 < len(s):
            b = s[i+1]
            if a == b:
                out.append(enc_pair(a, filler))
                i += 1
            else:
                out.append(enc_pair(a, b)); i += 2
        else:
            out.append(enc_pair(a, filler)); i += 1
    return "".join(out)

# ---------- main ----------
def main() -> None:
    # English paragraph → (idx, wli, runes). For Playfair, we remove spaces (no WLI).
    pt_en = (
        "THERE WAS A TABLE SET OUT UNDER A TREE IN FRONT OF THE HOUSE "
        "AND THE MARCH HARE AND THE HATTER WERE HAVING TEA AT IT"
    )
    pt_idx, wli, pt_runes = Runeglish.encode_english_to_runes(pt_en, direction="rev")
    pt_runes_ns = pt_runes.replace(" ", "")

    # Demo keyword → build square → encrypt
    key_en = "MARCH HARE"
    _, _, key_runes = Runeglish.encode_english_to_runes(key_en, direction="fwd")
    order = make_square_from_keyword(key_runes)
    ct_runes = playfair29_encrypt(pt_runes_ns, order)

    # Build cipher + key spec (search a permutation of the 29-symbol order)
    cipher = by_name.cipher("playfair29", key_len=29)  # your modern core class
    key_spec = KeySpec.permutation(len=29)

    # Hybrid search with sane defaults (works well in your other tutorials)
    solve = SolveSpec.hybrid(
        pop_size=200, generations=120,          # GA
        sa_iters=2000, sa_init_temp=1.0, sa_min_temp=0.001, sa_cooling=0.999
    )

    # Optional crib to help optimizer (first 2–3 words is plenty)
    crib_en = "THERE WAS A TABLE"
    _, _, crib_runes = Runeglish.encode_english_to_runes(crib_en, direction="rev")

    sol = run.solve(
        text=ct_runes,
        cipher=cipher,
        key=key_spec,
        solve=solve,
        device="cpu",
        scorer="rune",
        scorer_params={
            "objective": "pct.logp.win10",
            "n_char": 2,
            "n_wli": None,
            "win": 10,
            "include_char": True,
            "use_word_breaks": False,  # Playfair: spaces unknown
            "weights": (1.0,),
            # optional crib support — your core reads this from solve params/meta
            "crib_runes": crib_runes
        },
        wli_data=None,
        force_no_wli=True,
    )

    # Prepare pretty output
    rec_runes = getattr(sol, "plaintext", "")
    if not isinstance(rec_runes, str) or not rec_runes:
        pt_idx_found = getattr(sol, "plaintext_idx", None)
        if pt_idx_found:
            rec_runes = "".join(Runeglish.pos_to_rune(p) for p in pt_idx_found)

    rec_latin = "".join(" " if ch == " " else str(Runeglish.rune_to_latin(ch)) for ch in rec_runes)

    print_report(
        title="Playfair-29 (Permutation key, optional crib)",
        key_found=getattr(sol, "key", None),
        score=getattr(sol, "score", None),
        pt_runes_head=pt_runes_ns[:180],
        ct_runes_head=ct_runes[:180],
        rec_runes_head=rec_runes[:360],
        rec_latin_head=rec_latin[:360],
        meta=(getattr(sol, "meta", {}) or {})
    )

if __name__ == "__main__":
    main()
