from __future__ import annotations

"""Benchmark-only seed utilities for periodic-columnar in the col_then_sub direction.

Why this exists
--------------
This module is *not* part of the canonical seed path yet. It lives under tools/benchmarks
so we can iterate on seeding strategies without changing the core library.

Focus
-----
col_then_sub pipelines usually do:
  1) periodic substitution first (phase-aware) using mainly unigram signal,
  2) then solve the columnar tail,
  3) then a full integrated refine.

This module provides a deterministic phase-aware seed pool for step (1), plus a small
helper to combine a substitution key with a tail permutation when needed.

Design rules
------------
- Deterministic by construction: no hidden entropy; all RNG comes from an explicit seed.
- Strict validation: bad inputs raise ValueError early.
- No optimiser logic: we only build candidate starts; Kaeding/keyops handle optimisation.
"""

from functools import lru_cache
from typing import List, Sequence

import numpy as np

from rune_decrypter_prime.scoring.language_model.language_model_prime import LanguageModelPrime


def _validate_rank_order(order: Sequence[int], *, A: int) -> list[int]:
    out = [int(x) for x in order]
    if len(out) != int(A):
        raise ValueError(f"pt_unigram_rank_override must have length {A}")
    if sorted(out) != list(range(int(A))):
        raise ValueError("pt_unigram_rank_override must be a permutation of [0..A-1]")
    return out


@lru_cache(maxsize=8)
def _lm_unigram_rank_cached(A: int, direction: str) -> tuple[int, ...]:
    """Cached plaintext unigram rank order (most likely first) using LMPrime."""
    # Estimate by scoring constant single-symbol strings.
    L = 64
    lm = LanguageModelPrime(
        lm_root=None, smoothing=None, alpha=0.5, oov_policy=None, include_char=True
    )
    pts = [[r] * L for r in range(int(A))]
    res = lm.score(pts, None, direction=direction, se="nose", n=1, model="char")
    raw = [float(np.exp(float(s.logprob_sum) / float(L))) for s in res]
    raw_arr = np.asarray(raw, dtype=np.float64)
    Z = float(raw_arr.sum()) or 1.0
    probs = raw_arr / Z
    # Stable sort: if tied, lower symbol id first.
    return tuple(int(x) for x in np.argsort(-probs, kind="stable").tolist())


def _lm_unigram_rank(*, A: int, direction: str) -> list[int]:
    """Return a plaintext unigram rank order (most likely first) using LMPrime."""
    d = str(direction).strip().lower()
    if d not in {"ltr", "rtl"}:
        raise ValueError("direction must be 'ltr' or 'rtl'")
    return list(_lm_unigram_rank_cached(int(A), d))


def _rank_align_perm_from_counts(
    counts: np.ndarray,
    *,
    pt_order: Sequence[int],
) -> np.ndarray:
    """Build a ct->pt permutation by aligning ciphertext count ranks to pt unigram rank."""
    A = int(counts.size)
    pt = _validate_rank_order(pt_order, A=A)
    # Ciphertext rank order (stable for ties).
    ct_order = np.argsort(-np.asarray(counts, dtype=np.float64), kind="stable").tolist()
    out = np.empty((A,), dtype=np.int64)
    for c_sym, p_sym in zip(ct_order, pt):
        out[int(c_sym)] = int(p_sym)
    return out.astype(np.uint8)


def _jitter_perm(
    perm: np.ndarray,
    *,
    swaps: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Random swap jitter (perm stays a valid permutation)."""
    A = int(perm.size)
    out = np.asarray(perm, dtype=np.uint8).copy()
    for _ in range(max(0, int(swaps))):
        i = int(rng.integers(0, A))
        j = int(rng.integers(0, A))
        if i == j:
            continue
        out[i], out[j] = out[j], out[i]
    return out


def make_periodic_seed_pool_col_then_sub(
    ct_idx: Sequence[int] | np.ndarray,
    *,
    period: int,
    direction: str,
    seed: int,
    n_block_seeds: int,
    total_seeds: int,
    swaps_per_block: int,
    alphabet_size: int = 29,
    pt_unigram_rank_override: Sequence[int] | None = None,
    global_shrink: float = 0.0,
    phase_len_target: int = 160,
) -> List[List[int]]:
    """Build a deterministic seed pool for *periodic_substitution* (K = period * A).

    This is a benchmark-only alternative to core seed builders.

    Parameters
    ----------
    ct_idx:
        Ciphertext indices (uint8-like), flattened. Spaces should already be removed.
    period:
        Period p (number of substitution blocks).
    direction:
        "ltr" or "rtl" (only used if pt_unigram_rank_override is None).
    seed:
        RNG seed (deterministic).
    n_block_seeds:
        Candidate permutations per phase (first is rank-aligned, rest are jittered).
    total_seeds:
        Total full keys to return (assembled by sampling one phase-candidate per phase).
    swaps_per_block:
        Swap depth when jittering each phase permutation.
    alphabet_size:
        Rune alphabet size (default 29).
    pt_unigram_rank_override:
        Optional explicit pt unigram rank order (perm of 0..A-1). If provided, no LM load.
    global_shrink:
        Strength (0..1) for shrinking short phase histograms toward the global histogram.
        Effective per-phase shrinkage is scaled by (1 - phase_len/phase_len_target), clipped.
    phase_len_target:
        Phase length at which shrinkage is turned off (roughly, “enough samples per phase”).

    Returns
    -------
    List[List[int]]
        Flattened ct->pt keys, each length period*A, block-major.
    """
    p = int(period)
    A = int(alphabet_size)
    if p <= 0:
        raise ValueError("period must be >= 1")
    if A <= 0:
        raise ValueError("alphabet_size must be >= 1")
    if int(total_seeds) <= 0:
        return []
    if int(n_block_seeds) <= 0:
        raise ValueError("n_block_seeds must be >= 1")
    if not (0.0 <= float(global_shrink) <= 1.0):
        raise ValueError("global_shrink must be in [0,1]")
    if int(phase_len_target) <= 0:
        raise ValueError("phase_len_target must be >= 1")

    ct = np.asarray(ct_idx, dtype=np.uint8).reshape(-1)
    rng = np.random.default_rng(int(seed))

    if pt_unigram_rank_override is None:
        pt_order = _lm_unigram_rank(A=A, direction=direction)
    else:
        pt_order = _validate_rank_order(pt_unigram_rank_override, A=A)

    # Global histogram (for shrinkage).
    global_counts = np.bincount(ct.astype(np.int64), minlength=A).astype(np.float64)

    # Build per-phase candidate blocks.
    blocks_per_phase: List[List[List[int]]] = []
    for r in range(p):
        phase = ct[r::p]
        phase_counts = np.bincount(phase.astype(np.int64), minlength=A).astype(np.float64)

        w = 0.0
        if float(global_shrink) > 0.0:
            phase_len = int(phase.size)
            # More shrinkage if the phase is short.
            shortness = 1.0 - min(1.0, float(phase_len) / float(phase_len_target))
            w = float(global_shrink) * float(max(0.0, shortness))
        counts = (1.0 - w) * phase_counts + w * global_counts

        base = _rank_align_perm_from_counts(counts, pt_order=pt_order)
        phase_rng = np.random.default_rng(int(seed) + 1009 * int(r))
        seeds: List[List[int]] = [base.tolist()]
        for _ in range(max(0, int(n_block_seeds) - 1)):
            jittered = _jitter_perm(base, swaps=int(swaps_per_block), rng=phase_rng)
            seeds.append(jittered.tolist())
        # De-dup per-phase seeds while preserving deterministic order.
        seen_phase: set[tuple[int, ...]] = set()
        uniq_phase: List[List[int]] = []
        for s in seeds:
            st = tuple(int(x) for x in s)
            if st in seen_phase:
                continue
            seen_phase.add(st)
            uniq_phase.append(s)
        blocks_per_phase.append(uniq_phase)

    def _concat(blocks: List[List[int]]) -> List[int]:
        out: List[int] = []
        for b in blocks:
            out.extend(b)
        return out

    keys: List[List[int]] = []
    seen_full: set[tuple[int, ...]] = set()

    def _push_full(candidate: List[int]) -> bool:
        ctup = tuple(int(x) for x in candidate)
        if ctup in seen_full:
            return False
        seen_full.add(ctup)
        keys.append(candidate)
        return True

    target = max(1, int(total_seeds))
    # Base key: take the base block from each phase.
    _push_full(_concat([seeds[0] for seeds in blocks_per_phase]))

    # Sample random combinations first (deterministic RNG stream).
    attempts = 0
    max_attempts = max(1024, target * 16)
    while (len(keys) < target) and (attempts < max_attempts):
        pick = [
            phase_seeds[int(rng.integers(0, len(phase_seeds)))]
            for phase_seeds in blocks_per_phase
        ]
        _push_full(_concat(pick))
        attempts += 1

    # Deterministic fallback to fill remaining unique keys, if available.
    if len(keys) < target:
        radices = [len(phase_seeds) for phase_seeds in blocks_per_phase]
        idx = [0] * len(radices)
        wrapped = False
        while (len(keys) < target) and (not wrapped):
            pick = [blocks_per_phase[r][idx[r]] for r in range(len(radices))]
            _push_full(_concat(pick))
            for r in range(len(radices) - 1, -1, -1):
                idx[r] += 1
                if idx[r] < radices[r]:
                    break
                idx[r] = 0
                if r == 0:
                    wrapped = True
    return keys


def make_tail_seed_pool(
    *,
    columns: int,
    seed: int,
    total_seeds: int = 256,
    structured_swaps: int = 96,
    random_seeds: int = 128,
    max_exact_columns: int = 7,
) -> list[list[int]]:
    """Deterministic candidate pool for the columnar tail permutation.

    Intended use (benchmark only)
    -----------------------------
    For columns > 7, exact enumeration is not feasible. This helper returns a small,
    structured set of permutations plus a deterministic random tail to seed the hybrid
    solver (beam/GA/SA).

    Design rules
    ------------
    - Deterministic: depends only on (columns, seed, knobs).
    - Valid permutations only.
    - Low bloat: one simple neighbourhood + random fill, with de-duplication.

    Returns
    -------
    List of permutation keys (each length == columns).
    """
    if int(columns) < 1:
        raise ValueError("columns must be >= 1")
    columns = int(columns)
    rng = np.random.default_rng(int(seed))

    def _as_key(arr: np.ndarray) -> tuple[int, ...]:
        return tuple(int(x) for x in arr.tolist())

    # Exact enumeration for tiny columns (keeps behaviour aligned with other helpers).
    if columns <= int(max_exact_columns):
        import itertools
        out = [list(map(int, p)) for p in itertools.permutations(range(columns))]
        # Deterministic order, already exhaustive.
        return out

    seen: set[tuple[int, ...]] = set()
    out: list[list[int]] = []

    def _push(arr: np.ndarray) -> None:
        key = _as_key(arr)
        if key in seen:
            return
        seen.add(key)
        out.append([int(x) for x in arr.tolist()])

    # 1) Identity
    base = np.arange(columns, dtype=np.int16)
    _push(base)

    # 2) Adjacent swaps (very cheap local neighbourhood)
    for i in range(columns - 1):
        a = base.copy()
        a[i], a[i + 1] = a[i + 1], a[i]
        _push(a)

    # 3) A few deterministic long swaps (spread out)
    for i in range(0, columns, max(1, columns // 4)):
        j = (i + (columns // 2)) % columns
        if i == j:
            continue
        a = base.copy()
        a[i], a[j] = a[j], a[i]
        _push(a)

    # 4) Small block rotations (captures “mis-blocked” tails better than pure swaps)
    # Rotate windows of size 3 and 4 at a few positions.
    for w in (3, 4):
        if columns < w:
            continue
        step = max(1, columns // 5)
        for start in range(0, columns - w + 1, step):
            a = base.copy()
            window = a[start : start + w].copy()
            # left rotate by 1
            window = np.roll(window, -1)
            a[start : start + w] = window
            _push(a)

    # 5) Structured random swaps from identity (deterministic stream)
    # These are “nearby” permutations that give beam/GA a head start.
    n_struct = max(0, int(structured_swaps))
    for _ in range(n_struct):
        a = base.copy()
        i = int(rng.integers(0, columns))
        j = int(rng.integers(0, columns))
        if i == j:
            j = (j + 1) % columns
        a[i], a[j] = a[j], a[i]
        _push(a)

    # 6) Fully random permutations (diversity)
    n_rand = max(0, int(random_seeds))
    for _ in range(n_rand):
        a = base.copy()
        rng.shuffle(a)
        _push(a)

    # Cap / pad deterministically to total_seeds
    target = max(1, int(total_seeds))
    if len(out) > target:
        out = out[:target]
    while len(out) < target:
        a = base.copy()
        rng.shuffle(a)
        _push(a)

    return out

def combine_periodic_sub_key_with_tail(
    sub_key: Sequence[int] | np.ndarray,
    *,
    tail_perm: Sequence[int] | np.ndarray,
    period: int,
    alphabet_size: int = 29,
    columns: int | None = None,
) -> List[int]:
    """Combine a periodic-substitution key (period*A) with a column tail permutation.

    This helper is useful when you want to lift a Stage-1 substitution key into a full
    periodic-columnar key candidate for later stages.
    """
    p = int(period)
    A = int(alphabet_size)
    sub = np.asarray(sub_key, dtype=np.int64).reshape(-1)
    if sub.size != p * A:
        raise ValueError(f"sub_key must have length {p*A}")
    tail = np.asarray(tail_perm, dtype=np.int64).reshape(-1)
    c = int(tail.size)
    if columns is not None and int(columns) != c:
        raise ValueError("columns does not match tail_perm length")
    if c <= 0:
        raise ValueError("tail_perm must be non-empty")
    if np.unique(tail).size != c or int(tail.min()) != 0 or int(tail.max()) != c - 1:
        raise ValueError("tail_perm must be a permutation of [0..columns-1]")
    full = np.concatenate([sub.astype(np.int64), tail.astype(np.int64)], axis=0)
    return [int(x) for x in full.tolist()]
