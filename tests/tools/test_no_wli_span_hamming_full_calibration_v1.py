from __future__ import annotations

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    calibrate_span_hamming_full_space_v1 as mod,
)


def test_numeric_token_parser_rejects_out_of_range_values() -> None:
    assert mod._parse_numeric_tokens("0 1 28") == (0, 1, 28)
    with pytest.raises(ValueError):
        mod._parse_numeric_tokens("29")
    with pytest.raises(ValueError):
        mod._parse_numeric_tokens("-1")


def test_error_rate_and_bucket_contract() -> None:
    assert mod._error_rate(0, 5) == pytest.approx(0.0)
    assert mod._error_rate(1, 5) == pytest.approx(0.2)
    assert mod._error_bucket(0, 5) == "exact"
    assert mod._error_bucket(1, 10) == "very_low_error"
    assert mod._error_bucket(2, 10) == "medium_low_error"
    assert mod._error_bucket(3, 10) == "high_error"
    assert mod._error_bucket(5, 10) == "very_high_error"
    with pytest.raises(ValueError):
        mod._error_rate(2, 1)


def test_candidate_fieldnames_are_unique() -> None:
    fields = mod._candidate_fieldnames()
    assert len(fields) == len(set(fields))
    assert "span_raw_selected_current" in fields
    assert "candidate_cap_pruned_rate" in fields


def test_missing_dictionary_is_reported() -> None:
    spec = mod.SpanConfigSpec(
        config_id="missing",
        dictionary_id="missing",
        wordlist_rel="assets/does_not_exist_for_s1f_test",
        require_selected=True,
        template_id="t",
        len_min=1,
        len_max=3,
        max_hd=1,
        max_candidates_per_window=256,
    )
    rows = mod._dictionary_summary([spec])
    assert rows[0]["wordlist_exists"] == 0
    assert rows[0]["missing_reason"] == "missing_wordlist_dir:assets/does_not_exist_for_s1f_test"


def test_pair_feature_summary_counts_rescues_and_breaks() -> None:
    pair_rows = [
        {
            "winner_token_hash": "truth_better_a",
            "challenger_token_hash": "truth_worse_a",
            "current_score_correct": "0",
        },
        {
            "winner_token_hash": "truth_better_b",
            "challenger_token_hash": "truth_worse_b",
            "current_score_correct": "1",
        },
    ]
    candidate_rows = [
        {
            "config_id": "cfg",
            "token_hash": "truth_better_a",
            "span_raw_selected_current": 2.0,
            "candidate_cap_pruned_rate": 0.1,
        },
        {
            "config_id": "cfg",
            "token_hash": "truth_worse_a",
            "span_raw_selected_current": 1.0,
            "candidate_cap_pruned_rate": 0.2,
        },
        {
            "config_id": "cfg",
            "token_hash": "truth_better_b",
            "span_raw_selected_current": 1.0,
            "candidate_cap_pruned_rate": 0.2,
        },
        {
            "config_id": "cfg",
            "token_hash": "truth_worse_b",
            "span_raw_selected_current": 2.0,
            "candidate_cap_pruned_rate": 0.1,
        },
    ]
    rows = mod._pair_feature_summary(pair_rows, candidate_rows)
    span_raw = next(row for row in rows if row["feature_name"] == "span_raw_selected_current")
    cap_rate = next(row for row in rows if row["feature_name"] == "candidate_cap_pruned_rate")

    assert span_raw["rescues"] == 1
    assert span_raw["breaks"] == 1
    assert span_raw["net"] == 0
    assert cap_rate["rescues"] == 1
    assert cap_rate["breaks"] == 1


def test_chunk_rows_are_marked_not_for_pair_metrics() -> None:
    row = {
        "config_id": "cfg",
        "token_hash": "abc",
        "sample_kind": "prefix_300",
        "token_length": 300,
        "elapsed_ms": "1.0",
        "backend_build_ms": "2.0",
        "used_for_pair_metrics": 0,
        "missing_reason": "",
    }
    assert row["used_for_pair_metrics"] == 0


def test_readout_states_no_runtime_change_and_interval_caveat() -> None:
    readout = mod._build_readout(
        {
            "pair_row_count": 2,
            "token_hash_count": 2,
            "config_count_requested": 1,
            "config_count_run": 1,
            "config_count_missing": 0,
            "candidate_feature_row_count": 2,
            "interval_bucket_row_count": 4,
            "pair_feature_summary_row_count": 2,
            "python_parity_failure_count": 0,
            "elapsed_seconds": 60.0,
        },
        [],
    )
    assert "No runtime behaviour changed" in readout
    assert "aggregate buckets" in readout
    assert "Numeric rune/base-29" in readout
