from __future__ import annotations

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    scan_span_hamming_500_normalized_canary_v1 as mod,
)


def test_build_chunk_samples_uses_prefix_middle_suffix_500() -> None:
    samples = mod.build_chunk_samples({"abc": tuple(range(1000))})
    assert [(sample.chunk_kind, sample.start, sample.end) for sample in samples] == [
        ("prefix", 0, 500),
        ("middle", 250, 750),
        ("suffix", 500, 1000),
    ]
    assert all(len(sample.tokens) == 500 for sample in samples)


def test_build_chunk_samples_skips_short_texts() -> None:
    assert mod.build_chunk_samples({"abc": tuple(range(499))}) == []


def test_normalized_features_scale_hamming_error_by_length() -> None:
    payload = {
        "selected_intervals": [
            {"length": 10, "distance": 2},
            {"length": 14, "distance": 2},
            {"length": 4, "distance": 1},
        ],
        "n_candidates_considered": 10,
        "n_candidates_pruned_cap": 5,
    }
    features = mod._normalized_features(payload, 500)

    assert features["err20_len_ge_10_norm"] > 0.0
    assert features["err20_len_ge_12_norm"] > 0.0
    assert features["err15_len_ge_8_norm"] > 0.0
    assert features["short_fuzzy_noise_len_le_4_norm"] > 0.0
    assert features["candidate_cap_pruned_rate"] == 5 / 15


def test_feature_preference_respects_lower_noise_direction() -> None:
    assert mod._feature_preference("lower", 0.1, 0.2) == "truth_better"
    assert mod._feature_preference("lower", 0.3, 0.2) == "truth_worse"

