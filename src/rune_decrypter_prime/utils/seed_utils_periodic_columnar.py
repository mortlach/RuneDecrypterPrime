from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Dict, Iterable, List, Optional, Sequence

import numpy as np

from rune_decrypter_prime.ciphers.periodic_columnar_cipher import PeriodicColumnarCipher
from rune_decrypter_prime.core.config.cipher import CipherConfig
from rune_decrypter_prime.core.config.scoring import ScoringConfig
from rune_decrypter_prime.core.engine.builders import build_scorer
from rune_decrypter_prime.core.transpositions import assert_is_permutation
from rune_decrypter_prime.core.types import Direction, Device, KEY_DTYPE, ensure_direction
from rune_decrypter_prime.scoring.language_model.language_model_prime import LanguageModelPrime

ALPHABET_SIZE = 29
_ALLOWED_ORDERS = {"col_then_sub", "sub_then_col"}


@dataclass(frozen=True)
class SeedPlan:
    n_block_seeds: int = 6
    n_tail_seeds: int = 6
    n_starts: int = 24
    refine_steps: int = 600
    tail_move_prob: float = 0.45
    temp_start: float = 0.06
    temp_end: float = 0.008


class _RawCharScorer:
    def __init__(self, cfg: ScoringConfig, *, direction: Direction):
        self._direction = ensure_direction(direction)
        self.lm = LanguageModelPrime(
            lm_root=getattr(cfg, "model_root", None),
            smoothing=getattr(cfg, "smoothing", None),
            alpha=float(getattr(cfg, "alpha", 0.5) or 0.5),
            oov_policy=getattr(cfg, "oov_policy", None),
            include_char=True,
        )
        weights = dict(cfg.char_weights) if cfg.char_weights else {3: 0.5, 4: 0.5}
        self._weights = {int(n): float(w) for n, w in weights.items() if int(n) > 0 and float(w) > 0.0}
        if not self._weights:
            raise ValueError("char_weights must include at least one positive n-gram weight")

    def score(self, plaintext: Iterable[int], _wli=None) -> float:
        pt = np.asarray(list(plaintext), dtype=np.uint8).reshape(-1)
        if pt.size == 0:
            return float("-inf")
        total_w = float(sum(self._weights.values()))
        if total_w <= 0:
            return float("-inf")

        acc = 0.0
        L = int(pt.size)
        for n, w in self._weights.items():
            n = int(n)
            total_eval = L - n + 1
            if total_eval <= 0:
                return float("-inf")
            res = self.lm.score([pt.tolist()], None, direction=self._direction.value, se="nose", n=n, model="char")[0]
            avg = float(res.logprob_sum) / float(total_eval)
            acc += float(w) * avg
        return acc / total_w


def generate_seed_keys_periodic_columnar(
    ct_idx: Sequence[int] | np.ndarray,
    *,
    period: int,
    columns: int,
    order: str,
    direction: Direction,
    seed: int,
    wli_data: Sequence[Sequence[int]] | None = None,
    scoring_cfg: ScoringConfig | None = None,
    pt_unigram_rank_override: Sequence[int] | None = None,
    n_keys: int = 64,
    plan: SeedPlan | None = None,
    refine: bool = True,
    rerank_cfg: ScoringConfig | None = None,
) -> List[List[int]]:
    """
    Deterministic seed generator for PeriodicColumnarCipher.

    Key layout (matches PeriodicColumnarCipher):
      - blocks: period blocks, each a length-29 permutation mapping ct_sym -> pt_sym
      - tail: length-columns permutation for the columnar step
    """
    plan = plan or SeedPlan()
    order = str(order)
    direction = ensure_direction(direction)
    if scoring_cfg is not None and bool(getattr(scoring_cfg, "use_word_breaks", False)):
        raise ValueError("Seed refinement does not support WLI; set scoring_cfg.use_word_breaks=False and use rerank_cfg for WLI rerank")
    if rerank_cfg is not None and bool(getattr(rerank_cfg, "use_word_breaks", False)):
        if not wli_data:
            raise ValueError("wli_data is required when rerank_cfg.use_word_breaks=True")

    ct_u8 = _validate_inputs(
        ct_idx=ct_idx,
        period=period,
        columns=columns,
        order=order,
        n_keys=n_keys,
        scoring_cfg=scoring_cfg,
        pt_unigram_rank_override=pt_unigram_rank_override,
    )
    wli = list(wli_data) if wli_data else []
    if wli and len(wli) != int(ct_u8.size):
        raise ValueError("wli_data length must match ciphertext length")

    rng = np.random.default_rng(int(seed))

    raw_scorer = _RawCharScorer(scoring_cfg, direction=direction) if scoring_cfg is not None else None

    pt_order = _pt_unigram_order(
        scoring_cfg=scoring_cfg,
        direction=direction,
        pt_unigram_rank_override=pt_unigram_rank_override,
        lm=raw_scorer.lm if raw_scorer is not None else None,
    )

    per_phase_counts = _phase_symbol_counts(ct_u8, period=period, order=order)
    block_seeds_by_phase = _make_block_seeds_by_phase(
        per_phase_counts=per_phase_counts,
        pt_order=pt_order,
        n_block_seeds=plan.n_block_seeds,
        rng=rng,
    )
    tail_seeds = _make_tail_seeds(columns=columns, n_tail_seeds=plan.n_tail_seeds, rng=rng)
    start_keys = _make_start_keys(
        block_seeds_by_phase=block_seeds_by_phase,
        tail_seeds=tail_seeds,
        period=period,
        n_starts=plan.n_starts,
        rng=rng,
    )

    cipher_cfg = None
    cipher = None
    if scoring_cfg is not None or rerank_cfg is not None:
        cipher_cfg = _make_cipher_cfg(
            ct_u8=ct_u8,
            period=period,
            columns=columns,
            order=order,
            direction=direction,
            wli_data=wli,
        )
        cipher = PeriodicColumnarCipher(cipher_cfg)

    candidates = start_keys
    cache: Dict[bytes, float] | None = None
    if scoring_cfg is not None and refine and int(plan.refine_steps) > 0:
        cache = {}
        refined = [
            _refine_key(
                k0,
                ciphertext=ct_u8,
                cipher=cipher,
                scorer=raw_scorer,
                wli=wli,
                per_phase_counts=per_phase_counts,
                period=period,
                columns=columns,
                rng=rng,
                refine_steps=int(plan.refine_steps),
                tail_move_prob=float(plan.tail_move_prob),
                temp_start=float(plan.temp_start),
                temp_end=float(plan.temp_end),
                cache=cache,
            )
            for k0 in start_keys
        ]
        candidates = _unique_keys_preserve_order(start_keys + refined)

    if len(candidates) < int(n_keys):
        candidates = _pad_candidates(
            candidates,
            n_target=int(n_keys),
            period=period,
            columns=columns,
            rng=rng,
        )

    if rerank_cfg is not None:
        scorer = build_scorer(cipher_cfg, rerank_cfg)
        ranked = _rank_candidates(ct_u8, candidates, scorer, cipher, cache=None, wli=wli)
    elif raw_scorer is not None:
        ranked = _rank_candidates(ct_u8, candidates, raw_scorer, cipher, cache=cache, wli=wli)
    else:
        ranked = candidates

    top = ranked[: int(n_keys)]
    for k in top:
        _validate_key_layout(k, period=period, columns=columns)

    return [k.astype(int).tolist() for k in top]


# -------------------- validation + helpers --------------------

def _validate_inputs(
    *,
    ct_idx: Sequence[int] | np.ndarray,
    period: int,
    columns: int,
    order: str,
    n_keys: int,
    scoring_cfg: ScoringConfig | None,
    pt_unigram_rank_override: Sequence[int] | None,
) -> np.ndarray:
    if ct_idx is None:
        raise ValueError("ct_idx is required")
    if not isinstance(period, (int, np.integer)) or int(period) <= 0:
        raise ValueError(f"period must be a positive int; got {period!r}")
    if not isinstance(columns, (int, np.integer)) or int(columns) <= 0:
        raise ValueError(f"columns must be an int >= 1; got {columns!r}")
    if order not in _ALLOWED_ORDERS:
        raise ValueError("order must be exactly 'col_then_sub' or 'sub_then_col' (required; do not rely on cipher defaults)")
    if not isinstance(n_keys, (int, np.integer)) or int(n_keys) <= 0:
        raise ValueError(f"n_keys must be > 0; got {n_keys!r}")

    arr = np.asarray(ct_idx)
    if arr.size == 0:
        raise ValueError("ct_idx must be non-empty")
    arr = arr.reshape(-1)
    if not np.issubdtype(arr.dtype, np.integer):
        if np.any(np.mod(arr, 1) != 0):
            raise ValueError("ct_idx must contain integers")
    arr_i64 = arr.astype(np.int64)
    if arr_i64.min() < 0 or arr_i64.max() >= ALPHABET_SIZE:
        raise ValueError(f"ct_idx symbols must be in [0,{ALPHABET_SIZE - 1}]")

    if scoring_cfg is None:
        if pt_unigram_rank_override is None:
            raise ValueError("pt_unigram_rank_override is required when scoring_cfg is None")
        _validate_pt_rank_override(pt_unigram_rank_override)

    return np.ascontiguousarray(arr_i64.astype(np.uint8), dtype=np.uint8)


def _validate_pt_rank_override(pt_rank: Sequence[int]) -> None:
    seq = [int(x) for x in pt_rank]
    assert_is_permutation(seq, ALPHABET_SIZE)


def _make_cipher_cfg(
    *,
    ct_u8: np.ndarray,
    period: int,
    columns: int,
    order: str,
    direction: Direction,
    wli_data: Sequence[Sequence[int]] | None,
) -> CipherConfig:
    key_len = int(period * ALPHABET_SIZE + columns)
    return CipherConfig(
        name="periodic_columnar",
        ciphertext=ct_u8.tolist(),
        wli_data=list(wli_data) if wli_data else [],
        key_length=key_len,
        period=period,
        columns=columns,
        alphabet_size=ALPHABET_SIZE,
        order=order,
        encoding_dir=direction,
        device=Device.CPU,
    )


def _pt_unigram_order(
    *,
    scoring_cfg: ScoringConfig | None,
    direction: Direction,
    pt_unigram_rank_override: Sequence[int] | None,
    lm: LanguageModelPrime | None,
) -> np.ndarray:
    if pt_unigram_rank_override is not None:
        _validate_pt_rank_override(pt_unigram_rank_override)
        return np.asarray(list(pt_unigram_rank_override), dtype=np.int64)

    if scoring_cfg is None:
        raise ValueError("pt_unigram_rank_override is required when scoring_cfg is None")

    probs = _lm_unigram_probs(scoring_cfg, direction=direction, lm=lm)
    return np.lexsort((np.arange(ALPHABET_SIZE), -probs))


def _lm_unigram_probs(cfg: ScoringConfig, *, direction: Direction, lm: LanguageModelPrime | None) -> np.ndarray:
    if lm is None:
        lm = LanguageModelPrime(
            lm_root=getattr(cfg, "model_root", None),
            smoothing=getattr(cfg, "smoothing", None),
            alpha=float(getattr(cfg, "alpha", 0.5) or 0.5),
            oov_policy=getattr(cfg, "oov_policy", None),
            include_char=True,
        )
    L = 64
    pts = [[r] * L for r in range(ALPHABET_SIZE)]
    res = lm.score(pts, None, direction=direction.value, se="nose", n=1, model="char")
    raw = [math.exp(s.logprob_sum / L) for s in res]
    Z = float(sum(raw) or 1.0)
    return np.asarray([x / Z for x in raw], dtype=np.float64)


def _phase_symbol_counts(ct_u8: np.ndarray, *, period: int, order: str) -> List[np.ndarray]:
    counts: List[np.ndarray] = []
    if order == "col_then_sub":
        for r in range(period):
            phase = ct_u8[r::period]
            counts.append(np.bincount(phase, minlength=ALPHABET_SIZE).astype(np.int64))
    else:
        g = np.bincount(ct_u8, minlength=ALPHABET_SIZE).astype(np.int64)
        for _ in range(period):
            counts.append(g.copy())
    return counts


def _rank_alignment_perm(ct_counts: np.ndarray, pt_order: np.ndarray) -> np.ndarray:
    ct_order = np.lexsort((np.arange(ALPHABET_SIZE), -ct_counts))
    perm = np.empty(ALPHABET_SIZE, dtype=KEY_DTYPE)
    perm[ct_order] = pt_order.astype(KEY_DTYPE)
    return perm


def _jitter_perm(perm: np.ndarray, *, rng: np.random.Generator, n_swaps: int) -> np.ndarray:
    out = perm.copy()
    for _ in range(max(1, int(n_swaps))):
        a = int(rng.integers(0, ALPHABET_SIZE))
        b = int(rng.integers(0, ALPHABET_SIZE - 1))
        if b >= a:
            b += 1
        out[a], out[b] = out[b], out[a]
    return out


def _make_block_seeds_by_phase(
    *,
    per_phase_counts: List[np.ndarray],
    pt_order: np.ndarray,
    n_block_seeds: int,
    rng: np.random.Generator,
) -> List[List[np.ndarray]]:
    seeds_by_phase: List[List[np.ndarray]] = []
    for counts in per_phase_counts:
        base = _rank_alignment_perm(counts, pt_order)
        phase_seeds = [base]
        for i in range(1, int(n_block_seeds)):
            phase_seeds.append(_jitter_perm(base, rng=rng, n_swaps=1 + (i // 2)))
        seeds_by_phase.append(phase_seeds)
    return seeds_by_phase


def _make_tail_seeds(*, columns: int, n_tail_seeds: int, rng: np.random.Generator) -> List[np.ndarray]:
    if columns <= 1:
        return [np.zeros(1, dtype=KEY_DTYPE)]

    base = np.arange(columns, dtype=KEY_DTYPE)
    seeds = [base]
    for i in range(1, min(int(n_tail_seeds), 4)):
        t = base.copy()
        for _ in range(i):
            a = int(rng.integers(0, columns))
            b = int(rng.integers(0, columns - 1))
            if b >= a:
                b += 1
            t[a], t[b] = t[b], t[a]
        seeds.append(t)
    while len(seeds) < int(n_tail_seeds):
        seeds.append(rng.permutation(columns).astype(KEY_DTYPE))
    return seeds


def _assemble_key(
    block_seeds_by_phase: List[List[np.ndarray]],
    picks: List[int],
    tail: np.ndarray,
    *,
    period: int,
) -> np.ndarray:
    head = np.concatenate([block_seeds_by_phase[r][picks[r]] for r in range(period)]).astype(KEY_DTYPE, copy=False)
    return np.concatenate([head, tail.astype(KEY_DTYPE, copy=False)]).astype(KEY_DTYPE, copy=False)


def _make_start_keys(
    *,
    block_seeds_by_phase: List[List[np.ndarray]],
    tail_seeds: List[np.ndarray],
    period: int,
    n_starts: int,
    rng: np.random.Generator,
) -> List[np.ndarray]:
    starts: List[np.ndarray] = []
    n_block = len(block_seeds_by_phase[0])
    n_tail = len(tail_seeds)

    starts.append(_assemble_key(block_seeds_by_phase, [0] * period, tail_seeds[0], period=period))

    attempts = 0
    max_attempts = max(10, int(n_starts) * 20)
    while len(starts) < int(n_starts) and attempts < max_attempts:
        picks = [int(rng.integers(0, n_block)) for _ in range(period)]
        tail_pick = int(rng.integers(0, n_tail))
        starts.append(_assemble_key(block_seeds_by_phase, picks, tail_seeds[tail_pick], period=period))
        attempts += 1

    return _unique_keys_preserve_order(starts)


def _unique_keys_preserve_order(keys: Iterable[np.ndarray]) -> List[np.ndarray]:
    out: List[np.ndarray] = []
    seen: set[bytes] = set()
    for k in keys:
        b = k.tobytes()
        if b in seen:
            continue
        seen.add(b)
        out.append(k)
    return out


def _pad_candidates(
    keys: List[np.ndarray],
    *,
    n_target: int,
    period: int,
    columns: int,
    rng: np.random.Generator,
) -> List[np.ndarray]:
    if len(keys) >= n_target:
        return keys
    out = list(keys)
    seen = {k.tobytes() for k in out}
    max_attempts = max(100, (n_target - len(out)) * 50)
    attempts = 0
    while len(out) < n_target and attempts < max_attempts:
        blocks = [rng.permutation(ALPHABET_SIZE).astype(KEY_DTYPE) for _ in range(period)]
        if columns <= 1:
            tail = np.zeros(1, dtype=KEY_DTYPE)
        else:
            tail = rng.permutation(columns).astype(KEY_DTYPE)
        k = np.concatenate([*blocks, tail]).astype(KEY_DTYPE, copy=False)
        kb = k.tobytes()
        if kb not in seen:
            seen.add(kb)
            out.append(k)
        attempts += 1
    return out


def _score_key(
    cipher: PeriodicColumnarCipher,
    scorer,
    ciphertext: np.ndarray,
    key: np.ndarray,
    *,
    cache: Optional[Dict[bytes, float]],
    wli: Sequence[Sequence[int]] | None,
) -> float:
    # scorer contract (both engine scorer and _RawCharScorer): score(pt, wli) -> float
    kb = key.tobytes()
    if cache is not None and kb in cache:
        return cache[kb]
    pt = cipher.decrypt_single(ciphertext=ciphertext, key=key)
    s = float(scorer.score(pt, wli))
    if cache is not None:
        cache[kb] = s
    return s


def _refine_key(
    k0: np.ndarray,
    *,
    ciphertext: np.ndarray,
    cipher: PeriodicColumnarCipher,
    scorer,
    wli: Sequence[Sequence[int]] | None,
    per_phase_counts: List[np.ndarray],
    period: int,
    columns: int,
    rng: np.random.Generator,
    refine_steps: int,
    tail_move_prob: float,
    temp_start: float,
    temp_end: float,
    cache: Dict[bytes, float],
) -> np.ndarray:
    if refine_steps <= 0:
        return k0

    k = k0.copy()
    s = _score_key(cipher, scorer, ciphertext, k, cache=cache, wli=wli)
    k_best = k.copy()
    s_best = s

    ratio = (temp_end / temp_start) if temp_start > 0 else 0.0

    for step in range(refine_steps):
        frac = step / max(1, refine_steps - 1)
        T = temp_start * (ratio ** frac) if temp_start > 0 else 0.0

        k_new = k.copy()
        do_tail = (columns >= 2) and (float(rng.random()) < tail_move_prob)
        if do_tail:
            a = int(rng.integers(0, columns))
            b = int(rng.integers(0, columns - 1))
            if b >= a:
                b += 1
            off = period * ALPHABET_SIZE
            k_new[off + a], k_new[off + b] = k_new[off + b], k_new[off + a]
        else:
            phase = int(rng.integers(0, period))
            counts = per_phase_counts[phase].astype(np.float64)
            weights = counts + 1.0
            weights /= float(weights.sum())
            a = int(rng.choice(ALPHABET_SIZE, p=weights))
            b = int(rng.choice(ALPHABET_SIZE, p=weights))
            while b == a:
                b = int(rng.choice(ALPHABET_SIZE, p=weights))
            off = phase * ALPHABET_SIZE
            k_new[off + a], k_new[off + b] = k_new[off + b], k_new[off + a]

        s_new = _score_key(cipher, scorer, ciphertext, k_new, cache=cache, wli=wli)
        delta = s_new - s

        accept = False
        if delta >= 0:
            accept = True
        elif T > 0:
            accept = float(rng.random()) < math.exp(delta / max(T, 1e-12))

        if accept:
            k = k_new
            s = s_new
            if s > s_best:
                k_best = k.copy()
                s_best = s

    return k_best


def _rank_candidates(
    ciphertext: np.ndarray,
    keys: List[np.ndarray],
    scorer,
    cipher: PeriodicColumnarCipher,
    *,
    cache: Optional[Dict[bytes, float]],
    wli: Sequence[Sequence[int]] | None,
) -> List[np.ndarray]:
    scored = [
        (float(_score_key(cipher, scorer, ciphertext, k, cache=cache, wli=wli)), k)
        for k in keys
    ]
    scored.sort(key=lambda pair: (-pair[0], pair[1].tobytes()))
    return [k for _, k in scored]


def _validate_key_layout(key: np.ndarray, *, period: int, columns: int) -> None:
    k = np.asarray(key, dtype=KEY_DTYPE).reshape(-1)
    expected = period * ALPHABET_SIZE + columns
    if k.size != expected:
        raise ValueError(f"Key length mismatch: expected {expected}, got {k.size}")
    for r in range(period):
        block = k[r * ALPHABET_SIZE : (r + 1) * ALPHABET_SIZE]
        _assert_perm_1d(block, ALPHABET_SIZE, f"Block {r} is not a permutation of 0..{ALPHABET_SIZE - 1}")
    tail = k[period * ALPHABET_SIZE :]
    _assert_perm_1d(tail, columns, f"Tail is not a permutation of 0..{columns - 1}")


def _assert_perm_1d(x: np.ndarray, size: int, msg: str) -> None:
    arr = np.asarray(x, dtype=np.int64).reshape(-1)
    if arr.size != size:
        raise ValueError(msg)
    if arr.min() < 0 or arr.max() >= size:
        raise ValueError(msg)
    if np.unique(arr).size != size:
        raise ValueError(msg)
