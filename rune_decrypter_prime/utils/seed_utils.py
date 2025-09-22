# -*- coding: utf-8 -*-
# ============================================================
# rune_decrypter_prime/utils/seed_utils.py
# Seed builders for mono-substitution (rank alignment + jitter).
# Behaviour unchanged; pure NumPy + LanguageModelPrime unigram probe.
# ============================================================

from __future__ import annotations
from typing import Iterable, List, Sequence, Tuple, Union, Optional
from collections import Counter
import math
import numpy as np

from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.scoring.language_model.language_model_prime import LanguageModelPrime

CiphertextLike = Union[str, Sequence[int], np.ndarray]


def _to_ct_indices(ct: CiphertextLike) -> List[int]:
    """Convert ciphertext to a flat list of rune indices (spaces ignored)."""
    if isinstance(ct, str):
        return [Runeglish.rune_to_pos(c) for c in ct if c != " "]
    arr = np.asarray(ct).astype(int).ravel().tolist()
    return [int(x) for x in arr]


def _lm_unigram_probs(A: int = 29, direction: str = "rev") -> List[float]:
    """Estimate rune 1-gram probabilities via LanguageModelPrime; normalised."""
    L = 64
    lm = LanguageModelPrime(lm_root=None, smoothing=None, oov_policy=None, include_char=True)
    pts = [[r] * L for r in range(A)]
    res = lm.score(pts, None, direction=direction, se="nose", n=1, model="char")
    raw = [math.exp(s.logprob_sum / L) for s in res]
    Z = sum(raw) or 1.0
    return [x / Z for x in raw]


def _normalize_perm(key: np.ndarray, A: int) -> np.ndarray:
    """
    Make a best-effort valid permutation (0..A-1). If duplicates exist,
    fill missing symbols in order. (Simple belt-and-braces repair.)
    """
    k = np.asarray(key, dtype=np.int64).copy()
    k %= A
    mask = np.ones(A, dtype=bool)
    out = np.full(A, -1, dtype=np.int64)
    # First pass: keep first occurrence
    for i, v in enumerate(k):
        if 0 <= v < A and mask[v]:
            out[i] = int(v)
            mask[v] = False
    # Fill remaining
    missing = np.nonzero(mask)[0].tolist()
    j = 0
    for i in range(A):
        if out[i] < 0:
            out[i] = int(missing[j]); j += 1
    return out.astype(np.uint8)


def rank_alignment_seed(ct: CiphertextLike, *, A: int = 29, direction: str = "rev") -> List[int]:
    """
    Build a single ct→pt permutation seed by aligning ciphertext
    frequency ranks to language-model unigram ranks.
    """
    ct_idx = Runeglish.rune_to_pos(ct)
    counts = Counter(ct_idx)
    ct_order = [s for s, _ in counts.most_common()] + [i for i in range(A) if i not in counts]
    probs = _lm_unigram_probs(A=A, direction=direction)
    pt_order = list(np.argsort(-np.asarray(probs)))
    base = np.arange(A, dtype=np.int64)
    for c_sym, p_sym in zip(ct_order, pt_order):
        base[c_sym] = int(p_sym)
    return _normalize_perm(base, A).tolist()


def mutate_seed_once(seed_key: Sequence[int], *, swaps: int = 1, rng: Optional[np.random.Generator] = None) -> List[int]:
    """Randomly swap a few positions in the permutation (simple jitter)."""
    rng = rng or np.random.default_rng()
    A = int(len(seed_key))
    out = np.asarray(seed_key, dtype=np.int64).copy()
    for _ in range(max(1, int(swaps))):
        i, j = int(rng.integers(0, A)), int(rng.integers(0, A))
        if i != j:
            out[i], out[j] = out[j], out[i]
    return _normalize_perm(out, A).tolist()


def make_seeds_from_freq(
    ct: CiphertextLike,
    *,
    n_keys: int = 100,
    swaps_per_key: int = 2,
    seed: int = 12345,
    A: int = 29,
    direction: str = "rev",
) -> List[List[int]]:
    """
    Return a small pool of ct→pt trial keys:
      - seed[0] is the pure rank-alignment key.
      - the rest are jittered versions (random swaps).
    """
    base = rank_alignment_seed(ct, A=A, direction=direction)
    rng = np.random.default_rng(seed)
    out = [base]
    for _ in range(max(0, n_keys - 1)):
        out.append(mutate_seed_once(base, swaps=swaps_per_key, rng=rng))
    return out

# TODO: Confirm that constructing LanguageModelPrime without lm_root is stable
#       across environments (no hidden disk I/O); if not, document/test the contract.
