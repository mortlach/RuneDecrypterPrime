from __future__ import annotations

import json

import numpy as np

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    run_phaseB_failed_decryption_length_aware_order2_informed_n3c_query_planning_v1 as planner,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    run_phaseB_failed_decryption_n3c_memory_bounded_medium_group_canary_v1 as medium_canary,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    run_phaseB_failed_decryption_n3c_medium_shape_diverse_candidate_microbatch_v1 as diverse_microbatch,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    run_phaseB_failed_decryption_n3c_vectorized_12_plus_stratified_shape_microbatch_v1 as stratified_12_plus,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    run_phaseB_failed_decryption_n3c_full80_query_evidence_v1 as full80,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.phaseB_n3c_query_planning_core_v1 import (
    brute_force_hits,
    build_sorted_block_index,
    candidate_keyed_hits,
    exact_word_structured_match,
    length_bucket,
    partition_filter_hits,
    sorted_block_partition_hit_details,
    sorted_block_partition_hits,
    vectorized_word_structured_match_indexes,
)


def test_length_buckets_classify_boundaries() -> None:
    assert [length_bucket(value) for value in (8, 9, 10, 11, 12, 14, 15, 17, 18, 40)] == [
        "8-9", "8-9", "10-11", "10-11", "12-14", "12-14", "15-17", "15-17", "18+", "18+",
    ]


def test_candidate_keyed_lookup_matches_brute_force_and_emits_all_hits() -> None:
    phrases = np.asarray([[1, 2, 3, 4], [1, 9, 3, 8], [7, 7, 7, 7]], dtype=np.uint8)
    candidate = [0, 1, 2, 3, 4, 1, 9, 3, 8, 0]
    brute = brute_force_hits(candidate, phrases, (2, 2))
    keyed, generated_count, unique_count = candidate_keyed_hits(candidate, phrases, (2, 2))

    assert keyed == brute
    assert keyed == {(1, 0), (1, 1), (5, 0), (5, 1)}
    assert generated_count >= unique_count > 0


def test_candidate_keyed_lookup_respects_word_structure() -> None:
    phrases = np.asarray([[1, 2, 3, 4]], dtype=np.uint8)

    assert exact_word_structured_match([1, 9, 3, 8], phrases[0], (2, 2)) == (1, 1)
    assert exact_word_structured_match([9, 8, 3, 4], phrases[0], (2, 2)) is None


def test_partition_filter_matches_brute_force() -> None:
    phrases = np.asarray([[1, 2, 3, 4, 5, 6], [1, 9, 3, 4, 8, 6], [7, 7, 7, 7, 7, 7]], dtype=np.uint8)
    candidate = [0, 1, 2, 3, 4, 5, 6, 0]

    brute = brute_force_hits(candidate, phrases, (2, 2, 2))
    filtered, proposed_count = partition_filter_hits(candidate, phrases, (2, 2, 2))

    assert filtered == brute
    assert filtered == {(1, 0), (1, 1)}
    assert proposed_count > 0


def test_seeded_partition_filter_records_unseeded_miss() -> None:
    phrases = np.asarray([[1, 2, 3, 4, 5, 6]], dtype=np.uint8)
    candidate = [0, 1, 2, 3, 4, 5, 6, 0, 1, 2, 3, 4, 5, 6]

    unseeded, _ = partition_filter_hits(candidate, phrases, (2, 2, 2))
    seeded, _ = partition_filter_hits(candidate, phrases, (2, 2, 2), allowed_start_ranges=((0, 5),))

    assert unseeded == {(1, 0), (8, 0)}
    assert seeded == {(1, 0)}
    assert unseeded - seeded == {(8, 0)}


def test_sorted_block_partition_index_matches_dictionary_filter_and_is_bounded() -> None:
    phrases = np.asarray([
        [1, 2, 3, 4, 5, 6],
        [1, 9, 3, 4, 8, 6],
        [7, 7, 7, 7, 7, 7],
    ], dtype=np.uint8)
    candidate = [0, 1, 2, 3, 4, 5, 6, 0]
    index = build_sorted_block_index(phrases)

    expected, expected_proposals = partition_filter_hits(candidate, phrases, (2, 2, 2))
    actual, actual_proposals = sorted_block_partition_hits(candidate, phrases, (2, 2, 2), index)

    assert actual == expected
    assert actual_proposals == expected_proposals
    assert index.allocated_bytes <= phrases.nbytes + phrases.shape[0] * 3 * 8


def test_sorted_block_partition_hit_details_match_hit_set_and_hds() -> None:
    phrases = np.asarray([
        [1, 2, 3, 4, 5, 6],
        [1, 9, 3, 4, 8, 6],
        [7, 7, 7, 7, 7, 7],
    ], dtype=np.uint8)
    candidate = [0, 1, 2, 3, 4, 5, 6, 0]
    index = build_sorted_block_index(phrases)

    expected, expected_proposals = sorted_block_partition_hits(candidate, phrases, (2, 2, 2), index)
    details, actual_proposals = sorted_block_partition_hit_details(candidate, phrases, (2, 2, 2), index)

    assert {(start, phrase_index) for start, phrase_index, _word_hds in details} == expected
    assert actual_proposals == expected_proposals
    assert {
        (start, phrase_index): word_hds
        for start, phrase_index, word_hds in details
    } == {
        (1, 0): (0, 0, 0),
        (1, 1): (1, 0, 1),
    }


def test_vectorized_word_structured_verification_matches_scalar() -> None:
    phrases = np.asarray([
        [1, 2, 3, 4],
        [1, 9, 3, 8],
        [9, 8, 3, 4],
        [7, 7, 7, 7],
    ], dtype=np.uint8)
    window = [1, 2, 3, 4]
    expected = {
        index for index, phrase in enumerate(phrases)
        if exact_word_structured_match(window, phrase, (2, 2)) is not None
    }

    actual = vectorized_word_structured_match_indexes(window, phrases, range(len(phrases)), (2, 2))

    assert set(actual.tolist()) == expected


def test_group_planner_selects_each_bucket_and_declares_skips() -> None:
    files = []
    for index, length in enumerate((8, 9, 10, 11, 12, 14, 15, 17, 18, 20)):
        files.append({
            "direction": "fwd", "ngram_order": 3, "dictionary_cut": "normal",
            "phrase_token_length": length, "word_token_lengths": "[2,3,3]",
            "phrase_count": 100 + index, "path": f"group_{index}.npz",
        })

    selected, skipped = planner.select_groups(files)

    assert {length_bucket(int(row["phrase_token_length"])) for row in selected} == set(planner.BUCKET_ORDER)
    assert len(selected) == 5
    assert len(skipped) == 5
    assert all(row["would_be_required_for_full_n3c"] is True and row["searched"] is False for row in skipped)


def test_candidate_planner_uses_one_per_trial_without_inventing_rank() -> None:
    rows = [
        {"trial_id": "a", "candidate_id": "a-low", "baseline_score": "1", "candidate_rank": ""},
        {"trial_id": "a", "candidate_id": "a-high", "baseline_score": "2", "candidate_rank": ""},
        {"trial_id": "b", "candidate_id": "b-only", "baseline_score": "1", "candidate_rank": ""},
    ]

    selected = planner.select_candidates(rows)

    assert [row["candidate_id"] for row in selected] == ["a-high", "b-only"]
    assert all(row["candidate_stratum"] == "trial_highest_baseline_score_rank_unavailable" for row in selected)


def test_completed_study_preserves_authority_and_declares_partial_scope() -> None:
    manifest = json.loads((planner.OUTPUT_DIR / "run_manifest.json").read_text(encoding="utf-8"))

    assert manifest["status"] == "pass_partial_budgeted_canary"
    assert manifest["query_is_full_n3c"] is False
    assert manifest["all_started_groups_completed"] is True
    assert manifest["full_phrase_verified"] is True
    assert manifest["order2_used_for_query_planning_only"] is True
    assert manifest["order2_score_authority"] == "diagnostic_only"
    assert manifest["seeded_missed_n3c_hit_count"] > 0
    assert manifest["seeded_missed_n3c_cluster_count"] > 0
    assert manifest["production_scoring_change"] is False
    assert manifest["production_ranking_change"] is False


def test_medium_group_selector_is_deterministic_and_medium_frequency() -> None:
    files = [
        {
            "direction": "fwd", "ngram_order": 3, "dictionary_cut": "normal",
            "phrase_token_length": 8, "word_token_lengths": f"[1,2,{index + 5}]",
            "phrase_count": count, "path": f"group_{index}.npz",
        }
        for index, count in enumerate((10, 20, 30, 40, 50))
    ]

    selected = medium_canary.select_medium_group(files)

    assert selected["path"] == "group_2.npz"
    assert selected["shape_frequency_class"] == "medium"
    assert selected["shape_frequency_rank"] == 3


def test_diverse_candidate_sampler_uses_high_and_middle_without_inventing_rank() -> None:
    rows = [
        {"trial_id": "a", "candidate_id": f"a-{index}", "baseline_score": str(index), "candidate_rank": ""}
        for index in range(5)
    ]

    selected = diverse_microbatch.select_diverse_candidates(rows)

    assert [row["candidate_id"] for row in selected] == ["a-4", "a-2"]
    assert {row["candidate_stratum"] for row in selected} == {
        "trial_highest_baseline_score_rank_unavailable",
        "trial_middle_baseline_score_rank_unavailable",
    }


def test_12_plus_stratified_selector_uses_requested_frequency_mix_per_bucket() -> None:
    files = []
    for length in (12, 15, 18):
        for index in range(10):
            files.append({
                "direction": "fwd", "ngram_order": 3, "dictionary_cut": "normal",
                "phrase_token_length": length, "word_token_lengths": f"[1,2,{length - 3}]",
                "phrase_count": 100 + index, "path": f"group_{length}_{index}.npz",
            })

    selected = stratified_12_plus.select_stratified_12_plus_groups(files)

    assert len(selected) == 24
    for bucket in stratified_12_plus.TARGET_BUCKETS:
        rows = [row for row in selected if length_bucket(int(row["phrase_token_length"])) == bucket]
        assert [row["shape_frequency_class"] for row in rows] == [
            "rare", "rare", "medium", "medium", "medium", "common", "common", "common",
        ]


def test_full80_logical_group_collapses_chunks_without_losing_chunk_count() -> None:
    files = [
        {
            "direction": "fwd", "dictionary_cut": "normal", "ngram_order": 3,
            "phrase_token_length": 9, "word_token_lengths": "[3,2,4]",
            "phrase_count": 1_000_000, "chunk_index": 0, "path": "chunk0.npz",
        },
        {
            "direction": "fwd", "dictionary_cut": "normal", "ngram_order": 3,
            "phrase_token_length": 9, "word_token_lengths": "[3,2,4]",
            "phrase_count": 13144, "chunk_index": 1, "path": "chunk1.npz",
        },
        {
            "direction": "fwd", "dictionary_cut": "normal", "ngram_order": 3,
            "phrase_token_length": 9, "word_token_lengths": "[4,2,3]",
            "phrase_count": 2, "chunk_index": 0, "path": "other.npz",
        },
    ]

    chunks = full80.select_full_n3c_chunks(files)
    logical_ids = {row["logical_group_id"] for row in chunks}

    assert len(chunks) == 3
    assert len(logical_ids) == 2
    assert full80.logical_group_id(files[0]) == full80.logical_group_id(files[1])
    assert full80.logical_group_id(files[0]) != full80.logical_group_id(files[2])


def test_full80_pair_classification_distinguishes_rescue_break_and_tie() -> None:
    assert full80.classify_pair("gold", "base", "gold") == "rescue"
    assert full80.classify_pair("other", "gold", "gold") == "break"
    assert full80.classify_pair("gold", "gold", "gold") == "agree"
    assert full80.classify_pair("tie", "gold", "gold") == "tie"
