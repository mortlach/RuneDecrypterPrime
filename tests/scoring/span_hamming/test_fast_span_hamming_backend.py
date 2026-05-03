from __future__ import annotations

import time

import pytest

from rune_decrypter_prime.scoring.span_hamming.backend import SpanHammingBackend
from rune_decrypter_prime.scoring.span_hamming.fast_backend import (
    FastSpanHammingBackend,
    fast_span_hamming_available,
)
from rune_decrypter_prime.scoring.span_hamming.types import SpanHammingConfig


pytestmark = pytest.mark.skipif(
    not fast_span_hamming_available(),
    reason="optional _span_hamming_fast extension is not built",
)


def _stats_key(stats):
    return {
        "span_raw": stats.span_raw,
        "coverage": stats.coverage,
        "quality": stats.quality,
        "n_chars": stats.n_chars,
        "chars_covered": stats.chars_covered,
        "n_intervals_selected": stats.n_intervals_selected,
        "length_bins": stats.length_bins,
        "span_raw_by_len": stats.span_raw_by_len,
        "coverage_by_len": stats.coverage_by_len,
        "quality_by_len": stats.quality_by_len,
        "selected_intervals_by_len": stats.selected_intervals_by_len,
        "chars_covered_by_len": stats.chars_covered_by_len,
        "n_windows_total": stats.n_windows_total,
        "n_windows_scored": stats.n_windows_scored,
        "n_candidates_considered": stats.n_candidates_considered,
        "n_candidates_pruned_cap": stats.n_candidates_pruned_cap,
        "selected_intervals": stats.selected_intervals,
    }


def _assert_same_stats(py_stats, fast_stats) -> None:
    assert fast_stats.span_raw == pytest.approx(py_stats.span_raw)
    assert fast_stats.coverage == pytest.approx(py_stats.coverage)
    assert fast_stats.quality == pytest.approx(py_stats.quality)
    for field in (
        "n_chars",
        "chars_covered",
        "n_intervals_selected",
        "length_bins",
        "selected_intervals_by_len",
        "chars_covered_by_len",
        "n_windows_total",
        "n_windows_scored",
        "n_candidates_considered",
        "n_candidates_pruned_cap",
        "selected_intervals",
    ):
        assert getattr(fast_stats, field) == getattr(py_stats, field), field
    assert fast_stats.span_raw_by_len == pytest.approx(py_stats.span_raw_by_len)
    assert fast_stats.coverage_by_len == pytest.approx(py_stats.coverage_by_len)
    assert fast_stats.quality_by_len == pytest.approx(py_stats.quality_by_len)


def _build_pair(wordlists, cfg: SpanHammingConfig):
    return (
        SpanHammingBackend(config=cfg, wordlists=wordlists),
        FastSpanHammingBackend(config=cfg, wordlists=wordlists),
    )


def test_fast_backend_matches_python_exact_and_mismatch_fixture() -> None:
    cfg = SpanHammingConfig(len_min=3, len_max=4, max_hd=2, debug_return_intervals=True)
    py_backend, fast_backend = _build_pair(
        {
            3: [[1, 2, 3], [3, 2, 1], [4, 5, 6]],
            4: [[1, 2, 3, 4], [4, 5, 6, 7]],
        },
        cfg,
    )
    text = [1, 2, 4, 4, 5, 6, 7, 3, 2, 1]

    _assert_same_stats(py_backend.score(text), fast_backend.score(text))


def test_fast_backend_matches_python_overlap_tie_break() -> None:
    cfg = SpanHammingConfig(
        len_min=2,
        len_max=4,
        max_hd=0,
        debug_return_intervals=True,
        max_intervals_considered_per_start=8,
    )
    py_backend, fast_backend = _build_pair(
        {
            2: [[1, 2], [3, 4]],
            4: [[1, 2, 3, 4]],
        },
        cfg,
    )
    text = [1, 2, 3, 4]

    py_stats = py_backend.score(text)
    fast_stats = fast_backend.score(text)

    _assert_same_stats(py_stats, fast_stats)
    assert tuple(interval.start for interval in fast_stats.selected_intervals) == (0, 2)
    assert tuple(interval.length for interval in fast_stats.selected_intervals) == (2, 2)


def test_fast_backend_matches_python_candidate_cap_pressure() -> None:
    cfg = SpanHammingConfig(
        len_min=3,
        len_max=3,
        max_hd=2,
        debug_return_intervals=True,
        max_candidates_per_window=1,
    )
    words = {3: [[0, 0, 1], [0, 1, 0], [1, 1, 1]]}
    py_backend, fast_backend = _build_pair(words, cfg)
    text = [1, 1, 1]

    py_stats = py_backend.score(text)
    fast_stats = fast_backend.score(text)

    _assert_same_stats(py_stats, fast_stats)
    assert fast_stats.n_candidates_pruned_cap > 0


def test_fast_backend_is_deterministic() -> None:
    cfg = SpanHammingConfig(len_min=3, len_max=5, max_hd=1, debug_return_intervals=True)
    _py_backend, fast_backend = _build_pair(
        {
            3: [[1, 2, 3], [2, 3, 4], [3, 4, 5]],
            4: [[1, 2, 3, 4]],
            5: [[1, 2, 3, 4, 5]],
        },
        cfg,
    )
    text = [1, 2, 3, 4, 5, 6, 1, 2, 3]

    assert _stats_key(fast_backend.score(text)) == _stats_key(fast_backend.score(text))


def test_fast_backend_payload_exposes_raw_intervals_for_calibration() -> None:
    cfg = SpanHammingConfig(len_min=3, len_max=3, max_hd=0, debug_return_intervals=True)
    backend = FastSpanHammingBackend(
        config=cfg,
        wordlists={3: [[1, 2, 3], [2, 3, 4]]},
        return_raw_intervals=True,
    )

    payload = backend.score_payload([1, 2, 3, 4])

    assert payload["selected_intervals"]
    assert payload["raw_intervals"]
    assert len(payload["raw_intervals"]) >= len(payload["selected_intervals"])


def test_fast_backend_smoke_benchmark_is_not_slower_than_python_by_large_margin() -> None:
    cfg = SpanHammingConfig(len_min=3, len_max=6, max_hd=1)
    wordlists = {
        3: [[a, b, c] for a in range(6) for b in range(6) for c in range(2)],
        4: [[a, b, c, d] for a in range(4) for b in range(4) for c in range(3) for d in range(2)],
        5: [[a, b, c, d, e] for a in range(3) for b in range(3) for c in range(3) for d in range(3) for e in range(2)],
        6: [[a, b, c, d, e, f] for a in range(3) for b in range(3) for c in range(3) for d in range(2) for e in range(2) for f in range(2)],
    }
    text = [idx % 7 for idx in range(240)]
    py_backend, fast_backend = _build_pair(wordlists, cfg)

    py_start = time.perf_counter()
    py_stats = py_backend.score(text)
    py_elapsed = time.perf_counter() - py_start

    fast_start = time.perf_counter()
    fast_stats = fast_backend.score(text)
    fast_elapsed = time.perf_counter() - fast_start

    _assert_same_stats(py_stats, fast_stats)
    assert fast_elapsed <= py_elapsed * 1.25
