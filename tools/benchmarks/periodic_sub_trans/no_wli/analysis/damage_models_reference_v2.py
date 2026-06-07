from __future__ import annotations

"""
Strict O3 known-damage calibration reference damage models v2.

Goal
----
For calibration, every non-null damaged sample must hit the requested actual
changed fraction within tolerance *without flattening the intended damage shape*.

This module is intentionally standalone and deterministic. It is suitable for
focused tests and for wiring into the existing calibration scripts.
"""

import hashlib
from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np

GLOBAL_SEED = 20260507
ALPHABET_SIZE = 29
DEFAULT_TOLERANCE = 0.01

DAMAGE_MODELS = (
    "independent_substitution",
    "frequency_matched_global",
    "frequency_matched_book",
    "word_local_substitution",
    "burst_substitution",
    "lane_period_substitution",
)

ORDINARY_NULL_MODELS = (
    "uniform_random",
    "global_frequency_random",
    "within_chunk_shuffle",
)

HARD_LOCAL_ORDER_CONTROLS = (
    "block_shuffle_10",
    "block_shuffle_25",
    "block_shuffle_50",
)


@dataclass(frozen=True)
class DamageResult:
    model_name: str
    requested_damage_level: float
    tokens: tuple[int, ...]
    changed_positions: tuple[int, ...]
    actual_changed_fraction: float
    metadata: dict[str, Any]

    def assert_within_tolerance(self, *, tolerance: float = DEFAULT_TOLERANCE) -> None:
        delta = abs(self.actual_changed_fraction - float(self.requested_damage_level))
        if delta > float(tolerance):
            raise AssertionError(
                f"{self.model_name} actual damage {self.actual_changed_fraction:.12g} "
                f"missed requested {self.requested_damage_level:.12g} by {delta:.12g}"
            )


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


def changed_positions_between(left: Sequence[int], right: Sequence[int]) -> tuple[int, ...]:
    if len(left) != len(right):
        raise ValueError(f"length mismatch: {len(left)} != {len(right)}")
    return tuple(idx for idx, (a, b) in enumerate(zip(left, right)) if int(a) != int(b))


def changed_fraction(left: Sequence[int], right: Sequence[int]) -> float:
    if len(left) != len(right):
        raise ValueError(f"length mismatch: {len(left)} != {len(right)}")
    if not left:
        return 0.0
    return len(changed_positions_between(left, right)) / float(len(left))


def _target_position_count(n: int, p: float) -> int:
    if n <= 0:
        return 0
    if float(p) <= 0.0:
        return 0
    if float(p) >= 1.0:
        return n
    return min(n, max(0, int(round(float(p) * n))))


def _validate_tokens(tokens: Sequence[int]) -> np.ndarray:
    arr = np.asarray(tokens, dtype=np.uint8)
    if arr.size and (int(arr.min()) < 0 or int(arr.max()) >= ALPHABET_SIZE):
        raise ValueError(f"token outside 0..{ALPHABET_SIZE - 1}")
    return arr


def _sample_positions_exact(pool: Sequence[int] | np.ndarray, *, count: int, rng: np.random.Generator) -> np.ndarray:
    unique = np.unique(np.asarray(pool, dtype=np.int64))
    if count <= 0:
        return np.asarray([], dtype=np.int64)
    if unique.size < count:
        raise ValueError(f"not enough candidate positions for target damage count: {unique.size} < {count}")
    chosen = rng.choice(unique, size=count, replace=False)
    return np.asarray(sorted(int(x) for x in chosen.tolist()), dtype=np.int64)


def _replace_positions_uniform(tokens: np.ndarray, positions: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    out = tokens.copy()
    if positions.size == 0:
        return out
    original = out[positions].astype(np.int16)
    repl = rng.integers(0, ALPHABET_SIZE - 1, size=positions.size, dtype=np.int16)
    repl = repl + (repl >= original)
    out[positions] = repl.astype(np.uint8)
    return out


def _fallback_uniform_values(original_values: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    original = original_values.astype(np.int16)
    repl = rng.integers(0, ALPHABET_SIZE - 1, size=original.size, dtype=np.int16)
    repl = repl + (repl >= original)
    return repl.astype(np.uint8)


def _replace_positions_from_probs(
    tokens: np.ndarray,
    positions: np.ndarray,
    rng: np.random.Generator,
    probs: np.ndarray,
) -> np.ndarray:
    out = tokens.copy()
    if positions.size == 0:
        return out
    probs_arr = np.asarray(probs, dtype=np.float64)
    if probs_arr.shape != (ALPHABET_SIZE,):
        raise ValueError(f"expected probs shape {(ALPHABET_SIZE,)}, got {probs_arr.shape}")
    total = float(probs_arr.sum())
    if not np.isfinite(total) or total <= 0.0:
        probs_arr = np.ones(ALPHABET_SIZE, dtype=np.float64) / float(ALPHABET_SIZE)
    else:
        probs_arr = probs_arr / total
    alphabet = np.arange(ALPHABET_SIZE, dtype=np.uint8)
    original = out[positions]
    repl = rng.choice(alphabet, size=positions.size, replace=True, p=probs_arr).astype(np.uint8)
    same = repl == original
    guard = 0
    while bool(np.any(same)) and guard < 20:
        repl[same] = rng.choice(alphabet, size=int(np.sum(same)), replace=True, p=probs_arr).astype(np.uint8)
        same = repl == original
        guard += 1
    if bool(np.any(same)):
        # Important: update repl itself. Do not write to out and then overwrite it.
        repl[same] = _fallback_uniform_values(original[same], rng)
    if bool(np.any(repl == original)):
        raise AssertionError("replacement fallback failed to change all selected positions")
    out[positions] = repl
    return out


def complete_word_intervals(wli: Sequence[tuple[int, int]]) -> list[tuple[int, int]]:
    arr = np.asarray(wli, dtype=np.int64)
    if arr.ndim != 2 or arr.shape[1] != 2:
        raise ValueError(f"unexpected WLI shape {arr.shape}")
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


def _result(
    *,
    model_name: str,
    requested_damage_level: float,
    original: Sequence[int],
    damaged: Sequence[int],
    metadata: dict[str, Any],
) -> DamageResult:
    positions = changed_positions_between(original, damaged)
    return DamageResult(
        model_name=model_name,
        requested_damage_level=float(requested_damage_level),
        tokens=tuple(int(x) for x in damaged),
        changed_positions=tuple(int(x) for x in positions),
        actual_changed_fraction=(len(positions) / float(len(original))) if original else 0.0,
        metadata=dict(metadata),
    )


def damage_independent_target_actual_result(tokens: Sequence[int], *, p: float, seed: int) -> DamageResult:
    arr = _validate_tokens(tokens)
    rng = np.random.default_rng(seed)
    target = _target_position_count(int(arr.size), p)
    positions = _sample_positions_exact(np.arange(int(arr.size)), count=target, rng=rng)
    out = _replace_positions_uniform(arr, positions, rng)
    return _result(
        model_name="independent_substitution",
        requested_damage_level=p,
        original=tuple(int(x) for x in arr),
        damaged=tuple(int(x) for x in out),
        metadata={"target_count": target, "shape": "independent_exact_positions"},
    )


def damage_frequency_matched_target_actual_result(
    tokens: Sequence[int],
    *,
    p: float,
    seed: int,
    probs: np.ndarray,
    model_name: str,
) -> DamageResult:
    arr = _validate_tokens(tokens)
    rng = np.random.default_rng(seed)
    target = _target_position_count(int(arr.size), p)
    positions = _sample_positions_exact(np.arange(int(arr.size)), count=target, rng=rng)
    out = _replace_positions_from_probs(arr, positions, rng, probs)
    return _result(
        model_name=model_name,
        requested_damage_level=p,
        original=tuple(int(x) for x in arr),
        damaged=tuple(int(x) for x in out),
        metadata={"target_count": target, "shape": "frequency_matched_exact_positions"},
    )


def damage_word_local_target_actual_result(
    tokens: Sequence[int],
    wli: Sequence[tuple[int, int]],
    *,
    p: float,
    seed: int,
) -> DamageResult:
    arr = _validate_tokens(tokens)
    rng = np.random.default_rng(seed)
    target = _target_position_count(int(arr.size), p)
    intervals = complete_word_intervals(wli)
    if target == 0:
        return _result(
            model_name="word_local_substitution",
            requested_damage_level=p,
            original=tuple(int(x) for x in arr),
            damaged=tuple(int(x) for x in arr),
            metadata={"target_count": 0, "shape": "word_local_exact_count", "selected_word_count": 0, "partial_word_used": False},
        )
    capacity = sum(end - start for start, end in intervals)
    if capacity < target:
        raise ValueError(f"complete word intervals cover only {capacity} positions; target is {target}")

    order = np.arange(len(intervals))
    rng.shuffle(order)
    chosen: list[int] = []
    selected_intervals: list[tuple[int, int, str]] = []
    for interval_idx in order.tolist():
        start, end = intervals[int(interval_idx)]
        remaining = target - len(chosen)
        if remaining <= 0:
            break
        length = end - start
        if length <= remaining:
            chosen.extend(range(start, end))
            selected_intervals.append((start, end, "whole"))
        else:
            # One partial final word keeps word locality while allowing exact global count.
            max_offset = length - remaining
            offset = int(rng.integers(0, max_offset + 1)) if max_offset > 0 else 0
            partial_start = start + offset
            partial_end = partial_start + remaining
            chosen.extend(range(partial_start, partial_end))
            selected_intervals.append((partial_start, partial_end, "partial"))
            break
    if len(set(chosen)) != target:
        raise AssertionError(f"word-local target selection produced {len(set(chosen))} positions, expected {target}")
    positions = np.asarray(sorted(set(chosen)), dtype=np.int64)
    out = _replace_positions_uniform(arr, positions, rng)
    return _result(
        model_name="word_local_substitution",
        requested_damage_level=p,
        original=tuple(int(x) for x in arr),
        damaged=tuple(int(x) for x in out),
        metadata={
            "target_count": target,
            "shape": "word_local_exact_count",
            "selected_word_count": len(selected_intervals),
            "partial_word_used": any(kind == "partial" for *_rest, kind in selected_intervals),
            "selected_intervals": selected_intervals,
        },
    )


def _run_count(sorted_positions: Sequence[int]) -> int:
    if not sorted_positions:
        return 0
    runs = 1
    previous = int(sorted_positions[0])
    for raw in sorted_positions[1:]:
        current = int(raw)
        if current != previous + 1:
            runs += 1
        previous = current
    return runs


def damage_burst_target_actual_result(tokens: Sequence[int], *, p: float, seed: int) -> DamageResult:
    arr = _validate_tokens(tokens)
    rng = np.random.default_rng(seed)
    n = int(arr.size)
    target = _target_position_count(n, p)
    chosen: set[int] = set()
    attempts = 0
    while len(chosen) < target and attempts < 20_000:
        attempts += 1
        if target - len(chosen) <= 0:
            break
        remaining = target - len(chosen)
        proposed = int(rng.integers(5, 21)) if rng.random() < 0.7 else int(rng.integers(25, 81))
        length = max(1, min(remaining, proposed))
        start = int(rng.integers(0, max(1, n)))
        for pos in range(start, min(n, start + length)):
            chosen.add(pos)
            if len(chosen) >= target:
                break
    if len(chosen) < target:
        # Deterministic fill by extending existing burst-like coverage, not random one-offs.
        for pos in range(n):
            chosen.add(pos)
            if len(chosen) >= target:
                break
    positions = np.asarray(sorted(chosen), dtype=np.int64)
    if positions.size != target:
        raise AssertionError(f"burst target selection produced {positions.size} positions, expected {target}")
    out = _replace_positions_uniform(arr, positions, rng)
    return _result(
        model_name="burst_substitution",
        requested_damage_level=p,
        original=tuple(int(x) for x in arr),
        damaged=tuple(int(x) for x in out),
        metadata={"target_count": target, "shape": "burst_exact_count", "run_count": _run_count(positions.tolist())},
    )


def damage_lane_period_target_actual_result(tokens: Sequence[int], *, p: float, seed: int) -> DamageResult:
    arr = _validate_tokens(tokens)
    rng = np.random.default_rng(seed)
    n = int(arr.size)
    target = _target_position_count(n, p)
    if target == 0:
        return _result(
            model_name="lane_period_substitution",
            requested_damage_level=p,
            original=tuple(int(x) for x in arr),
            damaged=tuple(int(x) for x in arr),
            metadata={"target_count": 0, "shape": "lane_period_exact_count", "period": None, "lanes": []},
        )

    candidate_periods = [5, 7, 13, 19, 29]
    order = np.arange(len(candidate_periods))
    rng.shuffle(order)
    selected: tuple[int, tuple[int, ...], list[int]] | None = None
    for idx in order.tolist():
        period = candidate_periods[int(idx)]
        # Preserve the old spirit: up to three selected lanes. Pick enough lanes for the target.
        min_lanes = max(1, int(np.ceil((target / float(max(1, n))) * period)))
        if min_lanes > min(3, period):
            continue
        lane_order = np.arange(period)
        rng.shuffle(lane_order)
        lanes = tuple(sorted(int(x) for x in lane_order[:min_lanes].tolist()))
        lane_positions = [pos for pos in range(n) if (pos % period) in lanes]
        if len(lane_positions) >= target:
            selected = (period, lanes, lane_positions)
            break
    if selected is None:
        raise ValueError(f"no lane-period configuration can support target count {target} for n={n}")
    period, lanes, lane_positions = selected
    positions = _sample_positions_exact(lane_positions, count=target, rng=rng)
    if any((int(pos) % period) not in set(lanes) for pos in positions.tolist()):
        raise AssertionError("lane-period selection leaked off selected lanes")
    out = _replace_positions_uniform(arr, positions, rng)
    return _result(
        model_name="lane_period_substitution",
        requested_damage_level=p,
        original=tuple(int(x) for x in arr),
        damaged=tuple(int(x) for x in out),
        metadata={
            "target_count": target,
            "shape": "lane_period_exact_count",
            "period": period,
            "lanes": list(lanes),
            "lane_capacity": len(lane_positions),
            "off_lane_fallback_used": False,
        },
    )


def make_target_actual_damage_result(
    tokens: Sequence[int],
    *,
    model_name: str,
    damage_level: float,
    seed: int,
    wli: Sequence[tuple[int, int]] | None = None,
    global_probs: np.ndarray | None = None,
    book_probs: np.ndarray | None = None,
    tolerance: float = DEFAULT_TOLERANCE,
) -> DamageResult:
    p = float(damage_level)
    probs_global = global_probs if global_probs is not None else empirical_probs(tokens)
    probs_book = book_probs if book_probs is not None else empirical_probs(tokens)
    if model_name == "independent_substitution":
        result = damage_independent_target_actual_result(tokens, p=p, seed=seed)
    elif model_name == "frequency_matched_global":
        result = damage_frequency_matched_target_actual_result(
            tokens, p=p, seed=seed, probs=probs_global, model_name=model_name
        )
    elif model_name == "frequency_matched_book":
        result = damage_frequency_matched_target_actual_result(
            tokens, p=p, seed=seed, probs=probs_book, model_name=model_name
        )
    elif model_name == "word_local_substitution":
        if wli is None:
            raise ValueError("word_local_substitution requires wli")
        result = damage_word_local_target_actual_result(tokens, wli, p=p, seed=seed)
    elif model_name == "burst_substitution":
        result = damage_burst_target_actual_result(tokens, p=p, seed=seed)
    elif model_name == "lane_period_substitution":
        result = damage_lane_period_target_actual_result(tokens, p=p, seed=seed)
    else:
        raise ValueError(f"unknown target-actual damage model: {model_name}")
    result.assert_within_tolerance(tolerance=tolerance)
    return result


def make_target_actual_damage_variant(*args: Any, **kwargs: Any) -> tuple[int, ...]:
    """Compatibility wrapper for callers that expect only token tuples."""
    return make_target_actual_damage_result(*args, **kwargs).tokens


def null_uniform(tokens: Sequence[int], *, seed: int) -> tuple[int, ...]:
    rng = np.random.default_rng(seed)
    return tuple(int(x) for x in rng.integers(0, ALPHABET_SIZE, size=len(tokens), dtype=np.uint8))


def null_frequency(tokens: Sequence[int], *, seed: int, probs: np.ndarray) -> tuple[int, ...]:
    rng = np.random.default_rng(seed)
    probs_arr = np.asarray(probs, dtype=np.float64)
    probs_arr = probs_arr / float(probs_arr.sum()) if float(probs_arr.sum()) > 0 else empirical_probs(tokens)
    return tuple(int(x) for x in rng.choice(np.arange(ALPHABET_SIZE, dtype=np.uint8), size=len(tokens), replace=True, p=probs_arr))


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
    out = np.concatenate([blocks[int(idx)] for idx in order]) if blocks else np.asarray([], dtype=np.uint8)
    return tuple(int(x) for x in out[: len(tokens)])


def null_class_for_model(model_name: str) -> str:
    if model_name in ORDINARY_NULL_MODELS:
        return "ordinary_null"
    if model_name in HARD_LOCAL_ORDER_CONTROLS or model_name.startswith("block_shuffle_"):
        return "hard_local_order_control"
    if model_name in DAMAGE_MODELS:
        return "damaged"
    if model_name == "clean":
        return "clean"
    raise ValueError(f"unknown model_name: {model_name}")


def make_null_or_control_variant(
    tokens: Sequence[int],
    *,
    model_name: str,
    seed: int,
    global_probs: np.ndarray | None = None,
) -> tuple[int, ...]:
    probs = global_probs if global_probs is not None else empirical_probs(tokens)
    if model_name == "uniform_random":
        return null_uniform(tokens, seed=seed)
    if model_name == "global_frequency_random":
        return null_frequency(tokens, seed=seed, probs=probs)
    if model_name == "within_chunk_shuffle":
        return null_within_chunk_shuffle(tokens, seed=seed)
    if model_name.startswith("block_shuffle_"):
        return null_block_shuffle(tokens, seed=seed, block_size=int(model_name.rsplit("_", 1)[1]))
    raise ValueError(f"unknown null/control model: {model_name}")
