from __future__ import annotations

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    audit_scorer_component_contracts_v1 as contracts,
)


def _pair(**overrides):
    row = {
        "pair_id": "pair-1",
        "artifact_path": "missing_artifact.json",
        "fixture_id": "fixture",
        "fixture_seed": "411",
        "search_seed": "0",
        "token_length": "1000",
        "winner_token_hash": "tw",
        "challenger_token_hash": "tc",
        "current_score_correct": "0",
    }
    row.update(overrides)
    return row


def _candidate(**overrides):
    row = {
        "token_hash": "tw",
        "token_length": "1000",
        "word_ngram_available": "1",
        "word_ngram_active": "1",
        "word_ngram_trust_score": "0.6",
        "word_ngram_xent": "2.0",
        "word_ngram_backoff_xent": "1.8",
        "word_ngram_miss_rate": "0.1",
    }
    row.update(overrides)
    return row


def test_pair_context_reports_below_min_length(monkeypatch) -> None:
    monkeypatch.setattr(
        contracts,
        "_artifact_context",
        lambda _path: {
            "direction": "ltr",
            "period": "9",
            "columns": "3",
            "alphabet_size": "29",
            "order": "sub_then_col",
        },
    )

    rows = contracts.build_pair_context_rows([
        _pair(token_length="1000"),
        _pair(pair_id="short", token_length="499"),
    ])

    assert int(rows[0]["below_min_token_length"]) == 0
    assert int(rows[1]["below_min_token_length"]) == 1
    assert rows[0]["direction"] == "ltr"


def test_active_state_rows_distinguish_pair_states_and_active_only_features() -> None:
    pair_rows = [
        _pair(pair_id="both"),
        _pair(pair_id="winner-only", winner_token_hash="tw", challenger_token_hash="tc_inactive"),
        _pair(pair_id="challenger-only", winner_token_hash="tw_inactive", challenger_token_hash="tc"),
    ]
    candidate_rows = [
        _candidate(token_hash="tw", word_ngram_active="1", word_ngram_trust_score="0.6", word_ngram_xent="2.0"),
        _candidate(token_hash="tc", word_ngram_active="1", word_ngram_trust_score="0.4", word_ngram_xent="3.0"),
        _candidate(token_hash="tc_inactive", word_ngram_active="0", word_ngram_trust_score="0.0", word_ngram_xent="20.0"),
        _candidate(token_hash="tw_inactive", word_ngram_active="0", word_ngram_trust_score="0.0", word_ngram_xent="20.0"),
    ]

    rows = contracts.build_active_state_rows(pair_rows=pair_rows, candidate_rows=candidate_rows)
    by_pair = {row["pair_id"]: row for row in rows}

    assert by_pair["both"]["word_active_pair_state"] == "both_active"
    assert by_pair["both"]["word_trust_prefers_truth_better_active_pair"] == 1
    assert by_pair["both"]["word_xent_prefers_truth_better_both_active"] == 1
    assert by_pair["winner-only"]["word_active_pair_state"] == "winner_only_active"
    assert by_pair["winner-only"]["word_xent_prefers_truth_better_both_active"] == ""
    assert by_pair["challenger-only"]["word_active_pair_state"] == "challenger_only_active"
    assert by_pair["challenger-only"]["word_trust_prefers_truth_better_active_pair"] == 0


def test_cache_context_marks_token_hash_only_unsafe_when_contexts_differ() -> None:
    rows = [
        {
            "winner_token_hash": "same",
            "challenger_token_hash": "other",
            "direction": "ltr",
            "period": "9",
            "columns": "3",
            "alphabet_size": "29",
            "order": "sub_then_col",
        },
        {
            "winner_token_hash": "same",
            "challenger_token_hash": "other2",
            "direction": "rtl",
            "period": "9",
            "columns": "3",
            "alphabet_size": "29",
            "order": "sub_then_col",
        },
    ]

    cache_rows = contracts.build_cache_context_rows(rows)
    same = [row for row in cache_rows if row["token_hash"] == "same"][0]

    assert int(same["context_count"]) == 2
    assert int(same["cache_safe_for_token_hash_only"]) == 0


def test_summary_records_contract_go_no_go(monkeypatch) -> None:
    monkeypatch.setattr(contracts, "_asset_snapshot", lambda: {"word_ngram_sqlite_exists": True})
    pair_context_rows = [
        {
            "pair_id": "p1",
            "token_length": 1000,
            "below_min_token_length": 0,
            "direction": "ltr",
            "period": "9",
            "columns": "3",
            "alphabet_size": "29",
            "order": "sub_then_col",
            "winner_token_hash": "tw",
            "challenger_token_hash": "tc",
        }
    ]
    candidate_rows = [
        _candidate(token_hash="tw"),
        _candidate(token_hash="tc", word_ngram_active="0"),
    ]
    active_rows = contracts.build_active_state_rows(
        pair_rows=[_pair(pair_id="p1", winner_token_hash="tw", challenger_token_hash="tc")],
        candidate_rows=candidate_rows,
    )
    cache_rows = contracts.build_cache_context_rows(pair_context_rows)

    summary = contracts.build_summary(
        pair_context_rows=pair_context_rows,
        candidate_rows=candidate_rows,
        active_rows=active_rows,
        cache_context_rows=cache_rows,
    )

    assert summary["runtime_behavior_changed"] is False
    assert summary["truth_is_evaluation_only"] is True
    assert summary["all_pairs_ltr"] is True
    assert summary["hard_coded_ltr_word_call_safe_for_s1"] is True
    assert summary["token_hash_only_cache_safe_for_s1"] is True
    assert summary["stage2_go"] is False
    assert summary["span_hamming_config"]["len_min"] == 3
    assert summary["word_ngram_config"]["min_positions"] == 12
