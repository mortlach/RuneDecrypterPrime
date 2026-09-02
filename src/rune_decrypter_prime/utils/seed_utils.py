# -*- coding: utf-8 -*-
# ============================================================
# rune_decrypter_prime/utils/seed_utils.py
# Seed builders for mono-substitution (rank alignment + jitter).
# Behaviour unchanged; pure NumPy + LanguageModelPrime unigram probe.
# ============================================================
from __future__ import annotations

from typing import Callable, List, Sequence, Union, Optional
from collections import Counter
import math
import numpy as np
import itertools

from rdp.core.types import Direction, TextDirection, ensure_direction
from rune_decrypter_prime.keyops.permutation_ops import PermutationKeyOps
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.scoring.language_model.language_model_prime import LanguageModelPrime
from rune_decrypter_prime.keyops.periodic_structured_matrix_ops import PeriodicStructuredMatrixKeyOps

CiphertextLike = Union[str, Sequence[int], np.ndarray]


def _to_ct_indices(ct: CiphertextLike) -> List[int]:
    """Convert ciphertext to a flat list of rune indices (spaces ignored)."""
    if isinstance(ct, str):
        return [Runeglish.rune_to_pos(c) for c in ct if c != " "]
    arr = np.asarray(ct).astype(int).ravel().tolist()
    return [int(x) for x in arr]


def _lm_unigram_probs(
    A: int = 29,
    direction: Direction | TextDirection | str = Direction.RTL,
) -> List[float]:
    """Estimate rune 1-gram probabilities via LanguageModelPrime; normalised."""
    lm_direction = ensure_direction(direction).value
    L = 64
    lm = LanguageModelPrime(lm_root=None, smoothing=None, oov_policy=None, include_char=True)
    pts = [[r] * L for r in range(A)]
    res = lm.score(pts, None, direction=lm_direction, se="nose", n=1, model="char")
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


def rank_alignment_seed(
    ct: CiphertextLike,
    *,
    A: int = 29,
    direction: Direction | TextDirection | str = Direction.RTL,
) -> List[int]:
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
    """Randomly swap a few positions in the permutation (simple jitter).

    Requires an injected RNG so callers remain deterministic by design.
    """
    if rng is None:
        raise ValueError("mutate_seed_once requires an injected RNG (no entropy fallback).")
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
    direction: Direction | TextDirection | str = Direction.RTL,
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


def make_periodic_structured_key(
    *,
    period: int,
    alphabet_size: int = 29,
    seed: int,
) -> List[int]:
    """
    Generate a deterministic periodic-structured key (period blocks of size A).

    Notes:
    - Uses PeriodicStructuredMatrixKeyOps to honour the cipher-family contract.
    - Deterministic: all randomness is sourced from the provided seed.
    """
    if int(period) <= 0:
        raise ValueError("period must be >= 1")
    if int(alphabet_size) <= 0:
        raise ValueError("alphabet_size must be >= 1")
    rng = np.random.default_rng(seed)
    keyops = PeriodicStructuredMatrixKeyOps(
        K=int(period) * int(alphabet_size),
        period=int(period),
        A=int(alphabet_size),
    )
    return keyops.random(rng).tolist()


def make_periodic_seed_pool(
    ct_idx: Sequence[int] | np.ndarray,
    *,
    period: int,
    direction: Direction | TextDirection | str,
    seed: int,
    n_block_seeds: int,
    total_seeds: int,
    swaps_per_block: int,
    alphabet_size: int = 29,
) -> List[List[int]]:
    """
    Build a deterministic periodic seed pool by seeding each phase separately.

    Notes:
    - `direction` is normalised to the engine's typed encoding direction.
    - Returns a list of flattened keys, one per seed candidate.
    - Deterministic: all randomness is sourced from the provided seed.
    """
    if int(period) <= 0:
        raise ValueError("period must be >= 1")
    if int(alphabet_size) <= 0:
        raise ValueError("alphabet_size must be >= 1")
    if total_seeds <= 0:
        return []
    ct_arr = np.asarray(ct_idx, dtype=np.uint8).reshape(-1)
    rng = np.random.default_rng(seed)
    block_seeds: List[List[List[int]]] = []
    for r in range(int(period)):
        phase_idx = ct_arr[r::int(period)]
        phase_runes = Runeglish.to_rune(phase_idx.tolist(), wli=None)
        seeds = make_seeds_from_freq(
            phase_runes,
            n_keys=int(n_block_seeds),
            swaps_per_key=int(swaps_per_block),
            seed=int(seed) + r,
            A=int(alphabet_size),
            direction=direction,
        )
        block_seeds.append(seeds)

    def _concat(blocks: List[List[int]]) -> List[int]:
        out: List[int] = []
        for block in blocks:
            out.extend(block)
        return out

    keys: List[List[int]] = []
    base = _concat([seeds[0] for seeds in block_seeds])
    keys.append(base)
    for _ in range(max(0, int(total_seeds) - 1)):
        pick = [_s[int(rng.integers(0, len(_s)))] for _s in block_seeds]
        keys.append(_concat(pick))
    return keys



def make_true_periodic_columnar_key(
    *,
    rng: np.random.Generator,
    period: int,
    alphabet_size: int = 29,
    columns: int = 13,
) -> np.ndarray:
    """
    Return a *flat* uint8 key of length (period * alphabet_size + columns)
    that PeriodicColumnarCipher.encrypt_single(...) accepts directly.

    Layout (flat):
      - First period*alphabet_size entries: periodic substitution blocks (each a permutation of 0..A-1)
      - Last columns entries: column permutation (a permutation of 0..columns-1)
    """
    period = int(period)
    alphabet_size = int(alphabet_size)
    columns = int(columns)

    if period <= 0:
        raise ValueError("period must be >= 1")
    if alphabet_size <= 0:
        raise ValueError("alphabet_size must be >= 1")
    if columns <= 0:
        raise ValueError("columns must be >= 1")

    keyops = PeriodicStructuredMatrixKeyOps(
        K=period * alphabet_size + columns,
        period=period,
        A=alphabet_size,
        columns=columns,
    )
    return keyops.random(rng)

def make_periodic_columnar_seed_pool(
    ciphertext_idx: np.ndarray,
    *,
    period: int,
    alphabet_size: int = 29,
    columns: int = 13,
    direction: Direction | TextDirection | str = Direction.RTL,
    seed: int = 12345,
    n_keys: int = 48,
    # substitution block seeding
    n_block_seeds: int = 8,
    swaps_per_block: int = 2,
    # tail (column permutation) seeding
    n_tail_seeds: int = 8,
    tail_swaps: int = 2,
    # how to interpret ciphertext for block seeding
    order: str = "col_then_sub",
    # optional tail sweep (requires a scoring callback)
    tail_sweep_score_fn: Optional[Callable[[Sequence[int]], float]] = None,
    tail_sweep_top_k: int = 16,
    tail_sweep_block_samples: int = 1,
    # optional score-guided refinement of substitution blocks (uses score_fn on full key)
    block_refine_score_fn: Optional[Callable[[Sequence[int]], float]] = None,
    block_refine_steps: int = 256,
    block_refine_swaps: int = 1,
    block_refine_tail_top_k: int = 1,
) -> list[list[int]]:
    """
    Build a seed pool for the integrated periodic-columnar key (flat list[int]).

    IMPORTANT ABOUT `order`:
      - If order == "col_then_sub": ciphertext preserves periodic structure, so we can seed each phase
        using ct_idx[r::period] (recommended for the “simple” tutorial).
      - If order == "sub_then_col": ciphertext is columnar-scrambled; we fall back to a weaker global
        seeding scheme (still returns valid keys, just less informed).

    If `tail_sweep_score_fn` is provided, we brute-force all column permutations
    and keep the top-K tails by score. When `tail_sweep_block_samples` > 1,
    we repeat the sweep for multiple base block combinations and keep the
    best-scoring block choice per tail (deterministic).

    Optional block refinement:
      If a score callback is available (either `block_refine_score_fn` or `tail_sweep_score_fn`)
      and `block_refine_steps > 0`, we do a small deterministic hill-climb that swaps symbols
      *within* periodic blocks (ct→pt permutations), accepting only improvements. This targets
      the failure mode where frequency-rank seeds are valid but too weak to bootstrap the solver.
    """
    period = int(period)
    alphabet_size = int(alphabet_size)
    columns = int(columns)
    n_keys = int(n_keys)
    n_block_seeds = int(n_block_seeds)
    swaps_per_block = int(swaps_per_block)
    n_tail_seeds = int(n_tail_seeds)
    tail_swaps = int(tail_swaps)
    tail_sweep_top_k = int(tail_sweep_top_k)
    tail_sweep_block_samples = int(tail_sweep_block_samples)

    block_refine_steps = int(block_refine_steps)
    block_refine_swaps = int(block_refine_swaps)
    block_refine_tail_top_k = int(block_refine_tail_top_k)

    if period <= 0:
        raise ValueError("period must be >= 1")
    if alphabet_size <= 0:
        raise ValueError("alphabet_size must be >= 1")
    if columns <= 0:
        raise ValueError("columns must be >= 1")
    if n_keys <= 0:
        return []

    engine_direction = ensure_direction(direction)

    ct = np.asarray(ciphertext_idx, dtype=np.uint8).reshape(-1)
    rng = np.random.default_rng(int(seed))

    # -----------------------
    # 1) substitution seeds
    # -----------------------
    block_seeds: list[list[list[int]]] = []

    if order == "col_then_sub":
        # Strong seeding: each periodic phase is intact in ciphertext
        for r in range(period):
            phase_idx = ct[r::period]
            phase_runes = Runeglish.to_rune(phase_idx.tolist(), wli=None)
            seeds_r = make_seeds_from_freq(
                phase_runes,
                n_keys=n_block_seeds,
                swaps_per_key=swaps_per_block,
                seed=int(seed) + r,
                A=alphabet_size,
                direction=engine_direction,
            )
            block_seeds.append(seeds_r)
    else:
        # Fallback: global (weaker) seeding repeated for each block
        all_runes = Runeglish.to_rune(ct.tolist(), wli=None)
        global_seeds = make_seeds_from_freq(
            all_runes,
            n_keys=n_block_seeds,
            swaps_per_key=swaps_per_block,
            seed=int(seed),
            A=alphabet_size,
            direction=engine_direction,
        )
        for _ in range(period):
            block_seeds.append(global_seeds)

    def _concat_blocks(blocks: Sequence[Sequence[int]]) -> list[int]:
        out: list[int] = []
        for b in blocks:
            out.extend(int(x) for x in b)
        return out

    # -----------------------
    # 2) tail (column perm) seeds
    # -----------------------
    tail_seeds: list[list[int]] = []
    tail_best_blocks: dict[tuple[int, ...], int] = {}
    base_subs: list[list[int]] = []
    tail_ranked: list[tuple[float, tuple[int, ...], int]] = []

    if tail_sweep_score_fn is not None:
        if tail_sweep_top_k <= 0:
            raise ValueError("tail_sweep_top_k must be >= 1 when tail_sweep_score_fn is provided")
        if tail_sweep_block_samples <= 0:
            raise ValueError("tail_sweep_block_samples must be >= 1 when tail_sweep_score_fn is provided")

        base_blocks_list: list[list[list[int]]] = []
        base_blocks_list.append([seeds_r[0] for seeds_r in block_seeds])
        for _ in range(max(0, tail_sweep_block_samples - 1)):
            pick = [seeds_r[int(rng.integers(0, len(seeds_r)))] for seeds_r in block_seeds]
            base_blocks_list.append(pick)

        base_subs = [_concat_blocks(blocks) for blocks in base_blocks_list]
        tail_best: dict[tuple[int, ...], tuple[float, int]] = {}

        for base_idx, base_sub in enumerate(base_subs):
            for tail in itertools.permutations(range(columns)):
                tail_key = tuple(tail)
                full_key = base_sub + list(tail_key)
                score = float(tail_sweep_score_fn(full_key))
                prev = tail_best.get(tail_key)
                if prev is None or score > prev[0]:
                    tail_best[tail_key] = (score, base_idx)

        tail_ranked = sorted(
            ((score, tail, base_idx) for tail, (score, base_idx) in tail_best.items()),
            key=lambda x: (x[0], x[1]),
            reverse=True,
        )
        tail_seeds = [list(tail) for _, tail, _ in tail_ranked[:tail_sweep_top_k]]
        tail_best_blocks = {tuple(tail): base_idx for _, tail, base_idx in tail_ranked}
    else:
        tail_best_blocks = {}

    if not tail_seeds:
        perm_ops = PermutationKeyOps(K=columns)
        identity = list(range(columns))
        tail_seeds.append(identity)

        for _ in range(max(0, n_tail_seeds - 1)):
            base = np.asarray(identity, dtype=np.uint8)
            if columns > 1 and tail_swaps > 0:
                cand = perm_ops.mutate_k_swaps(base, rng, k=tail_swaps)
            else:
                cand = base.copy()
            if columns > 2 and rng.random() < 0.35:
                cand = perm_ops.random(rng)
            tail_seeds.append([int(x) for x in np.asarray(cand).reshape(-1).tolist()])

    # -----------------------
    # 2b) optional block refinement (score-guided)
    # -----------------------
    score_fn = block_refine_score_fn or tail_sweep_score_fn
    refined_sub: Optional[list[int]] = None
    refined_tail: Optional[list[int]] = None
    refined_score: float = float("-inf")

    if (
        score_fn is not None
        and block_refine_steps > 0
        and block_refine_swaps > 0
        and order == "col_then_sub"
        and columns >= 1
        and alphabet_size >= 2
    ):
        if tail_ranked:
            candidates = [
                (list(tail), base_idx)
                for _, tail, base_idx in tail_ranked[: max(1, block_refine_tail_top_k)]
            ]
        else:
            candidates = [
                (tail, None)
                for tail in tail_seeds[: max(1, min(block_refine_tail_top_k, len(tail_seeds)))]
            ]

        base_sub_default = _concat_blocks([seeds_r[0] for seeds_r in block_seeds])
        sub_len = period * alphabet_size

        def _score_full(sub_part: list[int], tail_part: list[int]) -> float:
            return float(score_fn(sub_part + tail_part))

        for tail_part, base_idx in candidates:
            if base_idx is not None and 0 <= int(base_idx) < len(base_subs):
                sub_part = list(base_subs[int(base_idx)])
            else:
                sub_part = list(base_sub_default)

            best_s = _score_full(sub_part, tail_part)
            best_sub = np.asarray(sub_part, dtype=np.uint8).copy()

            for _ in range(block_refine_steps):
                cand = best_sub.copy()
                for _j in range(block_refine_swaps):
                    r = int(rng.integers(0, period))
                    i = int(rng.integers(0, alphabet_size))
                    j = int(rng.integers(0, alphabet_size - 1))
                    if j >= i:
                        j += 1
                    a = r * alphabet_size + i
                    b = r * alphabet_size + j
                    cand[a], cand[b] = cand[b], cand[a]

                s = _score_full(cand.tolist(), tail_part)
                if s > best_s:
                    best_s = s
                    best_sub = cand

            if best_s > refined_score:
                refined_score = best_s
                refined_sub = best_sub.astype(np.uint8, copy=False).tolist()[:sub_len]
                refined_tail = list(tail_part)

    # -----------------------
    # 3) combine into full keys
    # -----------------------
    keys: list[list[int]] = []

    def _append_key(k: list[int]) -> None:
        if len(keys) < n_keys:
            keys.append([int(x) for x in k])

    base_sub = _concat_blocks([seeds_r[0] for seeds_r in block_seeds])

    # Prefer refined key(s) first, if available
    if refined_sub is not None and refined_tail is not None:
        _append_key(refined_sub + refined_tail)
        for tail in tail_seeds:
            if len(keys) >= n_keys:
                break
            _append_key(refined_sub + list(tail))

    # Original behaviour: base blocks + each tail seed (or best base blocks per tail from sweep)
    for tail in tail_seeds:
        if len(keys) >= n_keys:
            break
        base_idx = tail_best_blocks.get(tuple(tail))
        if base_idx is None:
            _append_key(base_sub + tail)
        else:
            _append_key(base_subs[base_idx] + tail)

    # Remaining keys: mix-and-match across blocks + tails
    while len(keys) < n_keys:
        picked_blocks = [seeds_r[int(rng.integers(0, len(seeds_r)))] for seeds_r in block_seeds]
        sub = _concat_blocks(picked_blocks)
        tail = tail_seeds[int(rng.integers(0, len(tail_seeds)))]
        _append_key(sub + tail)

    expected_len = period * alphabet_size + columns
    for k in keys:
        if len(k) != expected_len:
            raise RuntimeError(f"Seed key has length {len(k)} but expected {expected_len}")

    return keys


def make_periodic_columnar_seed_pool_lmprime_sa(
    ciphertext_idx: np.ndarray,
    *,
    period: int,
    alphabet_size: int = 29,
    columns: int = 13,
    seed: int = 12345,
    n_keys: int = 48,
    order: str = "col_then_sub",
    # you MUST pass a fast scorer that reuses LMPrime / scorers (no rebuilding per call)
    score_key_fn: Callable[[Sequence[int]], float],
    # search budget (kept modest for tests; raise for real solves)
    n_starts: int = 6,
    rounds: int = 3,
    tail_steps: int = 20,
    block_steps: int = 30,
    start_temp: float = 0.35,
    end_temp: float = 0.05,
    # move behaviour
    swaps_per_move: int = 1,
    block_top_k: int = 12,
    # initial pool diversity
    n_block_jitter: int = 6,
    n_tail_seeds: int = 10,
    tail_jitter_swaps: int = 2,
) -> list[list[int]]:
    """
    Deterministic seed pool for PeriodicColumnar (flat key = period*A block entries + columns tail).

    This is intentionally "bespoke and clean":
      - Requires a fast score_key_fn (do NOT call score_plaintext inside it).
      - Uses coordinate SA: optimise tail, then optimise blocks, repeat.
      - Uses LMPrime-guided scoring via the callback you provide.

    NOTE: For now, we enforce order == "col_then_sub" to avoid silently doing nonsense.
          If you want sub_then_col support, do it explicitly as a separate design.
    """
    period = int(period)
    A = int(alphabet_size)
    C = int(columns)
    n_keys = int(n_keys)

    if n_keys <= 0:
        return []
    if period <= 0:
        raise ValueError("period must be >= 1")
    if A <= 1:
        raise ValueError("alphabet_size must be >= 2")
    if C <= 0:
        raise ValueError("columns must be >= 1")
    if order != "col_then_sub":
        raise ValueError(
            "make_periodic_columnar_seed_pool_lmprime_sa currently requires order='col_then_sub' "
            "(explicit by design; no silent weak fallback)."
        )

    ct = np.asarray(ciphertext_idx, dtype=np.uint8).reshape(-1)
    rng = np.random.default_rng(int(seed))

    sub_len = period * A
    key_len = sub_len + C

    # ------------------------------------------------------------
    # Phase statistics (for guided block swaps)
    # ------------------------------------------------------------
    phase_ct = [ct[r::period].astype(np.uint8, copy=False) for r in range(period)]
    phase_counts = [np.bincount(p.astype(np.int64), minlength=A) for p in phase_ct]

    # Build a stable "top symbols" list per phase (deterministic tie-breaking).
    phase_top = []
    phase_prob = []
    for counts in phase_counts:
        order_idx = np.argsort(-counts, kind="mergesort")
        top = order_idx[: max(2, min(int(block_top_k), A))].astype(np.int64, copy=False)
        w = (counts[top] + 1).astype(np.float64)  # +1 so zeros still selectable
        w /= float(np.sum(w))
        phase_top.append(top)
        phase_prob.append(w)

    # ------------------------------------------------------------
    # Initial block seeds: rank-align ct unigram ranks to LM unigram ranks
    # (fast, deterministic, no strings, no per-call LM building)
    # ------------------------------------------------------------
    # LM unigram order: most likely plaintext symbols first
    probs = _lm_unigram_probs(A=A, direction=Direction.RTL)  # LMPrime unigram probe already in this file
    pt_order = np.argsort(-np.asarray(probs), kind="mergesort").astype(np.int64, copy=False)

    block_seed_lists: list[list[np.ndarray]] = []
    for r in range(period):
        counts = phase_counts[r]
        ct_order = np.argsort(-counts, kind="mergesort").astype(np.int64, copy=False)

        base = np.arange(A, dtype=np.int64)
        for c_sym, p_sym in zip(ct_order, pt_order):
            base[int(c_sym)] = int(p_sym)
        base = _normalize_perm(base, A).astype(np.uint8, copy=False)

        seeds_r: list[np.ndarray] = [base.copy()]
        # jitter variants (small swaps)
        for j in range(max(0, int(n_block_jitter) - 1)):
            cand = base.copy()
            k_swaps = 1 + (j % 3)  # 1,2,3,1,2,3...
            for _ in range(k_swaps):
                i = int(rng.integers(0, A))
                j2 = int(rng.integers(0, A - 1))
                if j2 >= i:
                    j2 += 1
                cand[i], cand[j2] = cand[j2], cand[i]
            seeds_r.append(cand)
        block_seed_lists.append(seeds_r)

    # ------------------------------------------------------------
    # Initial tail seeds: identity + jitter + a few random perms
    # ------------------------------------------------------------
    tail_seeds: list[np.ndarray] = []
    identity = np.arange(C, dtype=np.uint8)
    tail_seeds.append(identity.copy())

    for _ in range(max(0, int(n_tail_seeds) - 1)):
        cand = identity.copy()
        # deterministic-ish: mostly near-identity, occasionally random
        if C >= 2:
            for _k in range(max(0, int(tail_jitter_swaps))):
                i = int(rng.integers(0, C))
                j = int(rng.integers(0, C - 1))
                if j >= i:
                    j += 1
                cand[i], cand[j] = cand[j], cand[i]
        if C >= 4 and rng.random() < 0.25:
            rng.shuffle(cand)
        tail_seeds.append(cand)

    # ------------------------------------------------------------
    # SA core (in-place swaps on a flat key array)
    # ------------------------------------------------------------
    def _accept(delta: float, temp: float) -> bool:
        if delta >= 0.0:
            return True
        if temp <= 0.0:
            return False
        return rng.random() < float(np.exp(delta / temp))

    def _temp(step: int, total: int) -> float:
        if total <= 1:
            return float(end_temp)
        t = float(step) / float(total - 1)
        return float(start_temp * (1.0 - t) + end_temp * t)

    def _flat_from_parts(blocks: np.ndarray, tail: np.ndarray) -> np.ndarray:
        out = np.empty(key_len, dtype=np.uint8)
        out[:sub_len] = blocks.reshape(-1)
        out[sub_len:] = tail.reshape(-1)
        return out

    scored_keys: dict[bytes, float] = {}

    # A handful of SA starts (deterministic).
    for s in range(int(n_starts)):
        # pick initial blocks
        blocks = np.empty((period, A), dtype=np.uint8)
        for r in range(period):
            seeds_r = block_seed_lists[r]
            pick = 0 if s == 0 else int(rng.integers(0, len(seeds_r)))
            blocks[r, :] = seeds_r[pick]

        # pick initial tail
        tail = tail_seeds[0].copy() if s == 0 else tail_seeds[int(rng.integers(0, len(tail_seeds)))].copy()

        key_flat = _flat_from_parts(blocks, tail)
        cur = float(score_key_fn(key_flat))
        best = cur
        best_flat = key_flat.copy()

        for rr in range(int(rounds)):
            # --- Tail SA ---
            total = int(tail_steps)
            for step in range(total):
                temp = _temp(step, total)
                for _m in range(max(1, int(swaps_per_move))):
                    i = int(rng.integers(0, C))
                    j = int(rng.integers(0, C - 1))
                    if j >= i:
                        j += 1

                    a = sub_len + i
                    b = sub_len + j
                    # swap tail
                    key_flat[a], key_flat[b] = key_flat[b], key_flat[a]
                    tail[i], tail[j] = tail[j], tail[i]

                    cand = float(score_key_fn(key_flat))
                    delta = cand - cur
                    if _accept(delta, temp):
                        cur = cand
                        if cand > best:
                            best = cand
                            best_flat = key_flat.copy()
                    else:
                        # revert
                        key_flat[a], key_flat[b] = key_flat[b], key_flat[a]
                        tail[i], tail[j] = tail[j], tail[i]

            # --- Block SA ---
            total = int(block_steps)
            for step in range(total):
                temp = _temp(step, total)
                for _m in range(max(1, int(swaps_per_move))):
                    r = int(rng.integers(0, period))
                    top = phase_top[r]
                    prob = phase_prob[r]

                    # choose two DISTINCT ciphertext symbols (positions in the ct->pt map)
                    idx = rng.choice(top.size, size=2, replace=False, p=prob)
                    c1 = int(top[int(idx[0])])
                    c2 = int(top[int(idx[1])])

                    a = r * A + c1
                    b = r * A + c2

                    # swap plaintext images for those ciphertext symbols
                    key_flat[a], key_flat[b] = key_flat[b], key_flat[a]
                    blocks[r, c1], blocks[r, c2] = blocks[r, c2], blocks[r, c1]

                    cand = float(score_key_fn(key_flat))
                    delta = cand - cur
                    if _accept(delta, temp):
                        cur = cand
                        if cand > best:
                            best = cand
                            best_flat = key_flat.copy()
                    else:
                        # revert
                        key_flat[a], key_flat[b] = key_flat[b], key_flat[a]
                        blocks[r, c1], blocks[r, c2] = blocks[r, c2], blocks[r, c1]

        scored_keys[best_flat.tobytes()] = max(scored_keys.get(best_flat.tobytes(), float("-inf")), best)

    # Sort unique best keys from the SA starts.
    ranked = sorted(scored_keys.items(), key=lambda kv: kv[1], reverse=True)
    out: list[list[int]] = []

    def _append_bytes(b: bytes) -> None:
        if len(out) >= n_keys:
            return
        arr = np.frombuffer(b, dtype=np.uint8).copy()
        out.append([int(x) for x in arr.tolist()])

    for b, _s in ranked:
        _append_bytes(b)
        if len(out) >= n_keys:
            break

    # Fill remaining keys with light deterministic mutations around the best key (diversity).
    if out:
        best0 = np.asarray(out[0], dtype=np.uint8)
        while len(out) < n_keys:
            cand = best0.copy()
            # mutate: one block swap + one tail swap
            r = int(rng.integers(0, period))
            i = int(rng.integers(0, A))
            j = int(rng.integers(0, A - 1))
            if j >= i:
                j += 1
            a = r * A + i
            b = r * A + j
            cand[a], cand[b] = cand[b], cand[a]

            if C >= 2:
                i2 = int(rng.integers(0, C))
                j2 = int(rng.integers(0, C - 1))
                if j2 >= i2:
                    j2 += 1
                a2 = sub_len + i2
                b2 = sub_len + j2
                cand[a2], cand[b2] = cand[b2], cand[a2]

            bb = cand.tobytes()
            if bb not in scored_keys:
                scored_keys[bb] = float(score_key_fn(cand))
                _append_bytes(bb)

    return out[:n_keys]
