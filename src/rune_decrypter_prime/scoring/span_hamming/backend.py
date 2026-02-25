from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

from rune_decrypter_prime.scoring.hamming.loader import load_raw1grams_wordlists
from rune_decrypter_prime.scoring.span_hamming.interval_select import select_non_overlapping
from rune_decrypter_prime.scoring.span_hamming.split_index import LengthSplitIndex
from rune_decrypter_prime.scoring.span_hamming.types import (
    SpanHammingConfig,
    SpanHammingStats,
    SpanInterval,
)


Wordlist = Dict[int, List[List[int]]]


def _hamming_distance_limited(lhs: Sequence[int], rhs: Sequence[int], max_value: int) -> int:
    mismatch = 0
    for left, right in zip(lhs, rhs):
        if left != right:
            mismatch += 1
            if mismatch > max_value:
                return mismatch
    return mismatch


class SpanHammingBackend:
    """
    No-WLI word-likeness scorer using approximate dictionary matching on spans.

    Score is computed from non-overlapping selected intervals:
      weight = quality * length
      quality = 1 - min(distance, max_hd + 1)/(max_hd + 1)
    """

    def __init__(
        self,
        config: SpanHammingConfig | None = None,
        *,
        wordlists: Wordlist | None = None,
        wordlist_dir: str | Path | None = None,
        require_selected: bool = True,
    ) -> None:
        self.config = config or SpanHammingConfig()
        self.length_bins: Tuple[int, ...] = tuple(range(self.config.len_min, self.config.len_max + 1))
        self._max_dist = int(self.config.max_hd) + 1

        if wordlists is None:
            loaded_ltr, _ = load_raw1grams_wordlists(
                wordlist_dir,
                build_rtl=False,
                require_selected=require_selected,
            )
            wordlists = loaded_ltr

        self._words_by_len = self._normalize_wordlists(wordlists)
        self._index_by_len: Dict[int, LengthSplitIndex] = {}
        for length in self.length_bins:
            words = self._words_by_len.get(length, tuple())
            if not words:
                continue
            self._index_by_len[length] = LengthSplitIndex.build(
                length,
                words,
                max_hd=self.config.max_hd,
            )

    def _normalize_wordlists(self, wordlists: Wordlist | None) -> Dict[int, Tuple[Tuple[int, ...], ...]]:
        normalized: Dict[int, Tuple[Tuple[int, ...], ...]] = {}
        if not wordlists:
            return normalized
        for length in self.length_bins:
            words_for_length = wordlists.get(length, [])
            deduped = sorted(
                {
                    tuple(int(token) for token in word)
                    for word in words_for_length
                    if len(word) == length
                }
            )
            if deduped:
                normalized[length] = tuple(deduped)
        return normalized

    def _build_zero_stats(self, n_chars: int) -> SpanHammingStats:
        n_bins = len(self.length_bins)
        zero_floats = tuple(0.0 for _ in range(n_bins))
        zero_ints = tuple(0 for _ in range(n_bins))
        return SpanHammingStats(
            span_raw=0.0,
            coverage=0.0,
            quality=0.0,
            n_chars=int(n_chars),
            chars_covered=0,
            n_intervals_selected=0,
            length_bins=self.length_bins,
            span_raw_by_len=zero_floats,
            coverage_by_len=zero_floats,
            quality_by_len=zero_floats,
            selected_intervals_by_len=zero_ints,
            chars_covered_by_len=zero_ints,
            n_windows_total=0,
            n_windows_scored=0,
            n_candidates_considered=0,
            n_candidates_pruned_cap=0,
            selected_intervals=tuple(),
        )

    def score(self, text_idx: Sequence[int] | Iterable[int]) -> SpanHammingStats:
        text = tuple(int(token) for token in text_idx)
        n_chars = len(text)
        if n_chars == 0 or n_chars < self.config.len_min:
            return self._build_zero_stats(n_chars)

        intervals: List[SpanInterval] = []
        n_windows_total = 0
        n_windows_scored = 0
        n_candidates_considered = 0
        n_candidates_pruned_cap = 0

        for start in range(n_chars):
            intervals_for_start: List[SpanInterval] = []

            for length in self.length_bins:
                end = start + length
                if end > n_chars:
                    continue
                n_windows_total += 1

                index = self._index_by_len.get(length)
                if index is None:
                    continue

                window = text[start:end]
                candidate_ids = index.candidate_word_ids(window)
                if not candidate_ids:
                    continue

                n_windows_scored += 1
                n_candidates_considered += len(candidate_ids)

                scored_candidates = []
                for word_id in candidate_ids:
                    dict_word = index.words[word_id]
                    distance = _hamming_distance_limited(window, dict_word, self._max_dist)
                    clipped_distance = min(distance, self._max_dist)
                    quality = 1.0 - (float(clipped_distance) / float(self._max_dist))
                    weight = quality * float(length)
                    scored_candidates.append((clipped_distance, -weight, word_id, quality, weight))

                scored_candidates.sort()
                if len(scored_candidates) > self.config.max_candidates_per_window:
                    n_candidates_pruned_cap += len(scored_candidates) - self.config.max_candidates_per_window
                    scored_candidates = scored_candidates[: self.config.max_candidates_per_window]

                best_distance, _, _, best_quality, best_weight = scored_candidates[0]
                if best_quality < self.config.min_quality_threshold:
                    continue
                intervals_for_start.append(
                    SpanInterval(
                        start=start,
                        end=end,
                        length=length,
                        distance=int(best_distance),
                        quality=float(best_quality),
                        weight=float(best_weight),
                    )
                )

            if len(intervals_for_start) > self.config.max_intervals_considered_per_start:
                intervals_for_start.sort(key=lambda item: (-item.weight, item.end, item.start, -item.length))
                intervals_for_start = intervals_for_start[: self.config.max_intervals_considered_per_start]

            intervals.extend(intervals_for_start)

        selected = select_non_overlapping(intervals)
        covered_chars = int(sum(item.length for item in selected))
        sum_weight = float(sum(item.weight for item in selected))

        denom_n = float(max(1, n_chars))
        coverage = float(covered_chars) / denom_n
        quality = sum_weight / float(max(1, covered_chars))
        span_raw = sum_weight / denom_n

        len_to_index = {length: idx for idx, length in enumerate(self.length_bins)}
        sum_weight_by_len = [0.0 for _ in self.length_bins]
        covered_chars_by_len = [0 for _ in self.length_bins]
        selected_intervals_by_len = [0 for _ in self.length_bins]

        for item in selected:
            idx = len_to_index[item.length]
            sum_weight_by_len[idx] += item.weight
            covered_chars_by_len[idx] += item.length
            selected_intervals_by_len[idx] += 1

        span_raw_by_len = tuple(weight / denom_n for weight in sum_weight_by_len)
        coverage_by_len = tuple(float(chars) / denom_n for chars in covered_chars_by_len)
        quality_by_len = tuple(
            (sum_weight_by_len[idx] / float(max(1, covered_chars_by_len[idx])))
            for idx in range(len(self.length_bins))
        )

        selected_intervals_debug = selected if self.config.debug_return_intervals else tuple()
        return SpanHammingStats(
            span_raw=span_raw,
            coverage=coverage,
            quality=quality,
            n_chars=n_chars,
            chars_covered=covered_chars,
            n_intervals_selected=len(selected),
            length_bins=self.length_bins,
            span_raw_by_len=span_raw_by_len,
            coverage_by_len=coverage_by_len,
            quality_by_len=quality_by_len,
            selected_intervals_by_len=tuple(selected_intervals_by_len),
            chars_covered_by_len=tuple(covered_chars_by_len),
            n_windows_total=n_windows_total,
            n_windows_scored=n_windows_scored,
            n_candidates_considered=n_candidates_considered,
            n_candidates_pruned_cap=n_candidates_pruned_cap,
            selected_intervals=selected_intervals_debug,
        )

