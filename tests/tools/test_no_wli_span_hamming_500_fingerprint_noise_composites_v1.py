from __future__ import annotations

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    sweep_span_hamming_500_fingerprint_noise_composites_v1 as mod,
)


def test_joined_rows_zscores_per_chunk() -> None:
    normalized = [
        {
            "config_id": mod.NORMALIZED_CONFIG_ID,
            "token_hash": "a",
            "chunk_kind": "prefix",
            "short_fuzzy_noise_len_le_4_norm": "1",
            "short_fuzzy_interval_count_norm": "2",
            "err20_len_ge_5_norm": "3",
            "exact_len_ge_5_norm": "4",
        },
        {
            "config_id": mod.NORMALIZED_CONFIG_ID,
            "token_hash": "b",
            "chunk_kind": "prefix",
            "short_fuzzy_noise_len_le_4_norm": "3",
            "short_fuzzy_interval_count_norm": "4",
            "err20_len_ge_5_norm": "5",
            "exact_len_ge_5_norm": "6",
        },
    ]
    fingerprint = [
        {
            "config_id": mod.FINGERPRINT_CONFIG_ID,
            "token_hash": "a",
            "chunk_kind": "prefix",
            "sample_id": "a::prefix",
            "selected_fingerprint_exact_count_norm": "1",
            "selected_fingerprint_close20_count_norm": "1",
            "selected_fingerprint_mean_error_rate": "1",
            "raw_fingerprint_exact_count_norm": "1",
            "raw_fingerprint_close20_count_norm": "1",
            "raw_fingerprint_mean_error_rate": "1",
            "selected_len6_hd0_count_norm": "1",
            "raw_len6_hd0_count_norm": "1",
            "selected_len8_hd_le3_count_norm": "1",
            "raw_len8_hd_le3_count_norm": "1",
        },
        {
            "config_id": mod.FINGERPRINT_CONFIG_ID,
            "token_hash": "b",
            "chunk_kind": "prefix",
            "sample_id": "b::prefix",
            "selected_fingerprint_exact_count_norm": "3",
            "selected_fingerprint_close20_count_norm": "3",
            "selected_fingerprint_mean_error_rate": "3",
            "raw_fingerprint_exact_count_norm": "3",
            "raw_fingerprint_close20_count_norm": "3",
            "raw_fingerprint_mean_error_rate": "3",
            "selected_len6_hd0_count_norm": "3",
            "raw_len6_hd0_count_norm": "3",
            "selected_len8_hd_le3_count_norm": "3",
            "raw_len8_hd_le3_count_norm": "3",
        },
    ]

    rows = mod._joined_rows(normalized, fingerprint)

    assert len(rows) == 2
    assert rows[0]["z_fp_selected_exact"] == -1
    assert rows[1]["z_fp_selected_exact"] == 1
    assert rows[0]["z_noise_short"] == -1
    assert rows[1]["z_noise_short"] == 1


def test_vote_preference_requires_two_chunks() -> None:
    assert mod._vote_preference({"prefix": 1, "middle": 1, "suffix": 0}, {"prefix": 0, "middle": 0, "suffix": 1}) == "truth_better"
    assert mod._vote_preference({"prefix": 0, "middle": 1, "suffix": 0}, {"prefix": 1, "middle": 0, "suffix": 1}) == "truth_worse"
