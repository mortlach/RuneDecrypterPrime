from __future__ import annotations

from tools.benchmarks.periodic_sub_trans.no_wli.partial_state_space_map import (
    SPACE_MAP_RECORD_VERSION,
    build_late_space_map_payload,
)


def test_build_late_space_map_payload_maps_phasec_and_stage35_rows() -> None:
    stage3_diagnostics = {
        "phaseC_start_policy": "source_order",
        "phaseC_novel_view_id": "prefix_hamming_le_24",
        "phaseC_anchor_candidate_hash": "anchor_hash",
        "phaseC_candidate_pool_rows": [
            {
                "candidate_hash": "anchor_hash",
                "source": "stage3_best_phaseB",
                "source_rank": 1,
                "key": [1, 2, 3],
                "eligible_novel_challenger": 0,
                "novelty_distance_to_anchor": 0,
            },
            {
                "candidate_hash": "candidate_hash",
                "source": "phaseA_selected",
                "source_rank": 2,
                "key": [1, 3, 2],
                "eligible_novel_challenger": 1,
                "novelty_distance_to_anchor": 2,
            },
            {
                "candidate_hash": "not_started_hash",
                "source": "phaseA_selected",
                "source_rank": 3,
                "key": [2, 1, 3],
                "eligible_novel_challenger": 1,
                "novelty_distance_to_anchor": 2,
            },
        ],
        "phaseC_start_summaries": [
            {
                "candidate_hash": "anchor_hash",
                "lane": "anchor",
                "source": "stage3_best_phaseB",
                "source_rank": 1,
                "start_idx": 1,
                "init_key_idx": [1, 2, 3],
                "final_key_idx": [1, 2, 3],
                "init_plaintext_idx": [1, 1, 1],
                "final_plaintext_idx": [1, 1, 1],
                "init_score": 0.10,
                "final_score": 0.12,
                "init_match": 0.30,
                "final_match": 0.32,
                "eligible_novel_challenger": 0,
            },
            {
                "candidate_hash": "candidate_hash",
                "lane": "challenger",
                "source": "phaseA_selected",
                "source_rank": 2,
                "start_idx": 2,
                "init_key_idx": [1, 3, 2],
                "final_key_idx": [1, 3, 2],
                "init_plaintext_idx": [2, 2, 2],
                "final_plaintext_idx": [2, 2, 2],
                "init_score": 0.11,
                "final_score": 0.15,
                "init_match": 0.35,
                "final_match": 0.41,
                "eligible_novel_challenger": 1,
            },
        ],
        "stage35_baseline_selector": "score_plus_novelty",
        "stage35_baseline_candidate_hash": "candidate_hash",
        "stage35_accept_passed": 1,
        "stage35_accept_reason": "accepted",
        "stage35_best_candidate_hash": "continued_hash",
        "stage35_best_score": 0.18,
        "stage35_best_match": 0.49,
    }
    stage35_seed_rows = [
        {
            "candidate_hash": "candidate_hash",
            "seed_source": "phaseA_selected",
            "stage3_source": "phaseA_selected",
            "lane": "challenger",
            "source_rank": 2,
            "seed_rank": 1,
            "key_idx": [1, 3, 2],
            "plaintext_idx": [2, 2, 2],
            "score": 0.15,
            "search_score": -10.5,
        },
    ]
    stage35_archive_rows = [
        {
            "candidate_hash": "continued_hash",
            "parent_hash": "candidate_hash",
            "seed_source": "stage3_topk_phaseb",
            "stage3_source": "phaseB_topk",
            "lane": "challenger",
            "source_rank": 3,
            "archive_rank": 1,
            "key_idx": [1, 2, 4],
            "plaintext_idx": [3, 3, 3],
            "score": 0.18,
            "search_score": -10.2,
        },
    ]
    stage2_promoted_rows = [
        {
            "candidate_hash": "stage2_anchor_hash",
            "source": "stage2_topk_saved",
            "rank": 1,
            "key_idx": [1, 2, 3],
            "plaintext_idx": [1, 1, 1],
            "score": -5.0,
            "match": 0.20,
        },
        {
            "candidate_hash": "stage2_other_hash",
            "source": "stage2_topk_saved",
            "rank": 2,
            "key_idx": [1, 3, 2],
            "plaintext_idx": [2, 2, 2],
            "score": -4.8,
            "match": 0.25,
        },
    ]
    stage3_prep_live = {
        "stage3_entry_allocation_policy": "legacy_fixed_budget",
        "promoted_keys": [[1, 2, 3], [1, 3, 2]],
        "init3": [[1, 2, 3], [1, 3, 2], [2, 1, 3]],
    }

    payload = build_late_space_map_payload(
        run_id="run_001",
        tier_name="fixture_fixture_001_p9_c3_l1000",
        text_id=0,
        key_seed=411,
        columns=3,
        stage3_diagnostics=stage3_diagnostics,
        stage2_promoted_rows=stage2_promoted_rows,
        stage3_prep_live=stage3_prep_live,
        stage35_seed_rows=stage35_seed_rows,
        stage35_archive_rows=stage35_archive_rows,
    )

    assert payload["record_version"] == SPACE_MAP_RECORD_VERSION
    assert payload["run_id"] == "run_001"
    partial_rows = list(payload["partial_state_rows"])
    pool_rows = list(payload["pool_summaries"])

    assert [row["stage_boundary"] for row in partial_rows] == [
        "stage2_promoted",
        "stage2_promoted",
        "stage3_prep",
        "stage3_prep",
        "stage3_prep",
        "phaseC_pool",
        "phaseC_pool",
        "phaseC_pool",
        "phaseC_start",
        "phaseC_start",
        "stage35_seed",
        "stage35_archive",
    ]
    stage2_anchor_row = partial_rows[0]
    assert stage2_anchor_row["stage_boundary"] == "stage2_promoted"
    assert stage2_anchor_row["candidate_hash"] == "stage2_anchor_hash"
    assert stage2_anchor_row["selected"] == 1
    assert stage2_anchor_row["admitted_by_next_stage"] == 1
    assert stage2_anchor_row["selection_policy"] == "stage2_promoted_rank"
    assert stage2_anchor_row["distance_to_anchor"] == 0.0

    stage3_mutation_row = partial_rows[4]
    assert stage3_mutation_row["stage_boundary"] == "stage3_prep"
    assert stage3_mutation_row["source"] == "stage3_init_mutation"
    assert stage3_mutation_row["selected"] == 1
    assert stage3_mutation_row["selection_policy"] == "legacy_fixed_budget"
    assert stage3_mutation_row["final_key_idx"] == [2, 1, 3]
    assert stage3_mutation_row["parent_candidate_hash"]
    assert stage3_mutation_row["parent_link_kind"] == "fallback_anchor"

    phasec_pool_unselected_row = partial_rows[7]
    assert phasec_pool_unselected_row["stage_boundary"] == "phaseC_pool"
    assert phasec_pool_unselected_row["candidate_hash"] == "not_started_hash"
    assert phasec_pool_unselected_row["selected"] == 0
    assert phasec_pool_unselected_row["eligible"] == 1
    assert phasec_pool_unselected_row["selection_policy"] == "source_order"
    assert phasec_pool_unselected_row["parent_candidate_hash"] == "anchor_hash"

    phasec_candidate_row = partial_rows[9]
    assert phasec_candidate_row["candidate_hash"] == "candidate_hash"
    assert phasec_candidate_row["selected"] == 1
    assert phasec_candidate_row["admitted_by_next_stage"] == 1
    assert phasec_candidate_row["selection_policy"] == "source_order"
    assert phasec_candidate_row["parent_candidate_hash"] == "anchor_hash"
    assert phasec_candidate_row["family_view_id"] == "prefix_hamming_le_24"
    assert phasec_candidate_row["family_id"] == "f0"
    assert phasec_candidate_row["family_id_kind"] == "run_local_cluster"
    assert phasec_candidate_row["distance_to_anchor"] == 2.0
    assert phasec_candidate_row["init_key_idx"] == [1, 3, 2]
    assert phasec_candidate_row["final_match"] == 0.41

    seed_row = partial_rows[10]
    assert seed_row["stage_boundary"] == "stage35_seed"
    assert seed_row["selection_policy"] == "score_plus_novelty"
    assert seed_row["selected"] == 1
    assert seed_row["admitted_by_next_stage"] == 1
    assert seed_row["continued_best_candidate_hash"] == "continued_hash"
    assert seed_row["continued_best_score"] == 0.18
    assert seed_row["continued_best_match"] == 0.49
    assert seed_row["next_stage_accept_reason"] == "accepted"
    assert seed_row["parent_link_kind"] == "root"
    assert seed_row["distance_to_anchor"] == 0.0

    archive_row = partial_rows[11]
    assert archive_row["parent_candidate_hash"] == "candidate_hash"
    assert archive_row["parent_link_kind"] == "observed"
    assert archive_row["selected"] == 1
    assert archive_row["selection_policy"] == "stage35_archive_rank"
    assert archive_row["family_view_id"] == "prefix_hamming_le_24"
    assert archive_row["family_id"] == "f0"
    assert archive_row["distance_to_anchor"] == 2.0

    assert [row["pool_id"] for row in pool_rows] == [
        "stage2_promoted",
        "stage3_prep",
        "phaseC_pool",
        "phaseC_start",
        "stage35_seed",
        "stage35_archive",
    ]
    stage2_pool = pool_rows[0]
    assert stage2_pool["row_count"] == 2
    assert stage2_pool["pool_status"] == "available"
    assert stage2_pool["selection_policy"] == "stage2_promoted_rank"
    assert stage2_pool["anchor_candidate_hash"] == "stage2_anchor_hash"

    stage3_prep_pool = pool_rows[1]
    assert stage3_prep_pool["row_count"] == 3
    assert stage3_prep_pool["pool_status"] == "available"
    assert stage3_prep_pool["selection_policy"] == "legacy_fixed_budget"

    phasec_pool = pool_rows[2]
    assert phasec_pool["row_count"] == 3
    assert phasec_pool["pool_status"] == "available"
    assert phasec_pool["selected_row_count"] == 2
    assert phasec_pool["review_primary_row_count"] == 2
    assert phasec_pool["review_primary_row_count_kind"] == "selected_row_count"
    assert phasec_pool["review_primary_relation"] == "selected_vs_available"
    assert phasec_pool["selected_family_count"] == 1
    assert phasec_pool["top_band_family_count"] == 1
    assert phasec_pool["selected_pairwise_distance_min"] == 2.0 / 3.0
    assert phasec_pool["selected_pairwise_distance_mean"] == 2.0 / 3.0
    assert phasec_pool["anchor_candidate_hash"] == "anchor_hash"

    phasec_start_pool = pool_rows[3]
    assert phasec_start_pool["row_count"] == 2
    assert phasec_start_pool["pool_status"] == "available"
    assert phasec_start_pool["eligible_row_count"] == 1
    assert phasec_start_pool["selected_row_count"] == 2
    assert phasec_start_pool["review_primary_row_count"] == 2
    assert phasec_start_pool["review_primary_row_count_kind"] == "selected_row_count"
    assert phasec_start_pool["review_primary_relation"] == "selected_vs_available"
    assert phasec_start_pool["family_view_id"] == "prefix_hamming_le_24"
    assert phasec_start_pool["anchor_candidate_hash"] == "anchor_hash"
    assert phasec_start_pool["selected_pairwise_distance_min"] == 2.0 / 3.0
    assert phasec_start_pool["selected_pairwise_distance_mean"] == 2.0 / 3.0

    stage35_seed_pool = pool_rows[4]
    assert stage35_seed_pool["selected_row_count"] == 1
    assert stage35_seed_pool["next_stage_started_count"] == 1
    assert stage35_seed_pool["next_stage_admitted_count"] == 1
    assert stage35_seed_pool["next_stage_rejected_count"] == 0
    assert stage35_seed_pool["review_primary_row_count"] == 1
    assert (
        stage35_seed_pool["review_primary_row_count_kind"]
        == "next_stage_started_count"
    )
    assert stage35_seed_pool["review_primary_relation"] == "started_vs_available"
    assert stage35_seed_pool["best_continued_candidate_hash"] == "continued_hash"
    assert stage35_seed_pool["best_continued_score"] == 0.18
    assert stage35_seed_pool["best_continued_match"] == 0.49


def test_build_late_space_map_payload_marks_missing_phasec_pool_as_not_run() -> None:
    payload = build_late_space_map_payload(
        run_id="run_not_phasec",
        tier_name="fixture_fixture_001_p5_c1_l1000",
        text_id=0,
        key_seed=511,
        stage3_diagnostics={
            "phaseC_ran": 0,
            "phaseC_start_policy": "source_order",
            "stage35_baseline_selector": "score_plus_novelty",
            "stage35_baseline_candidate_hash": "baseline_hash",
            "stage35_accept_passed": 0,
            "stage35_accept_reason": "top_candidate_matches_baseline",
            "stage35_best_candidate_hash": "baseline_hash",
            "stage35_best_score": 0.5,
            "stage35_best_match": 1.0,
        },
        stage35_seed_rows=[
            {
                "candidate_hash": "baseline_hash",
                "seed_source": "final_best",
                "key_idx": [1, 2, 3],
                "plaintext_idx": [3, 2, 1],
                "score": 0.5,
            }
        ],
        stage35_archive_rows=[],
    )

    pool_rows = list(payload["pool_summaries"])
    assert [row["stage_boundary"] for row in pool_rows] == [
        "stage2_promoted",
        "stage3_prep",
        "phaseC_pool",
        "phaseC_start",
        "stage35_seed",
        "stage35_archive",
    ]
    assert payload["run_id"] == "run_not_phasec"
    assert pool_rows[0]["pool_status"] == "empty"
    assert pool_rows[1]["pool_status"] == "not_run"
    assert pool_rows[2]["pool_status"] == "not_run"
    assert pool_rows[3]["pool_status"] == "not_run"
    assert pool_rows[3]["row_count"] == 0
    assert pool_rows[3]["run_id"] == "run_not_phasec"
    assert pool_rows[4]["pool_status"] == "available"
    assert pool_rows[5]["pool_status"] == "empty"
