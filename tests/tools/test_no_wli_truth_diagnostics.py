from __future__ import annotations

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.iteration_outcome import (
    build_stage3_diagnostics,
)
from tools.benchmarks.periodic_sub_trans.no_wli.phasec_truth_reporting import (
    build_phasec_truth_reporting,
)
from tools.benchmarks.periodic_sub_trans.no_wli.truth_diagnostics import (
    build_fixture_truth_diagnostics,
)


pytestmark = pytest.mark.tier_a


def test_build_fixture_truth_diagnostics_reports_key_slices_and_residues() -> None:
    target_key_idx = [
        0,
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        0,
        1,
    ]
    final_best_key_idx = [
        0,
        1,
        9,
        3,
        4,
        8,
        6,
        5,
        8,
        1,
        1,
    ]
    target_plaintext_idx = [0, 1, 2, 3, 4, 5]
    final_best_plaintext_idx = [0, 9, 2, 8, 4, 5]
    stage3_topk_rows = [
        {"rank": 1, "key_idx": final_best_key_idx, "plaintext_idx": final_best_plaintext_idx},
        {"rank": 2, "key_idx": target_key_idx, "plaintext_idx": target_plaintext_idx},
    ]

    out = build_fixture_truth_diagnostics(
        target_key_idx=target_key_idx,
        final_best_key_idx=final_best_key_idx,
        target_plaintext_idx=target_plaintext_idx,
        final_best_plaintext_idx=final_best_plaintext_idx,
        period=2,
        columns=1,
        stage3_topk_rows=stage3_topk_rows,
    )

    assert bool(out["available"]) is True
    assert int(out["alphabet_size"]) == 5
    assert int(out["key_hamming_total"]) == 4
    assert int(out["key_hamming_substitution"]) == 4
    assert int(out["key_hamming_columns"]) == 0
    assert int(out["worst_substitution_slice"]) == 1
    assert int(out["worst_substitution_slice_mismatches"]) == 3
    assert int(out["worst_plaintext_period_residue"]) == 1
    assert pytest.approx(float(out["worst_plaintext_period_residue_match_ratio"])) == (
        1.0 / 3.0
    )
    assert len(list(out["key_hamming_by_period_slice"])) == 2
    assert len(list(out["plaintext_match_by_period_residue"])) == 2
    assert len(list(out["stage3_topk_truth_diagnostics"])) == 2
    assert int(out["stage3_topk_truth_diagnostics"][1]["key_hamming_total"]) == 0


def test_build_stage3_diagnostics_keeps_phasec_start_summaries() -> None:
    out = build_stage3_diagnostics(
        phaseA_experiment="a_baseline",
        phaseB_experiment="c_min_late",
        init_target=1,
        init_actual=1,
        promoted_keys=1,
        gate_source="judge",
        continue_after_solve=False,
        solve_hits=0,
        period_init_mult=1.0,
        period_step_mult=1.0,
        period_restart_bonus=0,
        phaseB_top_n_cfg=8,
        phaseB_gate_delta_cfg=0.01,
        phaseB_gate_end_gain_cfg=0.01,
        phaseB_ran=1,
        phaseB_skipped=0,
        phaseB_top_n_used=8,
        phaseB_skip_reason="",
        phaseB_family_preservation_policy="reserve_by_family_v1",
        phaseB_family_view_id="prefix_hamming_le_24",
        phaseB_family_reserved_slots=2,
        phaseB_family_count_in_top_band=3,
        phaseB_family_preserved_count=2,
        phaseB_family_reservation_applied=1,
        phaseB_selected_unique_end_hash=5,
        phaseB_downstream_selected_count=8,
        phaseB_downstream_selected_unique_end_hash=4,
        phaseB_topk_saved_count=4,
        phaseB_topk_saved_unique_end_hash=3,
        phaseB_char_pct_min_dynamic=0.4,
        phaseB_char_pct_min_source="test",
        span_basin_judge_k_cfg=8,
        span_basin_judge_k=8,
        span_basin_judge_seconds=1.0,
        basin_judge_span_calls_total=8,
        basin_judge_span_calls_active=8,
        basin_judge_span_calls_rejected_or_gated=0,
        basin_judge_span_seconds_total=0.5,
        basin_judge_unique_end_hash=8,
        scan_stage3_gate_low_match=0.0,
        scan_stage3_gate_high_match=0.0,
        scan_phaseA_only=0,
        span_active_rate=1.0,
        span_active_rate_source="test",
        span_eval_total=8.0,
        span_eval_active=8.0,
        span_eval_skipped_char_gate=0.0,
        span_seconds_total=1.0,
        span_seconds_active=1.0,
        span_phaseA_eval_total=4.0,
        span_phaseA_eval_active=4.0,
        span_phaseA_eval_skipped_char_gate=0.0,
        span_phaseA_seconds_total=0.5,
        span_phaseA_seconds_active=0.5,
        span_full_eval_total=4.0,
        span_full_eval_active=4.0,
        span_full_eval_skipped_char_gate=0.0,
        span_full_seconds_total=0.5,
        span_full_seconds_active=0.5,
        stage3_eval_count=10,
        c1_focus=0,
        phaseC_lexical_min_match_cfg=0.68,
        phaseC_rescue_enabled_cfg=1,
        phaseC_rescue_ran=1,
        phaseC_rescue_starts_attempted=1,
        phaseC_rescue_applied_starts=1,
        phaseC_rescue_target_mode_cfg="slice_probe",
        phaseC_rescue_selector_mode_cfg="rescue_shallow_then_search",
        phaseC_rescue_candidates_cfg=8,
        phaseC_rescue_slip_swaps_cfg=6,
        phaseC_rescue_mini_search_steps_cfg=2,
        phaseC_rescue_mini_search_beam_width_cfg=4,
        phaseC_rescue_mini_search_top_symbols_cfg=10,
        phaseC_rescue_mini_search_keep_all_rows_cfg=1,
        phaseC_rescue_polish_steps_cfg=96,
        phaseC_rescue_probe_evals=9,
        phaseC_rescue_evals=8,
        phaseC_rescue_mini_search_evals=12,
        phaseC_rescue_anchor_enabled_cfg=0,
        phaseC_rescue_phaseb_topk_min_rank_cfg=2,
        phaseC_rescue_max_starts_cfg=2,
        phaseC_rescue_eligible_starts=2,
        phaseC_rescue_search_score_max_drop_cfg=0.0,
        phaseC_rescue_guard_search_evals=12,
        phaseC_rescue_guard_search_passes=2,
        phaseC_rescue_guard_search_rejects=3,
        phaseC_rescue_lexical_requests=2,
        phaseC_rescue_lexical_cache_hits=1,
        phaseC_rescue_lexical_cache_misses=1,
        phaseC_rescue_lexical_tiebreak_decisions=1,
        phaseC_rescue_lexical_budget_skips=0,
        phaseC_rescue_lexical_threshold_skips=1,
        phaseC_start_policy="novel_challenger_v1",
        phaseC_candidate_pool_count=6,
        phaseC_candidate_pool_unique_keys=5,
        phaseC_candidate_pool_unique_end_hash=4,
        phaseC_candidate_pool_source_counts={"stage3_best_phaseB": 1, "phaseB_topk": 3},
        phaseC_novel_view_id="prefix_hamming_le_24",
        phaseC_anchor_candidate_hash="anchor-hash",
        phaseC_candidate_pool_eligible_novel_count=3,
        phaseC_candidate_pool_eligible_novel_row_count=4,
        phaseC_candidate_pool_eligible_novel_source_counts={"phaseA_selected": 3},
        phaseC_start_source_counts={"stage3_best_phaseB": 1, "phaseB_topk": 1},
        phaseC_start_unique_end_hash=2,
        phaseC_start_eligible_novel_count=2,
        phaseC_selected_novel_challenger_count=2,
        phaseC_eligible_novel_not_selected_count=1,
        phaseC_selected_novel_challenger_hashes=["novel-a", "novel-b"],
        phaseC_improved_best=1,
        phaseC_checkpoint_jsonl_name="phasec_start_checkpoints.jsonl",
        phaseC_checkpoint_rows_written=2,
        phaseC_anchor_lane_starts=1,
        phaseC_challenger_lane_starts=1,
        phaseC_challenger_overtook_anchor_count=1,
        phaseC_final_winner_lane="challenger",
        phaseC_final_winner_source="phaseB_topk",
        phaseC_start_summaries=[
            {
                "start_idx": 1,
                "lane": "anchor",
                "source": "stage3_best_phaseB",
                "source_rank": 1,
                "selection_bucket": "anchor",
                "selected_by_novel_policy": 0,
                "eligible_novel_challenger": 0,
                "novelty_distance_to_anchor": None,
                "novelty_min_distance_to_selected_challenger": None,
                "candidate_hash": "anchor-hash",
                "init_key_idx": [1, 2],
                "init_plaintext_idx": [3, 4],
                "final_key_idx": [5, 6],
                "final_plaintext_idx": [7, 8],
                "init_match": 0.75,
                "final_match": 0.76,
                "init_score": 0.90,
                "final_score": 0.91,
                "became_global_best": 1,
            },
            {
                "start_idx": 2,
                "lane": "challenger",
                "source": "phaseB_topk",
                "source_rank": 2,
                "selection_bucket": "novel_reserved",
                "selected_by_novel_policy": 1,
                "eligible_novel_challenger": 1,
                "novelty_distance_to_anchor": 8,
                "novelty_min_distance_to_selected_challenger": None,
                "candidate_hash": "novel-a",
                "init_key_idx": [9, 10],
                "init_plaintext_idx": [11, 12],
                "final_key_idx": [13, 14],
                "final_plaintext_idx": [15, 16],
                "init_match": 0.82,
                "final_match": 0.89,
                "init_score": 0.82,
                "final_score": 0.83,
                "became_global_best": 0,
            }
        ],
        stage35_requested_cfg=1,
        stage35_enabled_cfg=1,
        stage35_ran=1,
        stage35_proof_valid=1,
        stage35_proof_invalid_reason="",
        stage35_selected=1,
        stage35_seed_count=4,
        stage35_tail_mismatch_count=1,
        stage35_seed_source_counts={"final_best": 1, "phasec_phaseb_challenger": 2},
        stage35_archive_count=6,
        stage35_rounds_completed=3,
        stage35_evals=42,
        stage35_runtime_seconds=1.25,
        stage35_partial_state_name="stage35_partial_state.json",
        stage35_progress_jsonl_name="stage35_progress.jsonl",
        stage35_progress_event_count=16,
        stage35_partial_dump_write_count=4,
        stage35_telemetry_summary={
            "row_scoring_seconds": 12.5,
            "mini_search_count": 9,
        },
        stage35_archive_unique_keys=6,
        stage35_archive_unique_seed_sources=2,
        stage35_archive_unique_target_slices=2,
        stage35_archive_mean_substitution_hamming=3.5,
        stage35_archive_max_substitution_hamming=7,
        stage35_baseline_search_score=0.21,
        stage35_accept_score_min_gain_cfg=0.0,
        stage35_accept_search_score_max_drop_cfg=0.0,
        stage35_accept_passed=1,
        stage35_accept_reason="accepted",
        stage35_mini_search_keep_all_rows_cfg=1,
        stage35_mini_search_collected_rows=18,
        stage35_mini_search_rows_kept=12,
        stage35_best_score=0.31,
        stage35_best_search_score=0.22,
        stage35_best_seed_source="phasec_phaseb_challenger",
        stage35_best_stage3_source="phaseB_topk",
        stage35_best_lane="challenger",
        stage35_best_source_rank=3,
        stage35_best_target_slice=1,
        stage35_best_depth=2,
        stage35_best_move_type="slice_local_mini_search",
        stage35_best_candidate_hash="abc123",
    )

    assert len(list(out["phaseC_start_summaries"])) == 2
    assert int(out["phaseC_start_summaries"][0]["start_idx"]) == 1
    assert str(out["phaseC_start_policy"]) == "novel_challenger_v1"
    assert str(out["phaseC_novel_view_id"]) == "prefix_hamming_le_24"
    assert str(out["phaseC_anchor_candidate_hash"]) == "anchor-hash"
    assert int(out["phaseC_candidate_pool_eligible_novel_count"]) == 3
    assert int(out["phaseC_candidate_pool_eligible_novel_row_count"]) == 4
    assert dict(out["phaseC_candidate_pool_eligible_novel_source_counts"]) == {
        "phaseA_selected": 3
    }
    assert int(out["phaseC_start_eligible_novel_count"]) == 2
    assert int(out["phaseC_selected_novel_challenger_count"]) == 2
    assert int(out["phaseC_eligible_novel_not_selected_count"]) == 1
    assert list(out["phaseC_selected_novel_challenger_hashes"]) == [
        "novel-a",
        "novel-b",
    ]
    assert str(out["phaseB_family_preservation_policy"]) == "reserve_by_family_v1"
    assert str(out["phaseB_family_view_id"]) == "prefix_hamming_le_24"
    assert int(out["phaseB_family_reserved_slots"]) == 2
    assert int(out["phaseB_family_count_in_top_band"]) == 3
    assert int(out["phaseB_family_preserved_count"]) == 2
    assert int(out["phaseB_family_reservation_applied"]) == 1
    assert int(out["phaseB_selected_unique_end_hash"]) == 5
    assert int(out["phaseB_downstream_selected_count"]) == 8
    assert int(out["phaseB_downstream_selected_unique_end_hash"]) == 4
    assert int(out["phaseB_topk_saved_count"]) == 4
    assert int(out["phaseC_candidate_pool_unique_keys"]) == 5
    assert float(out["phaseC_lexical_min_match_cfg"]) == pytest.approx(0.68)
    assert int(out["phaseC_rescue_enabled_cfg"]) == 1
    assert int(out["phaseC_rescue_ran"]) == 1
    assert int(out["phaseC_rescue_starts_attempted"]) == 1
    assert int(out["phaseC_rescue_applied_starts"]) == 1
    assert str(out["phaseC_rescue_target_mode_cfg"]) == "slice_probe"
    assert str(out["phaseC_rescue_selector_mode_cfg"]) == "rescue_shallow_then_search"
    assert int(out["phaseC_rescue_candidates_cfg"]) == 8
    assert int(out["phaseC_rescue_slip_swaps_cfg"]) == 6
    assert int(out["phaseC_rescue_mini_search_steps_cfg"]) == 2
    assert int(out["phaseC_rescue_mini_search_beam_width_cfg"]) == 4
    assert int(out["phaseC_rescue_mini_search_top_symbols_cfg"]) == 10
    assert int(out["phaseC_rescue_mini_search_keep_all_rows_cfg"]) == 1
    assert int(out["phaseC_rescue_polish_steps_cfg"]) == 96
    assert int(out["phaseC_rescue_probe_evals"]) == 9
    assert int(out["phaseC_rescue_evals"]) == 8
    assert int(out["phaseC_rescue_mini_search_evals"]) == 12
    assert int(out["phaseC_rescue_anchor_enabled_cfg"]) == 0
    assert int(out["phaseC_rescue_phaseb_topk_min_rank_cfg"]) == 2
    assert int(out["phaseC_rescue_max_starts_cfg"]) == 2
    assert int(out["phaseC_rescue_eligible_starts"]) == 2
    assert float(out["phaseC_rescue_search_score_max_drop_cfg"]) == pytest.approx(0.0)
    assert int(out["phaseC_rescue_guard_search_evals"]) == 12
    assert int(out["phaseC_rescue_guard_search_passes"]) == 2
    assert int(out["phaseC_rescue_guard_search_rejects"]) == 3
    assert dict(out["phaseC_start_source_counts"]) == {
        "stage3_best_phaseB": 1,
        "phaseB_topk": 1,
    }
    assert int(out["phaseC_improved_best"]) == 1
    assert str(out["phaseC_checkpoint_jsonl_name"]) == "phasec_start_checkpoints.jsonl"
    assert int(out["phaseC_checkpoint_rows_written"]) == 2
    assert int(out["phaseC_anchor_lane_starts"]) == 1
    assert int(out["phaseC_challenger_lane_starts"]) == 1
    assert int(out["phaseC_challenger_overtook_anchor_count"]) == 1
    assert str(out["phaseC_final_winner_lane"]) == "challenger"
    assert str(out["phaseC_final_winner_source"]) == "phaseB_topk"
    assert int(out["phaseC_truth_reporting_available"]) == 1
    assert str(out["phaseC_score_selected_winner_summary"]["candidate_hash"]) == "anchor-hash"
    assert str(out["phaseC_best_truth_start_summary"]["candidate_hash"]) == "novel-a"
    assert str(out["phaseC_best_truth_challenger_summary"]["candidate_hash"]) == "novel-a"
    assert int(out["phaseC_truth_disagreement_summary"]["winner_and_best_truth_differ"]) == 1
    assert float(
        out["phaseC_truth_disagreement_summary"]["truth_gap_best_truth_challenger_vs_winner"]
    ) == pytest.approx(0.13)
    assert float(
        out["phaseC_truth_disagreement_summary"]["score_gap_best_truth_challenger_vs_winner"]
    ) == pytest.approx(-0.08)
    assert int(out["stage35_requested_cfg"]) == 1
    assert int(out["stage35_enabled_cfg"]) == 1
    assert int(out["stage35_ran"]) == 1
    assert int(out["stage35_proof_valid"]) == 1
    assert str(out["stage35_proof_invalid_reason"]) == ""
    assert int(out["stage35_selected"]) == 1
    assert int(out["stage35_seed_count"]) == 4
    assert int(out["stage35_tail_mismatch_count"]) == 1
    assert dict(out["stage35_seed_source_counts"]) == {
        "final_best": 1,
        "phasec_phaseb_challenger": 2,
    }
    assert int(out["stage35_archive_count"]) == 6
    assert int(out["stage35_rounds_completed"]) == 3
    assert int(out["stage35_evals"]) == 42
    assert float(out["stage35_runtime_seconds"]) == pytest.approx(1.25)
    assert str(out["stage35_partial_state_name"]) == "stage35_partial_state.json"
    assert str(out["stage35_progress_jsonl_name"]) == "stage35_progress.jsonl"
    assert int(out["stage35_progress_event_count"]) == 16
    assert int(out["stage35_partial_dump_write_count"]) == 4
    assert dict(out["stage35_telemetry_summary"]) == {
        "mini_search_count": 9,
        "row_scoring_seconds": 12.5,
    }
    assert int(out["stage35_archive_unique_keys"]) == 6
    assert int(out["stage35_archive_unique_seed_sources"]) == 2
    assert int(out["stage35_archive_unique_target_slices"]) == 2
    assert float(out["stage35_archive_mean_substitution_hamming"]) == pytest.approx(3.5)
    assert int(out["stage35_archive_max_substitution_hamming"]) == 7
    assert float(out["stage35_baseline_search_score"]) == pytest.approx(0.21)
    assert float(out["stage35_accept_score_min_gain_cfg"]) == pytest.approx(0.0)
    assert float(out["stage35_accept_search_score_max_drop_cfg"]) == pytest.approx(0.0)
    assert int(out["stage35_accept_passed"]) == 1
    assert str(out["stage35_accept_reason"]) == "accepted"
    assert int(out["stage35_mini_search_keep_all_rows_cfg"]) == 1
    assert int(out["stage35_mini_search_collected_rows"]) == 18
    assert int(out["stage35_mini_search_rows_kept"]) == 12
    assert float(out["stage35_best_score"]) == pytest.approx(0.31)
    assert float(out["stage35_best_search_score"]) == pytest.approx(0.22)
    assert str(out["stage35_best_seed_source"]) == "phasec_phaseb_challenger"
    assert str(out["stage35_best_stage3_source"]) == "phaseB_topk"
    assert str(out["stage35_best_lane"]) == "challenger"
    assert int(out["stage35_best_source_rank"]) == 3
    assert int(out["stage35_best_target_slice"]) == 1
    assert int(out["stage35_best_depth"]) == 2
    assert str(out["stage35_best_move_type"]) == "slice_local_mini_search"
    assert str(out["stage35_best_candidate_hash"]) == "abc123"


def test_build_phasec_truth_reporting_surfaces_score_vs_truth_disagreement() -> None:
    out = build_phasec_truth_reporting(
        phasec_final_winner_lane="anchor",
        phasec_final_winner_source="stage3_best_phaseB",
        phasec_start_summaries=[
            {
                "start_idx": 1,
                "lane": "anchor",
                "source": "stage3_best_phaseB",
                "candidate_hash": "anchor-hash",
                "selection_bucket": "anchor",
                "selected_by_novel_policy": 0,
                "final_match": 0.039,
                "final_score": 0.1910166735,
                "became_global_best": 1,
            },
            {
                "start_idx": 2,
                "lane": "challenger",
                "source": "phaseA_selected",
                "candidate_hash": "truth-hash",
                "selection_bucket": "novel_reserved",
                "selected_by_novel_policy": 1,
                "final_match": 0.418,
                "final_score": 0.1728454286,
                "became_global_best": 0,
            },
        ],
    )

    assert int(out["phaseC_truth_reporting_available"]) == 1
    assert str(out["phaseC_score_selected_winner_summary"]["candidate_hash"]) == "anchor-hash"
    assert str(out["phaseC_best_truth_start_summary"]["candidate_hash"]) == "truth-hash"
    assert str(out["phaseC_best_truth_challenger_summary"]["candidate_hash"]) == "truth-hash"
    assert int(out["phaseC_truth_disagreement_summary"]["winner_and_best_truth_differ"]) == 1
    assert float(
        out["phaseC_truth_disagreement_summary"]["truth_gap_best_truth_challenger_vs_winner"]
    ) == pytest.approx(0.379)
    assert float(
        out["phaseC_truth_disagreement_summary"]["score_gap_best_truth_challenger_vs_winner"]
    ) == pytest.approx(-0.0181712449)
