from __future__ import annotations

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    scan_span_hamming_selected_dictionary_500_unit_fingerprint_v1 as mod,
)


def test_numeric_tokens_must_be_0_to_28() -> None:
    assert mod._parse_numeric_tokens("0 1 28") == (0, 1, 28)
    with pytest.raises(ValueError):
        mod._parse_numeric_tokens("29")
    with pytest.raises(ValueError):
        mod._parse_numeric_tokens("-1")


def test_dictionary_specs_are_selected_only() -> None:
    mod._validate_selected_only_specs()
    assert all(spec.require_selected for spec in mod.DICTIONARY_SPECS)
    assert not any(spec.dictionary_cut.endswith("_all") for spec in mod.DICTIONARY_SPECS)


def test_require_selected_false_is_rejected() -> None:
    with pytest.raises(ValueError):
        mod._validate_selected_only_specs(
            [mod.DictionarySpec("raw_selected", "assets/hamming_raw_1g", False)]
        )


def test_all_dictionary_ids_are_rejected() -> None:
    with pytest.raises(ValueError):
        mod._validate_selected_only_specs(
            [mod.DictionarySpec("raw_all", "assets/hamming_raw_1g", True)]
        )


def test_500_chunks_are_deterministic_and_full_1000_is_separate() -> None:
    tokens = tuple(range(1000))
    samples = mod.build_chunk_samples({"tok": tokens})
    by_kind = {sample.sample_kind: sample for sample in samples}

    assert by_kind["prefix_500"].sample_start == 0
    assert by_kind["prefix_500"].sample_length == 500
    assert by_kind["middle_500"].sample_start == 250
    assert by_kind["middle_500"].sample_length == 500
    assert by_kind["suffix_500"].sample_start == 500
    assert by_kind["suffix_500"].sample_length == 500
    assert by_kind["full_1000"].sample_start == 0
    assert by_kind["full_1000"].sample_length == 1000


def test_hd_bins_are_zero_to_length_minus_one() -> None:
    assert mod.HD_MAX_POLICY == "length_minus_one"
    for length in mod.SPAN_LENGTHS:
        assert list(range(length))[0] == 0
        assert list(range(length))[-1] == length - 1


def test_error_rate_and_exact_fraction_contract() -> None:
    assert mod._error_rate(0, 5) == pytest.approx(0.0)
    assert mod._error_rate(1, 5) == pytest.approx(0.2)
    assert mod._exact_fraction(1, 5) == pytest.approx(0.8)
    with pytest.raises(ValueError):
        mod._error_rate(0, 0)


def test_reference_fingerprint_excludes_hd_equal_length() -> None:
    observed = mod._reference_fingerprint_bin_map(
        [1, 2, 3],
        {
            3: [
                [1, 2, 3],
                [1, 2, 4],
                [1, 5, 4],
                [7, 8, 9],
            ]
        },
    )
    assert observed[(3, 0)] == 1
    assert observed[(3, 1)] == 1
    assert observed[(3, 2)] == 1
    assert (3, 3) not in observed


def test_length_one_has_only_hd_zero() -> None:
    observed = mod._reference_fingerprint_bin_map([1], {1: [[1], [2]]})
    assert observed[(1, 0)] == 1
    assert (1, 1) not in observed


def test_candidate_rows_reject_hd_equal_span_length() -> None:
    sample = mod.ChunkSample("tok", "prefix_500", 0, 3, (1, 2, 3))
    spec = mod.DictionarySpec("raw_selected", "assets/hamming_raw_1g", True)
    payload = {
        "chunk_bins": [{"length": 3, "hd": 3, "raw_match_count": 1}],
        "n_windows_scored": 1,
        "n_candidates_considered": 1,
        "n_candidates_pruned_cap": 0,
        "cap": 0,
        "is_uncapped": True,
    }
    with pytest.raises(ValueError):
        mod._candidate_fingerprint_rows(
            spec=spec,
            sample=sample,
            payload=payload,
            score_ms=1.0,
            backend_name="fast_span_backend",
            build_ms=0.0,
        )


def test_offset_histogram_sums_to_chunk_histogram_shape() -> None:
    # This checks the same aggregation contract used by the backend tests, but
    # at the S1g row-shaping layer.
    sample = mod.ChunkSample("tok", "prefix_500", 0, 3, (1, 2, 3))
    spec = mod.DictionarySpec("raw_selected", "assets/hamming_raw_1g", True)
    payload = {
        "chunk_bins": [
            {"length": 3, "hd": 0, "raw_match_count": 1},
            {"length": 3, "hd": 1, "raw_match_count": 2},
            {"length": 3, "hd": 2, "raw_match_count": 0},
        ],
        "offset_bins": [
            {"offset": 0, "length": 3, "hd": 0, "raw_match_count": 1},
            {"offset": 0, "length": 3, "hd": 1, "raw_match_count": 2},
        ],
        "n_windows_scored": 1,
        "n_candidates_considered": 3,
        "n_candidates_pruned_cap": 0,
        "cap": 0,
        "is_uncapped": True,
    }
    chunk_rows = mod._candidate_fingerprint_rows(
        spec=spec,
        sample=sample,
        payload=payload,
        score_ms=1.0,
        backend_name="fast_span_backend",
        build_ms=0.0,
    )
    offset_rows = mod._offset_fingerprint_rows(
        spec=spec,
        sample=sample,
        payload=payload,
        score_ms=1.0,
        backend_name="fast_span_backend",
    )
    chunk = {(int(row["span_length"]), int(row["hd"])): int(row["raw_match_count"]) for row in chunk_rows}
    offset: dict[tuple[int, int], int] = {}
    for row in offset_rows:
        key = (int(row["span_length"]), int(row["hd"]))
        offset[key] = offset.get(key, 0) + int(row["raw_match_count"])
    assert offset[(3, 0)] == chunk[(3, 0)]
    assert offset[(3, 1)] == chunk[(3, 1)]


def test_500_aggregate_features_are_deterministic() -> None:
    rows = []
    for sample_kind, value in (("prefix_500", 1), ("middle_500", 3), ("suffix_500", 5)):
        rows.append(
            {
                "dictionary_cut": "raw_selected",
                "token_hash": "tok",
                "sample_kind": sample_kind,
                "sample_start": 0,
                "sample_length": 500,
                "span_length": 5,
                "hd": 0,
                "raw_match_count": value,
                "error_rate": 0.0,
                "exact_fraction": 1.0,
            }
        )
    feature_rows = mod._candidate_feature_rows(rows)
    by_basis = {row["sample_basis"]: row for row in feature_rows}

    assert float(by_basis["500_mean"]["hd_le_0"]) == pytest.approx(0.03)
    assert float(by_basis["500_median"]["hd_le_0"]) == pytest.approx(0.03)
    assert float(by_basis["500_min"]["hd_le_0"]) == pytest.approx(0.01)
    assert float(by_basis["500_max"]["hd_le_0"]) == pytest.approx(0.05)
    assert float(by_basis["500_range"]["hd_le_0"]) == pytest.approx(0.04)


def test_pair_rescue_break_uses_explicit_sample_basis() -> None:
    pair_rows = [
        {"pair_id": "p1", "winner_token_hash": "good", "challenger_token_hash": "bad", "current_score_correct": "0"},
        {"pair_id": "p2", "winner_token_hash": "good2", "challenger_token_hash": "bad2", "current_score_correct": "1"},
    ]
    base = {
        "dictionary_cut": "raw_selected",
        "sample_basis": "500_mean",
        "aggregation": "mean",
        "fingerprint_scope": mod.FINGERPRINT_SCOPE,
        "hd_max_policy": mod.HD_MAX_POLICY,
    }
    feature_rows = [
        {**base, "token_hash": "good", "hd_le_0": 2.0},
        {**base, "token_hash": "bad", "hd_le_0": 1.0},
        {**base, "token_hash": "good2", "hd_le_0": 1.0},
        {**base, "token_hash": "bad2", "hd_le_0": 2.0},
    ]
    for row in feature_rows:
        for name, _direction in mod.FEATURE_DEFINITIONS:
            row.setdefault(name, 0.0)
    summary_rows, flag_rows = mod._pair_summaries(pair_rows=pair_rows, feature_rows=feature_rows)
    row = next(row for row in summary_rows if row["feature_name"] == "hd_le_0")

    assert row["sample_basis"] == "500_mean"
    assert row["rescues"] == 1
    assert row["breaks"] == 1
    assert row["net"] == 0
    assert {flag["flag"] for flag in flag_rows} == {"rescue", "break"}


def test_summary_records_report_only_runtime_false_and_hd_policy() -> None:
    summary = mod._summary_json(
        run_mode="inventory_only",
        status="test",
        inventory_rows=[],
        completed_configs=[],
        missing_configs=[],
        skipped_configs=[],
        failed_configs=[],
    )
    assert summary["report_only"] is True
    assert summary["runtime_change"] is False
    assert summary["stage2_gate_promotion"] is False
    assert summary["fingerprint_scope"] == "raw_hamming_counts"
    assert summary["hd_max_policy"] == "length_minus_one"
    assert summary["deviations_from_plan"]


def test_chunk_samples_do_not_duplicate_sample_ids() -> None:
    samples = mod.build_chunk_samples({"tok": tuple(range(1000))})
    sample_ids = [sample.sample_id for sample in samples]
    assert len(sample_ids) == len(set(sample_ids))
    assert [sample.sample_kind for sample in samples] == [
        "prefix_500",
        "middle_500",
        "suffix_500",
        "full_1000",
    ]


def test_cap_pressure_uses_one_row_per_sample_length_not_one_row_per_hd() -> None:
    rows = []
    for hd in range(3):
        rows.append(
            {
                "dictionary_cut": "raw_selected",
                "token_hash": "tok",
                "sample_kind": "prefix_500",
                "sample_start": 0,
                "sample_length": 500,
                "span_length": 3,
                "hd": hd,
                "cap": 0,
                "is_uncapped": 1,
                "n_windows_scored": 498,
                "n_candidates_considered": 12,
                "n_candidates_pruned_cap": 0,
                "score_ms": "1.0",
            }
        )

    out = mod._cap_pressure_rows(rows)

    assert len(out) == 1
    assert out[0]["n_windows_scored"] == 498
    assert out[0]["n_candidates_considered"] == 12


def test_config_summary_matches_failed_configs_with_reason_suffix() -> None:
    inventory = []
    for spec in mod.DICTIONARY_SPECS:
        for length in mod.SPAN_LENGTHS:
            inventory.append(
                {
                    "dictionary_cut": spec.dictionary_cut,
                    "length": length,
                    "load_ok": 1,
                    "file_exists": 1,
                }
            )
    rows = mod._config_summary_rows(
        run_mode="canary",
        inventory_rows=inventory,
        completed=[],
        missing=[],
        failed=["research_selected:missing_dictionary_path:assets/example"],
        skipped=[],
    )
    by_cut = {row["dictionary_cut"]: row for row in rows}
    assert by_cut["research_selected"]["status"] == "failed"
    assert "missing_dictionary_path" in by_cut["research_selected"]["reason"]
