from __future__ import annotations

"""Deterministic target-actual damage/null models for O4 bridge calibration."""

import hashlib
from typing import Sequence

import numpy as np

ALPHABET_SIZE = 29
GLOBAL_SEED = 20260507


def stable_int_seed(*parts: object) -> int:
    text = "|".join(str(part) for part in parts)
    digest = hashlib.blake2b(text.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "little", signed=False) & 0x7FFF_FFFF_FFFF_FFFF


def target_change_count(n: int, target_fraction: float) -> int:
    return max(0, min(int(n), int(round(float(target_fraction) * int(n)))))


def empirical_probs(tokens: Sequence[int]) -> np.ndarray:
    counts = np.bincount(np.asarray(tokens, dtype=np.int64), minlength=ALPHABET_SIZE).astype(np.float64)
    total = float(counts.sum())
    if total <= 0.0:
        return np.ones(ALPHABET_SIZE, dtype=np.float64) / ALPHABET_SIZE
    return counts / total


def changed_fraction(clean: Sequence[int], variant: Sequence[int]) -> float:
    if len(clean) != len(variant):
        raise ValueError("variant length changed")
    if not clean:
        return 0.0
    changed = sum(1 for a, b in zip(clean, variant) if int(a) != int(b))
    return changed / float(len(clean))


def _uniform_different(original: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    repl = rng.integers(0, ALPHABET_SIZE - 1, size=original.size, dtype=np.int16)
    original16 = original.astype(np.int16)
    repl = repl + (repl >= original16)
    return repl.astype(np.uint8)


def _frequency_different(original: np.ndarray, rng: np.random.Generator, probs: np.ndarray) -> np.ndarray:
    alphabet = np.arange(ALPHABET_SIZE, dtype=np.uint8)
    repl = rng.choice(alphabet, size=original.size, replace=True, p=probs)
    same = repl == original
    guard = 0
    while bool(np.any(same)):
        repl[same] = rng.choice(alphabet, size=int(np.sum(same)), replace=True, p=probs)
        same = repl == original
        guard += 1
        if guard > 20:
            repl[same] = _uniform_different(original[same], rng)
            break
    return repl.astype(np.uint8)


def replace_positions(tokens: Sequence[int], positions: Sequence[int], *, seed: int, probs: np.ndarray | None = None) -> tuple[int, ...]:
    arr = np.asarray(tokens, dtype=np.uint8)
    pos = np.asarray(sorted(set(int(p) for p in positions)), dtype=np.int64)
    out = arr.copy()
    rng = np.random.default_rng(seed)
    if pos.size == 0:
        return tuple(int(x) for x in out)
    if probs is None:
        out[pos] = _uniform_different(out[pos], rng)
    else:
        out[pos] = _frequency_different(out[pos], rng, probs)
    return tuple(int(x) for x in out)


def select_independent_positions(n: int, *, target_fraction: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    k = target_change_count(n, target_fraction)
    if k <= 0:
        return np.asarray([], dtype=np.int64)
    return np.sort(rng.choice(np.arange(n), size=k, replace=False)).astype(np.int64)


def complete_word_intervals(wli: Sequence[tuple[int, int]]) -> list[tuple[int, int]]:
    arr = np.asarray(wli, dtype=np.int64)
    out: list[tuple[int, int]] = []
    n = int(arr.shape[0])
    i = 0
    while i < n:
        pos = int(arr[i, 0])
        length = int(arr[i, 1])
        if pos == 0 and length > 0 and i + length <= n:
            expected = np.arange(length, dtype=np.int64)
            if np.array_equal(arr[i : i + length, 0], expected) and bool(np.all(arr[i : i + length, 1] == length)):
                out.append((i, i + length))
                i += length
                continue
        i += 1
    return out


def select_word_local_positions(n: int, wli: Sequence[tuple[int, int]], *, target_fraction: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    k = target_change_count(n, target_fraction)
    if k <= 0:
        return np.asarray([], dtype=np.int64)
    intervals = complete_word_intervals(wli)
    if not intervals:
        return select_independent_positions(n, target_fraction=target_fraction, seed=seed)
    # Choose whole local word islands until enough positions exist, then sample
    # exactly k inside the chosen local islands. This preserves locality while
    # making the achieved global damage rate honest.
    order = rng.permutation(len(intervals))
    pool: list[int] = []
    for idx in order.tolist():
        start, end = intervals[int(idx)]
        pool.extend(range(start, end))
        if len(set(pool)) >= k:
            break
    unique_pool = np.asarray(sorted(set(pool)), dtype=np.int64)
    if unique_pool.size < k:
        return select_independent_positions(n, target_fraction=target_fraction, seed=seed)
    return np.sort(rng.choice(unique_pool, size=k, replace=False)).astype(np.int64)


def select_burst_positions(n: int, *, target_fraction: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    k = target_change_count(n, target_fraction)
    chosen: set[int] = set()
    attempts = 0
    while len(chosen) < k and attempts < 10000:
        attempts += 1
        length = int(rng.integers(5, 21)) if rng.random() < 0.7 else int(rng.integers(25, 81))
        start = int(rng.integers(0, max(1, n)))
        for pos in range(start, min(n, start + length)):
            chosen.add(pos)
            if len(chosen) >= k:
                break
    if len(chosen) < k:
        remaining = sorted(set(range(n)) - chosen)
        extra = rng.choice(np.asarray(remaining, dtype=np.int64), size=k - len(chosen), replace=False)
        chosen.update(int(x) for x in extra.tolist())
    return np.asarray(sorted(chosen), dtype=np.int64)


def select_lane_period_positions(n: int, *, target_fraction: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    k = target_change_count(n, target_fraction)
    if k <= 0:
        return np.asarray([], dtype=np.int64)
    period = int(rng.choice(np.asarray([5, 7, 13, 19, 29], dtype=np.int64)))
    lanes = list(rng.permutation(period).tolist())
    pool: list[int] = []
    for lane in lanes:
        pool.extend(idx for idx in range(n) if idx % period == int(lane))
        if len(set(pool)) >= k:
            break
    unique_pool = np.asarray(sorted(set(pool)), dtype=np.int64)
    if unique_pool.size < k:
        unique_pool = np.arange(n, dtype=np.int64)
    return np.sort(rng.choice(unique_pool, size=k, replace=False)).astype(np.int64)


def make_target_damaged_variant(
    tokens: Sequence[int],
    *,
    model_name: str,
    target_fraction: float,
    seed: int,
    wli: Sequence[tuple[int, int]] | None = None,
    global_probs: np.ndarray | None = None,
    book_probs: np.ndarray | None = None,
    tolerance: float = 0.01,
) -> tuple[int, ...]:
    n = len(tokens)
    if model_name == "independent_substitution":
        positions = select_independent_positions(n, target_fraction=target_fraction, seed=seed)
        out = replace_positions(tokens, positions, seed=seed)
    elif model_name == "frequency_matched_global":
        positions = select_independent_positions(n, target_fraction=target_fraction, seed=seed)
        out = replace_positions(tokens, positions, seed=seed, probs=global_probs if global_probs is not None else empirical_probs(tokens))
    elif model_name == "frequency_matched_book":
        positions = select_independent_positions(n, target_fraction=target_fraction, seed=seed)
        out = replace_positions(tokens, positions, seed=seed, probs=book_probs if book_probs is not None else empirical_probs(tokens))
    elif model_name == "word_local_substitution":
        if wli is None:
            raise ValueError("word_local_substitution requires wli")
        positions = select_word_local_positions(n, wli, target_fraction=target_fraction, seed=seed)
        out = replace_positions(tokens, positions, seed=seed)
    elif model_name == "burst_substitution":
        positions = select_burst_positions(n, target_fraction=target_fraction, seed=seed)
        out = replace_positions(tokens, positions, seed=seed)
    elif model_name == "lane_period_substitution":
        positions = select_lane_period_positions(n, target_fraction=target_fraction, seed=seed)
        out = replace_positions(tokens, positions, seed=seed)
    else:
        raise ValueError(f"unknown damage model: {model_name}")
    actual = changed_fraction(tokens, out)
    if abs(actual - float(target_fraction)) > float(tolerance):
        raise AssertionError(
            f"damage model {model_name} missed target: requested={target_fraction:.6f} actual={actual:.6f}"
        )
    return out


def make_null_variant(tokens: Sequence[int], *, model_name: str, seed: int, global_probs: np.ndarray | None = None) -> tuple[int, ...]:
    arr = np.asarray(tokens, dtype=np.uint8)
    rng = np.random.default_rng(seed)
    if model_name == "uniform_random":
        return tuple(int(x) for x in rng.integers(0, ALPHABET_SIZE, size=len(arr), dtype=np.uint8))
    if model_name == "global_frequency_random":
        probs = global_probs if global_probs is not None else empirical_probs(tokens)
        return tuple(int(x) for x in rng.choice(np.arange(ALPHABET_SIZE, dtype=np.uint8), size=len(arr), replace=True, p=probs))
    if model_name == "within_chunk_shuffle":
        out = arr.copy(); rng.shuffle(out); return tuple(int(x) for x in out)
    if model_name.startswith("block_shuffle_"):
        block_size = int(model_name.rsplit("_", 1)[1])
        blocks = [arr[i : i + block_size].copy() for i in range(0, len(arr), block_size)]
        order = np.arange(len(blocks)); rng.shuffle(order)
        out = np.concatenate([blocks[int(i)] for i in order])
        return tuple(int(x) for x in out[: len(arr)])
    raise ValueError(f"unknown null/control model: {model_name}")
