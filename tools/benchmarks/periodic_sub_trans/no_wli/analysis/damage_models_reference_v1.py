from __future__ import annotations

"""
Reference damage/null models copied in spirit from the existing Runeberg NOSE
ladder, trimmed to be standalone for tests and calibration planning.

The model names intentionally match the old ladder contract:
- independent_substitution
- frequency_matched_global
- frequency_matched_book
- word_local_substitution
- burst_substitution
- lane_period_substitution
- uniform_random
- global_frequency_random
- within_chunk_shuffle
- block_shuffle_10/25/50
"""

import hashlib
from typing import Sequence
import numpy as np

GLOBAL_SEED = 20260507
ALPHABET_SIZE = 29


def stable_int_seed(*parts: object) -> int:
    text = "|".join(str(part) for part in parts)
    digest = hashlib.blake2b(text.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "little", signed=False) & 0x7FFF_FFFF_FFFF_FFFF


def empirical_probs(tokens: Sequence[int]) -> np.ndarray:
    counts = np.bincount(np.asarray(tokens, dtype=np.int64), minlength=ALPHABET_SIZE).astype(np.float64)
    total = float(counts.sum())
    if total <= 0.0:
        return np.ones(ALPHABET_SIZE, dtype=np.float64) / float(ALPHABET_SIZE)
    return counts / total


def _positions_by_probability(n: int, p: float, rng: np.random.Generator) -> np.ndarray:
    return np.flatnonzero(rng.random(n) < float(p)).astype(np.int64)


def _target_position_count(n: int, p: float) -> int:
    if n <= 0:
        return 0
    return max(1, min(n, int(round(float(p) * n))))


def _sample_positions_exact(pool: Sequence[int] | np.ndarray, *, count: int, rng: np.random.Generator) -> np.ndarray:
    arr = np.asarray(pool, dtype=np.int64)
    if count <= 0 or arr.size == 0:
        return np.asarray([], dtype=np.int64)
    unique = np.unique(arr)
    if unique.size < count:
        raise ValueError(f"not enough candidate positions for target damage count: {unique.size} < {count}")
    return np.asarray(sorted(int(x) for x in rng.choice(unique, size=count, replace=False).tolist()), dtype=np.int64)


def _replace_positions_uniform(tokens: np.ndarray, positions: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    out = tokens.copy()
    if positions.size == 0:
        return out
    original = out[positions].astype(np.int16)
    repl = rng.integers(0, ALPHABET_SIZE - 1, size=positions.size, dtype=np.int16)
    repl = repl + (repl >= original)
    out[positions] = repl.astype(np.uint8)
    return out


def _replace_positions_from_probs(
    tokens: np.ndarray,
    positions: np.ndarray,
    rng: np.random.Generator,
    probs: np.ndarray,
) -> np.ndarray:
    out = tokens.copy()
    if positions.size == 0:
        return out
    alphabet = np.arange(ALPHABET_SIZE, dtype=np.uint8)
    repl = rng.choice(alphabet, size=positions.size, replace=True, p=probs)
    same = repl == out[positions]
    guard = 0
    while bool(np.any(same)):
        repl[same] = rng.choice(alphabet, size=int(np.sum(same)), replace=True, p=probs)
        same = repl == out[positions]
        guard += 1
        if guard > 20:
            stubborn = positions[same]
            tmp = _replace_positions_uniform(out, stubborn, rng)
            out[stubborn] = tmp[stubborn]
            break
    out[positions] = repl.astype(np.uint8)
    return out


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
            observed_pos = arr[i:i + length, 0]
            observed_len = arr[i:i + length, 1]
            if np.array_equal(observed_pos, expected) and bool(np.all(observed_len == length)):
                out.append((i, i + length))
                i += length
                continue
        i += 1
    return out


def damage_independent(tokens: Sequence[int], *, p: float, seed: int) -> tuple[int, ...]:
    arr = np.asarray(tokens, dtype=np.uint8)
    rng = np.random.default_rng(seed)
    positions = _positions_by_probability(int(arr.size), p, rng)
    return tuple(int(x) for x in _replace_positions_uniform(arr, positions, rng))


def damage_independent_target_actual(tokens: Sequence[int], *, p: float, seed: int) -> tuple[int, ...]:
    arr = np.asarray(tokens, dtype=np.uint8)
    rng = np.random.default_rng(seed)
    positions = _sample_positions_exact(np.arange(int(arr.size)), count=_target_position_count(int(arr.size), p), rng=rng)
    return tuple(int(x) for x in _replace_positions_uniform(arr, positions, rng))


def damage_frequency_matched(tokens: Sequence[int], *, p: float, seed: int, probs: np.ndarray) -> tuple[int, ...]:
    arr = np.asarray(tokens, dtype=np.uint8)
    rng = np.random.default_rng(seed)
    positions = _positions_by_probability(int(arr.size), p, rng)
    return tuple(int(x) for x in _replace_positions_from_probs(arr, positions, rng, probs))


def damage_frequency_matched_target_actual(
    tokens: Sequence[int],
    *,
    p: float,
    seed: int,
    probs: np.ndarray,
) -> tuple[int, ...]:
    arr = np.asarray(tokens, dtype=np.uint8)
    rng = np.random.default_rng(seed)
    positions = _sample_positions_exact(np.arange(int(arr.size)), count=_target_position_count(int(arr.size), p), rng=rng)
    return tuple(int(x) for x in _replace_positions_from_probs(arr, positions, rng, probs))


def damage_word_local(tokens: Sequence[int], wli: Sequence[tuple[int, int]], *, p: float, seed: int) -> tuple[int, ...]:
    arr = np.asarray(tokens, dtype=np.uint8)
    rng = np.random.default_rng(seed)
    positions: list[int] = []
    for start, end in complete_word_intervals(wli):
        if rng.random() >= p:
            continue
        inner = np.arange(start, end, dtype=np.int64)
        positions.extend(int(x) for x in inner[rng.random(inner.size) < p])
    return tuple(int(x) for x in _replace_positions_uniform(arr, np.asarray(sorted(set(positions)), dtype=np.int64), rng))


def damage_word_local_target_actual(
    tokens: Sequence[int],
    wli: Sequence[tuple[int, int]],
    *,
    p: float,
    seed: int,
) -> tuple[int, ...]:
    arr = np.asarray(tokens, dtype=np.uint8)
    rng = np.random.default_rng(seed)
    word_positions: list[int] = []
    for start, end in complete_word_intervals(wli):
        word_positions.extend(range(start, end))
    if len(set(word_positions)) < _target_position_count(int(arr.size), p):
        word_positions = list(range(int(arr.size)))
    positions = _sample_positions_exact(word_positions, count=_target_position_count(int(arr.size), p), rng=rng)
    return tuple(int(x) for x in _replace_positions_uniform(arr, positions, rng))


def damage_burst(tokens: Sequence[int], *, p: float, seed: int) -> tuple[int, ...]:
    arr = np.asarray(tokens, dtype=np.uint8)
    rng = np.random.default_rng(seed)
    n = int(arr.size)
    target = max(1, int(round(float(p) * n)))
    chosen: set[int] = set()
    attempts = 0
    while len(chosen) < target and attempts < 10_000:
        attempts += 1
        length = int(rng.integers(5, 21)) if rng.random() < 0.7 else int(rng.integers(25, 81))
        start = int(rng.integers(0, max(1, n)))
        for pos in range(start, min(n, start + length)):
            chosen.add(pos)
            if len(chosen) >= target:
                break
    return tuple(int(x) for x in _replace_positions_uniform(arr, np.asarray(sorted(chosen), dtype=np.int64), rng))


def damage_burst_target_actual(tokens: Sequence[int], *, p: float, seed: int) -> tuple[int, ...]:
    return damage_burst(tokens, p=p, seed=seed)


def damage_lane_period(tokens: Sequence[int], *, p: float, seed: int) -> tuple[int, ...]:
    arr = np.asarray(tokens, dtype=np.uint8)
    rng = np.random.default_rng(seed)
    n = int(arr.size)
    period = int(rng.choice(np.asarray([5, 7, 13, 19, 29], dtype=np.int64)))
    lane_count = int(rng.integers(1, min(3, period) + 1))
    lanes = set(int(x) for x in rng.choice(np.arange(period), size=lane_count, replace=False).tolist())
    positions = np.asarray([idx for idx in range(n) if (idx % period) in lanes], dtype=np.int64)
    if positions.size:
        positions = positions[rng.random(positions.size) < float(p)]
    return tuple(int(x) for x in _replace_positions_uniform(arr, positions, rng))


def damage_lane_period_target_actual(tokens: Sequence[int], *, p: float, seed: int) -> tuple[int, ...]:
    arr = np.asarray(tokens, dtype=np.uint8)
    rng = np.random.default_rng(seed)
    n = int(arr.size)
    period = int(rng.choice(np.asarray([5, 7, 13, 19, 29], dtype=np.int64)))
    lane_count = int(rng.integers(1, min(3, period) + 1))
    lanes = set(int(x) for x in rng.choice(np.arange(period), size=lane_count, replace=False).tolist())
    lane_positions = [idx for idx in range(n) if (idx % period) in lanes]
    target = _target_position_count(n, p)
    if len(lane_positions) < target:
        lane_positions.extend(idx for idx in range(n) if idx not in set(lane_positions))
    positions = _sample_positions_exact(lane_positions, count=target, rng=rng)
    return tuple(int(x) for x in _replace_positions_uniform(arr, positions, rng))


def null_uniform(tokens: Sequence[int], *, seed: int) -> tuple[int, ...]:
    rng = np.random.default_rng(seed)
    return tuple(int(x) for x in rng.integers(0, ALPHABET_SIZE, size=len(tokens), dtype=np.uint8))


def null_frequency(tokens: Sequence[int], *, seed: int, probs: np.ndarray) -> tuple[int, ...]:
    rng = np.random.default_rng(seed)
    return tuple(int(x) for x in rng.choice(np.arange(ALPHABET_SIZE, dtype=np.uint8), size=len(tokens), replace=True, p=probs))


def null_within_chunk_shuffle(tokens: Sequence[int], *, seed: int) -> tuple[int, ...]:
    rng = np.random.default_rng(seed)
    arr = np.asarray(tokens, dtype=np.uint8).copy()
    rng.shuffle(arr)
    return tuple(int(x) for x in arr)


def null_block_shuffle(tokens: Sequence[int], *, seed: int, block_size: int) -> tuple[int, ...]:
    rng = np.random.default_rng(seed)
    arr = np.asarray(tokens, dtype=np.uint8)
    blocks = [arr[i:i + block_size].copy() for i in range(0, int(arr.size), block_size)]
    order = np.arange(len(blocks))
    rng.shuffle(order)
    out = np.concatenate([blocks[int(idx)] for idx in order])
    return tuple(int(x) for x in out[: len(tokens)])


def make_variant(
    tokens: Sequence[int],
    *,
    model_name: str,
    damage_level: float | None,
    seed: int,
    wli: Sequence[tuple[int, int]] | None = None,
    global_probs: np.ndarray | None = None,
    book_probs: np.ndarray | None = None,
) -> tuple[int, ...]:
    p = float(damage_level or 0.0)
    probs_global = global_probs if global_probs is not None else empirical_probs(tokens)
    probs_book = book_probs if book_probs is not None else empirical_probs(tokens)
    if model_name == "independent_substitution":
        return damage_independent(tokens, p=p, seed=seed)
    if model_name == "frequency_matched_global":
        return damage_frequency_matched(tokens, p=p, seed=seed, probs=probs_global)
    if model_name == "frequency_matched_book":
        return damage_frequency_matched(tokens, p=p, seed=seed, probs=probs_book)
    if model_name == "word_local_substitution":
        if wli is None:
            raise ValueError("word_local_substitution requires wli")
        return damage_word_local(tokens, wli, p=p, seed=seed)
    if model_name == "burst_substitution":
        return damage_burst(tokens, p=p, seed=seed)
    if model_name == "lane_period_substitution":
        return damage_lane_period(tokens, p=p, seed=seed)
    if model_name == "uniform_random":
        return null_uniform(tokens, seed=seed)
    if model_name == "global_frequency_random":
        return null_frequency(tokens, seed=seed, probs=probs_global)
    if model_name == "within_chunk_shuffle":
        return null_within_chunk_shuffle(tokens, seed=seed)
    if model_name.startswith("block_shuffle_"):
        return null_block_shuffle(tokens, seed=seed, block_size=int(model_name.rsplit("_", 1)[1]))
    raise ValueError(f"unknown damage/null model: {model_name}")


def make_target_actual_damage_variant(
    tokens: Sequence[int],
    *,
    model_name: str,
    damage_level: float,
    seed: int,
    wli: Sequence[tuple[int, int]] | None = None,
    global_probs: np.ndarray | None = None,
    book_probs: np.ndarray | None = None,
) -> tuple[int, ...]:
    p = float(damage_level)
    probs_global = global_probs if global_probs is not None else empirical_probs(tokens)
    probs_book = book_probs if book_probs is not None else empirical_probs(tokens)
    if model_name == "independent_substitution":
        return damage_independent_target_actual(tokens, p=p, seed=seed)
    if model_name == "frequency_matched_global":
        return damage_frequency_matched_target_actual(tokens, p=p, seed=seed, probs=probs_global)
    if model_name == "frequency_matched_book":
        return damage_frequency_matched_target_actual(tokens, p=p, seed=seed, probs=probs_book)
    if model_name == "word_local_substitution":
        if wli is None:
            raise ValueError("word_local_substitution requires wli")
        return damage_word_local_target_actual(tokens, wli, p=p, seed=seed)
    if model_name == "burst_substitution":
        return damage_burst_target_actual(tokens, p=p, seed=seed)
    if model_name == "lane_period_substitution":
        return damage_lane_period_target_actual(tokens, p=p, seed=seed)
    raise ValueError(f"unknown target-actual damage model: {model_name}")


def self_test() -> None:
    tokens = tuple(range(ALPHABET_SIZE)) * 20
    tokens = tokens[:500]
    wli = tuple((i % 5, 5) for i in range(len(tokens)))
    for model in (
        "independent_substitution",
        "frequency_matched_global",
        "frequency_matched_book",
        "word_local_substitution",
        "burst_substitution",
        "lane_period_substitution",
        "uniform_random",
        "global_frequency_random",
        "within_chunk_shuffle",
        "block_shuffle_25",
    ):
        seed = stable_int_seed(GLOBAL_SEED, model, "self-test")
        a = make_variant(tokens, model_name=model, damage_level=0.40, seed=seed, wli=wli)
        b = make_variant(tokens, model_name=model, damage_level=0.40, seed=seed, wli=wli)
        assert a == b, model
        assert len(a) == len(tokens), model
        assert min(a) >= 0 and max(a) < ALPHABET_SIZE, model


if __name__ == "__main__":
    self_test()
    print("damage_models_reference_v1 self-test passed")
