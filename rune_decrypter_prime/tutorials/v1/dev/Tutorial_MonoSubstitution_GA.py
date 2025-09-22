# # # ============================================================
# # # Tutorial: Monoalphabetic substitution (29-rune alphabet).
# # # ============================================================
# # -*- coding: utf-8 -*-
# """
# Mono Substitution (29 runes) — GA walkthrough
#
# What you’ll see
# ---------------
# 1) We take a short English sample and turn it into runes ("rev" direction).
# 2) We encrypt it with a random key to make ciphertext.
# 3) We build a few simple seed guesses from letter frequencies.
# 4) We run the Genetic Algorithm (GA) to recover the plaintext.
# 5) We print a short, friendly report.
#
# You can tweak the GA knobs below.
# """
# from __future__ import annotations
# from typing import Tuple
# import numpy as np
#
# from rune_decrypter_prime.ui.api import by_name, cipher_instance, KeySpec, SolveSpec, run
# from rune_decrypter_prime.utils.runeglish import Runeglish
# from rune_decrypter_prime.tutorials.v1 import pretty
# from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext_english_string
# from rune_decrypter_prime.utils.seed_utils import make_seeds_from_freq
#
#
# def preview(s: str, n: int = 120) -> str:
#     return s if len(s) <= n else s[:n] + "…"
#
#
# def _invert_perm(pt_to_ct: np.ndarray) -> np.ndarray:
#     inv = np.empty_like(pt_to_ct)
#     inv[pt_to_ct] = np.arange(pt_to_ct.size, dtype=np.uint8)
#     return inv
#
#
# def _build_ciphertext(pt_en: str, *, direction: str = "rev", seed: int = 42) -> Tuple[str, list[tuple[int,int]], list[int], list[int]]:
#     """Encode English→runes, make a random key, encrypt, and return (ct_runes, wli, key_fwd, key_inv)."""
#     pt_idx, wli, _ = Runeglish.encode_english_to_runes(pt_en, direction=direction)
#     rng = np.random.default_rng(seed)
#     key_fwd = rng.permutation(29).astype(np.uint8)  # pt→ct
#     ciph = cipher_instance(by_name.cipher("mono"))
#     ct_idx = ciph.encrypt(plaintext=np.asarray(pt_idx, np.uint8), key=key_fwd)
#     ct_runes = Runeglish.to_rune(ct_idx.tolist(), wli)
#     key_inv = _invert_perm(key_fwd)                 # ct→pt (truth, not used by solver)
#     return ct_runes, wli, key_fwd.tolist(), key_inv.tolist()
#
#
# def main():
#     direction = "rev"
#
#     # 1) English → ciphertext
#     pt_en = plaintext_english_string
#     ct_runes, wli, _key_fwd, _key_inv = _build_ciphertext(pt_en, direction=direction, seed=42)
#
#     # 2) Seeds from ciphertext (comment out to start GA from noise)
#     seeds = make_seeds_from_freq(ct_runes, n_keys=120, swaps_per_key=2, seed=12345, direction=direction)
#
#     # # 3) GA config (kept small & readable)
#     # ga = SolveSpec.ga(
#     #     population=160,
#     #     generations=300,
#     #     stop_score=0.52,  # early success exit
#     #     params=dict(
#     #         initial_keys=seeds,     # ← remove to start from noise
#     #         elite_frac=0.06,
#     #         cx_frac=0.80,
#     #         mut_prob=0.30,
#     #         tournament_k=3,
#     #         # Common
#     #         log_interval=20,
#     #         verbose=True,
#     #         seed=1,
#     #     ),
#     # )
#
#     # 4) Run solver (CPU default for determinism)
#     ga = SolveSpec.ga(
#         population=160,
#         generations=300,
#         stop_score=0.52,  # can stay top-level now
#         verbose=True,
#         params=dict(
#             initial_keys=seeds,  # seeds flow reliably now
#             elite_frac=0.06,
#             cx_frac=0.80,
#             mut_prob=0.30,
#             tournament_k=3,
#             log_interval=20,
#             seed=12345,  # match the “good” run seed
#         ),
#     )
#     sol = run.solve(
#         text=ct_runes,
#         cipher=by_name.cipher("mono"),
#         key=KeySpec.permutation(len=29),
#         solve=ga,
#         device="cpu",
#         scorer="rune",
#         scorer_params=dict(
#             objective="pct.logp.win10",
#             char_weights={2: 0.3},
#             wli_weights={2: 0.7},
#             include_char=True,
#             use_word_breaks=True,
#             direction=direction,
#         ),
#         wli_data=wli,
#     )
#
#     # 5) Report
#     print("─" * 72)
#     print("Mono Substitution — GA")
#     print("Recovered plaintext:", preview(sol.plaintext))
#     print("Score:", round(sol.score, 6))
#
#     pretty.print_run_report(
#         title="mono-ga",
#         cipher="mono",
#         key_idx=None,
#         ct_idx=[Runeglish.rune_to_pos(c) for c in ct_runes],
#         ct_rune=ct_runes,
#         solution=sol,
#         match_ok=None,
#         app_version="tutorial-1.2",
#         key_len=None,
#         wli=wli,
#         pt_rune_ref=pt_en,
#         pt_idx_ref="",
#     )
#
# if __name__ == "__main__":
#     main()
#

"""
1) Build ciphertext by calling the cipher's own `encrypt(...)`.
2) Estimate rune unigrams from the real Language Model (LM).
3) Create seed keys by matching CT frequencies to LM unigrams.
4) Solve with GA using multi-order scoring (char + WLI, 2-grams & 3-grams).

Conventions
-----------
• We keep a single `encoding_dir` ("rev" or "fwd") and pass it everywhere:
  Runeglish encoding, LM unigram estimation, and scorer params.
• Keys:
  - Cipher `encrypt(...)` expects a pt→ct (forward) permutation of length 29.
  - The solver expects ct→pt (inverse) permutations; we only need the forward
    key for generating the tutorial ciphertext and for truth-printing.
• GA knobs (now aligned with GAOptimizer):
  - population / generations
  - elite_frac / cx_frac / mut_prob / tournament_k
  - log_interval for readable progress printing
"""

from __future__ import annotations
import math
from collections import Counter
from typing import Tuple, List

import numpy as np

from rune_decrypter_prime.ui.api import by_name, cipher_instance, KeySpec, SolveSpec, run
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.tutorials.v1 import pretty
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext_english_string
from rune_decrypter_prime.scoring.language_model.language_model_prime import LanguageModelPrime


# ---------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------

def preview(s: str, n: int = 120) -> str:
    """Return a string preview (truncate with ellipsis)."""
    return s if len(s) <= n else s[:n] + "…"


def invert_perm(pt_to_ct: np.ndarray) -> np.ndarray:
    """Return ct→pt inverse of a pt→ct permutation."""
    inv = np.empty_like(pt_to_ct)
    inv[pt_to_ct] = np.arange(pt_to_ct.size, dtype=np.uint8)
    return inv


# ---------------------------------------------------------------------
# Step 1 — Build ciphertext via the cipher API
# ---------------------------------------------------------------------

def build_ciphertext_api(
    pt_en: str,
    *,
    encoding_dir: str = "rev",
    seed: int = 42,
) -> Tuple[str, List[Tuple[int, int]], List[int], List[int]]:
    """
    Encode English → rune indices, then encrypt using the cipher's own API.

    Returns
    -------
    ct_runes : str
        Ciphertext as rune string with spaces preserved.
    wli : list[tuple[int,int]]
        Word/line index structure from Runeglish.
    key_fwd : list[int]
        pt→ct permutation (length 29).
    key_inv : list[int]
        ct→pt permutation (length 29).
    """
    pt_idx, wli, _pt_runes = Runeglish.encode_english_to_runes(pt_en, direction=encoding_dir)

    rng = np.random.default_rng(seed)
    key_fwd = rng.permutation(29).astype(np.uint8)

    ciph = cipher_instance(by_name.cipher("mono"))
    ct_idx = ciph.encrypt(plaintext=np.asarray(pt_idx, dtype=np.uint8), key=key_fwd)

    ct_runes = Runeglish.to_rune(ct_idx.tolist(), wli)
    key_inv = invert_perm(key_fwd)

    return ct_runes, wli, key_fwd.tolist(), key_inv.tolist()


# ---------------------------------------------------------------------
# Step 2 — LM unigram estimation
# ---------------------------------------------------------------------

def estimate_unigram_probs_from_lm(direction: str = "rev") -> List[float]:
    """Estimate rune unigram probabilities from the Language Model."""
    L = 64
    lm = LanguageModelPrime(lm_root=None, smoothing=None, oov_policy=None, include_char=True)
    pts = [[r] * L for r in range(29)]
    res = lm.score(pts, None, direction=direction, se="nose", n=1, model="char")
    raw = [math.exp(s.logprob_sum / L) for s in res]
    Z = sum(raw) or 1.0
    return [x / Z for x in raw]


# ---------------------------------------------------------------------
# Step 3 — Seed generation (CT freq vs LM unigram)
# ---------------------------------------------------------------------

def make_seed_keys_from_unigram(
    ct_idx: List[int],
    *,
    n_keys: int = 50,
    swaps_per_key: int = 3,
    seed: int | None = 12345,
    direction: str = "rev",
) -> List[List[int]]:
    """
    Create ct→pt candidate keys by aligning CT frequency with LM unigrams,
    then jitter with random swaps.
    """
    counts = Counter(ct_idx)
    ct_order = [sym for sym, _ in counts.most_common()] + [i for i in range(29) if i not in counts]

    probs = estimate_unigram_probs_from_lm(direction=direction)
    pt_order = list(np.argsort(-np.asarray(probs)))

    base = np.arange(29, dtype=np.int64)
    for ct_sym, pt_sym in zip(ct_order, pt_order):
        base[ct_sym] = int(pt_sym)

    rng = np.random.default_rng(seed)
    seeds: List[List[int]] = []
    for _ in range(n_keys):
        k = base.copy()
        for _ in range(max(1, swaps_per_key)):
            i, j = rng.integers(0, 29, size=2)
            if i != j:
                k[i], k[j] = k[j], k[i]
        seeds.append(k.astype(np.uint8).tolist())

    seeds[0] = base.astype(np.uint8).tolist()
    return seeds


# ---------------------------------------------------------------------
# Step 4 — Solve wrapper (GA)
# ---------------------------------------------------------------------
# ---------------------------------------------------------------------
# Step 4 — Solve wrapper (GA)
# ---------------------------------------------------------------------

def run_solver(ct_runes: str, wli, solver: SolveSpec, label: str, *, direction: str, log_interval: int = 50):
    """
    Run GA solver with periodic progress prints.

    Args:
      ct_runes     : Ciphertext rune string (with spaces).
      wli          : Word/line index structure from Runeglish.
      solver       : SolveSpec describing GA config.
      label        : Label to show in printed headers.
      direction    : 'rev' or 'fwd', passed to scorer/LM.
      log_interval : Print status every N generations (default=50).
    """
    cipher_spec = by_name.cipher("mono")           # spec for the solver path
    key_spec = KeySpec.permutation(len=29)

    # Seeds from CT + LM (ct→pt)
    ct_idx = [Runeglish.rune_to_pos(c) for c in ct_runes if c != " "]
    seeds = make_seed_keys_from_unigram(ct_idx, n_keys=100, swaps_per_key=3, seed=12345, direction=direction)

    # Attach log_interval to solver params if not already set
    if "params" not in solver.__dict__:
        solver.params = {}
    solver.params.setdefault("log_interval", log_interval)

    sol = run.solve(
        text=ct_runes,
        cipher=cipher_spec,
        key=key_spec,
        solve=solver,
        device="cpu",
        scorer="rune",
        scorer_params=dict(
            objective="pct.logp.win10",
            char_weights={2: 0.3},
            #char_weights={2: 0.3, 3: 0.7},
            wli_weights={2: 0.7 },
            #wli_weights={2: 0.5},
            include_char=True,
            use_word_breaks=True,
            direction=direction,  # keep LM direction consistent
        ),
        wli_data=wli,
        initial_keys=seeds,      # ct→pt candidates injected
    )

    print("─" * 72)
    print(f"Mono Substitution ({label})")
    print("Recovered plaintext:", preview(sol.plaintext))
    print("Score:", round(sol.score, 3))
    return sol

# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def key_similarity_ct_to_pt(guess: List[int], truth_ct_to_pt: List[int]) -> float:
    """Return % similarity between guessed ct→pt key and truth key."""
    if len(guess) != len(truth_ct_to_pt):
        raise ValueError("Keys must have same length")
    return sum(int(g == t) for g, t in zip(guess, truth_ct_to_pt)) / len(truth_ct_to_pt)


def main():
    encoding_dir = "rev"  # or "fwd"

    pt_en = plaintext_english_string
    ct_runes, wli, key_fwd, key_inv = build_ciphertext_api(pt_en, encoding_dir=encoding_dir, seed=42)

    ct_idx_for_preview = [Runeglish.rune_to_pos(c) for c in ct_runes if c != " "]
    initial_guesses = make_seed_keys_from_unigram(
        ct_idx_for_preview, n_keys=100, swaps_per_key=3, seed=12345, direction=encoding_dir
    )

    sim = key_similarity_ct_to_pt(initial_guesses[0], key_inv)
    print(f"Initial guess similarity to true key (ct→pt): {sim:.2%}")

    ga_solver = SolveSpec.ga(
        verbose = True,
        population=100,
        generations=200,
        params=dict(
            initial_keys=initial_guesses,
            mut_prob=0.30,
            tournament_k=3,
            elite_frac=0.05,
            cx_frac=0.70,
            log_interval=50,  # <-- new knob, readable printouts
        ),
    )

    sol = run_solver(ct_runes, wli, ga_solver, "GA", direction=encoding_dir)

    pretty.print_run_report(
        title="mono",
        cipher="mono",
        key_idx=None,
        ct_idx=[Runeglish.rune_to_pos(c) for c in ct_runes],
        ct_rune=ct_runes,
        solution=sol,
        match_ok=None,
        app_version="tutorial-1.0",
        key_len=None,
        wli=wli,
        pt_rune_ref=pt_en,
        pt_idx_ref="",
    )


if __name__ == "__main__":
    main()

#
# # """
# # Tutorial: Monoalphabetic substitution (29-rune alphabet).
# # =========================================================
# # 1) Build ciphertext by calling the cipher's own `encrypt(...)`.
# # 2) Estimate rune unigrams from the real Language Model (LM).
# # 3) Create seed keys by matching CT frequencies to LM unigrams.
# # 4) Solve with GA using multi-order scoring (char + WLI, 2-grams & 3-grams).
# #
# # Conventions
# # -----------
# # • We keep a single `encoding_dir` ("rev" or "fwd") and pass it everywhere:
# #   Runeglish encoding, LM unigram estimation, and scorer params.
# # • Keys:
# #   - Cipher `encrypt(...)` expects a pt→ct (forward) permutation of length 29.
# #   - The solver expects ct→pt (inverse) permutations; we only need the forward
# #     key for generating the tutorial ciphertext and for truth-printing.
# # """
# #
# # from __future__ import annotations
# # import math
# # from collections import Counter
# # from typing import Tuple, List
# #
# # import numpy as np
# #
# # from rune_decrypter_prime.ui.api import by_name, cipher_instance, KeySpec, SolveSpec, run
# # from rune_decrypter_prime.utils.runeglish import Runeglish
# # from rune_decrypter_prime.tutorials.v1 import pretty
# # from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext_english_string
# # from rune_decrypter_prime.scoring.language_model.language_model_prime import LanguageModelPrime
# #
# #
# # # ---------------------------------------------------------------------
# # # Utilities
# # # ---------------------------------------------------------------------
# #
# # def preview(s: str, n: int = 120) -> str:
# #     return s if len(s) <= n else s[:n] + "…"
# #
# #
# # def invert_perm(pt_to_ct: np.ndarray) -> np.ndarray:
# #     """Return ct→pt inverse of a pt→ct permutation."""
# #     inv = np.empty_like(pt_to_ct)
# #     inv[pt_to_ct] = np.arange(pt_to_ct.size, dtype=np.uint8)
# #     return inv
# #
# #
# # # ---------------------------------------------------------------------
# # # Step 1 — Build ciphertext via the cipher API
# # # ---------------------------------------------------------------------
# #
# # def build_ciphertext_api(
# #     pt_en: str,
# #     *,
# #     encoding_dir: str = "rev",
# #     seed: int = 42,
# # ) -> Tuple[str, List[Tuple[int, int]], List[int], List[int]]:
# #     """
# #     Encode English → rune indices, then encrypt using the cipher's own API.
# #
# #     Returns:
# #       ct_runes: rune string with spaces preserved
# #       wli:      word/line index structure from Runeglish
# #       key_fwd:  pt→ct permutation (length 29) as list[int]
# #       key_inv:  ct→pt permutation (length 29) as list[int]
# #     """
# #     # Encode to rune indices using the selected direction (keep this consistent!)
# #     pt_idx, wli, _pt_runes = Runeglish.encode_english_to_runes(pt_en, direction=encoding_dir)
# #
# #     # Deterministic random forward key (pt→ct)
# #     rng = np.random.default_rng(seed)
# #     key_fwd = rng.permutation(29).astype(np.uint8)
# #
# #     # Materialise a real cipher instance (spec → instance) and encrypt
# #     ciph = cipher_instance(by_name.cipher("mono"))
# #     ct_idx = ciph.encrypt(plaintext=np.asarray(pt_idx, dtype=np.uint8), key=key_fwd)
# #
# #     # Convert back to rune string (spaces preserved by wli)
# #     ct_runes = Runeglish.to_rune(ct_idx.tolist(), wli)
# #
# #     # Also compute the inverse (ct→pt) for truth/metrics
# #     key_inv = invert_perm(key_fwd)
# #
# #     return ct_runes, wli, key_fwd.tolist(), key_inv.tolist()
# #
# #
# # # ---------------------------------------------------------------------
# # # Step 2 — LM unigram estimation (matches tutorial direction)
# # # ---------------------------------------------------------------------
# #
# # def estimate_unigram_probs_from_lm(direction: str = "rev") -> List[float]:
# #     """
# #     Estimate rune 1-gram probabilities from the Language Model.
# #     Method: for each rune r, score [r]*L with n=1 (char model),
# #     convert mean logp → probability, then normalise.
# #     """
# #     L = 64
# #     lm = LanguageModelPrime(lm_root=None, smoothing=None, oov_policy=None, include_char=True)
# #     pts = [[r] * L for r in range(29)]
# #     res = lm.score(pts, None, direction=direction, se="nose", n=1, model="char")
# #     raw = [math.exp(s.logprob_sum / L) for s in res]
# #     Z = sum(raw) or 1.0
# #     return [x / Z for x in raw]
# #
# #
# # # ---------------------------------------------------------------------
# # # Step 3 — Seed generation from CT frequency vs LM unigram ranking
# # # ---------------------------------------------------------------------
# #
# # def make_seed_keys_from_unigram(
# #     ct_idx: List[int],
# #     *,
# #     n_keys: int = 50,
# #     swaps_per_key: int = 3,
# #     seed: int | None = 12345,
# #     direction: str = "rev",
# # ) -> List[List[int]]:
# #     """
# #     Create ct→pt candidate keys by aligning CT symbol frequency with LM unigrams,
# #     then jitter with a few random swaps per key.
# #     """
# #     # Ciphertext symbol frequencies
# #     counts = Counter(ct_idx)
# #     ct_order = [sym for sym, _ in counts.most_common()] + [i for i in range(29) if i not in counts]
# #
# #     # Language model 1-gram ranking (most probable first)
# #     probs = estimate_unigram_probs_from_lm(direction=direction)
# #     pt_order = list(np.argsort(-np.asarray(probs)))
# #
# #     # Base ct→pt key: highest-freq CT maps to most-probable PT
# #     base = np.arange(29, dtype=np.int64)
# #     for ct_sym, pt_sym in zip(ct_order, pt_order):
# #         base[ct_sym] = int(pt_sym)
# #
# #     # Jitter variants
# #     rng = np.random.default_rng(seed)
# #     seeds: List[List[int]] = []
# #     for _ in range(n_keys):
# #         k = base.copy()
# #         for _ in range(max(1, swaps_per_key)):
# #             i, j = rng.integers(0, 29, size=2)
# #             if i != j:
# #                 k[i], k[j] = k[j], k[i]
# #         seeds.append(k.astype(np.uint8).tolist())
# #
# #     # Ensure the pure base is included
# #     seeds[0] = base.astype(np.uint8).tolist()
# #     return seeds
# #
# #
# # # ---------------------------------------------------------------------
# # # Step 4 — Solve wrapper (GA)
# # # ---------------------------------------------------------------------
# #
# # def run_solver(ct_runes: str, wli, solver: SolveSpec, label: str, *, direction: str):
# #     cipher_spec = by_name.cipher("mono")           # spec for the solver path
# #     key_spec = KeySpec.permutation(len=29)
# #
# #     # Seeds from CT + LM (ct→pt)
# #     ct_idx = [Runeglish.rune_to_pos(c) for c in ct_runes if c != " "]
# #     seeds = make_seed_keys_from_unigram(ct_idx, n_keys=100, swaps_per_key=3, seed=12345, direction=direction)
# #
# #     sol = run.solve(
# #         text=ct_runes,
# #         cipher=cipher_spec,
# #         key=key_spec,
# #         solve=solver,
# #         device="cpu",
# #         scorer="rune",
# #         scorer_params=dict(
# #             objective="pct.logp.win10",
# #             char_weights={2: 0.3, 3: 0.7},
# #             wli_weights={2: 0.3, 3: 0.7},
# #             include_char=True,
# #             use_word_breaks=True,
# #             direction=direction,  # keep LM direction consistent
# #         ),
# #         wli_data=wli,
# #         initial_keys=seeds,      # ct→pt candidates injected
# #     )
# #
# #     print("─" * 72)
# #     print(f"Mono Substitution ({label})")
# #     print("Recovered plaintext:", preview(sol.plaintext))
# #     print("Score:", round(sol.score, 3))
# #     return sol
# #
# #
# # # ---------------------------------------------------------------------
# # # Main
# # # ---------------------------------------------------------------------
# #
# # def key_similarity_ct_to_pt(guess: List[int], truth_ct_to_pt: List[int]) -> float:
# #     if len(guess) != len(truth_ct_to_pt):
# #         raise ValueError("Keys must have same length")
# #     return sum(int(g == t) for g, t in zip(guess, truth_ct_to_pt)) / len(truth_ct_to_pt)
# #
# #
# # def main():
# #     # Pick one direction and stick to it throughout
# #     encoding_dir = "rev"  # or "fwd"
# #
# #     pt_en = plaintext_english_string
# #     ct_runes, wli, key_fwd, key_inv = build_ciphertext_api(pt_en, encoding_dir=encoding_dir, seed=42)
# #
# #     # Build seeds (also used in GA SolveSpec below for reproducibility print)
# #     ct_idx_for_preview = [Runeglish.rune_to_pos(c) for c in ct_runes if c != " "]
# #     initial_guesses = make_seed_keys_from_unigram(
# #         ct_idx_for_preview,
# #         n_keys=100,
# #         swaps_per_key=3,
# #         seed=12345,
# #         direction=encoding_dir,
# #     )
# #
# #     # Seed vs truth (ct→pt)
# #     sim = key_similarity_ct_to_pt(initial_guesses[0], key_inv)
# #     print(f"Initial guess similarity to true key (ct→pt): {sim:.2%}")
# #
# #     # GA solver (population/generations tuned for demo; adjust as needed)
# #     ga_solver = SolveSpec.ga(
# #         population=200,
# #         generations=1000,
# #         params={
# #             "initial_keys": initial_guesses,
# #             "mut_prob": 0.30,       # ensure mutation is on
# #             "tournament_k": 3,      # reasonable selection pressure
# #             "elite_frac": 0.05,
# #             "cx_frac": 0.70,
# #         },
# #     )
# #
# #     sol = run_solver(ct_runes, wli, ga_solver, "GA", direction=encoding_dir)
# #
# #     # Pretty report (keeps the tutorial UX nice)
# #     pretty.print_run_report(
# #         title="mono",
# #         cipher="mono",
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
