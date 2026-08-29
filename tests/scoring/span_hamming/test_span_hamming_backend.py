from __future__ import annotations
import pytest
from rune_decrypter_prime.scoring.span_hamming.backend import SpanHammingBackend
from rune_decrypter_prime.scoring.span_hamming.types import SpanHammingConfig

def _build_backend(wordlists, *, len_min: int, len_max: int, max_hd: int=2, start_stride: int=1, max_windows_total: int=0, debug_return_intervals: bool=False, min_quality_threshold: float=1e-09, max_candidates_per_window: int=256, max_intervals_considered_per_start: int=4) -> SpanHammingBackend:
    cfg = SpanHammingConfig(len_min=len_min, len_max=len_max, max_hd=max_hd, start_stride=start_stride, max_windows_total=max_windows_total, debug_return_intervals=debug_return_intervals, min_quality_threshold=min_quality_threshold, max_candidates_per_window=max_candidates_per_window, max_intervals_considered_per_start=max_intervals_considered_per_start)
    return SpanHammingBackend(config=cfg, wordlists=wordlists)

def test_exact_match_full_score():
    backend = _build_backend({3: [[1, 2, 3]]}, len_min=3, len_max=3)
    stats = backend.score([1, 2, 3])
    assert stats.span_raw == pytest.approx(1.0)
    assert stats.coverage == pytest.approx(1.0)
    assert stats.quality == pytest.approx(1.0)
    assert stats.n_intervals_selected == 1
    assert stats.chars_covered == 3

def test_one_mismatch_quality():
    backend = _build_backend({3: [[1, 2, 3]]}, len_min=3, len_max=3, max_hd=2)
    stats = backend.score([1, 2, 4])
    expected_q = 1.0 - 1.0 / 3.0
    assert stats.quality == pytest.approx(expected_q)
    assert stats.coverage == pytest.approx(1.0)
    assert stats.span_raw == pytest.approx(expected_q)

def test_len_range_filter_respected():
    backend = _build_backend({2: [[9, 9]], 3: [[1, 2, 3]]}, len_min=3, len_max=3)
    stats = backend.score([9, 9, 9, 9])
    assert stats.span_raw == pytest.approx(0.0)
    assert stats.n_intervals_selected == 0

def test_overlap_tie_break_prefers_earlier_finishing_schedule():
    backend = _build_backend({2: [[1, 2], [3, 4]], 4: [[1, 2, 3, 4]]}, len_min=2, len_max=4, max_hd=0, debug_return_intervals=True, max_intervals_considered_per_start=8)
    stats = backend.score([1, 2, 3, 4])
    assert stats.n_intervals_selected == 2
    starts = tuple((interval.start for interval in stats.selected_intervals))
    lengths = tuple((interval.length for interval in stats.selected_intervals))
    assert starts == (0, 2)
    assert lengths == (2, 2)

def test_no_matches_returns_zero():
    backend = _build_backend({3: [[0, 0, 0]]}, len_min=3, len_max=3, max_hd=2)
    stats = backend.score([1, 2, 3])
    assert stats.span_raw == pytest.approx(0.0)
    assert stats.coverage == pytest.approx(0.0)
    assert stats.quality == pytest.approx(0.0)
    assert stats.n_intervals_selected == 0

def test_determinism_across_repeated_calls():
    backend = _build_backend({3: [[1, 2, 3], [3, 2, 1]], 4: [[4, 5, 6, 7]]}, len_min=3, len_max=4, debug_return_intervals=True)
    text = [1, 2, 3, 4, 5, 6, 7]
    stats_a = backend.score(text)
    stats_b = backend.score(text)
    assert stats_a == stats_b

def test_empty_text_safe():
    backend = _build_backend({3: [[1, 2, 3]]}, len_min=3, len_max=5)
    stats = backend.score([])
    assert stats.n_chars == 0
    assert stats.span_raw == pytest.approx(0.0)
    assert stats.length_bins == (3, 4, 5)
    assert stats.span_raw_by_len == (0.0, 0.0, 0.0)

def test_short_text_below_len_min_safe():
    backend = _build_backend({3: [[1, 2, 3]]}, len_min=3, len_max=4)
    stats = backend.score([1, 2])
    assert stats.n_chars == 2
    assert stats.span_raw == pytest.approx(0.0)
    assert stats.n_intervals_selected == 0
    assert stats.length_bins == (3, 4)

def test_duplicate_dictionary_entries_do_not_change_score():
    text = [1, 2, 3, 4, 5, 6]
    backend_unique = _build_backend({3: [[1, 2, 3], [4, 5, 6]]}, len_min=3, len_max=3)
    backend_dupes = _build_backend({3: [[1, 2, 3], [1, 2, 3], [4, 5, 6], [4, 5, 6]]}, len_min=3, len_max=3)
    assert backend_unique.score(text) == backend_dupes.score(text)

def test_per_length_aggregates_reconcile_to_totals():
    backend = _build_backend({3: [[1, 2, 3]], 4: [[4, 5, 6, 7]]}, len_min=3, len_max=4, max_hd=0)
    stats = backend.score([1, 2, 3, 4, 5, 6, 7])
    assert sum(stats.selected_intervals_by_len) == stats.n_intervals_selected
    assert sum(stats.chars_covered_by_len) == stats.chars_covered
    assert sum(stats.span_raw_by_len) == pytest.approx(stats.span_raw)

def test_length_bins_deterministic_ordering():
    backend = _build_backend({3: [[1, 2, 3]]}, len_min=3, len_max=6)
    stats = backend.score([1, 2, 3, 9, 9, 9])
    assert stats.length_bins == (3, 4, 5, 6)
    assert len(stats.span_raw_by_len) == 4
    assert len(stats.coverage_by_len) == 4
    assert len(stats.quality_by_len) == 4

def test_candidate_cap_is_enforced_and_tracked():
    words = {3: [[0, 0, 1], [0, 1, 0], [1, 1, 1]]}
    text = [1, 1, 1]
    backend_uncapped = _build_backend(words, len_min=3, len_max=3, max_hd=2, max_candidates_per_window=64)
    backend_capped = _build_backend(words, len_min=3, len_max=3, max_hd=2, max_candidates_per_window=1)
    stats_uncapped = backend_uncapped.score(text)
    stats_capped = backend_capped.score(text)
    assert stats_uncapped.span_raw > stats_capped.span_raw
    assert stats_capped.n_candidates_pruned_cap > 0

def test_fixed_shape_length_bins_even_with_zero_matches():
    backend = _build_backend({3: [[1, 1, 1]]}, len_min=3, len_max=5, min_quality_threshold=1e-09)
    stats = backend.score([9, 9, 9, 9, 9])
    assert stats.length_bins == (3, 4, 5)
    assert stats.span_raw_by_len == (0.0, 0.0, 0.0)
    assert stats.coverage_by_len == (0.0, 0.0, 0.0)
    assert stats.quality_by_len == (0.0, 0.0, 0.0)
    assert stats.selected_intervals_by_len == (0, 0, 0)
    assert stats.chars_covered_by_len == (0, 0, 0)

def test_start_stride_reduces_windows_scored_deterministically():
    backend_stride1 = _build_backend({3: [[1, 2, 3]]}, len_min=3, len_max=3, start_stride=1)
    backend_stride2 = _build_backend({3: [[1, 2, 3]]}, len_min=3, len_max=3, start_stride=2)
    text = [1, 2, 3, 4, 5, 6]
    stats1 = backend_stride1.score(text)
    stats2 = backend_stride2.score(text)
    assert stats1.n_windows_total == 4
    assert stats2.n_windows_total == 2
    assert stats2.n_windows_total < stats1.n_windows_total

def test_max_windows_total_caps_processing():
    backend_uncapped = _build_backend({3: [[1, 2, 3]]}, len_min=3, len_max=3, max_windows_total=0)
    backend_capped = _build_backend({3: [[1, 2, 3]]}, len_min=3, len_max=3, max_windows_total=2)
    text = [1, 2, 3, 4, 5, 6]
    stats_uncapped = backend_uncapped.score(text)
    stats_capped = backend_capped.score(text)
    assert stats_uncapped.n_windows_total == 4
    assert stats_capped.n_windows_total == 2
    assert stats_capped.n_windows_scored <= stats_capped.n_windows_total
