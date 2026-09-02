from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from typing import Sequence, Tuple

from rdp.scoring.span_hamming.types import SpanInterval


_EPS = 1e-12


@dataclass(frozen=True)
class _Plan:
    total_weight: float
    covered_chars: int
    selected_indices: Tuple[int, ...]
    canonical_keys: Tuple[Tuple[int, int, int], ...]


def _better_plan(plan_a: _Plan, plan_b: _Plan) -> _Plan:
    if plan_a.total_weight > plan_b.total_weight + _EPS:
        return plan_a
    if plan_b.total_weight > plan_a.total_weight + _EPS:
        return plan_b

    if plan_a.covered_chars > plan_b.covered_chars:
        return plan_a
    if plan_b.covered_chars > plan_a.covered_chars:
        return plan_b

    if plan_a.canonical_keys < plan_b.canonical_keys:
        return plan_a
    if plan_b.canonical_keys < plan_a.canonical_keys:
        return plan_b
    return plan_a


def select_non_overlapping(intervals: Sequence[SpanInterval]) -> Tuple[SpanInterval, ...]:
    if not intervals:
        return tuple()

    ordered = sorted(intervals, key=lambda item: item.canonical_key)
    ends = [item.end for item in ordered]
    predecessors = []
    for item in ordered:
        # Largest index with end <= item.start.
        prev_idx = bisect_right(ends, item.start) - 1
        predecessors.append(prev_idx)

    dp = [_Plan(total_weight=0.0, covered_chars=0, selected_indices=tuple(), canonical_keys=tuple())]

    for idx, item in enumerate(ordered):
        include_base = dp[predecessors[idx] + 1]
        include = _Plan(
            total_weight=include_base.total_weight + item.weight,
            covered_chars=include_base.covered_chars + item.length,
            selected_indices=include_base.selected_indices + (idx,),
            canonical_keys=include_base.canonical_keys + (item.canonical_key,),
        )
        exclude = dp[-1]
        dp.append(_better_plan(include, exclude))

    chosen = dp[-1].selected_indices
    return tuple(ordered[i] for i in chosen)

