# # -*- coding: utf-8 -*-
# """
# Tutorial: Monoalphabetic substitution (29-rune alphabet) with SA
# ----------------------------------------------------------------
# -*- coding: utf-8 -*-
"""
Mono Substitution (29 runes) — SA walkthrough

What you’ll see
---------------
1) English → runes (one direction, kept consistent).
2) Random key → encrypt → ciphertext.
3) Simple frequency-based seed guesses (optional but helpful).
4) Simulated Annealing (SA) recovers readable plaintext.
5) A short report at the end.

You can tweak the SA knobs below.
"""
from __future__ import annotations
from typing import Tuple
import numpy as np

from rune_decrypter_prime.ui.api import by_name, cipher_instance, KeySpec, SolveSpec, run
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.tutorials.v1 import pretty
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext_english_string
from rune_decrypter_prime.utils.seed_utils import make_seeds_from_freq


def preview(s: str, n: int = 120) -> str:
    return s if len(s) <= n else s[:n] + "…"


def _invert_perm(pt_to_ct: np.ndarray) -> np.ndarray:
    inv = np.empty_like(pt_to_ct)
    inv[pt_to_ct] = np.arange(pt_to_ct.size, dtype=np.uint8)
    return inv


def _build_ciphertext(pt_en: str, *, direction: str = "rev", seed: int = 42):
    pt_idx, wli, _ = Runeglish.encode_english_to_runes(pt_en, direction=direction)
    rng = np.random.default_rng(seed)
    key_fwd = rng.permutation(29).astype(np.uint8)
    ciph = cipher_instance(by_name.cipher("mono"))
    ct_idx = ciph.encrypt(plaintext=np.asarray(pt_idx, np.uint8), key=key_fwd)
    ct_runes = Runeglish.to_rune(ct_idx.tolist(), wli)
    key_inv = _invert_perm(key_fwd)
    return ct_runes, wli, key_fwd.tolist(), key_inv.tolist()


def main():
    direction = "rev"

    # 1) English → ciphertext
    pt_en = plaintext_english_string
    ct_runes, wli, _key_fwd, _key_inv = _build_ciphertext(pt_en, direction=direction, seed=42)

    # 2) Simple seeds from ciphertext (comment out to start from pure noise)
    seeds = make_seeds_from_freq(ct_runes.replace(" ",""), n_keys=120, swaps_per_key=2, seed=12345, direction=direction)

      # 3) SA config (kept readable) — pass kwargs directly
    sa = SolveSpec.sa(
           sa_iters = 30000,
        sa_init_temp = 0.8,
        sa_min_temp = 1e-3,
        sa_cooling = 0.998,
        sa_auto_cooling = True,
        sa_elitism = True,
        sa_reseed_interval = 5000,
        sa_rescue_drop_abs = 0.02,
        sa_rescue_drop_ratio = 0.5,
        local_improve_on_accept = True,
        log_interval = 500,
        verbose = True,
        seed = 123,
        stop_score = 0.52,
        patience=7000,
        tol=1e-6,
    )

    # 4) Run solver
    sol = run.solve(
        text=ct_runes,
        cipher=by_name.cipher("mono"),
        key=KeySpec.permutation(len=29),
        solve=sa,
        device="cpu",
        scorer="rune",
        scorer_params=dict(
            objective="pct.logp.win10",
            char_weights={2: 0.3},
            wli_weights={2: 0.7},
            include_char=True,
            use_word_breaks=True,
            direction=direction,
        ),
        wli_data=wli,
        initial_keys=seeds
    )

    # 5) Report
    print("─" * 72)
    print("Mono Substitution — SA")
    print("Recovered plaintext:", preview(sol.plaintext))
    print("Score:", round(sol.score, 6))

    pretty.print_run_report(
        title="mono-sa",
        cipher="mono",
        key_idx=None,
        ct_idx=Runeglish.rune_to_pos(ct_runes.replace(" ","")),
        ct_rune=ct_runes,
        solution=sol,
        match_ok=None,
        app_version="tutorial-1.2",
        key_len=None,
        wli=wli,
        pt_rune_ref=pt_en,
        pt_idx_ref="",
    )

if __name__ == "__main__":
    main()



# 1) Build ciphertext via cipher.encrypt(...)
# 2) Estimate LM unigrams (rev/fwd) and make CT-vs-LM frequency seeds
# 3) Pass seeds as initial_keys
# 4) Solve with SA (same scorer + direction discipline as GA)
# """
#
# from __future__ import annotations
# import math
# from collections import Counter
# from typing import List, Tuple
#
# import numpy as np
#
# from rune_decrypter_prime.ui.api import by_name, cipher_instance, KeySpec, SolveSpec, run
# from rune_decrypter_prime.utils.runeglish import Runeglish
# from rune_decrypter_prime.tutorials.v1 import pretty
# from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext_english_string
# from rune_decrypter_prime.scoring.language_model.language_model_prime import LanguageModelPrime
#
#
# # --------------------------- small utils --------------------------------------
#
# def preview(s: str, n: int = 120) -> str:
#     return s if len(s) <= n else s[:n] + "…"
#
# def invert_perm(pt_to_ct: np.ndarray) -> np.ndarray:
#     inv = np.empty_like(pt_to_ct)
#     inv[pt_to_ct] = np.arange(pt_to_ct.size, dtype=np.uint8)
#     return inv
#
# # -------------------- Step 1: ciphertext via cipher API -----------------------
#
# def build_ciphertext_api(
#     pt_en: str,
#     *,
#     encoding_dir: str = "rev",
#     seed: int = 42,
# ) -> Tuple[str, List[Tuple[int, int]], List[int], List[int]]:
#     """Encode English→runes, then encrypt using the cipher’s own API."""
#     pt_idx, wli, _ = Runeglish.encode_english_to_runes(pt_en, direction=encoding_dir)
#
#     rng = np.random.default_rng(seed)
#     key_fwd = rng.permutation(29).astype(np.uint8)  # pt→ct
#
#     ciph = cipher_instance(by_name.cipher("mono"))
#     ct_idx = ciph.encrypt(plaintext=np.asarray(pt_idx, dtype=np.uint8), key=key_fwd)
#
#     ct_runes = Runeglish.to_rune(ct_idx.tolist(), wli)
#     key_inv = invert_perm(key_fwd)  # ct→pt
#
#     return ct_runes, wli, key_fwd.tolist(), key_inv.tolist()
#
# # -------- Step 2: unigram estimation from the real LM (direction-aware) -------
#
# def estimate_unigram_probs_from_lm(direction: str = "rev") -> List[float]:
#     """Score 29 constant sequences; exp(mean logp) → normalize."""
#     L = 64
#     lm = LanguageModelPrime(lm_root=None, smoothing=None, oov_policy=None, include_char=True)
#     pts = [[r] * L for r in range(29)]
#     res = lm.score(pts, None, direction=direction, se="nose", n=1, model="char")
#     raw = [math.exp(s.logprob_sum / L) for s in res]
#     Z = sum(raw) or 1.0
#     return [x / Z for x in raw]
#
# # ---- Step 3: seed generation by CT frequency vs LM unigram ranking -----------
#
# def make_seed_keys_from_unigram(
#     ct_idx: List[int],
#     *,
#     n_keys: int = 100,
#     swaps_per_key: int = 3,
#     seed: int | None = 12345,
#     direction: str = "rev",
# ) -> List[List[int]]:
#     """Produce ct→pt candidate keys by rank alignment + small jitters."""
#     counts = Counter(ct_idx)
#     ct_order = [sym for sym, _ in counts.most_common()] + [i for i in range(29) if i not in counts]
#
#     probs = estimate_unigram_probs_from_lm(direction=direction)
#     pt_order = list(np.argsort(-np.asarray(probs)))
#
#     base = np.arange(29, dtype=np.int64)  # ct→pt
#     for ct_sym, pt_sym in zip(ct_order, pt_order):
#         base[ct_sym] = int(pt_sym)
#
#     rng = np.random.default_rng(seed)
#     seeds: List[List[int]] = []
#     for _ in range(n_keys):
#         k = base.copy()
#         for _ in range(max(1, swaps_per_key)):
#             i, j = rng.integers(0, 29, size=2)
#             if i != j:
#                 k[i], k[j] = k[j], k[i]
#         seeds.append(k.astype(np.uint8).tolist())
#
#     seeds[0] = base.astype(np.uint8).tolist()  # keep the pure rank alignment
#     return seeds
#
# # ------------------------ Step 4: solve wrapper (SA) --------------------------
#
# def run_solver(ct_runes: str, wli, *, direction: str, sa_params: dict):
#     cipher_spec = by_name.cipher("mono")
#     key_spec = KeySpec.permutation(len=29)
#
#     # Build seeds (ct→pt) from CT + LM
#     ct_idx = [Runeglish.rune_to_pos(c) for c in ct_runes if c != " "]
#     seeds = make_seed_keys_from_unigram(ct_idx, n_keys=sa_params.pop("_n_seed", 100),
#                                         swaps_per_key=sa_params.pop("_seed_swaps", 3),
#                                         seed=sa_params.pop("_seed_rng", 12345),
#                                         direction=direction)
#
#     sol = run.solve(
#         text=ct_runes,
#         cipher=cipher_spec,
#         key=key_spec,
#         solve=SolveSpec.sa(**sa_params),   # ← expose all SA knobs here
#         device="cpu",
#         scorer="rune",
#         scorer_params=dict(
#             objective="pct.logp.win10",
#             char_weights={2: 0.3},
#             #char_weights={2: 0.3, 3: 0.7},
#             wli_weights={2: 0.7 },
#             #wli_weights={2: 0.5},
#
#             include_char=True,
#             use_word_breaks=True,
#             direction=direction,
#         ),
#         wli_data=wli,
#         initial_keys=seeds,
#     )
#
#     print("─" * 72)
#     print("Mono Substitution (SA)")
#     print("Recovered plaintext:", preview(sol.plaintext))
#     print("Score:", round(sol.score, 6))
#     return sol
#
# # --------------------------------- Main ---------------------------------------
#
# def main():
#     direction = "rev"  # keep this consistent across LM, seeds, and scorer
#
#     pt_en = plaintext_english_string
#     ct_runes, wli, key_fwd, key_inv = build_ciphertext_api(pt_en, encoding_dir=direction, seed=42)
#
#     # Fully exposed SA config (tweak freely)
#     sa_params = dict(
#         sa_iters=500_000,
#         sa_init_temp=1.0,
#         sa_min_temp=0.01,
#         sa_cooling=0.9995,         # used when sa_auto_cooling=False
#         sa_auto_cooling=False,     # set True to derive cooling from T0, Tmin, iters
#         verbose=True,
#
#         sa_elitism=True,
#         sa_reseed_interval=5000,
#         sa_rescue_drop_abs=0.01,
#         sa_rescue_drop_ratio=0.6,
#
#         # permutation neighbourhood knobs (forwarded to keyops by SA)
#         perm_mutate_mix=(0.7, 0.2, 0.1),  # swap-2 / cycle-3 / block
#         perm_block_size=3,
#         perm_rotate_size=4,
#
#         # tutorial-only seeding helper knobs (consumed in run_solver, not SA):
#         _n_seed=100,
#         _seed_swaps=3,
#         _seed_rng=12345,
#
#         stop_score=0.52,
#         patience=10_000,
#         tol=1e-6,
#     )
#
#     sol = run_solver(ct_runes, wli, direction=direction, sa_params=sa_params)
#
#     # Pretty report
#     pretty.print_run_report(
#         title="mono-sa",
#         cipher="mono",
#         key_idx=None,
#         ct_idx=[Runeglish.rune_to_pos(c) for c in ct_runes],
#         ct_rune=ct_runes,
#         solution=sol,
#         match_ok=None,
#         app_version="tutorial-1.0",
#         key_len=None,
#         wli=wli,
#         pt_rune_ref=pt_en,
#         pt_idx_ref="",
#     )
#
# if __name__ == "__main__":
#     main()
#
# # # -*- coding: utf-8 -*-
# # """
# # Tutorial: Monoalphabetic substitution (29-rune alphabet) via Simulated Annealing
# # -------------------------------------------------------------------------------
# # - Passes `initial_keys` into the optimizer
# # - Seeds come from unigram frequency alignment (LanguageModelPrime, n=1, char)
# # - Prints diagnostics: ciphertext/plaintext frequencies, true key, seed keys,
# #   similarities, and a mismatch table (what we guessed vs what’s correct)
# # """
# # from __future__ import annotations
# # import math
# # import random
# # from collections import Counter
# # from typing import List
# #
# # import numpy as np
# #
# # from rune_decrypter_prime.ui.api import by_name, KeySpec, SolveSpec, run
# # from rune_decrypter_prime.utils.runeglish import Runeglish
# # from rune_decrypter_prime.tutorials.v1 import pretty
# # from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext_english_string
# # from rune_decrypter_prime.scoring.language_model.language_model_prime import LanguageModelPrime
# # from rune_decrypter_prime.data.cipher_tests.baseline_registry import BASELINE
# #
# #
# # # ──────────────────────────────────────────────────────────────────────────────
# # # Unigram helpers
# # # ──────────────────────────────────────────────────────────────────────────────
# #
# # def estimate_unigram_probs_from_lm(direction: str = "rev", L: int = 64) -> List[float]:
# #     """
# #     Estimate rune 1-gram probs using the real LM (n=1, char, NOSE).
# #     Uses counts_sum (simple, robust). Normalizes to 1.
# #     """
# #     lm = LanguageModelPrime(lm_root=None, smoothing=None, oov_policy=None, include_char=True)
# #     pts = [[r] * L for r in range(29)]
# #     res = lm.score(pts, None, direction=direction, se="nose", n=1, model="char")
# #     raw = [s.counts_sum for s in res]
# #     Z = float(sum(raw)) or 1.0
# #     return [x / Z for x in raw]
# #
# #
# # def make_seed_keys_from_unigram(ct_idx: list[int], direction="rev",
# #                                 n_keys=50, swaps_per_key=3, seed=12345):
# #     from collections import Counter
# #     import numpy as np
# #
# #     # ciphertext frequency ranking → ct_order
# #     c = Counter(ct_idx)
# #     ct_order = [sym for sym, _ in c.most_common()] + [i for i in range(29) if i not in c]
# #
# #     # LM unigram → pt_order
# #     p = estimate_unigram_probs_from_lm(direction)
# #     pt_order = list(np.argsort(-np.asarray(p, dtype=float)))
# #
# #     # base mapping from rank alignment
# #     base = np.arange(29, dtype=np.int64)
# #     for ct_sym, pt_sym in zip(ct_order, pt_order):
# #         base[ct_sym] = int(pt_sym)
# #
# #     rng = np.random.default_rng(seed)
# #     seeds = [base.copy().astype(np.uint8).tolist()]
# #
# #     # local-neighborhood variants (adjacent in ct_order most of the time)
# #     for _ in range(n_keys - 1):
# #         k = base.copy()
# #         for _ in range(swaps_per_key):
# #             # pick a position by frequency rank, then swap with a nearby rank
# #             i_pos = int(rng.integers(0, 29))
# #             j_pos = int(np.clip(i_pos + rng.choice([-2, -1, 1, 2, 3, -3], p=[.2,.3,.3,.2,.0,.0]), 0, 28))
# #             i = ct_order[i_pos]
# #             j = ct_order[j_pos]
# #             if i != j:
# #                 k[i], k[j] = k[j], k[i]
# #         seeds.append(k.astype(np.uint8).tolist())
# #
# #     # refine the first seed by bigram score
# #     seeds[0] = refine_seed_with_bigrams(seeds[0], ct_idx, direction=direction, passes=2, neighborhood=3)
# #     return seeds
# #
# #
# # def score_pt_with_char_bigrams(pt_idx: list[int], direction: str = "rev") -> float:
# #     """
# #     Score a single plaintext sequence with the real LM (char, n=2, NOSE).
# #     Returns mean log-prob per token (float).
# #     """
# #     from rune_decrypter_prime.scoring.language_model.language_model_prime import LanguageModelPrime
# #     lm = LanguageModelPrime(lm_root=None, smoothing=None, oov_policy=None, include_char=True)
# #     # lm.score returns SentScores(counts_sum, logprob_sum, z_sum, madsum)
# #     s = lm.score([pt_idx], None, direction=direction, se="nose", n=2, model="char")[0]
# #     L = max(1, len(pt_idx))
# #     return float(s.logprob_sum) / L
# #
# # def refine_seed_with_bigrams(base_key: list[int], ct_idx: list[int],
# #                              direction: str = "rev",
# #                              passes: int = 2, neighborhood: int = 3) -> list[int]:
# #     """
# #     Greedy local improvement: try swapping ct symbols whose LM-unigram ranks are close
# #     (±neighborhood in the ct frequency order), keep swaps that increase bigram score.
# #     """
# #     from collections import Counter
# #     k = base_key[:]  # copy
# #     pt_idx = [k[x] for x in ct_idx]
# #     best = score_pt_with_char_bigrams(pt_idx, direction)
# #
# #     # build a stable CT frequency order to propose local swaps
# #     freq_order = [sym for sym, _ in Counter(ct_idx).most_common()]
# #     freq_pos = {s: i for i, s in enumerate(freq_order)}
# #
# #     for _ in range(passes):
# #         improved = False
# #         for a in range(29):
# #             ia = freq_pos.get(a, 28)
# #             # try a few neighbors in rank space
# #             for delta in range(-neighborhood, neighborhood + 1):
# #                 if delta == 0:
# #                     continue
# #                 jb = ia + delta
# #                 if jb < 0 or jb >= len(freq_order):
# #                     continue
# #                 b = freq_order[jb]
# #                 if a == b:
# #                     continue
# #                 # propose swap in key (swap the PT symbols assigned to CT 'a' and CT 'b')
# #                 k[a], k[b] = k[b], k[a]
# #                 cand_pt = [k[x] for x in ct_idx]
# #                 sc = score_pt_with_char_bigrams(cand_pt, direction)
# #                 if sc > best:
# #                     best = sc
# #                     improved = True
# #                 else:
# #                     # revert
# #                     k[a], k[b] = k[b], k[a]
# #         if not improved:
# #             break
# #     return k
# #
# #
# #
# # # ──────────────────────────────────────────────────────────────────────────────
# # # Cipher construction and metrics
# # # ──────────────────────────────────────────────────────────────────────────────
# #
# # def build_ciphertext(pt_en: str, seed: int = 42, direction: str = "rev"):
# #     """
# #     Encrypts the provided plaintext with a random permutation key.
# #     Returns: (ct_runes, wli, true_key_perm, pt_idx)
# #     """
# #     pt_idx, wli, _pt_runes = Runeglish.encode_english_to_runes(pt_en, direction=direction)
# #     alphabet = list(range(29))
# #     perm = alphabet[:]
# #     random.seed(seed)
# #     random.shuffle(perm)  # true key: pt -> ct mapping (or ct->pt depending on convention)
# #     lookup = {alphabet[i]: perm[i] for i in range(29)}
# #     ct_idx = [lookup[x] for x in pt_idx]
# #     ct_runes = Runeglish.to_rune(ct_idx, wli)
# #     return ct_runes, wli, perm, pt_idx  # expose pt_idx for diagnostics
# #
# #
# # def similarity_score(key_guess: List[int], key_true: List[int]) -> float:
# #     """Fraction of symbols mapped correctly (0..1)."""
# #     return sum(int(a == b) for a, b in zip(key_guess, key_true)) / len(key_true)
# #
# #
# # def print_freq_table(name: str, idx_list: List[int], top: int = 10):
# #     freq = Counter(idx_list)
# #     items = freq.most_common()
# #     print(f"{name} frequencies (top {top}):")
# #     for sym, cnt in items[:top]:
# #         print(f"  rune {sym:2d} : {cnt}")
# #     print(f"  (unique {len(freq)}/29, total {sum(freq.values())})\n")
# #
# #
# # def print_key_mismatches(true_key: List[int], guess_key: List[int], max_rows: int = 15):
# #     """
# #     We treat key as a mapping array K where K[ct_sym] = pt_sym.
# #     Print rows where guess != true, limited to max_rows.
# #     """
# #     rows = [(ct, true_key[ct], guess_key[ct]) for ct in range(29) if true_key[ct] != guess_key[ct]]
# #     print(f"Mismatches (ct_sym -> pt_sym_true / pt_sym_guess), showing up to {max_rows}:")
# #     for ct, pt_t, pt_g in rows[:max_rows]:
# #         print(f"  ct {ct:2d} -> true {pt_t:2d} / guess {pt_g:2d}")
# #     if not rows:
# #         print("  (none)")
# #     print("")
# #
# #
# # def print_diagnostics(ct_idx: List[int], pt_idx: List[int], true_key: List[int], seeds: List[List[int]]):
# #     print("\n──────── Diagnostics ────────")
# #     print_freq_table("Ciphertext", ct_idx, top=12)
# #     print_freq_table("Plaintext ", pt_idx, top=12)
# #
# #     print("True key mapping (K[ct]=pt):")
# #     print(true_key, "\n")
# #
# #     # Report similarities for the first few seeds
# #     print("Seed similarities to true key:")
# #     best_i, best_sim = 0, -1.0
# #     for i, k in enumerate(seeds[:10]):
# #         sim = similarity_score(k, true_key)
# #         print(f"  seed[{i:2d}] -> {sim*100:5.2f}%")
# #         if sim > best_sim:
# #             best_sim, best_i = sim, i
# #     print(f"\nBest seed in first 10: index {best_i}, similarity {best_sim*100:.2f}%\n")
# #
# #     # Mismatches for the best-first seed
# #     print("First seed key:")
# #     print(seeds[0], "\n")
# #     print_key_mismatches(true_key, seeds[0], max_rows=15)
# #     print("──────── End Diagnostics ────────\n")
# #
# #
# # def print_freqs(title: str, counts: dict[int,int], top: int = 12):
# #     order = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
# #     total = sum(counts.values())
# #     uniq = len(counts)
# #     print(f"{title} (top {top}):")
# #     for r, c in order[:top]:
# #         print(f"  rune {r:2d} : {c}")
# #     print(f"  (unique {uniq}/29, total {total})\n")
# #
# # def decode_with_key(ct_idx: list[int], key: list[int]) -> list[int]:
# #     # key maps CT symbol -> PT symbol
# #     return [key[x] for x in ct_idx]
# #
# # def similarity_score(key_guess, key_true) -> float:
# #     return sum(int(a == b) for a, b in zip(key_guess, key_true)) / len(key_true)
# #
# # def print_seed_diagnostics(ct_idx: list[int], true_key: list[int], seeds: list[list[int]],
# #                            show: int = 10, show_mismatches: int = 15):
# #     from collections import Counter
# #     ct_counts = Counter(ct_idx)
# #     pt_idx = decode_with_key(ct_idx, true_key)
# #     pt_counts = Counter(pt_idx)
# #
# #     print("\n──────── Diagnostics ────────")
# #     print_freqs("Ciphertext frequencies", ct_counts, top=12)
# #     print_freqs("Plaintext  frequencies (true, via key)", pt_counts, top=12)
# #
# #     print("True key mapping (K[ct]=pt):")
# #     print(list(true_key), "\n")
# #
# #     sims = [(i, similarity_score(k, true_key)) for i, k in enumerate(seeds[:max(show, 1)])]
# #     best_i, best_s = max(sims, key=lambda t: t[1])
# #     print("Seed similarities to true key:")
# #     for i, s in sims:
# #         print(f"  seed[{i:2d}] -> {s*100:6.2f}%")
# #     print(f"\nBest seed in first {show}: index {best_i}, similarity {best_s*100:.2f}%\n")
# #
# #     if seeds:
# #         guess = seeds[0]
# #         print("First seed key:")
# #         print(list(guess), "\n")
# #         print("Mismatches (ct_sym -> pt_sym_true / pt_sym_guess), showing up to", show_mismatches, ":")
# #         shown = 0
# #         for ct_sym, (pt_t, pt_g) in enumerate(zip(true_key, guess)):
# #             if pt_t != pt_g:
# #                 print(f"  ct {ct_sym:2d} -> true {pt_t:2d} / guess {pt_g:2d}")
# #                 shown += 1
# #                 if shown >= show_mismatches:
# #                     break
# #         if shown == 0:
# #             print("  (none)")
# #     print("\n──────── End Diagnostics ────────\n")
# #
# #
# # # ──────────────────────────────────────────────────────────────────────────────
# # # Solver wrapper
# # # ──────────────────────────────────────────────────────────────────────────────
# #
# # def run_solver(ct_runes: str, wli, seeds: List[List[int]]):
# #     cipher = by_name.cipher("substitution")
# #     key_spec = KeySpec.permutation(len=29)
# #
# #     sol = run.solve(
# #         text=ct_runes,
# #         cipher=cipher,
# #         key=key_spec,
# #         solve=SolveSpec.sa(
# #             sa_iters=500_000,
# #             sa_init_temp=1.0,
# #             sa_min_temp=0.01,
# #             sa_cooling=0.9995,
# #             sa_auto_cooling=False,  # ← add this line
# #             verbose=True,
# #             # todo move to permuation ops somehow
# #             perm_mutate_mix=(0.7, 0.2, 0.1),
# #             perm_block_size=3,
# #             perm_rotate_size=4,
# #         ),
# #         device="cpu",
# #         scorer="rune",
# #         scorer_params=dict(
# #             objective="pct.logp.win10",
# #             char_weights={2: 0.4, 3: 0.6},
# #             wli_weights={2: 0.4, 3: 0.6},
# #             include_char=True,
# #             use_word_breaks=True,
# #             direction="rev",
# #         ),
# #         wli_data=wli,
# #         initial_keys=seeds,
# #     )
# #
# #     print("─" * 72)
# #     print("Mono Substitution (SA)")
# #     pt_preview = sol.plaintext if isinstance(sol.plaintext, str) else str(sol.plaintext)
# #     print("Recovered plaintext:", (pt_preview[:120] + "…") if len(pt_preview) > 120 else pt_preview)
# #     print("Score:", round(sol.score, 6))
# #     return sol
# #
# #
# # # ──────────────────────────────────────────────────────────────────────────────
# # # Main
# # # ──────────────────────────────────────────────────────────────────────────────
# #
# # def main():
# #     # (Optional) show LM 1-gram ranking (rev) for sanity
# #     # This also loads the LM once, so later calls are warmed.
# #     probs = estimate_unigram_probs_from_lm(direction="rev")
# #     order = sorted(range(29), key=lambda r: -probs[r])
# #     print("LM unigram (rev) top 10 (rune:prob):",
# #           [(r, round(probs[r], 4)) for r in order[:10]], "\n")
# #
# #     # Build example
# #     pt_en = plaintext_english_string
# #     ct_runes, wli, true_key, pt_idx = build_ciphertext(pt_en, seed=BASELINE["seed"], direction="rev")
# #     ct_idx = [Runeglish.rune_to_pos(c) for c in ct_runes if c != " "]
# #
# #     # Seeds from unigram alignment
# #     seeds = make_seed_keys_from_unigram(ct_idx, direction="rev", n_keys=1000, swaps_per_key=2)
# #
# #     from rune_decrypter_prime.utils.seed_utils import make_better_seed_keys
# #
# #     # Seeds from improved rank + E/T/A + bigram refinement (rev or fwd — pick ONE)
# #     seeds = make_better_seed_keys(
# #         ct_idx,
# #         direction="rev",
# #         n_keys=1000,
# #         swaps_per_key=2,
# #         seed=12345,
# #     )
# #
# #     print_seed_diagnostics(ct_idx, true_key, seeds, show=20, show_mismatches=20)
# #
# #     # Diagnostics before solving
# #     print_diagnostics(ct_idx, pt_idx, true_key, seeds)
# #
# #     # Solve
# #     sol = run_solver(ct_runes, wli, seeds)
# #
# #     # Standard report
# #     pretty.print_run_report(
# #         title="mono-sa",
# #         cipher="substitution",
# #         key_idx=None,
# #         ct_idx=[Runeglish.rune_to_pos(c) for c in ct_runes],
# #         ct_rune=ct_runes,
# #         solution=sol,
# #         match_ok=None,
# #         app_version="tutorial-1.0",
# #         key_len=None,
# #         wli=wli,
# #         pt_rune_ref=pt_en,
# #         pt_idx_ref="",
# #     )
# #
# #
# # if __name__ == "__main__":
# #     main()
