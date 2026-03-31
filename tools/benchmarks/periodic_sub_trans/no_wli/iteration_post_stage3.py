from __future__ import annotations

from typing import Any, Callable, Dict, Mapping

import numpy as np

from tools.benchmarks.periodic_sub_trans.no_wli.commit_bridge_state import (
    extract_commit_bridge_state,
)
from tools.benchmarks.periodic_sub_trans.no_wli.phasec_diagnostics_contract import (
    require_phasec_diagnostics_contract,
)


def finalize_iteration_post_stage3(
    *,
    state: Mapping[str, Any],
    stage3_continue_after_solve: bool,
    scan_stage3_gate_low_match: float,
    scan_stage3_gate_high_match: float,
    stage3_c1_focus_enabled: bool,
    solve_match_threshold: float,
    build_stage2_diagnostics_fn: Callable[..., Dict[str, Any]],
    build_stage3_diagnostics_fn: Callable[..., Dict[str, Any]],
    finalize_iteration_and_commit_fn: Callable[..., Dict[str, Any]],
    build_iteration_payloads_fn: Callable[..., Any],
    commit_iteration_with_checkpoint_fn: Callable[..., None],
    derive_outcome_code_fn: Callable[..., str],
    safe_preview_latin_fn: Callable[[Any, Any], str],
) -> None:
    require_phasec_diagnostics_contract(
        state,
        context="iteration_post_stage3.state",
    )
    stage2_diagnostics = build_stage2_diagnostics_fn(
        stage2_archive=state["stage2_archive"],
        stage2_ranked=state["stage2_ranked"],
        stage2_promoted=state["stage2_promoted"],
        stage2_score_match_spearman=float(state["stage2_score_match_spearman"]),
    )
    stage3_diagnostics = build_stage3_diagnostics_fn(
        phaseA_experiment=str(state["stage3_phaseA_experiment"]),
        phaseB_experiment=str(state["stage3_phaseB_experiment"]),
        init_target=int(state["stage3_init_target"]),
        init_actual=int(state["stage3_init_actual"]),
        promoted_keys=int(state["stage3_promoted_keys_count"]),
        gate_source=str(state["stage3_gate_source"]),
        continue_after_solve=bool(stage3_continue_after_solve),
        solve_hits=int(state["stage3_solve_hits"]),
        period_init_mult=float(state["stage3_period_init_mult"]),
        period_step_mult=float(state["stage3_period_step_mult"]),
        period_restart_bonus=int(state["stage3_period_restart_bonus"]),
        phaseB_top_n_cfg=int(state["stage3_phaseB_top_n_cfg"]),
        phaseB_gate_delta_cfg=float(state["stage3_phaseB_gate_delta_cfg"]),
        phaseB_gate_end_gain_cfg=float(state["stage3_phaseB_gate_end_gain_cfg"]),
        phaseB_ran=int(state.get("phaseB_ran", 0)),
        phaseB_skipped=int(state.get("phaseB_skipped", 0)),
        phaseB_top_n_used=int(state.get("phaseB_top_n_used", 0)),
        phaseB_skip_reason=str(state.get("phaseB_skip_reason", "")),
        phaseB_family_preservation_policy=str(
            state.get("phaseB_family_preservation_policy", "off")
        ),
        phaseB_family_view_id=str(
            state.get("phaseB_family_view_id", "prefix_hamming_le_24")
        ),
        phaseB_family_reserved_slots=int(
            state.get("phaseB_family_reserved_slots", 0)
        ),
        phaseB_family_count_in_top_band=int(
            state.get("phaseB_family_count_in_top_band", 0)
        ),
        phaseB_family_preserved_count=int(
            state.get("phaseB_family_preserved_count", 0)
        ),
        phaseB_family_reservation_applied=int(
            state.get("phaseB_family_reservation_applied", 0)
        ),
        phaseB_selected_unique_end_hash=int(
            state.get("phaseB_selected_unique_end_hash", 0)
        ),
        phaseB_downstream_selected_count=int(
            state.get("phaseB_downstream_selected_count", 0)
        ),
        phaseB_downstream_selected_unique_end_hash=int(
            state.get("phaseB_downstream_selected_unique_end_hash", 0)
        ),
        phaseB_topk_saved_count=int(state.get("phaseB_topk_saved_count", 0)),
        phaseB_topk_saved_unique_end_hash=int(
            state.get("phaseB_topk_saved_unique_end_hash", 0)
        ),
        phaseB_char_pct_min_dynamic=float(state["stage3_phaseB_char_pct_min_dynamic"]),
        phaseB_char_pct_min_source=str(state["stage3_phaseB_char_pct_min_source"]),
        span_basin_judge_k_cfg=int(state["stage3_span_basin_judge_k_cfg"]),
        span_basin_judge_k=int(state["stage3_span_basin_judge_k_used"]),
        span_basin_judge_seconds=float(state["stage3_span_basin_judge_seconds"]),
        basin_judge_span_calls_total=int(state["stage3_basin_judge_span_calls_total"]),
        basin_judge_span_calls_active=int(state["stage3_basin_judge_span_calls_active"]),
        basin_judge_span_calls_rejected_or_gated=int(
            state["stage3_basin_judge_span_calls_rejected_or_gated"]
        ),
        basin_judge_span_seconds_total=float(state["stage3_basin_judge_span_seconds_total"]),
        basin_judge_unique_end_hash=int(state["stage3_basin_judge_unique_end_hash"]),
        scan_stage3_gate_low_match=float(scan_stage3_gate_low_match),
        scan_stage3_gate_high_match=float(scan_stage3_gate_high_match),
        scan_phaseA_only=int(1 if bool(state["stage3_scan_phaseA_only"]) else 0),
        span_active_rate=float(state["stage3_span_active_rate"]),
        span_active_rate_source=str(state["stage3_span_active_rate_source"]),
        span_eval_total=float(state["stage3_span_eval_total"]),
        span_eval_active=float(state["stage3_span_eval_active"]),
        span_eval_skipped_char_gate=float(state["stage3_span_eval_skipped"]),
        span_seconds_total=float(state["stage3_span_seconds_total"]),
        span_seconds_active=float(state["stage3_span_seconds_active"]),
        span_phaseA_eval_total=float(state["stage3_span_phaseA_eval_total"]),
        span_phaseA_eval_active=float(state["stage3_span_phaseA_eval_active"]),
        span_phaseA_eval_skipped_char_gate=float(state["stage3_span_phaseA_eval_skipped"]),
        span_phaseA_seconds_total=float(state["stage3_span_phaseA_seconds_total"]),
        span_phaseA_seconds_active=float(state["stage3_span_phaseA_seconds_active"]),
        span_full_eval_total=float(state["stage3_span_full_eval_total"]),
        span_full_eval_active=float(state["stage3_span_full_eval_active"]),
        span_full_eval_skipped_char_gate=float(state["stage3_span_full_eval_skipped"]),
        span_full_seconds_total=float(state["stage3_span_full_seconds_total"]),
        span_full_seconds_active=float(state["stage3_span_full_seconds_active"]),
        stage3_eval_count=int(state["ev3"]),
        c1_focus=int(
            1
            if (int(state["tier"].columns) <= 1 and bool(stage3_c1_focus_enabled))
            else 0
        ),
        phaseC_enabled_cfg=int(state.get("phaseC_enabled_cfg", 0)),
        phaseC_enabled_effective=int(state.get("phaseC_enabled_effective", 0)),
        phaseC_ran=int(state.get("phaseC_ran", 0)),
        phaseC_start_keys_used=int(state.get("phaseC_start_keys_used", 0)),
        phaseC_start_policy=str(state.get("phaseC_start_policy", "source_order")),
        phaseC_steps_cfg=int(state.get("phaseC_steps_cfg", 0)),
        phaseC_proposals_per_step_cfg=int(
            state.get("phaseC_proposals_per_step_cfg", 0)
        ),
        phaseC_lexical_min_match_cfg=float(
            state.get("phaseC_lexical_min_match_cfg", float("nan"))
        ),
        phaseC_evals=int(state.get("phaseC_evals", 0)),
        phaseC_accepts=int(state.get("phaseC_accepts", 0)),
        phaseC_improves=int(state.get("phaseC_improves", 0)),
        phaseC_rescue_enabled_cfg=int(state.get("phaseC_rescue_enabled_cfg", 0)),
        phaseC_rescue_ran=int(state.get("phaseC_rescue_ran", 0)),
        phaseC_rescue_starts_attempted=int(
            state.get("phaseC_rescue_starts_attempted", 0)
        ),
        phaseC_rescue_applied_starts=int(
            state.get("phaseC_rescue_applied_starts", 0)
        ),
        phaseC_rescue_target_mode_cfg=str(
            state.get("phaseC_rescue_target_mode_cfg", "slice_probe")
        ),
        phaseC_rescue_selector_mode_cfg=str(
            state.get(
                "phaseC_rescue_selector_mode_cfg",
                "rescue_shallow_then_search",
            )
        ),
        phaseC_rescue_candidates_cfg=int(
            state.get("phaseC_rescue_candidates_cfg", 0)
        ),
        phaseC_rescue_slip_swaps_cfg=int(
            state.get("phaseC_rescue_slip_swaps_cfg", 0)
        ),
        phaseC_rescue_mini_search_steps_cfg=int(
            state.get("phaseC_rescue_mini_search_steps_cfg", 0)
        ),
        phaseC_rescue_mini_search_beam_width_cfg=int(
            state.get("phaseC_rescue_mini_search_beam_width_cfg", 0)
        ),
        phaseC_rescue_mini_search_top_symbols_cfg=int(
            state.get("phaseC_rescue_mini_search_top_symbols_cfg", 0)
        ),
        phaseC_rescue_mini_search_keep_all_rows_cfg=int(
            state.get("phaseC_rescue_mini_search_keep_all_rows_cfg", 0)
        ),
        phaseC_rescue_polish_steps_cfg=int(
            state.get("phaseC_rescue_polish_steps_cfg", 0)
        ),
        phaseC_rescue_probe_evals=int(state.get("phaseC_rescue_probe_evals", 0)),
        phaseC_rescue_evals=int(state.get("phaseC_rescue_evals", 0)),
        phaseC_rescue_mini_search_evals=int(
            state.get("phaseC_rescue_mini_search_evals", 0)
        ),
        phaseC_rescue_anchor_enabled_cfg=int(
            state.get("phaseC_rescue_anchor_enabled_cfg", 0)
        ),
        phaseC_rescue_phaseb_topk_min_rank_cfg=int(
            state.get("phaseC_rescue_phaseb_topk_min_rank_cfg", 2)
        ),
        phaseC_rescue_max_starts_cfg=int(
            state.get("phaseC_rescue_max_starts_cfg", 0)
        ),
        phaseC_rescue_eligible_starts=int(
            state.get("phaseC_rescue_eligible_starts", 0)
        ),
        phaseC_rescue_search_score_max_drop_cfg=float(
            state.get("phaseC_rescue_search_score_max_drop_cfg", 0.0)
        ),
        phaseC_rescue_guard_search_evals=int(
            state.get("phaseC_rescue_guard_search_evals", 0)
        ),
        phaseC_rescue_guard_search_passes=int(
            state.get("phaseC_rescue_guard_search_passes", 0)
        ),
        phaseC_rescue_guard_search_rejects=int(
            state.get("phaseC_rescue_guard_search_rejects", 0)
        ),
        phaseC_rescue_lexical_requests=int(
            state.get("phaseC_rescue_lexical_requests", 0)
        ),
        phaseC_rescue_lexical_cache_hits=int(
            state.get("phaseC_rescue_lexical_cache_hits", 0)
        ),
        phaseC_rescue_lexical_cache_misses=int(
            state.get("phaseC_rescue_lexical_cache_misses", 0)
        ),
        phaseC_rescue_lexical_tiebreak_decisions=int(
            state.get("phaseC_rescue_lexical_tiebreak_decisions", 0)
        ),
        phaseC_rescue_lexical_budget_skips=int(
            state.get("phaseC_rescue_lexical_budget_skips", 0)
        ),
        phaseC_rescue_lexical_threshold_skips=int(
            state.get("phaseC_rescue_lexical_threshold_skips", 0)
        ),
        phaseC_lexical_requests=int(state.get("phaseC_lexical_requests", 0)),
        phaseC_lexical_cache_hits=int(state.get("phaseC_lexical_cache_hits", 0)),
        phaseC_lexical_cache_misses=int(state.get("phaseC_lexical_cache_misses", 0)),
        phaseC_lexical_tiebreak_decisions=int(
            state.get("phaseC_lexical_tiebreak_decisions", 0)
        ),
        phaseC_lexical_budget_skips=int(state.get("phaseC_lexical_budget_skips", 0)),
        phaseC_lexical_threshold_skips=int(
            state.get("phaseC_lexical_threshold_skips", 0)
        ),
        phaseC_candidate_pool_count=int(state.get("phaseC_candidate_pool_count", 0)),
        phaseC_candidate_pool_unique_keys=int(
            state.get("phaseC_candidate_pool_unique_keys", 0)
        ),
        phaseC_candidate_pool_unique_end_hash=int(
            state.get("phaseC_candidate_pool_unique_end_hash", 0)
        ),
        phaseC_candidate_pool_source_counts=dict(
            state.get("phaseC_candidate_pool_source_counts", {})
        ),
        phaseC_novel_view_id=str(state.get("phaseC_novel_view_id", "")),
        phaseC_anchor_candidate_hash=str(
            state.get("phaseC_anchor_candidate_hash", "")
        ),
        phaseC_candidate_pool_eligible_novel_count=int(
            state.get("phaseC_candidate_pool_eligible_novel_count", 0)
        ),
        phaseC_candidate_pool_eligible_novel_row_count=int(
            state.get("phaseC_candidate_pool_eligible_novel_row_count", 0)
        ),
        phaseC_candidate_pool_eligible_novel_source_counts=dict(
            state.get("phaseC_candidate_pool_eligible_novel_source_counts", {})
        ),
        phaseC_start_source_counts=dict(state.get("phaseC_start_source_counts", {})),
        phaseC_start_unique_end_hash=int(
            state.get("phaseC_start_unique_end_hash", 0)
        ),
        phaseC_start_eligible_novel_count=int(
            state.get("phaseC_start_eligible_novel_count", 0)
        ),
        phaseC_selected_novel_challenger_count=int(
            state.get("phaseC_selected_novel_challenger_count", 0)
        ),
        phaseC_eligible_novel_not_selected_count=int(
            state.get("phaseC_eligible_novel_not_selected_count", 0)
        ),
        phaseC_selected_novel_challenger_hashes=list(
            state.get("phaseC_selected_novel_challenger_hashes", [])
        ),
        phaseC_improved_best=int(state.get("phaseC_improved_best", 0)),
        phaseC_checkpoint_jsonl_name=str(
            state.get("phaseC_checkpoint_jsonl_name", "")
        ),
        phaseC_checkpoint_rows_written=int(
            state.get("phaseC_checkpoint_rows_written", 0)
        ),
        phaseC_anchor_lane_starts=int(state.get("phaseC_anchor_lane_starts", 0)),
        phaseC_challenger_lane_starts=int(
            state.get("phaseC_challenger_lane_starts", 0)
        ),
        phaseC_challenger_overtook_anchor_count=int(
            state.get("phaseC_challenger_overtook_anchor_count", 0)
        ),
        phaseC_final_winner_lane=str(state.get("phaseC_final_winner_lane", "")),
        phaseC_final_winner_source=str(state.get("phaseC_final_winner_source", "")),
        phaseC_start_summaries=list(state.get("phaseC_start_summaries", [])),
        stage35_requested_cfg=int(state.get("stage35_requested_cfg", 0)),
        stage35_enabled_cfg=int(state.get("stage35_enabled_cfg", 0)),
        stage35_ran=int(state.get("stage35_ran", 0)),
        stage35_proof_valid=int(state.get("stage35_proof_valid", 0)),
        stage35_proof_invalid_reason=str(
            state.get("stage35_proof_invalid_reason", "")
        ),
        stage35_selected=int(state.get("stage35_selected", 0)),
        stage35_seed_count=int(state.get("stage35_seed_count", 0)),
        stage35_tail_mismatch_count=int(
            state.get("stage35_tail_mismatch_count", 0)
        ),
        stage35_seed_source_counts=dict(
            state.get("stage35_seed_source_counts", {})
        ),
        stage35_archive_count=int(state.get("stage35_archive_count", 0)),
        stage35_rounds_completed=int(state.get("stage35_rounds_completed", 0)),
        stage35_evals=int(state.get("stage35_evals", 0)),
        stage35_runtime_seconds=float(state.get("stage35_runtime_seconds", 0.0)),
        stage35_archive_unique_keys=int(
            state.get("stage35_archive_unique_keys", 0)
        ),
        stage35_archive_unique_seed_sources=int(
            state.get("stage35_archive_unique_seed_sources", 0)
        ),
        stage35_archive_unique_target_slices=int(
            state.get("stage35_archive_unique_target_slices", 0)
        ),
        stage35_archive_mean_substitution_hamming=float(
            state.get("stage35_archive_mean_substitution_hamming", 0.0)
        ),
        stage35_archive_max_substitution_hamming=int(
            state.get("stage35_archive_max_substitution_hamming", 0)
        ),
        stage35_baseline_search_score=float(
            state.get("stage35_baseline_search_score", float("nan"))
        ),
        stage35_accept_score_min_gain_cfg=float(
            state.get("stage35_accept_score_min_gain_cfg", 0.0)
        ),
        stage35_accept_search_score_max_drop_cfg=float(
            state.get("stage35_accept_search_score_max_drop_cfg", 0.0)
        ),
        stage35_accept_passed=int(state.get("stage35_accept_passed", 0)),
        stage35_accept_reason=str(state.get("stage35_accept_reason", "")),
        stage35_mini_search_keep_all_rows_cfg=int(
            state.get("stage35_mini_search_keep_all_rows_cfg", 0)
        ),
        stage35_mini_search_collected_rows=int(
            state.get("stage35_mini_search_collected_rows", 0)
        ),
        stage35_mini_search_rows_kept=int(
            state.get("stage35_mini_search_rows_kept", 0)
        ),
        stage35_best_score=float(state.get("stage35_best_score", float("nan"))),
        stage35_best_search_score=float(
            state.get("stage35_best_search_score", float("nan"))
        ),
        stage35_best_seed_source=str(state.get("stage35_best_seed_source", "")),
        stage35_best_stage3_source=str(
            state.get("stage35_best_stage3_source", "")
        ),
        stage35_best_lane=str(state.get("stage35_best_lane", "")),
        stage35_best_source_rank=int(state.get("stage35_best_source_rank", 0)),
        stage35_best_target_slice=state.get("stage35_best_target_slice", None),
        stage35_best_depth=int(state.get("stage35_best_depth", 0)),
        stage35_best_move_type=str(state.get("stage35_best_move_type", "")),
        stage35_best_candidate_hash=str(
            state.get("stage35_best_candidate_hash", "")
        ),
    )
    finalize_iteration_and_commit_fn(
        tier=state["tier"],
        text_id=int(state["text_id"]),
        key_seed=int(state["key_seed"]),
        off=int(state["off"]),
        offset_used=int(state["offset_used"]),
        stop_reason=str(state["stop_reason"]),
        solve_match_threshold=float(solve_match_threshold),
        t0_i=float(state["t0_i"]),
        ev1=int(state["ev1"]),
        stage2_evals_total=int(state["stage2_evals_total"]),
        ev3=int(state["ev3"]),
        best2_match=float(state["best2_match"]),
        best2_score=float(state["best2_score"]),
        best2_key=state["best2_key"],
        best2_pt=state["best2_pt"],
        best2_preview=str(state["best2_preview"]),
        best3_match=float(state["best3_match"]),
        best3_score=float(state["best3_score"]),
        best3_key=state["best3_key"],
        pt3=np.asarray(state["pt3"], dtype=np.uint8),
        wli=state["wli"],
        stage1_best_score=float(state["stage1_best_score"]),
        oracle_s1=float(state["oracle_s1"]),
        oracle_s2=float(state["oracle_s2"]),
        oracle_s3=float(state["oracle_s3"]),
        stage2_gap_to_oracle=float(state["stage2_gap_to_oracle"]),
        stage3_band_name=str(state["stage3_band_name"]),
        stage3_basin_judge_span_calls_total=int(state["stage3_basin_judge_span_calls_total"]),
        stage3_basin_judge_span_calls_active=int(state["stage3_basin_judge_span_calls_active"]),
        stage3_basin_judge_span_calls_rejected_or_gated=int(
            state["stage3_basin_judge_span_calls_rejected_or_gated"]
        ),
        stage3_basin_judge_span_seconds_total=float(state["stage3_basin_judge_span_seconds_total"]),
        stage3_basin_judge_unique_end_hash=int(state["stage3_basin_judge_unique_end_hash"]),
        oracle_mode=str(state["oracle_mode"]),
        oracle_consulted_in_decisions=bool(state["oracle_consulted_in_decisions"]),
        sub_key_match=float(state["sub_key_match"]),
        ct_idx=np.asarray(state["ct_idx"], dtype=np.uint8),
        pt_idx=np.asarray(state["pt_idx"], dtype=np.uint8),
        target_key_idx=state.get("key_true"),
        stage2_topk_payload=state["stage2_topk_payload"],
        stage2_topk_has_best_match=bool(state["stage2_topk_has_best_match"]),
        stage2_diagnostics=stage2_diagnostics,
        stage3_topk_payload=state["stage3_topk_payload"],
        stage3_diagnostics=stage3_diagnostics,
        stage35_selected=bool(state.get("stage35_selected", 0)),
        stage35_best_score=float(state.get("stage35_best_score", float("nan"))),
        stage35_best_key=state.get("stage35_best_key", None),
        stage35_best_plaintext_idx=state.get("stage35_best_plaintext_idx", None),
        stage35_archive_rows=list(state.get("stage35_archive_rows", [])),
        stage35_seed_rows=list(state.get("stage35_seed_rows", [])),
        scorer_word_ngram_report_runtime=state.get("scorer_word_ngram_report_runtime"),
        require_batch_scoring=bool(state["REQUIRE_BATCH_SCORING"]),
        build_iteration_payloads_fn=build_iteration_payloads_fn,
        commit_iteration_with_checkpoint_fn=commit_iteration_with_checkpoint_fn,
        instances=state["instances"],
        derive_outcome_code_fn=derive_outcome_code_fn,
        safe_preview_latin_fn=safe_preview_latin_fn,
        bridge_state=extract_commit_bridge_state(iteration_state=state),
    )
