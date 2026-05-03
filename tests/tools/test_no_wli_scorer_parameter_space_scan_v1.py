from __future__ import annotations

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import scan_scorer_parameter_space_v1 as mod


def test_numeric_token_parser_rejects_out_of_range_values() -> None:
    assert mod._parse_numeric_tokens("0 1 28") == (0, 1, 28)
    with pytest.raises(ValueError):
        mod._parse_numeric_tokens("0 29")
    with pytest.raises(ValueError):
        mod._parse_numeric_tokens("0 -1")


def test_chunk_samples_are_not_marked_as_full_candidates() -> None:
    rows = {"abc": tuple(range(29)) * 40}
    samples = mod.build_token_samples(rows)
    full = [sample for sample in samples if sample.is_full_candidate]
    chunks = [sample for sample in samples if not sample.is_full_candidate]
    assert len(full) == 1
    assert full[0].sample_kind == "full"
    assert chunks
    assert all(sample.sample_kind != "full" for sample in chunks)


def test_word_trust_neither_active_is_no_decision() -> None:
    span_winner = {"span_raw": 0.2}
    span_challenger = {"span_raw": 0.1}
    word_winner = {"word_active": 0, "word_trust_score": 0.0}
    word_challenger = {"word_active": 0, "word_trust_score": 0.0}
    winner, challenger, reason = mod._feature_values_for_pair(
        "word_trust_active_any",
        span_winner,
        span_challenger,
        word_winner,
        word_challenger,
    )
    assert winner is None
    assert challenger is None
    assert reason == "neither_word_ngram_active"
    assert mod._feature_preference("higher", winner, challenger) == "no_decision"


def test_word_xent_requires_both_candidates_active() -> None:
    span_winner = {"span_raw": 0.2}
    span_challenger = {"span_raw": 0.1}
    word_winner = {"word_active": 1, "word_xent": 3.0}
    word_challenger = {"word_active": 0, "word_xent": 20.0}
    winner, challenger, reason = mod._feature_values_for_pair(
        "word_xent_both_active",
        span_winner,
        span_challenger,
        word_winner,
        word_challenger,
    )
    assert winner is None
    assert challenger is None
    assert reason == "not_both_word_ngram_active"


def test_no_decision_counts_are_not_double_counted() -> None:
    span_spec = mod._span_specs()[0]
    word_spec = mod._word_specs()[0]
    pair_rows = [
        {
            "pair_id": "pair_1",
            "winner_token_hash": "truth_better",
            "challenger_token_hash": "truth_worse",
            "current_score_correct": "0",
        }
    ]
    span_rows = [
        {
            "token_hash": "truth_better",
            "sample_kind": "full",
            "span_config_id": span_spec.config_id,
            "span_raw": "",
            "span_coverage": "",
            "span_quality": "",
            "span_interval_count": "",
            "span_mean_interval_length": "",
            "span_candidate_cap_pruned_rate": "",
        },
        {
            "token_hash": "truth_worse",
            "sample_kind": "full",
            "span_config_id": span_spec.config_id,
            "span_raw": "",
            "span_coverage": "",
            "span_quality": "",
            "span_interval_count": "",
            "span_mean_interval_length": "",
            "span_candidate_cap_pruned_rate": "",
        },
    ]
    word_rows = [
        {
            "token_hash": row["token_hash"],
            "sample_kind": "full",
            "span_config_id": span_spec.config_id,
            "word_config_id": word_spec.config_id,
            "word_active": 0,
            "word_trust_score": 0.0,
        }
        for row in span_rows
    ]

    summary_rows, _flag_rows, _active_rows = mod.build_pair_summaries(
        pair_rows=pair_rows,
        span_rows=span_rows,
        word_rows=word_rows,
    )
    span_raw = next(row for row in summary_rows if row["feature_name"] == "span_raw")
    assert span_raw["pair_count"] == 1
    assert span_raw["no_decision"] == 1
    assert span_raw["current_misranked_no_decision"] == 1


def test_span_candidate_cap_pressure_prefers_lower() -> None:
    assert mod._feature_preference("lower", 0.0, 0.1) == "truth_better"
    assert mod._feature_preference("lower", 0.2, 0.1) == "truth_worse"
    assert mod._feature_preference("lower", 0.1, 0.1) == "tie"


def test_missing_dictionary_config_is_reported_without_fallback() -> None:
    spec = mod.SpanSpec(
        config_id="missing_policy",
        len_min=3,
        len_max=14,
        max_hd=2,
        max_candidates_per_window=256,
        require_selected=True,
        wordlist_rel="assets/does_not_exist_for_s1e_test",
    )
    backend, reason, build_ms = mod._build_span_backend(spec)
    assert backend is None
    assert build_ms == 0.0
    assert reason == "missing_wordlist_dir:assets/does_not_exist_for_s1e_test"


def test_pair_metrics_use_current_score_failure_and_control_split() -> None:
    span_spec = mod._span_specs()[0]
    word_spec = mod._word_specs()[0]
    pair_rows = [
        {
            "pair_id": "misranked",
            "winner_token_hash": "truth_better_a",
            "challenger_token_hash": "truth_worse_a",
            "current_score_correct": "0",
        },
        {
            "pair_id": "control",
            "winner_token_hash": "truth_better_b",
            "challenger_token_hash": "truth_worse_b",
            "current_score_correct": "1",
        },
    ]
    span_rows = [
        {
            "token_hash": "truth_better_a",
            "sample_kind": "full",
            "span_config_id": span_spec.config_id,
            "span_raw": 2.0,
            "span_coverage": 1.0,
            "span_quality": 1.0,
            "span_interval_count": 1,
            "span_mean_interval_length": 3,
            "span_candidate_cap_pruned_rate": 0.0,
        },
        {
            "token_hash": "truth_worse_a",
            "sample_kind": "full",
            "span_config_id": span_spec.config_id,
            "span_raw": 1.0,
            "span_coverage": 1.0,
            "span_quality": 1.0,
            "span_interval_count": 1,
            "span_mean_interval_length": 3,
            "span_candidate_cap_pruned_rate": 0.0,
        },
        {
            "token_hash": "truth_better_b",
            "sample_kind": "full",
            "span_config_id": span_spec.config_id,
            "span_raw": 1.0,
            "span_coverage": 1.0,
            "span_quality": 1.0,
            "span_interval_count": 1,
            "span_mean_interval_length": 3,
            "span_candidate_cap_pruned_rate": 0.0,
        },
        {
            "token_hash": "truth_worse_b",
            "sample_kind": "full",
            "span_config_id": span_spec.config_id,
            "span_raw": 2.0,
            "span_coverage": 1.0,
            "span_quality": 1.0,
            "span_interval_count": 1,
            "span_mean_interval_length": 3,
            "span_candidate_cap_pruned_rate": 0.0,
        },
    ]
    word_rows = [
        {
            "token_hash": row["token_hash"],
            "sample_kind": "full",
            "span_config_id": span_spec.config_id,
            "word_config_id": word_spec.config_id,
            "word_active": 0,
            "word_trust_score": 0.0,
        }
        for row in span_rows
    ]

    summary_rows, flag_rows, active_rows = mod.build_pair_summaries(
        pair_rows=pair_rows,
        span_rows=span_rows,
        word_rows=word_rows,
    )
    span_raw = next(row for row in summary_rows if row["feature_name"] == "span_raw")
    assert span_raw["current_misranked_pair_count"] == 1
    assert span_raw["current_correct_control_pair_count"] == 1
    assert span_raw["rescues"] == 1
    assert span_raw["breaks"] == 1
    assert flag_rows
    assert active_rows


def test_readout_reports_review_only_status() -> None:
    readout = mod._build_readout(
        {
            "pair_count": 2,
            "required_token_hash_count": 2,
            "token_sample_count": 2,
            "span_config_count": 1,
            "word_config_count": 1,
            "full_candidate_below_min_token_length_count": 0,
            "caveats": ["report-only caveat"],
        }
    )
    assert "does not change runtime behaviour" in readout
    assert "Numeric rune/base-29 token sequences only" in readout
