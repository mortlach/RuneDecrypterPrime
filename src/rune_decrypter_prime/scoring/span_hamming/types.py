from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class SpanHammingConfig:
    len_min: int = 3
    len_max: int = 14
    max_hd: int = 2
    overlap_policy: str = "non_overlapping"
    max_candidates_per_window: int = 256
    max_intervals_considered_per_start: int = 4
    min_quality_threshold: float = 1e-9
    debug_return_intervals: bool = False

    def __post_init__(self) -> None:
        if self.len_min < 1:
            raise ValueError("len_min must be >= 1")
        if self.len_max < self.len_min:
            raise ValueError("len_max must be >= len_min")
        if self.max_hd < 0:
            raise ValueError("max_hd must be >= 0")
        if self.overlap_policy != "non_overlapping":
            raise ValueError("only overlap_policy='non_overlapping' is supported")
        if self.max_candidates_per_window < 1:
            raise ValueError("max_candidates_per_window must be >= 1")
        if self.max_intervals_considered_per_start < 1:
            raise ValueError("max_intervals_considered_per_start must be >= 1")
        if not (0.0 <= float(self.min_quality_threshold) <= 1.0):
            raise ValueError("min_quality_threshold must be in [0, 1]")


@dataclass(frozen=True)
class SpanInterval:
    start: int
    end: int
    length: int
    distance: int
    quality: float
    weight: float

    @property
    def canonical_key(self) -> Tuple[int, int, int]:
        return (self.end, self.start, -self.length)


@dataclass(frozen=True)
class SpanHammingStats:
    span_raw: float
    coverage: float
    quality: float
    n_chars: int
    chars_covered: int
    n_intervals_selected: int
    length_bins: Tuple[int, ...]
    span_raw_by_len: Tuple[float, ...]
    coverage_by_len: Tuple[float, ...]
    quality_by_len: Tuple[float, ...]
    selected_intervals_by_len: Tuple[int, ...]
    chars_covered_by_len: Tuple[int, ...]
    n_windows_total: int
    n_windows_scored: int
    n_candidates_considered: int
    n_candidates_pruned_cap: int
    selected_intervals: Tuple[SpanInterval, ...] = ()

