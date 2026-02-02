# -*- coding: utf-8 -*-
"""
Tutorial: Vigenère via the *General Map* API (ct = (pt + k) mod 29)

What this shows :
1) Define the cipher *locally* as a tiny function: ct = (pt + k) % 29.
2) Take a normal English paragraph; convert to rune indices with word breaks.
3) Pick a short numeric key, encrypt to make a ciphertext (keeping the same word breaks).
4) Tell the solver only the *period* (K), not the key itself, and solve.
5) Pretty-print what happened, including a simple solver summary if available.

Notes:
- No numpy types. Lists, strings, and len() only.
- All conversions to arrays happen *inside* the API (`patche_old_ui/api.py`).
"""
from __future__ import annotations
from typing import List, Sequence, Dict, Any, Optional
from datetime import datetime

# --- Public API --------------------------------------------
from rune_decrypter_prime.api.api import define_map, KeySpec, SolverSpec, run
from rune_decrypter_prime.utils.runeglish import Runeglish

# ───────────────────────────────────────────────────────────────────────────
# 1) Define Vigenère cell as a general map: (pt, k) -> ct
# ───────────────────────────────────────────────────────────────────────────
N = 29  # Runeglish alphabet size

def vigenere_map(pt: int, k: int) -> int:
    """A single Vigenère cell in the Runeglish alphabet."""
    return (int(pt) + int(k)) % N


# ───────────────────────────────────────────────────────────────────────────
# 2) TODO meh this look shit
# ───────────────────────────────────────────────────────────────────────────
def repeat_to_length(pattern: Sequence[int], length: int) -> List[int]:
    """Repeat a short numeric key to a target length (e.g., K=4 over a long text)."""
    if length < 0:
        raise ValueError("length must be non-negative")
    if not pattern and length > 0:
        raise ValueError("pattern must not be empty when length > 0")
    out: List[int] = []
    L = len(pattern)
    for i in range(length):
        out.append(int(pattern[i % L]))
    return out

def encrypt_vigenere_indices(pt_idx: Sequence[int], key_idx: Sequence[int]) -> List[int]:
    """List-in, list-out encryption: ct[i] = (pt[i] + key[i]) % 29."""
    if len(pt_idx) != len(key_idx):
        raise ValueError("pt_idx and key_idx must be the same length")
    return [ (int(p) + int(k)) % N for p, k in zip(pt_idx, key_idx) ]

def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _preview_text(s: str, n: int = 160) -> str:
    return s if len(s) <= n else (s[:n] + "…")


# ───────────────────────────────────────────────────────────────────────────
# 3) Pretty printer (compact & narrative)
# ───────────────────────────────────────────────────────────────────────────
def print_report(
    *,
    title: str,
    cipher_kind: str,
    key_nums: Sequence[int],
    ct_idx_head: Sequence[int],
    ct_runes_head: str,
    pt_ref_runes_head: str,
    pt_ref_latin_head: str,
    rec_runes_head: str,
    rec_latin_head: str,
    key_found: Optional[Sequence[int]],
    score: Optional[float],
    optimizer_meta: Dict[str, Any],
    work_meta: Dict[str, Any],
    timings_meta: Dict[str, Any],
    no_wli: bool=True
) -> None:
    bar = "─" * 72
    print(bar)
    print(f"{title}  |  {_now()}")
    print(bar)
    print(f"Cipher     : {cipher_kind}")
    print(f"Key (nums) : {list(key_nums)}")
    if key_found is not None:
        try:
            print(f"Key(found) : {list(key_found)}")
        except Exception:
            print(f"Key(found) : {key_found}")
    print(f"PT (runes) : {_preview_text(pt_ref_runes_head)}")
    print(f"PT (latin) : {_preview_text(pt_ref_latin_head)}")
    print(f"CT idx     : {list(ct_idx_head)}{' …' if len(ct_idx_head) >= 32 else ''}")
    print(f"CT runes   : {_preview_text(ct_runes_head)}")
    print(bar)
    print("Recovered plaintext (runes):")
    print(_preview_text(rec_runes_head, 360))
    print("Recovered plaintext (latin):")
    print(_preview_text(rec_latin_head, 360))
    print(bar)
    if isinstance(score, (int, float)):
        print(f"Score      : {score:.6f}")
    print("Optimizer  :", optimizer_meta if optimizer_meta else {})
    print("Work       :", work_meta if work_meta else {})
    print("Timings    :", timings_meta if timings_meta else {})
    print(bar)
    print("Note: Higher scores ≈ more language-like (n-gram log-probabilities).")
    print(bar)


# ───────────────────────────────────────────────────────────────────────────
# 4) End-to-end tutorial
# ───────────────────────────────────────────────────────────────────────────
def main() -> None:
    # Step A — A normal English paragraph (with spaces)
    pt_english = (
        "THERE WAS A TABLE SET OUT UNDER A TREE IN FRONT OF THE HOUSE "
        "AND THE MARCH HARE AND THE HATTER WERE HAVING TEA AT IT "
        "A DORMOUSE WAS SITTING BETWEEN THEM FAST ASLEEP "
        "AND THE OTHER TWO WERE USING IT AS A CUSHION RESTING THEIR ELBOWS ON IT"
    )

    # Turn that into (indices, WLI, rune string). No numpy for the learner.
    # encode_english_to_runes handles punctuation cleanup & QU/KW etc per helper.
    pt_idx, wli, pt_runes = Runeglish.encode_english_to_runes(pt_english, direction="rtl")

    # Step B — Define the cipher via the general map (function form).
    cipher_spec = define_map(function=vigenere_map, N=N)

    # Step C — Pick a key (the learner sees numbers, not types) and encrypt.
    key_nums = [3, 1, 4, 1]                 # cute π-ish toy key
    stream   = repeat_to_length(key_nums, len(pt_idx))
    # todo kind of redundant aactually mayeb you havbe to defien to funcitons (for full demo??)
    ct_idx   = encrypt_vigenere_indices(pt_idx, stream)
    # keep the *same* WLI so spaces stay in corresponding places
    ct_runes = Runeglish.to_rune(ct_idx, wli)

    # Step D — Tell the solver only the period K; set a modest beam.
    key_spec   = KeySpec.repeat(len=len(key_nums))
    solve_spec = SolverSpec.beam(
        beam_width=32,
        plateau_rounds=8,
        plateau_min_delta=1e-4,
        stop_score=0.55,
    )

    # Make scoring word-break aware .
    scorer_params = {
        "objective": "pct.logp.win10",
        "n_char": 2,
        "n_wli": 2,
        "win": 10,
        "include_char": True,
        "use_word_breaks": True,
        "weights": (0.5, 0.5),
    }

    # Step E — Solve. Passing the *rune string with spaces* lets the UI infer WLI.
    solution = run.solve(
        text=ct_runes,
        cipher=cipher_spec,
        key=key_spec,
        solve=solve_spec,
        device="cpu",
        scorer="rune",
        scorer_params=scorer_params,
        logging=None,          # or a dict that maps to Core LoggingConfig in patche_old_ui/api.py
        wli_data=None        # omit → patche_old_ui/api builds it from spaces in ct_runes
    )

    # Step F — Prepare pretty output (robust to field shapes).
    key_found = getattr(solution, "key", None)
    score     = getattr(solution, "score", None)

    # The UI usually guarantees plaintext is a rune string; fall back if not.
    rec_runes = getattr(solution, "plaintext", "")
    if not isinstance(rec_runes, str) or not rec_runes:
        pt_idx_found = getattr(solution, "plaintext_idx", None)
        if pt_idx_found:
            rec_runes = Runeglish.to_rune(pt_idx_found, wli)

    # Latin glance (map runes to canonical tokens, spacing preserved)
    rec_latin = "".join(" " if ch == " " else str(Runeglish.rune_to_latin(ch)) for ch in rec_runes)
    pt_latin  = "".join(" " if ch == " " else str(Runeglish.rune_to_latin(ch)) for ch in pt_runes)

    # Optimizer summary, if telemetry got attached by the engine
    meta = getattr(solution, "meta", {}) or {}
    tel  = meta.get("telemetry", {}) if isinstance(meta, dict) else {}

    optimizer_meta: Dict[str, Any] = {}
    work_meta: Dict[str, Any] = {}
    timings_meta: Dict[str, Any] = {}

    try:
        opt_nodes = tel.get("solver", {}) if isinstance(tel, dict) else {}
        beam_node = opt_nodes.get("beam", {}) if isinstance(opt_nodes, dict) else {}
        if isinstance(beam_node, dict):
            params = beam_node.get("params", {}) if isinstance(beam_node.get("params", {}), dict) else {}
            optimizer_meta = {
                "name": "beam",
                "beam_width": params.get("beam_width"),
                "K": params.get("K"),
            }
            work_meta = {
                "attempted_total": beam_node.get("attempted_total"),
                "kept_total":      beam_node.get("kept_total"),
                "pruned_total":    beam_node.get("pruned_total"),
            }
            timings_meta = {
                "elapsed_sec": beam_node.get("elapsed_sec"),
            }
    except Exception:
        pass  # if no telemetry present, we just keep these dicts empty

    # Heads for compact previews
    ct_idx_head     = ct_idx[:32]
    ct_runes_head   = ct_runes[:180]
    pt_runes_head   = pt_runes[:180]
    pt_latin_head   = pt_latin[:180]
    rec_runes_head  = rec_runes[:360]
    rec_latin_head  = rec_latin[:360]

    # Print it
    print_report(
        title="Vigenère via General Map API",
        cipher_kind=cipher_spec.kind,
        key_nums=key_nums,
        ct_idx_head=ct_idx_head,
        ct_runes_head=ct_runes_head,
        pt_ref_runes_head=pt_runes_head,
        pt_ref_latin_head=pt_latin_head,
        rec_runes_head=rec_runes_head,
        rec_latin_head=rec_latin_head,
        key_found=key_found,
        score=score if isinstance(score, (int, float)) else None,
        optimizer_meta=optimizer_meta,
        work_meta=work_meta,
        timings_meta=timings_meta,
        no_wli=True
    )


if __name__ == "__main__":
    main()
