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


def _fingerprint_bin_map(payload: dict[str, object]) -> dict[tuple[int, int], int]:
    return {
        (int(row["length"]), int(row["hd"])): int(row["raw_match_count"])
        for row in payload["chunk_bins"]
    }


def _reference_fingerprint_bin_map(text: list[int], wordlists: dict[int, list[list[int]]], len_min: int, len_max: int) -> dict[tuple[int, int], int]:
    out: dict[tuple[int, int], int] = {}
    for length in range(len_min, len_max + 1):
        for hd in range(length):
            out[(length, hd)] = 0
        words = [word for word in wordlists.get(length, []) if len(word) == length]
        for start in range(0, max(0, len(text) - length + 1)):
            window = text[start:start + length]
            for word in words:
                distance = sum(1 for left, right in zip(window, word) if left != right)
                if distance < length:
                    out[(length, distance)] += 1
    return out


def test_fast_fingerprint_matches_python_reference_and_counts_all_useful_hd_bins() -> None:
    cfg = SpanHammingConfig(len_min=3, len_max=3, max_hd=0)
    wordlists = {
        3: [
            [1, 2, 3],  # hd 0
            [1, 2, 4],  # hd 1
            [1, 5, 4],  # hd 2
            [7, 8, 9],  # hd 3, deliberately excluded by length-minus-one policy
        ]
    }
    backend = FastSpanHammingBackend(config=cfg, wordlists=wordlists)

    payload = backend.fingerprint_raw_hamming_counts([1, 2, 3])

    assert payload["fingerprint_scope"] == "raw_hamming_counts"
    assert payload["hd_max_policy"] == "length_minus_one"
    assert _fingerprint_bin_map(payload) == _reference_fingerprint_bin_map([1, 2, 3], wordlists, 3, 3)
    assert _fingerprint_bin_map(payload) == {(3, 0): 1, (3, 1): 1, (3, 2): 1}


def test_fast_fingerprint_length_one_emits_only_hd_zero() -> None:
    cfg = SpanHammingConfig(len_min=1, len_max=1, max_hd=0)
    backend = FastSpanHammingBackend(config=cfg, wordlists={1: [[1], [2]]})

    payload = backend.fingerprint_raw_hamming_counts([1])

    assert _fingerprint_bin_map(payload) == {(1, 0): 1}
    assert all(int(row["hd"]) < int(row["length"]) for row in payload["chunk_bins"])


def test_fast_fingerprint_does_not_emit_hd_equal_length() -> None:
    cfg = SpanHammingConfig(len_min=3, len_max=3, max_hd=0)
    backend = FastSpanHammingBackend(
        config=cfg,
        wordlists={3: [[7, 8, 9]]},
    )

    payload = backend.fingerprint_raw_hamming_counts([1, 2, 3])

    assert (3, 3) not in _fingerprint_bin_map(payload)
    assert all(int(row["hd"]) < int(row["length"]) for row in payload["chunk_bins"])
    assert sum(_fingerprint_bin_map(payload).values()) == 0


def test_fast_fingerprint_offset_bins_sum_to_chunk_bins() -> None:
    cfg = SpanHammingConfig(len_min=2, len_max=3, max_hd=0)
    wordlists = {
        2: [[1, 2], [2, 3], [1, 4]],
        3: [[1, 2, 3], [2, 3, 4], [1, 9, 9]],
    }
    backend = FastSpanHammingBackend(config=cfg, wordlists=wordlists)

    payload = backend.fingerprint_raw_hamming_counts([1, 2, 3, 4], include_offset_rows=True)

    chunk = _fingerprint_bin_map(payload)
    offset_totals: dict[tuple[int, int], int] = {}
    for row in payload["offset_bins"]:
        key = (int(row["length"]), int(row["hd"]))
        offset_totals[key] = offset_totals.get(key, 0) + int(row["raw_match_count"])
    for key, chunk_count in chunk.items():
        assert offset_totals.get(key, 0) == chunk_count


def test_fast_fingerprint_match_dump_is_debug_only() -> None:
    cfg = SpanHammingConfig(len_min=3, len_max=3, max_hd=0)
    backend = FastSpanHammingBackend(config=cfg, wordlists={3: [[1, 2, 3], [1, 2, 4]]})

    normal_payload = backend.fingerprint_raw_hamming_counts([1, 2, 3])
    debug_payload = backend.fingerprint_raw_hamming_counts([1, 2, 3], include_match_dump=True)

    assert normal_payload["fingerprint_detail_level"] == "chunk_histogram"
    assert normal_payload["match_dump_rows"] == []
    assert debug_payload["fingerprint_detail_level"] == "match_dump"
    assert len(debug_payload["match_dump_rows"]) == 2


def test_fast_fingerprint_uncapped_and_capped_modes_report_pruning() -> None:
    cfg = SpanHammingConfig(len_min=3, len_max=3, max_hd=0)
    wordlists = {3: [[1, 2, 3], [1, 2, 4], [1, 5, 4]]}
    backend = FastSpanHammingBackend(config=cfg, wordlists=wordlists)

    uncapped = backend.fingerprint_raw_hamming_counts([1, 2, 3], max_candidates_per_window=0)
    capped = backend.fingerprint_raw_hamming_counts([1, 2, 3], max_candidates_per_window=1)

    assert uncapped["is_uncapped"] is True
    assert uncapped["cap"] == 0
    assert uncapped["n_candidates_pruned_cap"] == 0
    assert capped["is_uncapped"] is False
    assert capped["cap"] == 1
    assert int(capped["n_candidates_pruned_cap"]) > 0


def test_fast_fingerprint_is_deterministic() -> None:
    cfg = SpanHammingConfig(len_min=2, len_max=4, max_hd=0)
    backend = FastSpanHammingBackend(
        config=cfg,
        wordlists={
            2: [[1, 2], [2, 3], [3, 4]],
            3: [[1, 2, 3], [2, 3, 4]],
            4: [[1, 2, 3, 4]],
        },
    )

    first = backend.fingerprint_raw_hamming_counts([1, 2, 3, 4], include_offset_rows=True)
    second = backend.fingerprint_raw_hamming_counts([1, 2, 3, 4], include_offset_rows=True)

    assert first == second


def test_fast_fingerprint_reports_per_length_counters() -> None:
    cfg = SpanHammingConfig(len_min=2, len_max=3, max_hd=0)
    backend = FastSpanHammingBackend(
        config=cfg,
        wordlists={
            2: [[1, 2], [2, 3]],
            3: [[1, 2, 3], [2, 3, 4]],
        },
    )

    payload = backend.fingerprint_raw_hamming_counts([1, 2, 3, 4])

    assert payload["length_bins"] == [2, 3]
    assert payload["n_windows_total_by_len"] == [3, 2]
    assert payload["n_windows_scored_by_len"] == [3, 2]
    assert sum(payload["n_candidates_considered_by_len"]) == payload["n_candidates_considered"]
    assert sum(payload["n_candidates_pruned_cap_by_len"]) == payload["n_candidates_pruned_cap"]
