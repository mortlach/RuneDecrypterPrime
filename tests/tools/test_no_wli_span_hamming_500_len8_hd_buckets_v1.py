from __future__ import annotations

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    scan_span_hamming_500_len8_hd_buckets_canary_v1 as mod,
)


def test_bucket_features_counts_raw_and_selected_hd_buckets() -> None:
    payload = {
        "raw_intervals": [
            {"length": 8, "distance": 0},
            {"length": 8, "distance": 2},
            {"length": 8, "distance": 4},
            {"length": 7, "distance": 0},
        ],
        "selected_intervals": [
            {"length": 8, "distance": 0},
            {"length": 8, "distance": 4},
        ],
        "n_candidates_considered": 90,
        "n_candidates_pruned_cap": 10,
    }

    features = mod.bucket_features(payload, 500)

    assert features["raw_len8_hd0_count"] == 1
    assert features["raw_len8_hd2_count"] == 1
    assert features["raw_len8_hd4_count"] == 1
    assert features["raw_len8_hd_le2_count"] == 2
    assert features["raw_len8_hd3_4_count"] == 1
    assert features["selected_len8_hd0_count"] == 1
    assert features["selected_len8_hd4_count"] == 1
    assert features["candidate_cap_pruned_rate"] == 0.1


def test_len8_pair_summary_evaluates_higher_and_lower_directions() -> None:
    pair_rows = [
        {
            "pair_id": "p1",
            "winner_token_hash": "w",
            "challenger_token_hash": "c",
            "current_score_correct": "0",
        }
    ]
    candidate_rows = [
        {"config_id": "cfg", "token_hash": "w", "chunk_kind": "prefix", "raw_len8_hd4_count": "1"},
        {"config_id": "cfg", "token_hash": "c", "chunk_kind": "prefix", "raw_len8_hd4_count": "5"},
    ]

    rows = mod.build_pair_summaries(pair_rows=pair_rows, candidate_rows=candidate_rows)
    higher = next(row for row in rows if row["feature_name"] == "raw_len8_hd4_count" and row["feature_direction"] == "higher")
    lower = next(row for row in rows if row["feature_name"] == "raw_len8_hd4_count" and row["feature_direction"] == "lower")

    assert higher["truth_worse"] == 1
    assert higher["net"] == 0
    assert lower["net"] == 1
