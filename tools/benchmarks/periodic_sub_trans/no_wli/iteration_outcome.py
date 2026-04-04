from __future__ import annotations

from typing import Any, Callable, Dict, Mapping, Sequence

import numpy as np

from tools.benchmarks.periodic_sub_trans.no_wli.phasec_truth_reporting import (
    build_phasec_truth_reporting,
)


def resolve_iteration_outcome(
    *,
    stop_reason: str,
    solve_match_threshold: float,
    dt_i: float,
    ev1: int,
    stage2_evals_total: int,
    ev3: int,
    best2_match: float,
    best2_score: float,
    best2_key: Sequence[int] | None,
    best2_pt: Sequence[int] | None,
    best2_preview: str,
    best3_match: float,
    best3_score: float,
    best3_key: Sequence[int] | None,
    pt3: np.ndarray,
    target_plaintext_idx: Sequence[int] | None = None,
    stage35_selected: bool = False,
    stage35_best_score: float = float("nan"),
    stage35_best_key: Sequence[int] | None = None,
    stage35_best_plaintext_idx: Sequence[int] | None = None,
    wli: Sequence[Sequence[int]],
    stage1_best_score: float,
    oracle_s1: float,
    oracle_s2: float,
    oracle_s3: float,
    derive_outcome_code_fn: Callable[..., str],
    safe_preview_latin_fn: Callable[[Any, Any], str],
) -> Dict[str, Any]:
    target_pt = (
        np.asarray(target_plaintext_idx, dtype=np.uint8).reshape(-1)
        if target_plaintext_idx is not None
        else np.asarray([], dtype=np.uint8)
    )
    stage35_pt = np.asarray(
        stage35_best_plaintext_idx if stage35_best_plaintext_idx is not None else [],
        dtype=np.uint8,
    ).reshape(-1)
    stage35_match = float("nan")
    if (
        bool(stage35_selected)
        and int(stage35_pt.size) > 0
        and int(target_pt.size) > 0
        and int(stage35_pt.size) == int(target_pt.size)
    ):
        stage35_match = float(np.mean(stage35_pt == target_pt))

    best_match = max(
        float(best2_match if np.isfinite(best2_match) else 0.0),
        float(best3_match if np.isfinite(best3_match) else 0.0),
    )
    best_stage = (
        "stage3_full_refine"
        if np.isfinite(best3_match) and best3_match >= best2_match
        else "stage2_search"
    )
    if bool(stage35_selected) and stage35_best_key is not None and int(stage35_pt.size) > 0:
        best_stage = "stage35_substitution_only"
        if np.isfinite(stage35_match):
            best_match = float(stage35_match)
    status = (
        "solved"
        if best_match >= float(solve_match_threshold)
        else ("stalled" if str(stop_reason) == "stalled_no_improve" else "unsolved")
    )
    total_evals = int(ev1 + int(stage2_evals_total) + int(ev3))

    final_best_key_idx: list[int] | None = None
    final_best_plaintext_idx: list[int] | None = None
    final_best_score = float("nan")
    if (
        best_stage == "stage35_substitution_only"
        and stage35_best_key is not None
        and int(stage35_pt.size) > 0
    ):
        final_best_key_idx = list(map(int, stage35_best_key))
        final_best_plaintext_idx = stage35_pt.astype(int).tolist()
        final_best_score = float(stage35_best_score)
    elif best_stage == "stage3_full_refine" and int(pt3.size) > 0 and best3_key is not None:
        final_best_key_idx = list(map(int, best3_key))
        final_best_plaintext_idx = np.asarray(pt3, dtype=np.uint8).astype(int).tolist()
        final_best_score = float(best3_score)
    elif best2_key is not None and best2_pt is not None:
        final_best_key_idx = list(map(int, best2_key))
        final_best_plaintext_idx = list(map(int, best2_pt))
        final_best_score = float(best2_score)

    if best_stage == "stage35_substitution_only" and int(stage35_pt.size) > 0:
        preview_best = str(safe_preview_latin_fn(stage35_pt, wli))
    elif best_stage == "stage3_full_refine" and int(pt3.size) > 0:
        preview_best = str(safe_preview_latin_fn(np.asarray(pt3, dtype=np.uint8), wli))
    elif str(best2_preview):
        preview_best = str(best2_preview)
    else:
        preview_best = (
            str(safe_preview_latin_fn(np.asarray(pt3, dtype=np.uint8), wli))
            if int(pt3.size) > 0
            else ""
        )

    outcome_code = str(
        derive_outcome_code_fn(status=str(status), stop_reason=str(stop_reason))
    )
    oracle_scores_payload = dict(
        stage1=float(oracle_s1) if np.isfinite(oracle_s1) else float("nan"),
        stage2=float(oracle_s2) if np.isfinite(oracle_s2) else float("nan"),
        stage3=float(oracle_s3) if np.isfinite(oracle_s3) else float("nan"),
    )
    score_minus_oracle_payload = dict(
        stage1=(
            float(stage1_best_score - oracle_s1)
            if np.isfinite(stage1_best_score) and np.isfinite(oracle_s1)
            else float("nan")
        ),
        stage2=(
            float(best2_score - oracle_s2)
            if np.isfinite(best2_score) and np.isfinite(oracle_s2)
            else float("nan")
        ),
        stage3=(
            float(best3_score - oracle_s3)
            if np.isfinite(best3_score) and np.isfinite(oracle_s3)
            else float("nan")
        ),
    )
    return dict(
        best_match=float(best_match),
        best_stage=str(best_stage),
        status=str(status),
        dt_i=float(dt_i),
        total_evals=int(total_evals),
        final_best_key_idx=final_best_key_idx,
        final_best_plaintext_idx=final_best_plaintext_idx,
        final_best_score=float(final_best_score),
        preview_best=str(preview_best),
        outcome_code=str(outcome_code),
        oracle_scores_payload=oracle_scores_payload,
        score_minus_oracle_payload=score_minus_oracle_payload,
    )


def build_stage2_diagnostics(
    *,
    stage2_archive: Dict[Any, Any],
    stage2_ranked: Sequence[Any],
    stage2_promoted: Sequence[Any],
    stage2_score_match_spearman: float,
) -> Dict[str, Any]:
    return dict(
        archive_entries=int(len(stage2_archive)),
        kept_entries=int(len(stage2_ranked)),
        promoted_entries=int(len(stage2_promoted)),
        score_match_spearman=(
            float(stage2_score_match_spearman)
            if np.isfinite(stage2_score_match_spearman)
            else float("nan")
        ),
    )


def build_stage3_diagnostics(
    *,
    phaseA_experiment: str,
    phaseB_experiment: str,
    init_target: int,
    init_actual: int,
    promoted_keys: int,
    gate_source: str,
    continue_after_solve: bool,
    solve_hits: int,
    period_init_mult: float,
    period_step_mult: float,
    period_restart_bonus: int,
    phaseB_top_n_cfg: int,
    phaseB_gate_delta_cfg: float,
    phaseB_gate_end_gain_cfg: float,
    phaseB_ran: int,
    phaseB_skipped: int,
    phaseB_top_n_used: int,
    phaseB_skip_reason: str,
    phaseB_family_preservation_policy: str = "off",
    phaseB_family_view_id: str = "prefix_hamming_le_24",
    phaseB_family_reserved_slots: int = 0,
    phaseB_family_count_in_top_band: int = 0,
    phaseB_family_preserved_count: int = 0,
    phaseB_family_reservation_applied: int = 0,
    phaseB_selected_unique_end_hash: int = 0,
    phaseB_downstream_selected_count: int = 0,
    phaseB_downstream_selected_unique_end_hash: int = 0,
    phaseB_topk_saved_count: int = 0,
    phaseB_topk_saved_unique_end_hash: int = 0,
    phaseB_char_pct_min_dynamic: float,
    phaseB_char_pct_min_source: str,
    span_basin_judge_k_cfg: int,
    span_basin_judge_k: int,
    span_basin_judge_seconds: float,
    basin_judge_span_calls_total: int,
    basin_judge_span_calls_active: int,
    basin_judge_span_calls_rejected_or_gated: int,
    basin_judge_span_seconds_total: float,
    basin_judge_unique_end_hash: int,
    scan_stage3_gate_low_match: float,
    scan_stage3_gate_high_match: float,
    scan_phaseA_only: int,
    span_active_rate: float,
    span_active_rate_source: str,
    span_eval_total: float,
    span_eval_active: float,
    span_eval_skipped_char_gate: float,
    span_seconds_total: float,
    span_seconds_active: float,
    span_phaseA_eval_total: float,
    span_phaseA_eval_active: float,
    span_phaseA_eval_skipped_char_gate: float,
    span_phaseA_seconds_total: float,
    span_phaseA_seconds_active: float,
    span_full_eval_total: float,
    span_full_eval_active: float,
    span_full_eval_skipped_char_gate: float,
    span_full_seconds_total: float,
    span_full_seconds_active: float,
    stage3_eval_count: int,
    c1_focus: int,
    phaseC_enabled_cfg: int = 0,
    phaseC_enabled_effective: int = 0,
    phaseC_ran: int = 0,
    phaseC_start_keys_used: int = 0,
    phaseC_start_policy: str = "source_order",
    phaseC_steps_cfg: int = 0,
    phaseC_proposals_per_step_cfg: int = 0,
    phaseC_lexical_min_match_cfg: float = float("nan"),
    phaseC_evals: int = 0,
    phaseC_accepts: int = 0,
    phaseC_improves: int = 0,
    phaseC_rescue_enabled_cfg: int = 0,
    phaseC_rescue_ran: int = 0,
    phaseC_rescue_starts_attempted: int = 0,
    phaseC_rescue_applied_starts: int = 0,
    phaseC_rescue_target_mode_cfg: str = "slice_probe",
    phaseC_rescue_selector_mode_cfg: str = "rescue_shallow_then_search",
    phaseC_rescue_candidates_cfg: int = 0,
    phaseC_rescue_slip_swaps_cfg: int = 0,
    phaseC_rescue_mini_search_steps_cfg: int = 0,
    phaseC_rescue_mini_search_beam_width_cfg: int = 0,
    phaseC_rescue_mini_search_top_symbols_cfg: int = 0,
    phaseC_rescue_mini_search_keep_all_rows_cfg: int = 0,
    phaseC_rescue_polish_steps_cfg: int = 0,
    phaseC_rescue_probe_evals: int = 0,
    phaseC_rescue_evals: int = 0,
    phaseC_rescue_mini_search_evals: int = 0,
    phaseC_rescue_anchor_enabled_cfg: int = 0,
    phaseC_rescue_phaseb_topk_min_rank_cfg: int = 2,
    phaseC_rescue_max_starts_cfg: int = 0,
    phaseC_rescue_eligible_starts: int = 0,
    phaseC_rescue_search_score_max_drop_cfg: float = 0.0,
    phaseC_rescue_guard_search_evals: int = 0,
    phaseC_rescue_guard_search_passes: int = 0,
    phaseC_rescue_guard_search_rejects: int = 0,
    phaseC_rescue_lexical_requests: int = 0,
    phaseC_rescue_lexical_cache_hits: int = 0,
    phaseC_rescue_lexical_cache_misses: int = 0,
    phaseC_rescue_lexical_tiebreak_decisions: int = 0,
    phaseC_rescue_lexical_budget_skips: int = 0,
    phaseC_rescue_lexical_threshold_skips: int = 0,
    phaseC_lexical_requests: int = 0,
    phaseC_lexical_cache_hits: int = 0,
    phaseC_lexical_cache_misses: int = 0,
    phaseC_lexical_tiebreak_decisions: int = 0,
    phaseC_lexical_budget_skips: int = 0,
    phaseC_lexical_threshold_skips: int = 0,
    phaseC_candidate_pool_count: int = 0,
    phaseC_candidate_pool_unique_keys: int = 0,
    phaseC_candidate_pool_unique_end_hash: int = 0,
    phaseC_candidate_pool_rows: Sequence[Mapping[str, Any]] | None = None,
    phaseC_candidate_pool_source_counts: Mapping[str, Any] | None = None,
    phaseC_novel_view_id: str = "",
    phaseC_anchor_candidate_hash: str = "",
    phaseC_candidate_pool_eligible_novel_count: int = 0,
    phaseC_candidate_pool_eligible_novel_row_count: int = 0,
    phaseC_candidate_pool_eligible_novel_source_counts: Mapping[str, Any] | None = None,
    phaseC_start_source_counts: Mapping[str, Any] | None = None,
    phaseC_start_unique_end_hash: int = 0,
    phaseC_start_eligible_novel_count: int = 0,
    phaseC_selected_novel_challenger_count: int = 0,
    phaseC_eligible_novel_not_selected_count: int = 0,
    phaseC_selected_novel_challenger_hashes: Sequence[str] | None = None,
    phaseC_improved_best: int = 0,
    phaseC_checkpoint_jsonl_name: str = "",
    phaseC_checkpoint_rows_written: int = 0,
    phaseC_anchor_lane_starts: int = 0,
    phaseC_challenger_lane_starts: int = 0,
    phaseC_challenger_overtook_anchor_count: int = 0,
    phaseC_final_winner_lane: str = "",
    phaseC_final_winner_source: str = "",
    phaseC_start_summaries: Sequence[Mapping[str, Any]] | None = None,
    stage35_requested_cfg: int = 0,
    stage35_enabled_cfg: int = 0,
    stage35_ran: int = 0,
    stage35_proof_valid: int = 0,
    stage35_proof_invalid_reason: str = "",
    stage35_selected: int = 0,
    stage35_seed_count: int = 0,
    stage35_tail_mismatch_count: int = 0,
    stage35_seed_source_counts: Mapping[str, Any] | None = None,
    stage35_archive_count: int = 0,
    stage35_rounds_completed: int = 0,
    stage35_evals: int = 0,
    stage35_runtime_seconds: float = 0.0,
    stage35_outcome_status: str = "",
    stage35_outcome_reason: str = "",
    stage35_completed: int = 0,
    stage35_capped: int = 0,
    stage35_partial_state_name: str = "",
    stage35_progress_jsonl_name: str = "",
    stage35_progress_event_count: int = 0,
    stage35_partial_dump_write_count: int = 0,
    stage35_telemetry_summary: Mapping[str, Any] | None = None,
    stage35_archive_unique_keys: int = 0,
    stage35_archive_unique_seed_sources: int = 0,
    stage35_archive_unique_target_slices: int = 0,
    stage35_archive_mean_substitution_hamming: float = 0.0,
    stage35_archive_max_substitution_hamming: int = 0,
    stage35_baseline_selector: str = "legacy",
    stage35_phasec_score_winner_candidate_hash: str = "",
    stage35_phasec_score_winner_candidate_source: str = "",
    stage35_phasec_score_winner_candidate_lane: str = "",
    stage35_phasec_score_winner_candidate_final_score: float = float("nan"),
    stage35_phasec_score_winner_candidate_final_match: float = float("nan"),
    stage35_baseline_candidate_hash: str = "",
    stage35_baseline_candidate_source: str = "",
    stage35_baseline_candidate_lane: str = "",
    stage35_baseline_candidate_source_rank: int = 0,
    stage35_baseline_candidate_final_score: float = float("nan"),
    stage35_baseline_candidate_final_match: float = float("nan"),
    stage35_baseline_differs_from_phasec_score_winner: int = 0,
    stage35_baseline_search_score: float = float("nan"),
    stage35_accept_score_min_gain_cfg: float = 0.0,
    stage35_accept_search_score_max_drop_cfg: float = 0.0,
    stage35_accept_passed: int = 0,
    stage35_accept_reason: str = "",
    stage35_mini_search_keep_all_rows_cfg: int = 0,
    stage35_mini_search_collected_rows: int = 0,
    stage35_mini_search_rows_kept: int = 0,
    stage35_best_score: float = float("nan"),
    stage35_best_search_score: float = float("nan"),
    stage35_best_seed_source: str = "",
    stage35_best_stage3_source: str = "",
    stage35_best_lane: str = "",
    stage35_best_source_rank: int = 0,
    stage35_best_target_slice: int | None = None,
    stage35_best_depth: int = 0,
    stage35_best_move_type: str = "",
    stage35_best_candidate_hash: str = "",
    stage35_best_match: float = float("nan"),
    stage35_truth_gain_vs_selected_row: float = float("nan"),
    stage35_truth_gain_vs_phasec_score_winner: float = float("nan"),
) -> Dict[str, Any]:
    out = dict(
        phaseA_experiment=str(phaseA_experiment),
        phaseB_experiment=str(phaseB_experiment),
        init_target=int(init_target),
        init_actual=int(init_actual),
        promoted_keys=int(promoted_keys),
        gate_source=str(gate_source),
        continue_after_solve=bool(continue_after_solve),
        solve_hits=int(solve_hits),
        period_init_mult=float(period_init_mult),
        period_step_mult=float(period_step_mult),
        period_restart_bonus=int(period_restart_bonus),
        phaseB_top_n_cfg=int(phaseB_top_n_cfg),
        phaseB_gate_delta_cfg=float(phaseB_gate_delta_cfg),
        phaseB_gate_end_gain_cfg=float(phaseB_gate_end_gain_cfg),
        phaseB_ran=int(phaseB_ran),
        phaseB_skipped=int(phaseB_skipped),
        phaseB_top_n_used=int(phaseB_top_n_used),
        phaseB_skip_reason=str(phaseB_skip_reason),
        phaseB_family_preservation_policy=str(phaseB_family_preservation_policy),
        phaseB_family_view_id=str(phaseB_family_view_id),
        phaseB_family_reserved_slots=int(phaseB_family_reserved_slots),
        phaseB_family_count_in_top_band=int(phaseB_family_count_in_top_band),
        phaseB_family_preserved_count=int(phaseB_family_preserved_count),
        phaseB_family_reservation_applied=int(phaseB_family_reservation_applied),
        phaseB_selected_unique_end_hash=int(phaseB_selected_unique_end_hash),
        phaseB_downstream_selected_count=int(phaseB_downstream_selected_count),
        phaseB_downstream_selected_unique_end_hash=int(
            phaseB_downstream_selected_unique_end_hash
        ),
        phaseB_topk_saved_count=int(phaseB_topk_saved_count),
        phaseB_topk_saved_unique_end_hash=int(phaseB_topk_saved_unique_end_hash),
        phaseB_char_pct_min_dynamic=float(phaseB_char_pct_min_dynamic),
        phaseB_char_pct_min_source=str(phaseB_char_pct_min_source),
        span_basin_judge_k_cfg=int(span_basin_judge_k_cfg),
        span_basin_judge_k=int(span_basin_judge_k),
        span_basin_judge_seconds=float(span_basin_judge_seconds),
        basin_judge_span_calls_total=int(basin_judge_span_calls_total),
        basin_judge_span_calls_active=int(basin_judge_span_calls_active),
        basin_judge_span_calls_rejected_or_gated=int(
            basin_judge_span_calls_rejected_or_gated
        ),
        basin_judge_span_seconds_total=float(basin_judge_span_seconds_total),
        basin_judge_unique_end_hash=int(basin_judge_unique_end_hash),
        scan_stage3_gate_low_match=float(scan_stage3_gate_low_match),
        scan_stage3_gate_high_match=float(scan_stage3_gate_high_match),
        scan_phaseA_only=int(scan_phaseA_only),
        span_active_rate=float(span_active_rate),
        span_active_rate_source=str(span_active_rate_source),
        span_eval_total=float(span_eval_total),
        span_eval_active=float(span_eval_active),
        span_eval_skipped_char_gate=float(span_eval_skipped_char_gate),
        span_calls_total=int(round(float(span_eval_total))),
        span_calls_active=int(round(float(span_eval_active))),
        span_calls_skipped_char_gate=int(round(float(span_eval_skipped_char_gate))),
        span_seconds_total=float(span_seconds_total),
        span_seconds_active=float(span_seconds_active),
        span_phaseA_eval_total=float(span_phaseA_eval_total),
        span_phaseA_eval_active=float(span_phaseA_eval_active),
        span_phaseA_eval_skipped_char_gate=float(span_phaseA_eval_skipped_char_gate),
        span_phaseA_seconds_total=float(span_phaseA_seconds_total),
        span_phaseA_seconds_active=float(span_phaseA_seconds_active),
        span_full_eval_total=float(span_full_eval_total),
        span_full_eval_active=float(span_full_eval_active),
        span_full_eval_skipped_char_gate=float(span_full_eval_skipped_char_gate),
        span_full_seconds_total=float(span_full_seconds_total),
        span_full_seconds_active=float(span_full_seconds_active),
        stage3_eval_count=int(stage3_eval_count),
        c1_focus=int(c1_focus),
        phaseC_enabled_cfg=int(phaseC_enabled_cfg),
        phaseC_enabled_effective=int(phaseC_enabled_effective),
        phaseC_ran=int(phaseC_ran),
        phaseC_start_keys_used=int(phaseC_start_keys_used),
        phaseC_start_policy=str(phaseC_start_policy),
        phaseC_steps_cfg=int(phaseC_steps_cfg),
        phaseC_proposals_per_step_cfg=int(phaseC_proposals_per_step_cfg),
        phaseC_lexical_min_match_cfg=float(phaseC_lexical_min_match_cfg),
        phaseC_evals=int(phaseC_evals),
        phaseC_accepts=int(phaseC_accepts),
        phaseC_improves=int(phaseC_improves),
        phaseC_rescue_enabled_cfg=int(phaseC_rescue_enabled_cfg),
        phaseC_rescue_ran=int(phaseC_rescue_ran),
        phaseC_rescue_starts_attempted=int(phaseC_rescue_starts_attempted),
        phaseC_rescue_applied_starts=int(phaseC_rescue_applied_starts),
        phaseC_rescue_target_mode_cfg=str(phaseC_rescue_target_mode_cfg),
        phaseC_rescue_selector_mode_cfg=str(phaseC_rescue_selector_mode_cfg),
        phaseC_rescue_candidates_cfg=int(phaseC_rescue_candidates_cfg),
        phaseC_rescue_slip_swaps_cfg=int(phaseC_rescue_slip_swaps_cfg),
        phaseC_rescue_mini_search_steps_cfg=int(phaseC_rescue_mini_search_steps_cfg),
        phaseC_rescue_mini_search_beam_width_cfg=int(
            phaseC_rescue_mini_search_beam_width_cfg
        ),
        phaseC_rescue_mini_search_top_symbols_cfg=int(
            phaseC_rescue_mini_search_top_symbols_cfg
        ),
        phaseC_rescue_mini_search_keep_all_rows_cfg=int(
            phaseC_rescue_mini_search_keep_all_rows_cfg
        ),
        phaseC_rescue_polish_steps_cfg=int(phaseC_rescue_polish_steps_cfg),
        phaseC_rescue_probe_evals=int(phaseC_rescue_probe_evals),
        phaseC_rescue_evals=int(phaseC_rescue_evals),
        phaseC_rescue_mini_search_evals=int(phaseC_rescue_mini_search_evals),
        phaseC_rescue_anchor_enabled_cfg=int(phaseC_rescue_anchor_enabled_cfg),
        phaseC_rescue_phaseb_topk_min_rank_cfg=int(
            phaseC_rescue_phaseb_topk_min_rank_cfg
        ),
        phaseC_rescue_max_starts_cfg=int(phaseC_rescue_max_starts_cfg),
        phaseC_rescue_eligible_starts=int(phaseC_rescue_eligible_starts),
        phaseC_rescue_search_score_max_drop_cfg=float(
            phaseC_rescue_search_score_max_drop_cfg
        ),
        phaseC_rescue_guard_search_evals=int(phaseC_rescue_guard_search_evals),
        phaseC_rescue_guard_search_passes=int(phaseC_rescue_guard_search_passes),
        phaseC_rescue_guard_search_rejects=int(phaseC_rescue_guard_search_rejects),
        phaseC_rescue_lexical_requests=int(phaseC_rescue_lexical_requests),
        phaseC_rescue_lexical_cache_hits=int(phaseC_rescue_lexical_cache_hits),
        phaseC_rescue_lexical_cache_misses=int(
            phaseC_rescue_lexical_cache_misses
        ),
        phaseC_rescue_lexical_tiebreak_decisions=int(
            phaseC_rescue_lexical_tiebreak_decisions
        ),
        phaseC_rescue_lexical_budget_skips=int(phaseC_rescue_lexical_budget_skips),
        phaseC_rescue_lexical_threshold_skips=int(
            phaseC_rescue_lexical_threshold_skips
        ),
        phaseC_lexical_requests=int(phaseC_lexical_requests),
        phaseC_lexical_cache_hits=int(phaseC_lexical_cache_hits),
        phaseC_lexical_cache_misses=int(phaseC_lexical_cache_misses),
        phaseC_lexical_tiebreak_decisions=int(phaseC_lexical_tiebreak_decisions),
        phaseC_lexical_budget_skips=int(phaseC_lexical_budget_skips),
        phaseC_lexical_threshold_skips=int(phaseC_lexical_threshold_skips),
        phaseC_candidate_pool_count=int(phaseC_candidate_pool_count),
        phaseC_candidate_pool_unique_keys=int(phaseC_candidate_pool_unique_keys),
        phaseC_candidate_pool_unique_end_hash=int(phaseC_candidate_pool_unique_end_hash),
        phaseC_candidate_pool_rows=[
            dict(row) for row in list(phaseC_candidate_pool_rows or [])
        ],
        phaseC_candidate_pool_source_counts=dict(phaseC_candidate_pool_source_counts or {}),
        phaseC_novel_view_id=str(phaseC_novel_view_id),
        phaseC_anchor_candidate_hash=str(phaseC_anchor_candidate_hash),
        phaseC_candidate_pool_eligible_novel_count=int(
            phaseC_candidate_pool_eligible_novel_count
        ),
        phaseC_candidate_pool_eligible_novel_row_count=int(
            phaseC_candidate_pool_eligible_novel_row_count
        ),
        phaseC_candidate_pool_eligible_novel_source_counts=dict(
            phaseC_candidate_pool_eligible_novel_source_counts or {}
        ),
        phaseC_start_source_counts=dict(phaseC_start_source_counts or {}),
        phaseC_start_unique_end_hash=int(phaseC_start_unique_end_hash),
        phaseC_start_eligible_novel_count=int(phaseC_start_eligible_novel_count),
        phaseC_selected_novel_challenger_count=int(
            phaseC_selected_novel_challenger_count
        ),
        phaseC_eligible_novel_not_selected_count=int(
            phaseC_eligible_novel_not_selected_count
        ),
        phaseC_selected_novel_challenger_hashes=[
            str(x) for x in list(phaseC_selected_novel_challenger_hashes or [])
        ],
        phaseC_improved_best=int(phaseC_improved_best),
        phaseC_checkpoint_jsonl_name=str(phaseC_checkpoint_jsonl_name),
        phaseC_checkpoint_rows_written=int(phaseC_checkpoint_rows_written),
        phaseC_anchor_lane_starts=int(phaseC_anchor_lane_starts),
        phaseC_challenger_lane_starts=int(phaseC_challenger_lane_starts),
        phaseC_challenger_overtook_anchor_count=int(
            phaseC_challenger_overtook_anchor_count
        ),
        phaseC_final_winner_lane=str(phaseC_final_winner_lane),
        phaseC_final_winner_source=str(phaseC_final_winner_source),
        phaseC_start_summaries=[
            dict(row) for row in list(phaseC_start_summaries or [])
        ],
        stage35_requested_cfg=int(stage35_requested_cfg),
        stage35_enabled_cfg=int(stage35_enabled_cfg),
        stage35_ran=int(stage35_ran),
        stage35_proof_valid=int(stage35_proof_valid),
        stage35_proof_invalid_reason=str(stage35_proof_invalid_reason),
        stage35_selected=int(stage35_selected),
        stage35_seed_count=int(stage35_seed_count),
        stage35_tail_mismatch_count=int(stage35_tail_mismatch_count),
        stage35_seed_source_counts=dict(stage35_seed_source_counts or {}),
        stage35_archive_count=int(stage35_archive_count),
        stage35_rounds_completed=int(stage35_rounds_completed),
        stage35_evals=int(stage35_evals),
        stage35_runtime_seconds=float(stage35_runtime_seconds),
        stage35_outcome_status=str(stage35_outcome_status),
        stage35_outcome_reason=str(stage35_outcome_reason),
        stage35_completed=int(stage35_completed),
        stage35_capped=int(stage35_capped),
        stage35_partial_state_name=str(stage35_partial_state_name),
        stage35_progress_jsonl_name=str(stage35_progress_jsonl_name),
        stage35_progress_event_count=int(stage35_progress_event_count),
        stage35_partial_dump_write_count=int(stage35_partial_dump_write_count),
        stage35_telemetry_summary=dict(stage35_telemetry_summary or {}),
        stage35_archive_unique_keys=int(stage35_archive_unique_keys),
        stage35_archive_unique_seed_sources=int(
            stage35_archive_unique_seed_sources
        ),
        stage35_archive_unique_target_slices=int(
            stage35_archive_unique_target_slices
        ),
        stage35_archive_mean_substitution_hamming=float(
            stage35_archive_mean_substitution_hamming
        ),
        stage35_archive_max_substitution_hamming=int(
            stage35_archive_max_substitution_hamming
        ),
        stage35_baseline_selector=str(stage35_baseline_selector),
        stage35_phasec_score_winner_candidate_hash=str(
            stage35_phasec_score_winner_candidate_hash
        ),
        stage35_phasec_score_winner_candidate_source=str(
            stage35_phasec_score_winner_candidate_source
        ),
        stage35_phasec_score_winner_candidate_lane=str(
            stage35_phasec_score_winner_candidate_lane
        ),
        stage35_phasec_score_winner_candidate_final_score=float(
            stage35_phasec_score_winner_candidate_final_score
        ),
        stage35_phasec_score_winner_candidate_final_match=float(
            stage35_phasec_score_winner_candidate_final_match
        ),
        stage35_baseline_candidate_hash=str(stage35_baseline_candidate_hash),
        stage35_baseline_candidate_source=str(stage35_baseline_candidate_source),
        stage35_baseline_candidate_lane=str(stage35_baseline_candidate_lane),
        stage35_baseline_candidate_source_rank=int(
            stage35_baseline_candidate_source_rank
        ),
        stage35_baseline_candidate_final_score=float(
            stage35_baseline_candidate_final_score
        ),
        stage35_baseline_candidate_final_match=float(
            stage35_baseline_candidate_final_match
        ),
        stage35_baseline_differs_from_phasec_score_winner=int(
            stage35_baseline_differs_from_phasec_score_winner
        ),
        stage35_baseline_search_score=float(stage35_baseline_search_score),
        stage35_accept_score_min_gain_cfg=float(stage35_accept_score_min_gain_cfg),
        stage35_accept_search_score_max_drop_cfg=float(
            stage35_accept_search_score_max_drop_cfg
        ),
        stage35_accept_passed=int(stage35_accept_passed),
        stage35_accept_reason=str(stage35_accept_reason),
        stage35_mini_search_keep_all_rows_cfg=int(
            stage35_mini_search_keep_all_rows_cfg
        ),
        stage35_mini_search_collected_rows=int(stage35_mini_search_collected_rows),
        stage35_mini_search_rows_kept=int(stage35_mini_search_rows_kept),
        stage35_best_score=float(stage35_best_score),
        stage35_best_search_score=float(stage35_best_search_score),
        stage35_best_seed_source=str(stage35_best_seed_source),
        stage35_best_stage3_source=str(stage35_best_stage3_source),
        stage35_best_lane=str(stage35_best_lane),
        stage35_best_source_rank=int(stage35_best_source_rank),
        stage35_best_target_slice=(
            int(stage35_best_target_slice)
            if stage35_best_target_slice is not None
            else None
        ),
        stage35_best_depth=int(stage35_best_depth),
        stage35_best_move_type=str(stage35_best_move_type),
        stage35_best_candidate_hash=str(stage35_best_candidate_hash),
        stage35_best_match=float(stage35_best_match),
        stage35_truth_gain_vs_selected_row=float(stage35_truth_gain_vs_selected_row),
        stage35_truth_gain_vs_phasec_score_winner=float(
            stage35_truth_gain_vs_phasec_score_winner
        ),
    )
    out.update(
        build_phasec_truth_reporting(
            phasec_start_summaries=list(phaseC_start_summaries or []),
            phasec_final_winner_lane=str(phaseC_final_winner_lane),
            phasec_final_winner_source=str(phaseC_final_winner_source),
        )
    )
    return out
