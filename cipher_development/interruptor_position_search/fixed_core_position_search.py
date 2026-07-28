from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Callable, Iterable, Sequence

import numpy as np

Subset = tuple[int, ...]
ScoreSubsets = Callable[[tuple[Subset, ...]], np.ndarray]


@dataclass(frozen=True, slots=True)
class PositionCandidate:
    positions: Subset
    score: float


@dataclass(frozen=True, slots=True)
class PositionSearchRound:
    round_index: int
    generated: int
    newly_evaluated: int
    cache_size: int
    beam_size: int
    best_positions: Subset
    best_score: float
    improved: bool


@dataclass(frozen=True, slots=True)
class PositionSearchOutcome:
    best: PositionCandidate
    beam: tuple[PositionCandidate, ...]
    rounds: tuple[PositionSearchRound, ...]
    evaluations: int
    stopped_reason: str


def _canonical_subset(
    values: Iterable[int],
    *,
    pool_set: frozenset[int],
    min_count: int,
    max_count: int,
) -> Subset:
    subset = tuple(int(value) for value in values)
    if subset != tuple(sorted(subset)):
        raise ValueError("interruptor positions must be sorted")
    if len(set(subset)) != len(subset):
        raise ValueError("interruptor positions must be unique")
    if not min_count <= len(subset) <= max_count:
        raise ValueError("interruptor position count is outside the search range")
    missing = [value for value in subset if value not in pool_set]
    if missing:
        raise ValueError(f"interruptor positions are outside the pool: {missing}")
    return subset


def _candidate_sort_key(candidate: PositionCandidate) -> tuple:
    return (-candidate.score, len(candidate.positions), candidate.positions)


def _seed_subsets(
    pool: tuple[int, ...],
    *,
    min_count: int,
    max_count: int,
) -> set[Subset]:
    seeds: set[Subset] = set()
    if min_count == 0:
        seeds.add(())
    if min_count <= 1 <= max_count:
        seeds.update((value,) for value in pool)

    n = len(pool)
    for count in range(max(2, min_count), max_count + 1):
        if count > n:
            break
        for offset in range(min(n, max(1, count * 2))):
            indices = sorted(
                {
                    min(n - 1, ((2 * i + 1) * n) // (2 * count) + offset)
                    for i in range(count)
                }
            )
            if len(indices) == count:
                seeds.add(tuple(pool[index] for index in indices))
    return seeds


def _neighbours(
    subset: Subset,
    pool: tuple[int, ...],
    *,
    min_count: int,
    max_count: int,
) -> set[Subset]:
    selected = set(subset)
    unselected = tuple(value for value in pool if value not in selected)
    neighbours: set[Subset] = set()
    if len(subset) < max_count:
        for value in unselected:
            neighbours.add(tuple(sorted((*subset, value))))
    if len(subset) > min_count:
        for value in subset:
            neighbours.add(tuple(item for item in subset if item != value))
    if subset and unselected:
        for old in subset:
            kept = tuple(item for item in subset if item != old)
            for new in unselected:
                neighbours.add(tuple(sorted((*kept, new))))
    return neighbours


def search_fixed_core_positions(
    *,
    pool: Sequence[int],
    min_count: int,
    max_count: int,
    evaluate_subsets: ScoreSubsets,
    beam_width: int = 512,
    maximum_rounds: int = 24,
    plateau_rounds: int = 8,
    minimum_delta: float = 1e-4,
    evaluation_batch_size: int = 2048,
) -> PositionSearchOutcome:
    pool_tuple = tuple(sorted(int(value) for value in pool))
    if len(set(pool_tuple)) != len(pool_tuple):
        raise ValueError("interruptor pool must contain unique positions")
    if not pool_tuple:
        raise ValueError("interruptor pool must not be empty")
    if min_count < 0:
        raise ValueError("min_count must be non-negative")
    if max_count < min_count:
        raise ValueError("max_count must be at least min_count")
    if max_count > len(pool_tuple):
        raise ValueError("max_count cannot exceed pool size")
    for name, value in (
        ("beam_width", beam_width),
        ("maximum_rounds", maximum_rounds),
        ("plateau_rounds", plateau_rounds),
        ("evaluation_batch_size", evaluation_batch_size),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"{name} must be a positive integer")
    if not isfinite(float(minimum_delta)) or minimum_delta < 0:
        raise ValueError("minimum_delta must be finite and non-negative")

    pool_set = frozenset(pool_tuple)
    cache: dict[Subset, float] = {}
    evaluations = 0

    def score(items: Iterable[Subset]) -> int:
        nonlocal evaluations
        pending = sorted(
            {
                _canonical_subset(
                    item,
                    pool_set=pool_set,
                    min_count=min_count,
                    max_count=max_count,
                )
                for item in items
                if item not in cache
            },
            key=lambda item: (len(item), item),
        )
        newly_evaluated = 0
        for start in range(0, len(pending), evaluation_batch_size):
            batch = tuple(pending[start : start + evaluation_batch_size])
            values = np.asarray(evaluate_subsets(batch), dtype=np.float64)
            if values.shape != (len(batch),):
                raise ValueError(
                    "position evaluator must return one score per candidate subset"
                )
            if not np.all(np.isfinite(values)):
                raise ValueError("position evaluator returned a non-finite score")
            for subset, value in zip(batch, values.tolist()):
                cache[subset] = float(value)
            newly_evaluated += len(batch)
        evaluations += newly_evaluated
        return newly_evaluated

    seeds = _seed_subsets(pool_tuple, min_count=min_count, max_count=max_count)
    if not seeds:
        seeds.add(tuple(pool_tuple[:min_count]))
    score(seeds)

    beam = sorted(
        (PositionCandidate(item, cache[item]) for item in seeds),
        key=_candidate_sort_key,
    )[:beam_width]
    if not beam:
        raise RuntimeError("position search produced an empty initial beam")

    trace: list[PositionSearchRound] = []
    best_score = beam[0].score
    stagnant = 0
    for round_index in range(1, maximum_rounds + 1):
        generated: set[Subset] = {candidate.positions for candidate in beam}
        for candidate in beam:
            generated.update(
                _neighbours(
                    candidate.positions,
                    pool_tuple,
                    min_count=min_count,
                    max_count=max_count,
                )
            )
        newly_evaluated = score(generated)
        new_beam = sorted(
            (PositionCandidate(item, cache[item]) for item in generated),
            key=_candidate_sort_key,
        )[:beam_width]
        current_best = new_beam[0].score
        improved = current_best > best_score + minimum_delta
        if improved:
            best_score = current_best
            stagnant = 0
        else:
            stagnant += 1
        trace.append(
            PositionSearchRound(
                round_index=round_index,
                generated=len(generated),
                newly_evaluated=newly_evaluated,
                cache_size=len(cache),
                beam_size=len(new_beam),
                best_positions=new_beam[0].positions,
                best_score=new_beam[0].score,
                improved=improved,
            )
        )
        beam = new_beam
        if round_index >= max_count and stagnant >= plateau_rounds:
            return PositionSearchOutcome(
                best=beam[0],
                beam=tuple(beam),
                rounds=tuple(trace),
                evaluations=evaluations,
                stopped_reason="plateau",
            )

    return PositionSearchOutcome(
        best=beam[0],
        beam=tuple(beam),
        rounds=tuple(trace),
        evaluations=evaluations,
        stopped_reason="maximum_rounds",
    )
