from __future__ import annotations

import csv
import gzip
from pathlib import Path

import numpy as np
import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    build_phaseB_runeberg_medium_book_lists_v1 as list_builder,
    run_phaseB_runeberg_nose_damage_ladder_v1 as phaseb,
    run_phaseB_runeberg_nose_damage_ladder_reverse_books_v1 as phaseb_reverse,
)


EXPECTED_MAX_HD_BY_LENGTH = {
    1: 0,
    2: 0,
    3: 1,
    4: 1,
    5: 1,
    6: 2,
    7: 3,
    8: 3,
    9: 4,
    10: 4,
    11: 5,
    12: 5,
    13: 6,
    14: 6,
}


def _npz_path(tmp_path: Path, name: str) -> Path:
    return tmp_path / name


def _clean_chunk() -> phaseb.CleanChunk:
    tokens = tuple((idx % 29) for idx in range(phaseb.CHUNK_SIZE))
    return phaseb.CleanChunk(
        book="book_a",
        direction="fwd",
        chunk_index=0,
        chunk_start=0,
        chunk_end=phaseb.CHUNK_SIZE,
        tokens=tokens,
        wli=tuple((idx % 5, 5) for idx in range(phaseb.CHUNK_SIZE)),
    )


def test_complete_books_requires_fwd_and_rev(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(phaseb, "EXCLUDE_BOOKS", ())
    monkeypatch.setattr(phaseb, "BOOK_ORDER", "forward")
    monkeypatch.setattr(phaseb, "BOOK_LIST_FILE_REL", "")
    rows = [
        ("book_a", "fwd", tmp_path / "book_a_fwd.npz"),
        ("book_a", "rev", tmp_path / "book_a_rev.npz"),
        ("book_b", "fwd", tmp_path / "book_b_fwd.npz"),
        ("book_c", "rev", tmp_path / "book_c_rev.npz"),
    ]

    assert phaseb.complete_books_from_rows(rows) == ["book_a"]
    assert phaseb.select_books(rows, max_books=10) == ["book_a"]


def test_select_books_uses_forward_order_and_excludes_done(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(phaseb, "BOOK_ORDER", "forward")
    monkeypatch.setattr(phaseb, "EXCLUDE_BOOKS", ("book_b",))
    monkeypatch.setattr(phaseb, "BOOK_LIST_FILE_REL", "")
    rows = []
    for book in ("book_a", "book_b", "book_c", "book_d"):
        rows.append((book, "fwd", tmp_path / f"{book}_fwd.npz"))
        rows.append((book, "rev", tmp_path / f"{book}_rev.npz"))

    assert phaseb.select_books(rows, max_books=2) == ["book_a", "book_c"]


def test_select_books_uses_reverse_order_and_excludes_done(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(phaseb, "BOOK_ORDER", "reverse")
    monkeypatch.setattr(phaseb, "EXCLUDE_BOOKS", ("book_b",))
    monkeypatch.setattr(phaseb, "BOOK_LIST_FILE_REL", "")
    rows = []
    for book in ("book_a", "book_b", "book_c", "book_d"):
        rows.append((book, "fwd", tmp_path / f"{book}_fwd.npz"))
        rows.append((book, "rev", tmp_path / f"{book}_rev.npz"))

    assert phaseb.select_books(rows, max_books=2) == ["book_d", "book_c"]


def test_select_books_can_skip_for_hardcoded_book_shards(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(phaseb, "BOOK_ORDER", "forward")
    monkeypatch.setattr(phaseb, "BOOK_SKIP", 2)
    monkeypatch.setattr(phaseb, "EXCLUDE_BOOKS", ())
    monkeypatch.setattr(phaseb, "BOOK_LIST_FILE_REL", "")
    rows = []
    for book in ("book_a", "book_b", "book_c", "book_d"):
        rows.append((book, "fwd", tmp_path / f"{book}_fwd.npz"))
        rows.append((book, "rev", tmp_path / f"{book}_rev.npz"))

    assert phaseb.select_books(rows, max_books=2) == ["book_c", "book_d"]


def test_select_books_from_book_list_file_preflights_complete_pairs(tmp_path: Path) -> None:
    list_path = tmp_path / "medium_pc_a.txt"
    list_path.write_text("book_a\nbook_b\n", encoding="utf-8")
    rows = [
        ("book_a", "fwd", tmp_path / "book_a_fwd.npz"),
        ("book_a", "rev", tmp_path / "book_a_rev.npz"),
        ("book_b", "fwd", tmp_path / "book_b_fwd.npz"),
        ("book_b", "rev", tmp_path / "book_b_rev.npz"),
    ]

    assert phaseb.select_books_from_book_list_file(rows, book_list_file=list_path) == ["book_a", "book_b"]


def test_select_books_from_book_list_file_rejects_duplicates_and_missing_pairs(tmp_path: Path) -> None:
    duplicate_path = tmp_path / "dup.txt"
    duplicate_path.write_text("book_a\nbook_a\n", encoding="utf-8")
    rows = [
        ("book_a", "fwd", tmp_path / "book_a_fwd.npz"),
        ("book_a", "rev", tmp_path / "book_a_rev.npz"),
        ("book_b", "fwd", tmp_path / "book_b_fwd.npz"),
    ]

    with pytest.raises(ValueError, match="duplicate"):
        phaseb.select_books_from_book_list_file(rows, book_list_file=duplicate_path)

    missing_pair_path = tmp_path / "missing_pair.txt"
    missing_pair_path.write_text("book_b\nbook_c\n", encoding="utf-8")
    with pytest.raises(ValueError, match="preflight failed"):
        phaseb.select_books_from_book_list_file(rows, book_list_file=missing_pair_path)


def test_select_books_from_book_list_file_rejects_excluded_books(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(phaseb, "EXCLUDE_BOOKS", ("book_b",))
    list_path = tmp_path / "medium_pc_a.txt"
    list_path.write_text("book_a\nbook_b\n", encoding="utf-8")
    rows = [
        ("book_a", "fwd", tmp_path / "book_a_fwd.npz"),
        ("book_a", "rev", tmp_path / "book_a_rev.npz"),
        ("book_b", "fwd", tmp_path / "book_b_fwd.npz"),
        ("book_b", "rev", tmp_path / "book_b_rev.npz"),
    ]

    with pytest.raises(ValueError, match="excluded books"):
        phaseb.select_books_from_book_list_file(rows, book_list_file=list_path)


def test_book_list_builder_balances_and_validates_no_overlap(tmp_path: Path) -> None:
    rows = [
        {"book": "a", "pair_bytes": 100, "fwd_bytes": 40, "rev_bytes": 60},
        {"book": "b", "pair_bytes": 80, "fwd_bytes": 30, "rev_bytes": 50},
        {"book": "c", "pair_bytes": 60, "fwd_bytes": 20, "rev_bytes": 40},
        {"book": "d", "pair_bytes": 40, "fwd_bytes": 10, "rev_bytes": 30},
    ]

    left, right = list_builder.greedy_two_way_balance(rows)
    list_builder.validate_no_overlap(left, right)

    assert {row["book"] for row in left}.isdisjoint({row["book"] for row in right})
    assert sum(int(row["pair_bytes"]) for row in left) == sum(int(row["pair_bytes"]) for row in right)


def test_reverse_script_has_distinct_label_output_and_same_inputs() -> None:
    assert phaseb.BOOK_ORDER == "forward"
    assert phaseb_reverse.BOOK_ORDER == "reverse"
    assert phaseb_reverse.RUN_LABEL == "phaseB_runeberg_nose_damage_ladder_reverse_books_v1"
    assert phaseb_reverse.OUTPUT_DIR_REL.endswith("phaseB_runeberg_nose_damage_ladder_reverse_books_v1")
    assert phaseb_reverse.OUTPUT_DIR_REL != phaseb.OUTPUT_DIR_REL
    assert phaseb_reverse.TOKENIZED_ROOT_REL == phaseb.TOKENIZED_ROOT_REL
    assert phaseb_reverse.EXCLUDE_BOOKS == phaseb.EXCLUDE_BOOKS
    assert phaseb_reverse.BOOK_SKIP == phaseb.BOOK_SKIP


def test_load_tokenized_nose_rejects_missing_arrays(tmp_path: Path) -> None:
    path = _npz_path(tmp_path, "book_a_fwd.npz")
    np.savez(path, pt_nose_data=np.array([0, 1, 2], dtype=np.uint8))

    with pytest.raises(KeyError, match="wli_nose_data"):
        phaseb.load_tokenized_nose("book_a", "fwd", path)


def test_load_tokenized_nose_rejects_token_wli_length_mismatch(tmp_path: Path) -> None:
    path = _npz_path(tmp_path, "book_a_fwd.npz")
    np.savez(
        path,
        pt_nose_data=np.array([0, 1, 2], dtype=np.uint8),
        wli_nose_data=np.array([0, 1, 2, 3], dtype=np.uint8),
    )

    with pytest.raises(ValueError, match="token/WLI length mismatch"):
        phaseb.load_tokenized_nose("book_a", "fwd", path)


def test_load_tokenized_nose_rejects_odd_wli_length(tmp_path: Path) -> None:
    path = _npz_path(tmp_path, "book_a_fwd.npz")
    np.savez(
        path,
        pt_nose_data=np.array([0, 1], dtype=np.uint8),
        wli_nose_data=np.array([0, 1, 2], dtype=np.uint8),
    )

    with pytest.raises(ValueError, match="length is not even"):
        phaseb.load_tokenized_nose("book_a", "fwd", path)


def test_damage_functions_are_deterministic() -> None:
    clean_chunk = _clean_chunk()
    global_probs = np.ones(29, dtype=np.float64) / 29.0
    book_probs = phaseb._empirical_probs(clean_chunk.tokens)
    limits = {
        "damage_repeats_per_chunk": 1,
        "damage_levels": (0.30,),
        "include_damage_models": (
            "independent_substitution",
            "frequency_matched_global",
            "frequency_matched_book",
            "word_local_substitution",
            "burst_substitution",
            "lane_period_substitution",
        ),
        "include_null_models": (
            "uniform_random",
            "global_frequency_random",
            "within_chunk_shuffle",
            "block_shuffle_25",
        ),
    }

    first = list(phaseb.iter_samples_for_chunk(clean_chunk, global_probs=global_probs, book_probs=book_probs, limits=limits))
    second = list(phaseb.iter_samples_for_chunk(clean_chunk, global_probs=global_probs, book_probs=book_probs, limits=limits))

    assert [(row.sample_id, row.seed, row.tokens) for row in first] == [
        (row.sample_id, row.seed, row.tokens) for row in second
    ]


def test_damage_functions_preserve_length_and_token_range() -> None:
    clean_chunk = _clean_chunk()
    global_probs = np.ones(29, dtype=np.float64) / 29.0
    book_probs = phaseb._empirical_probs(clean_chunk.tokens)
    samples = list(
        phaseb.iter_samples_for_chunk(
            clean_chunk,
            global_probs=global_probs,
            book_probs=book_probs,
            limits=phaseb.MODE_LIMITS["smoke"],
        )
    )

    assert {sample.source_kind for sample in samples} == {"clean", "damaged", "null"}
    assert all(len(sample.tokens) == phaseb.CHUNK_SIZE for sample in samples)
    assert all(min(sample.tokens) >= 0 and max(sample.tokens) <= 28 for sample in samples)


def test_source_word_chunks_are_non_overlapping_and_never_exceed_500() -> None:
    word_lengths = [3, 4, 2, 6]
    wli = []
    for length in word_lengths:
        wli.extend((pos, length) for pos in range(length))

    spans = phaseb.source_word_chunks_for_wli(wli, max_tokens=9)

    assert spans == [(0, 9), (9, 15)]
    assert all(end - start <= 9 for start, end in spans)
    assert all(wli[start][0] == 0 for start, _end in spans)
    assert all(left_end <= right_start for (_left_start, left_end), (right_start, _right_end) in zip(spans, spans[1:]))


def test_build_clean_chunks_uses_source_word_boundaries_and_next_word_starts() -> None:
    word_lengths = [3, 4, 2, 6]
    tokens = []
    wli = []
    for length in word_lengths:
        for pos in range(length):
            tokens.append(len(tokens) % 29)
            wli.append((pos, length))
    book_dir = phaseb.TokenizedBookDirection(
        book="book_a",
        direction="fwd",
        path=Path("book_a_fwd.npz"),
        tokens=np.asarray(tokens, dtype=np.uint8),
        wli=np.asarray(wli, dtype=np.uint8),
    )

    chunks = phaseb.build_clean_chunks(book_dir, chunks_per_book_direction=3)

    assert [(chunk.chunk_start, chunk.chunk_end) for chunk in chunks] == [(0, 15)]
    assert [chunk.chunk_start for chunk in chunks] == [0]
    assert all(len(chunk.tokens) <= phaseb.CHUNK_SIZE for chunk in chunks)
    assert {chunk.source_start_assumption for chunk in chunks} == {phaseb.SOURCE_START_ASSUMPTION}


def test_score_views_write_start_assumption_and_half_regions(monkeypatch: pytest.MonkeyPatch) -> None:
    clean_chunk = _clean_chunk()
    sample = phaseb.Sample(
        sample_id="sample",
        source_kind="clean",
        damage_model="none",
        damage_level="",
        null_model="",
        repeat_index=0,
        seed=1,
        clean_chunk=clean_chunk,
        tokens=clean_chunk.tokens,
    )
    monkeypatch.setattr(phaseb, "START_VIEW_SHIFTS_BY_MODE", {"smoke": (0, 3)})

    views = list(phaseb.iter_score_views_for_sample(sample, run_mode="smoke"))

    assert [(view.start_shift, view.score_region) for view in views] == [
        (0, "full"),
        (0, "first_half"),
        (0, "second_half"),
        (3, "full"),
        (3, "first_half"),
        (3, "second_half"),
    ]
    assert views[0].start_assumption == phaseb.SOURCE_START_ASSUMPTION
    assert views[3].start_assumption == phaseb.DEFAULT_START_ASSUMPTION
    assert len(views[1].tokens) + len(views[2].tokens) == len(clean_chunk.tokens)


def test_sample_row_reports_actual_changed_fraction() -> None:
    clean_chunk = phaseb.CleanChunk(
        book="book_a",
        direction="fwd",
        chunk_index=0,
        chunk_start=0,
        chunk_end=5,
        tokens=(0, 1, 2, 3, 4),
        wli=tuple((idx, 5) for idx in range(5)),
    )
    sample = phaseb.Sample(
        sample_id="sample",
        source_kind="damaged",
        damage_model="unit_test_damage",
        damage_level="0.50",
        null_model="",
        repeat_index=0,
        seed=1,
        clean_chunk=clean_chunk,
        tokens=(0, 9, 2, 8, 4),
    )

    row = phaseb._sample_row(sample)

    assert row["changed_positions"] == 2
    assert row["changed_fraction"] == "0.4"
    assert row["same_positions"] == 3
    assert row["same_fraction"] == "0.6"
    assert {"changed_positions", "changed_fraction", "same_positions", "same_fraction"} <= set(phaseb.SAMPLE_FIELDS)


class _FakeFingerprintBackend:
    def fingerprint_raw_hamming_counts(self, tokens, **_kwargs):
        chunk_bins = []
        offset_bins = []
        for length in phaseb.SPAN_LENGTHS:
            if len(tokens) < length:
                continue
            chunk_bins.append({"length": length, "hd": 0, "raw_match_count": 1})
            offset_bins.append({"length": length, "hd": 0, "start": 0, "raw_match_count": 1})
        return {
            "chunk_bins": chunk_bins,
            "offset_bins": offset_bins,
            "length_bins": list(phaseb.SPAN_LENGTHS),
            "n_candidates_considered_by_len": [1 for _ in phaseb.SPAN_LENGTHS],
            "n_candidates_pruned_cap_by_len": [0 for _ in phaseb.SPAN_LENGTHS],
            "hd_max_policy": "length_minus_one",
            "cap": 0,
            "is_uncapped": True,
        }


def test_no_wli_feature_rows_ignore_source_word_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(phaseb, "START_VIEW_SHIFTS_BY_MODE", {"full": (0,)})
    tokens = tuple((idx % 29) for idx in range(phaseb.CHUNK_SIZE))
    left_chunk = phaseb.CleanChunk(
        book="book_a",
        direction="fwd",
        chunk_index=0,
        chunk_start=0,
        chunk_end=len(tokens),
        tokens=tokens,
        wli=tuple((idx % 5, 5) for idx in range(len(tokens))),
    )
    right_chunk = phaseb.CleanChunk(
        book="book_a",
        direction="fwd",
        chunk_index=0,
        chunk_start=0,
        chunk_end=len(tokens),
        tokens=tokens,
        wli=tuple((0, 1) for _ in range(len(tokens))),
    )
    spec = phaseb.DictionarySpec("fake", "unused", True)

    left_rows, _ = phaseb.fingerprint_rows_for_sample(
        sample=phaseb.Sample("sample", "clean", "none", "", "", 0, 1, left_chunk, tokens),
        spec=spec,
        backend=_FakeFingerprintBackend(),
    )
    right_rows, _ = phaseb.fingerprint_rows_for_sample(
        sample=phaseb.Sample("sample", "clean", "none", "", "", 0, 1, right_chunk, tokens),
        spec=spec,
        backend=_FakeFingerprintBackend(),
    )

    ignored = {"chunk_id", "score_ms"}
    assert [{k: v for k, v in row.items() if k not in ignored} for row in left_rows] == [
        {k: v for k, v in row.items() if k not in ignored} for row in right_rows
    ]


def _summary_feature_row(
    source_kind: str,
    *,
    damage_model: str = "",
    damage_level: str = "",
    null_model: str = "",
    direction: str = "fwd",
    start_shift: int = 3,
    score_region: str = "first_half",
    exact_count: int = 2,
    hd_le_count: int = 4,
) -> dict:
    return {
        "direction": direction,
        "source_kind": source_kind,
        "damage_model": damage_model,
        "damage_level": damage_level,
        "null_model": null_model,
        "start_assumption": "unknown_start",
        "start_shift": start_shift,
        "score_region": score_region,
        "dictionary_cut": "strict",
        "span_length": 6,
        "hd": 2,
        "window_count": 10,
        "exact_count": exact_count,
        "hd_le_count": hd_le_count,
        "matched_window_count": 3,
        "no_match_count": 7,
        "exact_count_norm": str(exact_count / 10.0),
        "hd_le_count_norm": str(hd_le_count / 10.0),
        "candidate_cap_pruned_rate": "0",
    }


def test_summary_feature_sets_include_raw_counts_and_keep_distribution_compact() -> None:
    stats: dict[tuple, phaseb.RunningStat] = {}
    histograms: dict[tuple, phaseb.HistogramStat] = {}
    rows = [_summary_feature_row("damaged", damage_model="independent_substitution", damage_level="0.20")]

    phaseb.update_feature_stats(stats, rows)
    phaseb.update_feature_histograms(histograms, rows)

    stat_features = {key[-1] for key in stats}
    histogram_features = {key[-1] for key in histograms}
    assert set(phaseb.FINAL_FEATURE_NAMES) <= stat_features
    assert {"exact_count", "hd_le_count", "matched_window_count", "no_match_count", "window_count"} <= stat_features
    assert histogram_features == set(phaseb.DISTRIBUTION_FEATURE_NAMES)


def test_damaged_vs_null_summary_splits_by_damage_and_null_model() -> None:
    stats: dict[tuple, phaseb.RunningStat] = {}
    phaseb.update_feature_stats(
        stats,
        [
            _summary_feature_row("damaged", damage_model="independent_substitution", damage_level="0.20"),
            _summary_feature_row("null", null_model="uniform_random"),
        ],
    )

    rows = phaseb.damaged_vs_null_summary_rows(stats)
    exact = [
        row
        for row in rows
        if row["damage_model"] == "independent_substitution"
        and row["damage_level"] == "0.20"
        and row["null_model"] == "uniform_random"
        and row["feature_name"] == "exact_count"
    ]

    assert len(exact) == 1
    assert exact[0]["damaged_count"] == 1
    assert exact[0]["null_count"] == 1
    assert "cohen_d" in exact[0]


def test_damaged_vs_null_by_view_keeps_direction_shift_and_region() -> None:
    stats: dict[tuple, phaseb.RunningStat] = {}
    phaseb.update_feature_stats(
        stats,
        [
            _summary_feature_row(
                "damaged",
                damage_model="independent_substitution",
                damage_level="0.20",
                direction="fwd",
                start_shift=3,
                score_region="first_half",
            ),
            _summary_feature_row(
                "null",
                null_model="uniform_random",
                direction="fwd",
                start_shift=3,
                score_region="first_half",
            ),
            _summary_feature_row(
                "damaged",
                damage_model="independent_substitution",
                damage_level="0.20",
                direction="rev",
                start_shift=11,
                score_region="second_half",
            ),
            _summary_feature_row(
                "null",
                null_model="uniform_random",
                direction="rev",
                start_shift=11,
                score_region="second_half",
            ),
        ],
    )

    rows = phaseb.damaged_vs_null_summary_rows(stats, include_view=True)
    exact_views = {
        (row["direction"], row["start_shift"], row["score_region"])
        for row in rows
        if row["feature_name"] == "exact_count"
    }

    assert exact_views == {("fwd", 3, "first_half"), ("rev", 11, "second_half")}


def test_top_damaged_vs_null_rows_can_filter_normalised_features() -> None:
    rows = [
        {"feature_name": "exact_count", "cohen_d": 99.0},
        {"feature_name": "exact_count_norm", "cohen_d": 1.5},
        {"feature_name": "hd_le_count_norm", "cohen_d": -2.0},
    ]

    top = phaseb.top_damaged_vs_null_rows(rows, feature_names=("exact_count_norm", "hd_le_count_norm"))

    assert [row["feature_name"] for row in top] == ["hd_le_count_norm", "exact_count_norm"]


def test_input_manifest_rows_report_only_used_clean_chunks(tmp_path: Path) -> None:
    def book_dir(book: str, direction: str) -> phaseb.TokenizedBookDirection:
        wli = np.array([[0, 4], [1, 4], [2, 4], [3, 4], [0, 3], [1, 3], [2, 3]], dtype=np.uint16)
        return phaseb.TokenizedBookDirection(
            book=book,
            direction=direction,
            path=tmp_path / f"{book}_{direction}.npz",
            tokens=np.arange(len(wli), dtype=np.uint8),
            wli=wli,
        )

    loaded = [
        book_dir("book_a", "fwd"),
        book_dir("book_a", "rev"),
        book_dir("book_b", "fwd"),
        book_dir("book_b", "rev"),
    ]
    chunks = [
        phaseb.CleanChunk("book_a", "fwd", 0, 0, 4, (0, 1, 2, 3), tuple()),
        phaseb.CleanChunk("book_a", "fwd", 1, 4, 7, (4, 5, 6), tuple()),
        phaseb.CleanChunk("book_b", "rev", 0, 0, 4, (0, 1, 2, 3), tuple()),
    ]

    rows = phaseb.input_manifest_rows_for_used_chunks(loaded, chunks)

    assert [(row["book"], row["direction"], row["sampled_chunks"]) for row in rows] == [
        ("book_a", "fwd", 2),
        ("book_b", "rev", 1),
    ]


def test_csv_helpers_write_gzip_csv(tmp_path: Path) -> None:
    path = tmp_path / "summary.csv.gz"
    fields = ["a", "b"]

    count = phaseb._write_csv_rows(path, [{"a": 1, "b": 2}], fields)

    with gzip.open(path, "rt", encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert count == 1
    assert rows == [{"a": "1", "b": "2"}]


def test_named_ladder_records_v0_3_baseline_and_extra_rungs() -> None:
    assert phaseb.CHUNK_MAX_TOKENS == 500
    assert phaseb.CHUNK_SIZE == phaseb.CHUNK_MAX_TOKENS
    assert phaseb.SPAN_LENGTHS == tuple(range(1, 15))
    assert phaseb.LADDER_PROFILE == "v0_3_plus_long_relaxed_v2"
    assert phaseb.BASELINE_V0_3_RUNG_COUNT == 50
    assert phaseb.MAX_HD_BY_LENGTH == EXPECTED_MAX_HD_BY_LENGTH
    assert phaseb.TOTAL_LADDER_RUNG_COUNT == 55
    assert phaseb.EXTRA_EXPERIMENTAL_RUNG_COUNT == 5


def test_estimate_total_samples_matches_mode_config() -> None:
    limits = phaseb.MODE_LIMITS["smoke"]
    expected_per_chunk = (
        1
        + int(limits["damage_repeats_per_chunk"])
        * len(tuple(limits["damage_levels"]))
        * len(tuple(limits["include_damage_models"]))
        + int(limits["damage_repeats_per_chunk"]) * len(tuple(limits["include_null_models"]))
    )

    assert expected_per_chunk == 19
    assert phaseb.estimate_total_samples(8, limits) == 152


def test_estimate_output_shape_counts_feature_rows() -> None:
    limits = phaseb.MODE_LIMITS["smoke"]
    shape = phaseb.estimate_output_shape(selected_books=2, clean_chunk_count=8, limits=limits, run_mode="smoke")

    assert shape["selected_books"] == 2
    assert shape["chunks"] == 8
    assert shape["samples"] == 152
    assert shape["score_views_per_sample"] == 12
    assert shape["dictionary_cuts"] == 2
    assert shape["ladder_rows_per_dictionary"] == phaseb.TOTAL_LADDER_RUNG_COUNT
    assert shape["total_feature_rows"] == 152 * 12 * 2 * phaseb.TOTAL_LADDER_RUNG_COUNT


def test_timing_pilot_shape_is_about_20_chunks_all_models() -> None:
    limits = phaseb.MODE_LIMITS["timing_pilot"]
    shape = phaseb.estimate_output_shape(selected_books=5, clean_chunk_count=20, limits=limits, run_mode="timing_pilot")

    assert int(limits["max_books"]) == 5
    assert int(limits["chunks_per_book_direction"]) == 2
    assert len(tuple(limits["include_damage_models"])) == 6
    assert len(tuple(limits["include_null_models"])) == 6
    assert shape["samples"] == 740
    assert shape["chunk_max_tokens"] == 500
    assert shape["num_clean_chunks"] == 20
    assert shape["score_views_per_sample"] == 12
    assert shape["total_feature_rows"] == 740 * 12 * 2 * phaseb.TOTAL_LADDER_RUNG_COUNT


def test_medium_summary_500_shape_uses_num_clean_chunks_not_chunk_length() -> None:
    limits = phaseb.MODE_LIMITS["medium_summary_500"]
    shape = phaseb.estimate_output_shape(
        selected_books=int(limits["max_books"]),
        clean_chunk_count=int(limits["num_clean_chunks"]),
        limits=limits,
        run_mode="medium_summary_500",
    )

    assert phaseb.CHUNK_MAX_TOKENS == 500
    assert int(limits["num_clean_chunks"]) == 500
    assert int(limits["max_books"]) == 250
    assert int(limits["chunks_per_book_direction"]) == 1
    assert shape["chunk_max_tokens"] == 500
    assert shape["num_clean_chunks"] == 500
    assert shape["samples"] == 18_500
    assert shape["regions"] == ["first_half", "second_half"]
    assert shape["start_view_shifts"] == [0, 3, 7, 11]
    assert shape["score_views_per_sample"] == 8
    assert shape["total_feature_rows"] == 18_500 * 8 * 2 * phaseb.TOTAL_LADDER_RUNG_COUNT
    assert phaseb.write_raw_feature_rows_enabled("medium_summary_500") is False
    assert phaseb.write_feature_histograms_enabled("medium_summary_500") is True
    assert phaseb.write_feature_quantiles_enabled("medium_summary_500") is True


def test_medium_summary_50_canary_shape_matches_summary_only_policy() -> None:
    limits = phaseb.MODE_LIMITS["medium_summary_50"]
    shape = phaseb.estimate_output_shape(
        selected_books=int(limits["max_books"]),
        clean_chunk_count=int(limits["num_clean_chunks"]),
        limits=limits,
        run_mode="medium_summary_50",
    )

    assert phaseb.CHUNK_MAX_TOKENS == 500
    assert int(limits["num_clean_chunks"]) == 50
    assert int(limits["max_books"]) == 25
    assert int(limits["chunks_per_book_direction"]) == 1
    assert shape["num_clean_chunks_this_run"] == 50
    assert shape["samples"] == 1_850
    assert shape["regions"] == ["first_half", "second_half"]
    assert shape["start_view_shifts"] == [0, 3, 7, 11]
    assert shape["score_views_per_sample"] == 8
    assert shape["total_feature_rows"] == 1_850 * 8 * 2 * phaseb.TOTAL_LADDER_RUNG_COUNT
    assert phaseb.write_raw_feature_rows_enabled("medium_summary_50") is False
    assert phaseb.write_feature_histograms_enabled("medium_summary_50") is True
    assert phaseb.write_feature_quantiles_enabled("medium_summary_50") is True


def test_stage0_canary_shape_is_fwd_full_shift0_summary_only() -> None:
    limits = phaseb.MODE_LIMITS["stage0_fwd_full_canary"]
    shape = phaseb.estimate_output_shape(
        selected_books=int(limits["max_books"]),
        clean_chunk_count=int(limits["num_clean_chunks"]),
        limits=limits,
        run_mode="stage0_fwd_full_canary",
    )

    assert int(limits["num_clean_chunks"]) == 25
    assert phaseb.directions_for_mode("stage0_fwd_full_canary") == ("fwd",)
    assert shape["regions"] == ["full"]
    assert shape["start_view_shifts"] == [0]
    assert shape["score_views_per_sample"] == 1
    assert shape["samples"] == 925
    assert shape["total_feature_rows"] == 925 * 1 * 2 * phaseb.TOTAL_LADDER_RUNG_COUNT
    assert phaseb.write_raw_feature_rows_enabled("stage0_fwd_full_canary") is False
    assert phaseb.write_feature_histograms_enabled("stage0_fwd_full_canary") is True
    assert phaseb.write_feature_quantiles_enabled("stage0_fwd_full_canary") is True


def test_verbose_rolling_is_smoke_only_by_default() -> None:
    assert phaseb.verbose_rolling_summary_enabled("smoke") is True
    assert phaseb.verbose_rolling_summary_enabled("timing_pilot") is False
    assert phaseb.verbose_rolling_summary_enabled("pilot") is False
    assert phaseb.verbose_rolling_summary_enabled("full") is False
