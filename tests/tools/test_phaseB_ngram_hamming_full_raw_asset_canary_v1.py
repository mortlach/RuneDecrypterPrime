from __future__ import annotations

import gzip
import json
import math
from types import SimpleNamespace

from rune_decrypter_prime.scoring.ngram_hamming.reference import PhraseEntry

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    build_phaseB_ngram_hamming_canary_probe_assets_v1 as probe_builder,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    build_phaseB_ngram_hamming_full_raw_assets_v1 as builder,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    run_phaseB_ngram_hamming_canary_probe_v1 as probe_canary,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    run_phaseB_ngram_hamming_full_raw_canary_v1 as canary,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    summarise_phaseB_ngram_hamming_full_raw_assets_v1 as summary,
)


def test_full_raw_asset_builder_scope_is_required_fwd_order2_order3_only() -> None:
    assert builder.RUN_MODE == "full"
    assert builder.FULL_ASSET_AVAILABLE is True
    assert builder.FULL_RAW_NGRAM_REBUILD_CONFIRMED is True
    assert builder.SAMPLE_LINE_LIMIT_PER_ORDER is None
    assert builder.BUILDER_REQUESTED_SAMPLE_LINE_LIMIT_PER_ORDER == 0
    assert builder.effective_sample_line_limit_for_builder("full", 0) is None
    assert builder.effective_sample_line_limit_for_builder("sample", 25_000) == 25_000
    assert builder.REQUIRED_DIRECTIONS == ("fwd",)
    assert builder.REQUIRED_CUTS == ("normal", "strict")
    assert builder.REQUIRED_ORDERS == (2, 3)


def test_full_raw_build_config_passes_none_sample_limit_to_builder() -> None:
    captured = {}

    class FakeBuilder:
        RAW_NGRAM_ROOT = "raw"
        RAW_NGRAM_FILES_BY_ORDER = {}
        RAW_NGRAM_GLOBS_BY_ORDER = {}
        DICTIONARY_DIRS_BY_CUT = {}

        @staticmethod
        def BuildConfig(**kwargs):
            captured.update(kwargs)
            return SimpleNamespace(**kwargs)

    config = builder.make_full_raw_build_config(FakeBuilder)

    assert config.sample_line_limit_per_order is None
    assert captured["sample_line_limit_per_order"] is None


def test_canary_probe_assets_are_not_full_assets() -> None:
    assert probe_builder.ASSET_MODE == "canary_probe"
    assert probe_builder.BUILDER_RUN_MODE == "sample"
    assert probe_builder.FULL_ASSET_AVAILABLE is False
    assert probe_builder.FULL_RAW_NGRAM_REBUILD_CONFIRMED is False
    assert probe_builder.SAMPLE_LINE_LIMIT_PER_ORDER == 25_000
    assert probe_builder.REQUIRED_DIRECTIONS == ("fwd",)
    assert probe_builder.REQUIRED_CUTS == ("normal", "strict")
    assert probe_builder.REQUIRED_ORDERS == (2, 3)


def test_canary_probe_runs_order2_order3_but_rejects_full_claims() -> None:
    assert probe_canary.REQUIRED_ASSET_MODE == "canary_probe"
    assert probe_canary.NGRAM_ORDERS == (2, 3)
    assert probe_canary.DICTIONARY_CUTS == ("normal", "strict")
    assert probe_canary.SAMPLE_LINE_LIMIT_PER_ORDER == 25_000
    assert probe_canary.NO_PRODUCTION_SCORER_CHANGES is True
    manifest = {
        "asset_mode": "canary_probe",
        "full_asset_available": False,
        "full_raw_ngram_rebuild_confirmed": False,
        "sample_line_limit_per_order": 25_000,
        "scan_mode": "whole_phrase_only",
        "internal_phrase_windows": False,
        "phrase_index_path": "AGENTS.md",
    }
    assert probe_canary.validate_canary_probe_summary(manifest) == []
    assert canary.validate_full_asset_summary(manifest)


def test_full_raw_summary_profiles_include_p2_and_p3_contracts() -> None:
    profiles = {profile.profile_id: profile for profile in summary.PROFILES}

    assert set(profiles) == {"P2_conservative_len8_hd2", "P3_word_shape_guarded_len8_hd2"}
    assert profiles["P2_conservative_len8_hd2"].min_phrase_token_length == 8
    assert profiles["P2_conservative_len8_hd2"].max_total_phrase_hd == 2
    assert profiles["P2_conservative_len8_hd2"].max_word_hd == 1
    assert profiles["P2_conservative_len8_hd2"].exact_match_word_lengths == ()
    assert profiles["P3_word_shape_guarded_len8_hd2"].min_phrase_token_length == 8
    assert profiles["P3_word_shape_guarded_len8_hd2"].max_total_phrase_hd == 2
    assert profiles["P3_word_shape_guarded_len8_hd2"].max_word_hd == 1
    assert profiles["P3_word_shape_guarded_len8_hd2"].exact_match_word_lengths == (1, 2)


def test_full_matrix_gate_rejects_sample_index_assets_when_full_required() -> None:
    manifest = {
        "asset_mode": "sample",
        "full_asset_available": False,
        "full_raw_ngram_rebuild_confirmed": False,
        "sample_line_limit_per_order": 25000,
        "scan_mode": "whole_phrase_only",
        "internal_phrase_windows": False,
        "phrase_index_path": "output/missing.jsonl.gz",
    }

    blocked = canary.validate_full_asset_summary(manifest)

    assert any("actual_asset_mode" in reason for reason in blocked)
    assert any("sample_line_limit_per_order" in reason for reason in blocked)
    assert any("phrase index" in reason for reason in blocked)


def test_full_matrix_gate_rejects_non_phrase_index_existing_file() -> None:
    manifest = {
        "asset_mode": "full",
        "full_asset_available": True,
        "full_raw_ngram_rebuild_confirmed": True,
        "sample_line_limit_per_order": None,
        "scan_mode": "whole_phrase_only",
        "internal_phrase_windows": False,
        "phrase_index_path": "AGENTS.md",
        "phrase_entry_count": 1,
    }

    blocked = canary.validate_full_asset_summary(manifest)

    assert any(".jsonl.gz" in reason for reason in blocked)


def test_full_matrix_gate_accepts_valid_phrase_index(tmp_path, monkeypatch) -> None:
    phrase_index = tmp_path / "phrase_index.jsonl.gz"
    row = {
        "phrase_id": "p1",
        "direction": "fwd",
        "dictionary_cut": "normal",
        "ngram_order": 2,
        "word_token_ids": [[1, 2, 3, 4], [5, 6, 7, 8]],
        "rune_token_ids": [1, 2, 3, 4, 5, 6, 7, 8],
        "word_lengths": [4, 4],
        "phrase_token_length": 8,
        "count": 1.0,
        "sum_count": 1.0,
        "max_count": 1.0,
        "log_count": 0.69,
        "max_log_count": 0.69,
        "phrase_count": 1,
        "top_latin_ngram_for_max_count": "abcd efgh",
    }
    with gzip.open(phrase_index, "wt", encoding="utf-8") as handle:
        handle.write(json.dumps(row) + "\n")
    monkeypatch.setattr(canary, "REPO_ROOT", tmp_path)
    manifest = {
        "asset_mode": "full",
        "full_asset_available": True,
        "full_raw_ngram_rebuild_confirmed": True,
        "sample_line_limit_per_order": None,
        "scan_mode": "whole_phrase_only",
        "internal_phrase_windows": False,
        "phrase_index_path": "phrase_index.jsonl.gz",
        "phrase_entry_count": 1,
        "phrase_index_rows_checked": 1,
        "phrase_index_invalid_row_count": 0,
    }

    assert canary.validate_full_asset_summary(manifest) == []


def test_full_matrix_gate_rejects_invalid_phrase_index_shape(tmp_path, monkeypatch) -> None:
    phrase_index = tmp_path / "phrase_index.jsonl.gz"
    with gzip.open(phrase_index, "wt", encoding="utf-8") as handle:
        handle.write(json.dumps({"phrase_id": "p1"}) + "\n")
    monkeypatch.setattr(canary, "REPO_ROOT", tmp_path)
    manifest = {
        "asset_mode": "full",
        "full_asset_available": True,
        "full_raw_ngram_rebuild_confirmed": True,
        "sample_line_limit_per_order": None,
        "scan_mode": "whole_phrase_only",
        "internal_phrase_windows": False,
        "phrase_index_path": "phrase_index.jsonl.gz",
        "phrase_entry_count": 0,
        "phrase_index_rows_checked": 1,
        "phrase_index_invalid_row_count": 1,
    }

    blocked = canary.validate_full_asset_summary(manifest)

    assert any("missing required fields" in reason for reason in blocked)
    assert any("phrase_entry_count" in reason for reason in blocked)


def valid_phrase_index_row() -> dict[str, object]:
    return {
        "phrase_id": "p1",
        "direction": "fwd",
        "dictionary_cut": "normal",
        "ngram_order": 2,
        "word_token_ids": [[1, 2, 3, 4], [5, 6, 7, 8]],
        "rune_token_ids": [1, 2, 3, 4, 5, 6, 7, 8],
        "word_lengths": [4, 4],
        "phrase_token_length": 8,
        "count": 1.0,
        "sum_count": 1.0,
        "max_count": 1.0,
        "log_count": 0.69,
        "max_log_count": 0.69,
        "phrase_count": 1,
        "top_latin_ngram_for_max_count": "abcd efgh",
    }


def test_phrase_index_validation_rejects_bad_token_shapes() -> None:
    cases = [
        ("bool token", {"word_token_ids": [[True], [2, 3, 4, 5, 6, 7, 8, 9]]}),
        ("float token", {"word_token_ids": [[1.2], [2, 3, 4, 5, 6, 7, 8, 9]]}),
        ("token outside range", {"rune_token_ids": [29]}),
        ("empty word", {"word_token_ids": [[], [2, 3, 4, 5, 6, 7, 8, 9]]}),
    ]
    for _name, patch in cases:
        row = valid_phrase_index_row()
        row.update(patch)
        errors = canary.validate_phrase_index_row(row, 1)
        assert errors


def test_phrase_index_validation_rejects_bad_counts() -> None:
    cases = [
        {"count": -1.0},
        {"log_count": math.inf},
        {"phrase_count": 0},
    ]
    for patch in cases:
        row = valid_phrase_index_row()
        row.update(patch)
        errors = canary.validate_phrase_index_row(row, 1)
        assert errors


def test_canary_records_whole_phrase_only_and_no_internal_windows() -> None:
    assert canary.SCAN_MODE == "whole_phrase_only"
    assert canary.INTERNAL_PHRASE_WINDOWS is False
    assert canary.NO_PRODUCTION_SCORER_CHANGES is True
    assert [profile.profile_id for profile in canary.PROFILES] == [
        "P2_conservative_len8_hd2",
        "P3_word_shape_guarded_len8_hd2",
    ]


def test_duplicate_phrase_identity_collapse_preserves_frequency_metadata() -> None:
    collapsed: dict[tuple[str, str, int, tuple[tuple[int, ...], ...]], dict[str, object]] = {}
    first = PhraseEntry(
        phrase_id="a",
        direction="fwd",
        dictionary_cut="normal",
        ngram_order=2,
        word_token_ids=((1, 2, 3, 4), (5, 6, 7, 8)),
        rune_token_ids=(1, 2, 3, 4, 5, 6, 7, 8),
        count=3.0,
        log_count=1.386,
        phrase_count=1,
        top_latin_ngram="low count",
    )
    second = PhraseEntry(
        phrase_id="b",
        direction="fwd",
        dictionary_cut="normal",
        ngram_order=2,
        word_token_ids=((1, 2, 3, 4), (5, 6, 7, 8)),
        rune_token_ids=(1, 2, 3, 4, 5, 6, 7, 8),
        count=9.0,
        log_count=2.303,
        phrase_count=2,
        top_latin_ngram="high count",
    )

    summary.add_collapsed_entry(collapsed, first, {"top_latin_ngram": "low count"})
    summary.add_collapsed_entry(collapsed, second, {"top_latin_ngram": "high count"})
    row = summary.collapsed_to_json(next(iter(collapsed.values())))

    assert row["sum_count"] == 12.0
    assert row["max_count"] == 9.0
    assert row["max_log_count"] == 2.303
    assert row["phrase_count"] == 3
    assert row["top_latin_ngram_for_max_count"] == "high count"
    assert row["duplicate_row_count"] == 1


def test_hit_payload_records_short_word_and_normalised_diagnostics() -> None:
    hit = {
        "candidate_id": "c1",
        "chunk_id": "k1",
        "ngram_order": 2,
        "dictionary_cut": "normal",
        "phrase_token_length": 11,
        "word_lengths": [1, 10],
        "word_hds": [1, 0],
        "total_phrase_hd": 1,
        "max_word_hd": 1,
        "phrase_count": 1,
        "phrase_log_count": 7.0,
        "hit_start": 2,
        "hit_end": 13,
        "phrase_id": "p",
    }

    row = canary.hit_payload(
        hit,
        candidate_role_value="known_better",
        profile_id="P2_conservative_len8_hd2",
        phrase_metadata={
            "sum_count": 12.0,
            "max_count": 9.0,
            "max_log_count": 2.3,
            "duplicate_row_count": 1,
            "top_latin_ngram_for_max_count": "high count",
        },
    )

    assert row["short_word_count"] == 1
    assert row["short_word_token_count"] == 1
    assert row["short_word_hd"] == 1
    assert row["short_word_mismatch_count"] == 1
    assert row["non_short_word_token_count"] == 10
    assert row["normalised_total_hd"] == 1 / 11
    assert row["normalised_non_short_hd"] == 0.0
    assert row["sum_count"] == 12.0
    assert row["max_count"] == 9.0
    assert row["max_log_count"] == 2.3
    assert row["duplicate_row_count"] == 1
    assert row["top_latin_ngram_for_max_count"] == "high count"


def test_aggregate_rows_keep_order_and_role_keys() -> None:
    row = {
        "candidate_id": "c1",
        "chunk_id": "k1",
        "candidate_role": "known_better",
        "profile_id": "P2_conservative_len8_hd2",
        "cut": "normal",
        "direction": "fwd",
        "ngram_order": 3,
        "phrase_token_length_bin": "11-15",
        "word_length_pattern": "[1,10]",
        "phrase_log_count_bin": "medium",
        "phrase_log_count": 7.0,
        "total_phrase_hd_bin": "1",
        "normalised_total_hd_bin": "0-0.10",
        "short_word_fraction_of_phrase_bin": "0-0.25",
        "non_short_word_token_count_bin": "6-10",
        "normalised_non_short_hd_bin": "0",
        "phrase_id": "p",
        "hit_start": 1,
        "hit_end": 12,
    }

    aggregates = canary.aggregate_hit_rows([row])
    length_row = aggregates["hit_summary_by_phrase_length_bin.csv"][0]

    assert length_row["ngram_order"] == 3
    assert length_row["candidate_role"] == "known_better"
    assert length_row["direction"] == "fwd"
    assert "normalised_non_short_hd_distribution.csv" in aggregates


def test_candidate_chunk_profile_aggregate_rows_include_zero_hit_cells() -> None:
    cell_rows = [
        {
            "candidate_id": "c1",
            "chunk_id": "k1",
            "candidate_role": "known_better",
            "cut": "normal",
            "direction": "fwd",
            "ngram_order": 2,
            "profile_id": "P2_conservative_len8_hd2",
        }
    ]

    rows = canary.candidate_chunk_profile_aggregate_rows(cell_rows, [])

    assert len(rows) == 1
    assert rows[0]["raw_hit_count"] == 0
    assert rows[0]["unique_phrase_hit_count"] == 0
    assert rows[0]["weighted_hit_sum"] == 0
    assert rows[0]["max_phrase_log_count"] == 0
    assert rows[0]["mean_phrase_log_count"] == 0
    assert rows[0]["cell_p2_hit_count"] == 0
    assert rows[0]["cell_p3_retained_hit_count"] == 0
    assert rows[0]["cell_p2_only_rejected_by_p3_count"] == 0


def test_length_and_frequency_bins_are_stable() -> None:
    assert canary.length_bin(8) == "8-10"
    assert canary.length_bin(10) == "8-10"
    assert canary.length_bin(11) == "11-15"
    assert canary.length_bin(16) == "16-20"
    assert canary.length_bin(21) == "21+"
    assert canary.log_count_bin(1.0) == "low"
    assert canary.log_count_bin(7.0) == "medium"
    assert canary.log_count_bin(12.0) == "high"
    assert canary.log_count_bin(18.0) == "very_high"
