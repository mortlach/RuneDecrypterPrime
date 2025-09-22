# -*- coding: utf-8 -*-
"""
Tutorial: Vigenère via the General Map API

What it shows:
1. Define a Vigenère cell as a simple function: (pt, k) % 29.
2. Encode English text → rune indices (with spaces/WLI).
3. Encrypt with a short numeric key, repeat-to-length handled inline.
4. Tell the solver only the period, not the key.
5. Use the built-in pretty printer to show results.
"""
from __future__ import annotations
import random
from rune_decrypter_prime.ui.api import define_map, KeySpec, SolveSpec, run
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext_english_string
from rune_decrypter_prime.tutorials.v1.pretty import print_run_report

N = 29  # Rune alphabet

def vigenere_map(pt: int, k: int) -> int:
    return (pt + k) % N

def main():
    # Plaintext: a paragraph with spaces
    pt_en = (
        "THERE WAS A TABLE SET OUT UNDER A TREE IN FRONT OF THE HOUSE "
        "AND THE MARCH HARE AND THE HATTER WERE HAVING TEA AT IT "
        "A DORMOUSE WAS SITTING BETWEEN THEM FAST ASLEEP "
        "AND THE OTHER TWO WERE USING IT AS A CUSHION RESTING THEIR ELBOWS ON IT"
    )
    # test strgin from package
    pt_en = plaintext_english_string
    pt_idx, wli, pt_runes = Runeglish.encode_english_to_runes(pt_en, direction="rev")

    # Cipher spec: Vigenère cell (pt,k) -> (pt+k)%29
    cipher = define_map(function=vigenere_map, N=N)

    # Encrypt with a short numeric key
    key_nums = [3, 1, 4, 1,5, 6]
    stream = [key_nums[i % len(key_nums)] for i in range(len(pt_idx))]
    ct_idx = [vigenere_map(p, k) for p, k in zip(pt_idx, stream)]
    ct_runes = Runeglish.to_rune(ct_idx, wli)

    # Solver knows only the period (length of key), not the key itself
    key_spec   = KeySpec.repeat(len=len(key_nums))
    solve_spec = SolveSpec.beam(beam_width=32)

    # Run solver (defaults handle wli from spaces in ct_runes)
    sol = run.solve(
        text=ct_runes,
        cipher=cipher,
        key=key_spec,
        solve=solve_spec,
        device="cpu",
        scorer="rune",
        scorer_params=dict(
            objective="pct.logp.win10",
            char_weights={2: 1},
            wli_weights={2: 1},
            win=10,
            include_char=True, use_word_breaks=True,
        ),
    )

    # Pretty printer already formats everything (pt, ct, recovered, meta)
    print_run_report(
        title="Vigenère via General Map API",
        cipher="vigenere",
        key_idx=key_nums,
        ct_idx=ct_idx,
        ct_rune=ct_runes,
        solution=sol,
        match_ok=None,
        app_version="tutorial-1.0",
        key_len=len(key_nums),
        wli=wli,
        pt_rune_ref=pt_runes,
        pt_idx_ref=pt_idx,
    )

if __name__ == "__main__":
    main()

# # -*- coding: utf-8 -*-
# """
# Tutorial: Vigenère via the General Map API  (ct = (pt + k) mod 29)
#
# What this demonstrates:
#   1) Define a single-cell map locally (tiny pure-Python function).
#   2) Convert a normal English paragraph -> (indices, WLI, rune string) using Runeglish.
#   3) Encrypt with a short numeric key; keep the SAME WLI for display.
#   4) Tell the solver only the period K (not the key), then solve.
#   5) Pretty-print a compact report with optimizer telemetry (if available).
# """
#
# from __future__ import annotations
# from typing import List, Sequence, Dict, Any, Optional
# from datetime import datetime
#
# from rune_decrypter_prime.ui.api import define_map, KeySpec, SolveSpec, run
# from rune_decrypter_prime.utils.runeglish import Runeglish
#
# # ───────────────────────────────────────────────────────────────────────────
# # 1) Define the map
# # ───────────────────────────────────────────────────────────────────────────
# N = 29
#
# def vigenere_map(pt: int, k: int) -> int:
#     return (int(pt) + int(k)) % N
#
# # ───────────────────────────────────────────────────────────────────────────
# # 2) Tiny helpers (list-in/list-out for beginners)
# # ───────────────────────────────────────────────────────────────────────────
# def repeat_to_length(pattern: Sequence[int], length: int) -> List[int]:
#     if length < 0:
#         raise ValueError("length must be non-negative")
#     if not pattern and length > 0:
#         raise ValueError("pattern must not be empty when length > 0")
#     out: List[int] = []
#     L = len(pattern)
#     for i in range(length):
#         out.append(int(pattern[i % L]))
#     return out
#
# def encrypt_vigenere_indices(pt_idx: Sequence[int], key_idx: Sequence[int]) -> List[int]:
#     if len(pt_idx) != len(key_idx):
#         raise ValueError("pt_idx and key_idx must be the same length")
#     return [ (int(p) + int(k)) % N for p, k in zip(pt_idx, key_idx) ]
#
# def _now() -> str:
#     return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#
# def _preview(s: str, n: int = 160) -> str:
#     return s if len(s) <= n else (s[:n] + "…")
#
# # ───────────────────────────────────────────────────────────────────────────
# # 3) Pretty printer (compact & narrative, no numpy types)
# # ───────────────────────────────────────────────────────────────────────────
# def print_report(
#     *,
#     title: str,
#     key_nums: Sequence[int],
#     ct_idx_head: Sequence[int],
#     ct_runes_head: str,
#     pt_ref_runes_head: str,
#     pt_ref_latin_head: str,
#     rec_runes_head: str,
#     rec_latin_head: str,
#     key_found: Optional[Sequence[int]],
#     score: Optional[float],
#     optimizer_meta: Dict[str, Any],
#     work_meta: Dict[str, Any],
#     timings_meta: Dict[str, Any],
# ) -> None:
#     bar = "─" * 72
#     print(bar)
#     print(f"{title}  |  {_now()}")
#     print(bar)
#     print(f"Cipher     : user_map2 (Vigenère cell)")
#     print(f"Key (nums) : {list(key_nums)}")
#     if key_found is not None:
#         try:
#             print(f"Key(found) : {list(key_found)}")
#         except Exception:
#             print(f"Key(found) : {key_found}")
#     print(f"PT (runes) : {_preview(pt_ref_runes_head)}")
#     print(f"PT (latin) : {_preview(pt_ref_latin_head)}")
#     print(f"CT idx     : {list(ct_idx_head)}{' …' if len(ct_idx_head) >= 32 else ''}")
#     print(f"CT runes   : {_preview(ct_runes_head)}")
#     print(bar)
#     print("Recovered plaintext (runes):")
#     print(_preview(rec_runes_head, 360))
#     print("Recovered plaintext (latin):")
#     print(_preview(rec_latin_head, 360))
#     print(bar)
#     if isinstance(score, (int, float)):
#         print(f"Score      : {score:.6f}")
#     print("Optimizer  :", optimizer_meta if optimizer_meta else {})
#     print("Work       :", work_meta if work_meta else {})
#     print("Timings    :", timings_meta if timings_meta else {})
#     print(bar)
#     print("Note: Higher scores ≈ more language-like (n-gram log-probabilities).")
#     print(bar)
#
# # ───────────────────────────────────────────────────────────────────────────
# # 4) End-to-end tutorial
# # ───────────────────────────────────────────────────────────────────────────
# def main() -> None:
#     # Step A — a normal English paragraph
#     pt_english = (
#         "THERE WAS A TABLE SET OUT UNDER A TREE IN FRONT OF THE HOUSE "
#         "AND THE MARCH HARE AND THE HATTER WERE HAVING TEA AT IT "
#         "A DORMOUSE WAS SITTING BETWEEN THEM FAST ASLEEP "
#         "AND THE OTHER TWO WERE USING IT AS A CUSHION RESTING THEIR ELBOWS ON IT"
#     )
#
#     # Convert to rune indices + WLI (spaces → word breaks); direction='rev' to match your demos
#     pt_idx, wli, pt_runes = Runeglish.encode_english_to_runes(pt_english, direction="rev")
#
#     # Define cipher via general map
#     cipher_spec = define_map(function=vigenere_map, N=N)
#
#     # Pick a short numeric key and encrypt
#     key_nums = [3, 1, 4, 1]
#     stream   = repeat_to_length(key_nums, len(pt_idx))
#     ct_idx   = encrypt_vigenere_indices(pt_idx, stream)
#     ct_runes = Runeglish.to_rune(ct_idx, wli)  # keep spaces for nicer scoring
#
#     # Solve: only period K is given
#     key_spec   = KeySpec.repeat(len=len(key_nums))
#     solve_spec = SolveSpec.beam(beam_width=48)
#
#     scorer_params = {
#         "objective": "pct.logp.win10",
#         "n_char": 2,
#         "n_wli": 2,
#         "win": 10,
#         "include_char": True,
#         "use_word_breaks": True,
#         "weights": (0.5, 0.5),
#     }
#
#     sol = run.solve(
#         text=ct_runes,       # string with spaces → UI infers WLI
#         cipher=cipher_spec,
#         key=key_spec,
#         solve=solve_spec,
#         device="cpu",
#         scorer="rune",
#         scorer_params=scorer_params,
#         logging=None,
#         wli_data=None,
#     )
#
#     # Pretty preparation
#     key_found = getattr(sol, "key", None)
#     score     = getattr(sol, "score", None)
#
#     rec_runes = getattr(sol, "plaintext", "")
#     if not isinstance(rec_runes, str) or not rec_runes:
#         pt_idx_found = getattr(sol, "plaintext_idx", None)
#         if pt_idx_found:
#             rec_runes = Runeglish.to_rune(pt_idx_found, wli)
#
#     rec_latin = "".join(" " if ch == " " else str(Runeglish.rune_to_latin(ch)) for ch in rec_runes)
#     pt_latin  = "".join(" " if ch == " " else str(Runeglish.rune_to_latin(ch)) for ch in pt_runes)
#
#     meta = getattr(sol, "meta", {}) or {}
#     tel  = meta.get("telemetry", {}) if isinstance(meta, dict) else {}
#
#     optimizer_meta: Dict[str, Any] = {}
#     work_meta: Dict[str, Any] = {}
#     timings_meta: Dict[str, Any] = {}
#     try:
#         opt_nodes = tel.get("optimizer", {}) if isinstance(tel, dict) else {}
#         beam_node = opt_nodes.get("beam", {}) if isinstance(opt_nodes, dict) else {}
#         if isinstance(beam_node, dict):
#             params = beam_node.get("params", {}) if isinstance(beam_node.get("params", {}), dict) else {}
#             optimizer_meta = {"name": "beam", **({"beam_width": params.get("beam_width")} if params else {})}
#             work_meta = {k: beam_node.get(k) for k in ("attempted_total", "kept_total", "pruned_total") if k in beam_node}
#             timings_meta = {k: beam_node.get(k) for k in ("elapsed_sec",) if k in beam_node}
#     except Exception:
#         pass
#
#     print_report(
#         title="Vigenère via General Map API",
#         key_nums=key_nums,
#         ct_idx_head=ct_idx[:32],
#         ct_runes_head=ct_runes[:180],
#         pt_ref_runes_head=pt_runes[:180],
#         pt_ref_latin_head=pt_latin[:180],
#         rec_runes_head=rec_runes[:360],
#         rec_latin_head=rec_latin[:360],
#         key_found=key_found,
#         score=score if isinstance(score, (int, float)) else None,
#         optimizer_meta=optimizer_meta,
#         work_meta=work_meta,
#         timings_meta=timings_meta,
#     )
#
# if __name__ == "__main__":
#     main()
