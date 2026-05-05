from __future__ import annotations

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    scan_span_hamming_500_length_hd_fingerprint_canary_v1 as mod,
)


def test_length_bucket_features_count_each_hd_bucket() -> None:
    payload = {
        "raw_intervals": [
            {"length": 6, "distance": 0},
            {"length": 6, "distance": 2},
            {"length": 6, "distance": 3},
            {"length": 7, "distance": 0},
        ],
        "selected_intervals": [
            {"length": 6, "distance": 2},
        ],
        "n_candidates_considered": 100,
        "n_candidates_pruned_cap": 0,
    }

    features = mod.length_bucket_features(payload, length=6, token_length=500)

    assert features["raw_len6_hd0_count"] == 1
    assert features["raw_len6_hd2_count"] == 1
    assert features["raw_len6_hd3_count"] == 1
    assert features["raw_len6_hd_le2_count"] == 2
    assert features["selected_len6_hd2_count"] == 1
    assert features["raw_len6_mean_hd"] == (0 + 2 + 3) / 3
    assert features["len6_candidate_cap_pruned_rate"] == 0.0


def test_fingerprint_aggregate_features_use_expected_directions() -> None:
    row = {
        "len6_window_count": 495,
        "raw_len6_hd0_count": 2,
        "raw_len6_hd_le1_count": 5,
        "raw_len6_matched_window_count": 10,
        "raw_len6_mean_error_rate": 0.2,
        "selected_len6_hd0_count": 1,
        "selected_len6_hd_le1_count": 3,
        "selected_len6_matched_window_count": 5,
        "selected_len6_mean_error_rate": 0.1,
    }
    for length in (7, 8, 9, 10):
        row[f"len{length}_window_count"] = 0
        row[f"raw_len{length}_hd0_count"] = 0
        row[f"raw_len{length}_hd_le{round(length * 0.20)}_count"] = 0
        row[f"raw_len{length}_matched_window_count"] = 0
        row[f"raw_len{length}_mean_error_rate"] = 0
        row[f"selected_len{length}_hd0_count"] = 0
        row[f"selected_len{length}_hd_le{round(length * 0.20)}_count"] = 0
        row[f"selected_len{length}_matched_window_count"] = 0
        row[f"selected_len{length}_mean_error_rate"] = 0

    features = mod._aggregate_features(row)

    assert features["raw_fingerprint_exact_count_norm"] == 2 / 495
    assert features["raw_fingerprint_close20_count_norm"] == 5 / 495
    assert features["raw_fingerprint_mean_error_rate"] == 0.2
    assert mod._feature_direction("raw_fingerprint_mean_error_rate") == "lower"
