from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
import time
from typing import Any, Callable, Dict, Mapping

import numpy as np

from tools.benchmarks.periodic_sub_trans.no_wli.phasec_diagnostics_contract import (
    require_phasec_diagnostics_contract,
)
from tools.benchmarks.periodic_sub_trans.no_wli.late_stage_selector_core import (
    normalize_stage35_baseline_selector,
    select_phasec_score_winner_row,
    select_stage35_baseline_row,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage3_runtime_calls import (
    Stage3RuntimeCallContext,
    run_stage3_phasea_restarts_call,
    run_stage3_single_phase_call,
    run_stage3_two_phase_followup_call,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage35_substitution_solver import (
    run_stage35_live_followup,
)


def _stage35_wall_ts() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def run_stage3_iteration_flow(
    *,
    state: Mapping[str, Any],
    stage3_runtime_call_ctx: Stage3RuntimeCallContext,
    stage3_two_phase_enabled: bool,
    stage3_continue_after_solve: bool,
    stage3_phasea_cfg_default: Dict[str, Any],
    stage3_phaseb_cfg_default: Dict[str, Any],
    stage3_phaseb_top_n_default: int,
    stage3_phaseb_gate_delta_floor_default: float,
    stage3_phaseb_gate_end_gain_floor_default: float,
    solver_stage3_default_cfg: Dict[str, Any],
    stage3_span_basin_judge_k: int,
    tier_heartbeat_seconds: float,
    solve_match_threshold: float,
    stall_delta: float,
    stall_stage_limit: int,
    evaluate_stage3_entry_policy_fn: Callable[..., Dict[str, Any]],
    prepare_stage3_refine_inputs_fn: Callable[..., Dict[str, Any]],
    summarize_stage3_span_fn: Callable[..., Dict[str, Any]],
    mark_oracle_decision_use_fn: Callable[[], None],
    print_stage_preview_fn: Callable[..., None],
    fmt_finite_float_fn: Callable[..., str],
    log_prefix: str = "[pipeline_no_wli]",
) -> Dict[str, Any]:
    tier = state["tier"]
    text_id = int(state["text_id"])
    key_seed = int(state["key_seed"])
    t0_i = float(state["t0_i"])
    key_len = int(state["key_len"])
    best2_match = float(state["best2_match"])
    best2_key = state["best2_key"]
    stage2_promoted = list(state["stage2_promoted"])
    stage2_entry_score = float(state["stage2_entry_score"])
    stage2_entry_score_judge = float(state["stage2_entry_score_judge"])
    scorer_stage2 = dict(state["scorer_stage2"])
    scorer_full = dict(state["scorer_full"])
    oracle_s3 = float(state["oracle_s3"])
    oracle_decision_paths_enabled = bool(state["oracle_decision_paths_enabled"])
    ct_idx = np.asarray(state["ct_idx"], dtype=np.uint8)
    pt_idx = np.asarray(state["pt_idx"], dtype=np.uint8)
    wli = state["wli"]
    direction = state["direction"]
    scorer_stage3_phaseA = dict(state["scorer_stage3_phaseA"])
    scorer_stage3_phaseB = dict(state["scorer_stage3_phaseB"])
    scorer_stage3_phaseA_runtime = state["scorer_stage3_phaseA_runtime"]
    scorer_stage3_search_runtime = state["scorer_stage3_search_runtime"]
    scorer_basin_judge_runtime = state["scorer_basin_judge_runtime"]
    scorer_word_ngram_report_runtime = state.get(
        "scorer_word_ngram_report_runtime",
        None,
    )
    scorer_full_runtime = state["scorer_full_runtime"]
    full_cipher = state["full_cipher"]
    stage2_evals_total = int(state["stage2_evals_total"])
    stage2_continue_to_gate = bool(state["stage2_continue_to_gate"])
    stage2_continue_stop_reason = str(state["stage2_continue_stop_reason"])
    stage3_phaseA_experiment = str(state["stage3_phaseA_experiment"])
    stage3_phaseB_experiment = str(state["stage3_phaseB_experiment"])
    stage3_phaseB_char_pct_min_dynamic = float(state["stage3_phaseB_char_pct_min_dynamic"])
    stage3_phaseB_char_pct_min_source = str(state["stage3_phaseB_char_pct_min_source"])
    oracle_assist_selection_effective = bool(state["oracle_assist_selection_effective"])
    stages = state["stages"]
    stage35_enabled = bool(state["STAGE35_ENABLED"])
    stage35_baseline_selector = normalize_stage35_baseline_selector(
        state.get("STAGE35_BASELINE_SELECTOR", "legacy")
    )
    stage35_cfg = dict(state["STAGE35_CFG"])

    best3_match, best3_score, stop_reason = float("nan"), float("nan"), "completed_pipeline"
    ev3 = 0
    stage2_gap_to_oracle = float("nan")
    stage3_band_name = ""
    pt3 = np.asarray([], dtype=np.uint8)
    best3_key: list[int] | None = None
    stage3_topk_payload: list[Dict[str, Any]] = []
    stage3_init_target = 0
    stage3_init_actual = 0
    stage3_promoted_keys_count = 0
    stage3_gate_source = ""
    stage3_entry_allocation_policy = "legacy_fixed_budget"
    stage3_entry_base_budget = 0
    stage3_entry_target_before_cap = 0
    stage3_entry_cap = 0
    stage3_entry_cap_applied = 0
    stage3_entry_mutations_per_promoted_cfg = 0
    stage3_entry_mutation_calls_per_promoted = 0
    stage3_phaseB_top_n_cfg = 0
    stage3_phaseB_gate_delta_cfg = float("nan")
    stage3_phaseB_gate_end_gain_cfg = float("nan")
    stage3_solve_hits = 0
    stage3_period_init_mult = 1.0
    stage3_period_step_mult = 1.0
    stage3_period_restart_bonus = 0
    stage3_span_active_rate = 0.0
    stage3_span_active_rate_source = "solver_run_telemetry_zero_total"
    stage3_span_eval_total = 0.0
    stage3_span_eval_active = 0.0
    stage3_span_eval_skipped = 0.0
    stage3_span_seconds_total = 0.0
    stage3_span_seconds_active = 0.0
    stage3_span_phaseA_eval_total = 0.0
    stage3_span_phaseA_eval_active = 0.0
    stage3_span_phaseA_eval_skipped = 0.0
    stage3_span_phaseA_seconds_total = 0.0
    stage3_span_phaseA_seconds_active = 0.0
    stage3_span_full_eval_total = 0.0
    stage3_span_full_eval_active = 0.0
    stage3_span_full_eval_skipped = 0.0
    stage3_span_full_seconds_total = 0.0
    stage3_span_full_seconds_active = 0.0
    stage3_span_basin_judge_k_cfg = int(max(1, int(stage3_span_basin_judge_k)))
    stage3_span_basin_judge_k_used = 0
    stage3_span_basin_judge_seconds = 0.0
    stage3_basin_judge_span_calls_total = 0
    stage3_basin_judge_span_calls_active = 0
    stage3_basin_judge_span_calls_rejected_or_gated = 0
    stage3_basin_judge_span_seconds_total = 0.0
    stage3_basin_judge_unique_end_hash = 0
    stage3_word_ngram_rows_scored = 0
    stage3_word_ngram_rows_active = 0
    stage3_scan_phaseA_only = False
    stage35_requested_cfg = int(1 if bool(stage35_enabled) else 0)
    stage35_enabled_cfg = int(1 if bool(stage35_enabled) else 0)
    stage35_ran = 0
    stage35_selected = 0
    stage35_seed_count = 0
    stage35_tail_mismatch_count = 0
    stage35_seed_source_counts: Dict[str, int] = {}
    stage35_archive_count = 0
    stage35_rounds_completed = 0
    stage35_evals = 0
    stage35_runtime_seconds = 0.0
    stage35_archive_unique_keys = 0
    stage35_archive_unique_seed_sources = 0
    stage35_archive_unique_target_slices = 0
    stage35_archive_mean_substitution_hamming = 0.0
    stage35_archive_max_substitution_hamming = 0
    stage35_phasec_score_winner_candidate_hash = ""
    stage35_phasec_score_winner_candidate_source = ""
    stage35_phasec_score_winner_candidate_lane = ""
    stage35_phasec_score_winner_candidate_final_score = float("nan")
    stage35_phasec_score_winner_candidate_final_match = float("nan")
    stage35_baseline_candidate_hash = ""
    stage35_baseline_candidate_source = ""
    stage35_baseline_candidate_lane = ""
    stage35_baseline_candidate_source_rank = 0
    stage35_baseline_candidate_final_score = float("nan")
    stage35_baseline_candidate_final_match = float("nan")
    stage35_baseline_differs_from_phasec_score_winner = 0
    stage35_baseline_search_score = float("nan")
    stage35_accept_score_min_gain_cfg = 0.0
    stage35_accept_search_score_max_drop_cfg = 0.0
    stage35_accept_passed = 0
    stage35_accept_reason = ""
    stage35_mini_search_keep_all_rows_cfg = 0
    stage35_mini_search_collected_rows = 0
    stage35_mini_search_rows_kept = 0
    stage35_best_score = float("nan")
    stage35_best_search_score = float("nan")
    stage35_best_seed_source = ""
    stage35_best_stage3_source = ""
    stage35_best_lane = ""
    stage35_best_source_rank = 0
    stage35_best_target_slice: int | None = None
    stage35_best_depth = 0
    stage35_best_move_type = ""
    stage35_best_candidate_hash = ""
    stage35_best_match = float("nan")
    stage35_truth_gain_vs_selected_row = float("nan")
    stage35_truth_gain_vs_phasec_score_winner = float("nan")
    stage35_best_key: list[int] | None = None
    stage35_best_plaintext_idx: list[int] | None = None
    stage35_archive_rows: list[Dict[str, Any]] = []
    stage35_seed_rows: list[Dict[str, Any]] = []
    stage35_outcome_status = ""
    stage35_outcome_reason = ""
    stage35_completed = 0
    stage35_capped = 0
    stage35_partial_state_name = ""
    stage35_progress_jsonl_name = ""
    stage35_progress_event_count = 0
    stage35_partial_dump_write_count = 0
    stage35_telemetry_summary: Dict[str, Any] = {}
    stage2_resume_live: Dict[str, Any] | None = None
    stage3_prep_live: Dict[str, Any] | None = None
    stage35_proof_valid = int(1 if int(stage35_requested_cfg) == 0 else 0)
    stage35_proof_invalid_reason = ""

    tier_elapsed_before_stage3 = float(time.time() - t0_i)
    stage3_policy = evaluate_stage3_entry_policy_fn(
        tier=tier,
        text_id=int(text_id),
        key_seed=int(key_seed),
        best2_match=float(best2_match),
        stage2_continue_to_gate=bool(stage2_continue_to_gate),
        stage2_continue_stop_reason=str(stage2_continue_stop_reason),
        tier_elapsed_before_stage3=float(tier_elapsed_before_stage3),
        stages=stages,
    )
    stop_reason = str(stage3_policy.get("stop_reason", stop_reason))
    stage3_band_name = str(stage3_policy.get("stage3_band_name", stage3_band_name))
    stage3_scan_phaseA_only = bool(stage3_policy.get("stage3_scan_phaseA_only", False))
    stage3_policy_branch = str(stage3_policy.get("policy_branch", "continue"))
    if stage3_policy_branch == "continue" and best2_key is not None:
        stage3_prep = prepare_stage3_refine_inputs_fn(
            tier=tier,
            key_len=int(key_len),
            key_seed=int(key_seed),
            best2_key=best2_key,
            best2_match=float(best2_match),
            stage2_promoted=stage2_promoted,
            stage2_entry_score=float(stage2_entry_score),
            stage2_entry_score_judge=float(stage2_entry_score_judge),
            scorer_stage2=dict(scorer_stage2),
            scorer_full=dict(scorer_full),
            oracle_s3=float(oracle_s3),
            oracle_decision_paths_enabled=bool(oracle_decision_paths_enabled),
        )
        best2_score_live = float(state.get("best2_score", float("nan")))
        best2_pt_live = list(map(int, state.get("best2_pt", []) or []))
        best2_preview_live = str(state.get("best2_preview", "") or "")
        best2_key_tuple = tuple(int(x) for x in list(best2_key or []) or [])
        if best2_key_tuple:
            for promoted_entry in list(stage2_promoted):
                entry_key = tuple(
                    int(x)
                    for x in list(
                        promoted_entry.get("key", promoted_entry.get("key_idx", [])) or []
                    )
                )
                if entry_key != best2_key_tuple:
                    continue
                if not best2_pt_live:
                    best2_pt_live = list(
                        map(
                            int,
                            promoted_entry.get(
                                "plaintext",
                                promoted_entry.get(
                                    "plaintext_idx",
                                    promoted_entry.get("pt", []),
                                ),
                            )
                            or [],
                        )
                    )
                if not np.isfinite(best2_score_live):
                    best2_score_live = float(
                        promoted_entry.get("score", float("nan"))
                    )
                if not best2_preview_live:
                    best2_preview_live = str(
                        promoted_entry.get("preview", "") or ""
                    )
                break
        stage2_resume_live = dict(
            best2_key=list(map(int, best2_key or [])),
            best2_pt=list(best2_pt_live),
            best2_score=float(best2_score_live),
            best2_match=float(best2_match),
            best2_preview=str(best2_preview_live),
            stage2_promoted=[dict(row) for row in list(stage2_promoted)],
            stage2_entry_score=float(stage2_entry_score),
            stage2_entry_score_judge=float(stage2_entry_score_judge),
            stage2_topk_row_count=int(len(list(state.get("stage2_topk_payload", []) or []))),
            stage2_promote_top_cfg=int(len(list(stage2_promoted))),
            stage2_promoted_from_topk_count=int(len(list(stage2_promoted))),
        )
        stage3_prep_live = dict(stage3_prep)
        c1_focus_enabled = bool(stage3_prep.get("c1_focus_enabled", False))
        init3_n = int(stage3_prep.get("init3_n", 1))
        init3 = list(stage3_prep.get("init3", []))
        promoted_keys = list(stage3_prep.get("promoted_keys", []))
        stage3_promoted_keys_count = int(stage3_prep.get("stage3_promoted_keys_count", len(promoted_keys)))
        stage3_init_target = int(init3_n)
        stage3_init_actual = int(len(init3))
        stage3_entry_allocation_policy = str(
            stage3_prep.get("stage3_entry_allocation_policy", "legacy_fixed_budget")
        )
        stage3_entry_base_budget = int(stage3_prep.get("stage3_entry_base_budget", init3_n))
        stage3_entry_target_before_cap = int(
            stage3_prep.get("stage3_entry_target_before_cap", init3_n)
        )
        stage3_entry_cap = int(stage3_prep.get("stage3_entry_cap", 0))
        stage3_entry_cap_applied = int(
            1 if bool(stage3_prep.get("stage3_entry_cap_applied", False)) else 0
        )
        stage3_entry_mutations_per_promoted_cfg = int(
            stage3_prep.get("stage3_entry_mutations_per_promoted_cfg", 0)
        )
        stage3_entry_mutation_calls_per_promoted = int(
            stage3_prep.get("stage3_entry_mutation_calls_per_promoted", 0)
        )
        stage3_period_init_mult = float(stage3_prep.get("stage3_period_init_mult", 1.0))
        stage3_period_step_mult = float(stage3_prep.get("stage3_period_step_mult", 1.0))
        stage3_period_restart_bonus = int(stage3_prep.get("stage3_period_restart_bonus", 0))
        stage2_gap_to_oracle = float(stage3_prep.get("stage2_gap_to_oracle", float("nan")))
        stage2_gate_score = float(stage3_prep.get("stage2_gate_score", stage2_entry_score))
        stage2_gate_source = str(stage3_prep.get("stage2_gate_source", "mid"))
        stage3_gate_source = str(stage2_gate_source)
        promoted_best_match = float(stage3_prep.get("promoted_best_match", float("nan")))
        if bool(stage3_prep.get("oracle_used_for_stage3_band", False)):
            mark_oracle_decision_use_fn()
        stage3_band_name = str(stage3_prep.get("stage3_band_name", stage3_band_name))
        stage3_phaseA_cfg = dict(stage3_prep.get("stage3_phaseA_cfg", dict(stage3_phasea_cfg_default)))
        stage3_phaseB_cfg = dict(stage3_prep.get("stage3_phaseB_cfg", dict(stage3_phaseb_cfg_default)))
        stage3_phaseB_top_n = int(stage3_prep.get("stage3_phaseB_top_n", int(stage3_phaseb_top_n_default)))
        stage3_phaseB_gate_delta = float(
            stage3_prep.get("stage3_phaseB_gate_delta", float(stage3_phaseb_gate_delta_floor_default))
        )
        stage3_phaseB_gate_end_gain = float(
            stage3_prep.get(
                "stage3_phaseB_gate_end_gain",
                float(stage3_phaseb_gate_end_gain_floor_default),
            )
        )
        stage3_phaseB_top_n_cfg = int(stage3_phaseB_top_n)
        stage3_phaseB_gate_delta_cfg = float(stage3_phaseB_gate_delta)
        stage3_phaseB_gate_end_gain_cfg = float(stage3_phaseB_gate_end_gain)
        solver_stage3_cfg = dict(stage3_prep.get("solver_stage3_cfg", dict(solver_stage3_default_cfg)))
        print(
            f"{log_prefix} stage3-stop tier={tier.name} text={text_id} key_seed={key_seed} "
            f"band={stage3_band_name} entry_mode=full "
            f"entry_policy={stage3_entry_allocation_policy} "
            f"entry_base_budget={int(stage3_entry_base_budget)} "
            f"entry_target_before_cap={int(stage3_entry_target_before_cap)} "
            f"entry_cap={int(stage3_entry_cap)} "
            f"entry_cap_applied={int(stage3_entry_cap_applied)} "
            f"entry_mutations_per_promoted_cfg={int(stage3_entry_mutations_per_promoted_cfg)} "
            f"entry_mutation_calls_per_promoted={int(stage3_entry_mutation_calls_per_promoted)} "
            f"entry_score={stage2_gate_score:.6f} "
            f"entry_score_source={stage2_gate_source} "
            f"init_keys={len(init3)} promoted_keys={len(promoted_keys)} "
            f"init_target={int(init3_n)} c1_focus={1 if c1_focus_enabled else 0} "
            f"period_scale=(init={float(stage3_period_init_mult):.2f},"
            f"steps={float(stage3_period_step_mult):.2f},"
            f"restart_bonus={int(stage3_period_restart_bonus)}) "
            f"stage2_best_match={float(best2_match):.3f} promoted_best_match={float(promoted_best_match):.3f} "
            f"steps={solver_stage3_cfg.get('steps')} restarts={solver_stage3_cfg.get('restarts')} "
            f"col_batch={solver_stage3_cfg.get('col_batch')} inner_batch={solver_stage3_cfg.get('inner_batch')} "
            f"gap_to_oracle={stage2_gap_to_oracle:.6f}",
            flush=True,
        )
        if bool(stage3_two_phase_enabled):
            print(
                f"{log_prefix} stage3-two-phase "
                f"phaseA={json.dumps(dict(stage3_phaseA_cfg), separators=(',', ':'))} "
                f"phaseB={json.dumps(dict(stage3_phaseB_cfg), separators=(',', ':'))} "
                f"phaseB_top_n={int(stage3_phaseB_top_n)} "
                f"scan_phaseA_only={1 if bool(stage3_scan_phaseA_only) else 0} "
                f"continue_after_solve={1 if bool(stage3_continue_after_solve) else 0} "
                f"gate=(delta={float(stage3_phaseB_gate_delta):.4f},"
                f"end_gain={float(stage3_phaseB_gate_end_gain):.4f})",
                flush=True,
            )
        print(
            f"{log_prefix} tier-heartbeat tier={tier.name} stage=stage3_start "
            f"text={text_id} key_seed={key_seed} elapsed={float(time.time() - t0_i):.1f}s "
            f"stage2_match={fmt_finite_float_fn(best2_match, digits=3)} "
            f"stage2_evals={int(stage2_evals_total)} "
            f"interval={float(tier_heartbeat_seconds):.0f}s",
            flush=True,
        )
        dt3 = 0.0
        ev3 = 0
        phaseB_ran = 0
        phaseB_skipped = 0
        phaseB_top_n_used = 0
        phaseB_skip_reason = ""
        phaseB_family_preservation_policy = "off"
        phaseB_family_view_id = "prefix_hamming_le_24"
        phaseB_family_reserved_slots = 0
        phaseB_family_count_in_top_band = 0
        phaseB_family_preserved_count = 0
        phaseB_family_reservation_applied = 0
        phaseB_selected_unique_end_hash = 0
        phaseB_downstream_selected_count = 0
        phaseB_downstream_selected_unique_end_hash = 0
        phaseB_topk_saved_count = 0
        phaseB_topk_saved_unique_end_hash = 0
        phaseC_enabled_cfg = 0
        phaseC_enabled_effective = 0
        phaseC_ran = 0
        phaseC_start_keys_used = 0
        phaseC_steps_cfg = 0
        phaseC_proposals_per_step_cfg = 0
        phaseC_lexical_min_match_cfg = float("nan")
        phaseC_evals = 0
        phaseC_accepts = 0
        phaseC_improves = 0
        phaseC_rescue_enabled_cfg = 0
        phaseC_rescue_ran = 0
        phaseC_rescue_starts_attempted = 0
        phaseC_rescue_applied_starts = 0
        phaseC_rescue_target_mode_cfg = "slice_probe"
        phaseC_rescue_selector_mode_cfg = "rescue_shallow_then_search"
        phaseC_rescue_candidates_cfg = 0
        phaseC_rescue_slip_swaps_cfg = 0
        phaseC_rescue_mini_search_steps_cfg = 0
        phaseC_rescue_mini_search_beam_width_cfg = 0
        phaseC_rescue_mini_search_top_symbols_cfg = 0
        phaseC_rescue_mini_search_keep_all_rows_cfg = 0
        phaseC_rescue_polish_steps_cfg = 0
        phaseC_rescue_probe_evals = 0
        phaseC_rescue_evals = 0
        phaseC_rescue_mini_search_evals = 0
        phaseC_rescue_lexical_requests = 0
        phaseC_rescue_lexical_cache_hits = 0
        phaseC_rescue_lexical_cache_misses = 0
        phaseC_rescue_lexical_tiebreak_decisions = 0
        phaseC_rescue_lexical_budget_skips = 0
        phaseC_rescue_lexical_threshold_skips = 0
        phaseC_rescue_anchor_enabled_cfg = 0
        phaseC_rescue_phaseb_topk_min_rank_cfg = 2
        phaseC_rescue_max_starts_cfg = 0
        phaseC_rescue_eligible_starts = 0
        phaseC_rescue_search_score_max_drop_cfg = 0.0
        phaseC_rescue_guard_search_evals = 0
        phaseC_rescue_guard_search_passes = 0
        phaseC_rescue_guard_search_rejects = 0
        phaseC_lexical_requests = 0
        phaseC_lexical_cache_hits = 0
        phaseC_lexical_cache_misses = 0
        phaseC_lexical_tiebreak_decisions = 0
        phaseC_lexical_budget_skips = 0
        phaseC_lexical_threshold_skips = 0
        phaseC_candidate_pool_count = 0
        phaseC_candidate_pool_unique_keys = 0
        phaseC_candidate_pool_unique_end_hash = 0
        phaseC_candidate_pool_rows: list[Dict[str, Any]] = []
        phaseC_start_policy = str(state["STAGE3_PHASEC_START_POLICY"])
        phaseC_candidate_pool_source_counts: Dict[str, int] = {}
        phaseC_novel_view_id = ""
        phaseC_anchor_candidate_hash = ""
        phaseC_candidate_pool_eligible_novel_count = 0
        phaseC_candidate_pool_eligible_novel_row_count = 0
        phaseC_candidate_pool_eligible_novel_source_counts: Dict[str, int] = {}
        phaseC_start_source_counts: Dict[str, int] = {}
        phaseC_start_unique_end_hash = 0
        phaseC_start_eligible_novel_count = 0
        phaseC_selected_novel_challenger_count = 0
        phaseC_eligible_novel_not_selected_count = 0
        phaseC_selected_novel_challenger_hashes: list[str] = []
        phaseC_improved_best = 0
        phaseC_checkpoint_jsonl_name = ""
        phaseC_checkpoint_rows_written = 0
        phaseC_anchor_lane_starts = 0
        phaseC_challenger_lane_starts = 0
        phaseC_challenger_overtook_anchor_count = 0
        phaseC_final_winner_lane = ""
        phaseC_final_winner_source = ""
        phaseC_start_summaries: list[Dict[str, Any]] = []
        stage3_hb_state: Dict[str, Any] = dict(last_emit_ts=float("-inf"))
        stage3_phaseA_hb_state: Dict[str, Any] = dict(last_emit_ts=float("-inf"))

        if not bool(stage3_two_phase_enabled):
            single_phase = run_stage3_single_phase_call(
                ctx=stage3_runtime_call_ctx,
                tier_name=str(tier.name),
                tier_period=int(tier.period),
                tier_columns=int(tier.columns),
                text_id=int(text_id),
                key_seed=int(key_seed),
                ct_idx=np.asarray(ct_idx, dtype=np.uint8),
                pt_idx=np.asarray(pt_idx, dtype=np.uint8),
                key_len=int(key_len),
                init3=init3,
                solver_stage3_cfg=dict(solver_stage3_cfg),
                scorer_stage3_phaseB=dict(scorer_stage3_phaseB),
                scorer_full_runtime=scorer_full_runtime,
                direction=direction,
                ev3_base=int(ev3),
                stage3_hb_state=stage3_hb_state,
            )
            dt3 += float(single_phase["dt3"])
            ev3 += int(single_phase["ev3"])
            pt3 = np.asarray(single_phase["pt3"], dtype=np.uint8).reshape(-1)
            best3_key = single_phase.get("best3_key", best3_key)
            best3_match = float(single_phase["best3_match"])
            best3_score = float(single_phase["best3_score"])
            stage3_solve_hits += int(1 if bool(single_phase.get("stage3_solve_hit", False)) else 0)
            stage3_span_full_eval_total += float(single_phase["span_total"])
            stage3_span_full_eval_active += float(single_phase["span_active"])
            stage3_span_full_eval_skipped += float(single_phase["span_skipped"])
            stage3_span_full_seconds_total += float(single_phase["span_seconds_total"])
            stage3_span_full_seconds_active += float(single_phase["span_seconds_active"])
            stage3_runtime_call_ctx.append_stage3_topk_from_kaeding_fn(
                payload=stage3_topk_payload,
                kaeding_obj=single_phase.get("kaeding3", {}),
                key_len=int(key_len),
                full_cipher=full_cipher,
                ciphertext=np.asarray(ct_idx, dtype=np.uint8),
                scorer_full_runtime=scorer_full_runtime,
                target_plaintext=np.asarray(pt_idx, dtype=np.uint8),
            )
        else:
            base_seed = int(solver_stage3_cfg.get("seed", solver_stage3_default_cfg.get("seed", 2026)))
            phaseA_cfg = dict(solver_stage3_cfg)
            phaseA_cfg.update(dict(stage3_phaseA_cfg))
            phaseA_cfg["restarts"] = 1
            phaseA_cfg["seed_restarts"] = 0
            phasea_restarts = run_stage3_phasea_restarts_call(
                ctx=stage3_runtime_call_ctx,
                tier_name=str(tier.name),
                tier_period=int(tier.period),
                tier_columns=int(tier.columns),
                text_id=int(text_id),
                key_seed=int(key_seed),
                key_len=int(key_len),
                init3=init3,
                base_seed=int(base_seed),
                ct_idx=np.asarray(ct_idx, dtype=np.uint8),
                pt_idx=np.asarray(pt_idx, dtype=np.uint8),
                full_cipher=full_cipher,
                direction=direction,
                phaseA_cfg=dict(phaseA_cfg),
                scorer_stage3_phaseA=dict(scorer_stage3_phaseA),
                scorer_stage3_phaseA_runtime=scorer_stage3_phaseA_runtime,
                stage3_phaseA_hb_state=stage3_phaseA_hb_state,
            )
            phaseA_rows = list(phasea_restarts.get("phaseA_rows", []))
            phase_stage_rows = [dict(stage_row) for stage_row in phasea_restarts.get("stage_rows", [])]
            stage3_solve_hits += int(phasea_restarts.get("stage3_solve_hits_delta", 0))
            dt3 += float(phasea_restarts.get("dt3_delta", 0.0))
            ev3 += int(phasea_restarts.get("ev3_delta", 0))
            stage3_span_phaseA_eval_total += float(phasea_restarts.get("span_phaseA_eval_total", 0.0))
            stage3_span_phaseA_eval_active += float(phasea_restarts.get("span_phaseA_eval_active", 0.0))
            stage3_span_phaseA_eval_skipped += float(phasea_restarts.get("span_phaseA_eval_skipped", 0.0))
            stage3_span_phaseA_seconds_total += float(phasea_restarts.get("span_phaseA_seconds_total", 0.0))
            stage3_span_phaseA_seconds_active += float(phasea_restarts.get("span_phaseA_seconds_active", 0.0))
            two_phase_followup = run_stage3_two_phase_followup_call(
                ctx=stage3_runtime_call_ctx,
                tier_name=str(tier.name),
                tier_period=int(tier.period),
                tier_columns=int(tier.columns),
                text_id=int(text_id),
                key_seed=int(key_seed),
                key_len=int(key_len),
                ct_idx=np.asarray(ct_idx, dtype=np.uint8),
                pt_idx=np.asarray(pt_idx, dtype=np.uint8),
                direction=direction,
                oracle_assist_selection_effective=bool(oracle_assist_selection_effective),
                stage3_phaseA_experiment=str(stage3_phaseA_experiment),
                stage3_phaseB_experiment=str(stage3_phaseB_experiment),
                stage3_phaseB_char_pct_min_dynamic=float(stage3_phaseB_char_pct_min_dynamic),
                stage3_phaseB_char_pct_min_source=str(stage3_phaseB_char_pct_min_source),
                phaseA_rows=phaseA_rows,
                stage_rows=phase_stage_rows,
                scorer_stage3_search_runtime=scorer_stage3_search_runtime,
                scorer_basin_judge_runtime=scorer_basin_judge_runtime,
                scorer_word_ngram_report_runtime=scorer_word_ngram_report_runtime,
                scorer_full_runtime=scorer_full_runtime,
                scorer_stage3_phaseB=dict(scorer_stage3_phaseB),
                solver_stage3_cfg=dict(solver_stage3_cfg),
                stage3_phaseB_cfg=dict(stage3_phaseB_cfg),
                stage3_phaseB_top_n=int(stage3_phaseB_top_n),
                stage3_phaseB_gate_delta=float(stage3_phaseB_gate_delta),
                stage3_phaseB_gate_end_gain=float(stage3_phaseB_gate_end_gain),
                stage3_scan_phaseA_only=bool(stage3_scan_phaseA_only),
                stage3_span_basin_judge_k_cfg=int(stage3_span_basin_judge_k_cfg),
                base_seed=int(base_seed),
                ev3_base=int(ev3),
                stage3_hb_state=stage3_hb_state,
                stage3_topk_payload=stage3_topk_payload,
                full_cipher=full_cipher,
            )
            two_phase_followup = dict(two_phase_followup or {})
            two_phase_followup.setdefault(
                "phaseC_start_policy",
                str(phaseC_start_policy),
            )
            two_phase_followup.setdefault(
                "phaseC_final_winner_lane",
                str(phaseC_final_winner_lane),
            )
            two_phase_followup.setdefault(
                "phaseC_final_winner_source",
                str(phaseC_final_winner_source),
            )
            two_phase_followup.setdefault(
                "phaseC_start_summaries",
                [dict(row) for row in list(phaseC_start_summaries)],
            )
            require_phasec_diagnostics_contract(
                two_phase_followup,
                context="stage3_iteration_flow.two_phase_followup",
            )
            for stage_row in two_phase_followup.get("stage_rows", []):
                stages.append(dict(stage_row))
            dt3 += float(two_phase_followup.get("dt3_delta", 0.0))
            ev3 += int(two_phase_followup.get("ev3_delta", 0))
            stage3_solve_hits += int(two_phase_followup.get("stage3_solve_hits_delta", 0))
            stage3_span_full_eval_total += float(two_phase_followup.get("stage3_span_full_eval_total", 0.0))
            stage3_span_full_eval_active += float(two_phase_followup.get("stage3_span_full_eval_active", 0.0))
            stage3_span_full_eval_skipped += float(two_phase_followup.get("stage3_span_full_eval_skipped", 0.0))
            stage3_span_full_seconds_total += float(two_phase_followup.get("stage3_span_full_seconds_total", 0.0))
            stage3_span_full_seconds_active += float(two_phase_followup.get("stage3_span_full_seconds_active", 0.0))
            phaseB_ran = int(two_phase_followup.get("phaseB_ran", phaseB_ran))
            phaseB_skipped = int(two_phase_followup.get("phaseB_skipped", phaseB_skipped))
            phaseB_skip_reason = str(two_phase_followup.get("phaseB_skip_reason", phaseB_skip_reason))
            phaseB_top_n_used = int(two_phase_followup.get("phaseB_top_n_used", phaseB_top_n_used))
            phaseB_family_preservation_policy = str(
                two_phase_followup.get(
                    "phaseB_family_preservation_policy",
                    phaseB_family_preservation_policy,
                )
            )
            phaseB_family_view_id = str(
                two_phase_followup.get(
                    "phaseB_family_view_id",
                    phaseB_family_view_id,
                )
            )
            phaseB_family_reserved_slots = int(
                two_phase_followup.get(
                    "phaseB_family_reserved_slots",
                    phaseB_family_reserved_slots,
                )
            )
            phaseB_family_count_in_top_band = int(
                two_phase_followup.get(
                    "phaseB_family_count_in_top_band",
                    phaseB_family_count_in_top_band,
                )
            )
            phaseB_family_preserved_count = int(
                two_phase_followup.get(
                    "phaseB_family_preserved_count",
                    phaseB_family_preserved_count,
                )
            )
            phaseB_family_reservation_applied = int(
                two_phase_followup.get(
                    "phaseB_family_reservation_applied",
                    phaseB_family_reservation_applied,
                )
            )
            phaseB_selected_unique_end_hash = int(
                two_phase_followup.get(
                    "phaseB_selected_unique_end_hash",
                    phaseB_selected_unique_end_hash,
                )
            )
            phaseB_downstream_selected_count = int(
                two_phase_followup.get(
                    "phaseB_downstream_selected_count",
                    phaseB_downstream_selected_count,
                )
            )
            phaseB_downstream_selected_unique_end_hash = int(
                two_phase_followup.get(
                    "phaseB_downstream_selected_unique_end_hash",
                    phaseB_downstream_selected_unique_end_hash,
                )
            )
            phaseB_topk_saved_count = int(
                two_phase_followup.get("phaseB_topk_saved_count", phaseB_topk_saved_count)
            )
            phaseB_topk_saved_unique_end_hash = int(
                two_phase_followup.get(
                    "phaseB_topk_saved_unique_end_hash",
                    phaseB_topk_saved_unique_end_hash,
                )
            )
            phaseC_enabled_cfg = int(
                two_phase_followup.get("phaseC_enabled_cfg", phaseC_enabled_cfg)
            )
            phaseC_enabled_effective = int(
                two_phase_followup.get(
                    "phaseC_enabled_effective",
                    phaseC_enabled_effective,
                )
            )
            phaseC_ran = int(two_phase_followup.get("phaseC_ran", phaseC_ran))
            phaseC_start_keys_used = int(
                two_phase_followup.get(
                    "phaseC_start_keys_used",
                    phaseC_start_keys_used,
                )
            )
            phaseC_start_policy = str(
                two_phase_followup.get("phaseC_start_policy", phaseC_start_policy)
            )
            phaseC_steps_cfg = int(two_phase_followup.get("phaseC_steps_cfg", phaseC_steps_cfg))
            phaseC_proposals_per_step_cfg = int(
                two_phase_followup.get(
                    "phaseC_proposals_per_step_cfg",
                    phaseC_proposals_per_step_cfg,
                )
            )
            phaseC_lexical_min_match_cfg = float(
                two_phase_followup.get(
                    "phaseC_lexical_min_match_cfg",
                    phaseC_lexical_min_match_cfg,
                )
            )
            phaseC_evals = int(two_phase_followup.get("phaseC_evals", phaseC_evals))
            phaseC_accepts = int(two_phase_followup.get("phaseC_accepts", phaseC_accepts))
            phaseC_improves = int(two_phase_followup.get("phaseC_improves", phaseC_improves))
            phaseC_rescue_enabled_cfg = int(
                two_phase_followup.get(
                    "phaseC_rescue_enabled_cfg",
                    phaseC_rescue_enabled_cfg,
                )
            )
            phaseC_rescue_ran = int(
                two_phase_followup.get("phaseC_rescue_ran", phaseC_rescue_ran)
            )
            phaseC_rescue_starts_attempted = int(
                two_phase_followup.get(
                    "phaseC_rescue_starts_attempted",
                    phaseC_rescue_starts_attempted,
                )
            )
            phaseC_rescue_applied_starts = int(
                two_phase_followup.get(
                    "phaseC_rescue_applied_starts",
                    phaseC_rescue_applied_starts,
                )
            )
            phaseC_rescue_target_mode_cfg = str(
                two_phase_followup.get(
                    "phaseC_rescue_target_mode_cfg",
                    phaseC_rescue_target_mode_cfg,
                )
            )
            phaseC_rescue_selector_mode_cfg = str(
                two_phase_followup.get(
                    "phaseC_rescue_selector_mode_cfg",
                    phaseC_rescue_selector_mode_cfg,
                )
            )
            phaseC_rescue_candidates_cfg = int(
                two_phase_followup.get(
                    "phaseC_rescue_candidates_cfg",
                    phaseC_rescue_candidates_cfg,
                )
            )
            phaseC_rescue_slip_swaps_cfg = int(
                two_phase_followup.get(
                    "phaseC_rescue_slip_swaps_cfg",
                    phaseC_rescue_slip_swaps_cfg,
                )
            )
            phaseC_rescue_mini_search_steps_cfg = int(
                two_phase_followup.get(
                    "phaseC_rescue_mini_search_steps_cfg",
                    phaseC_rescue_mini_search_steps_cfg,
                )
            )
            phaseC_rescue_mini_search_beam_width_cfg = int(
                two_phase_followup.get(
                    "phaseC_rescue_mini_search_beam_width_cfg",
                    phaseC_rescue_mini_search_beam_width_cfg,
                )
            )
            phaseC_rescue_mini_search_top_symbols_cfg = int(
                two_phase_followup.get(
                    "phaseC_rescue_mini_search_top_symbols_cfg",
                    phaseC_rescue_mini_search_top_symbols_cfg,
                )
            )
            phaseC_rescue_mini_search_keep_all_rows_cfg = int(
                two_phase_followup.get(
                    "phaseC_rescue_mini_search_keep_all_rows_cfg",
                    phaseC_rescue_mini_search_keep_all_rows_cfg,
                )
            )
            phaseC_rescue_polish_steps_cfg = int(
                two_phase_followup.get(
                    "phaseC_rescue_polish_steps_cfg",
                    phaseC_rescue_polish_steps_cfg,
                )
            )
            phaseC_rescue_probe_evals = int(
                two_phase_followup.get(
                    "phaseC_rescue_probe_evals",
                    phaseC_rescue_probe_evals,
                )
            )
            phaseC_rescue_evals = int(
                two_phase_followup.get("phaseC_rescue_evals", phaseC_rescue_evals)
            )
            phaseC_rescue_mini_search_evals = int(
                two_phase_followup.get(
                    "phaseC_rescue_mini_search_evals",
                    phaseC_rescue_mini_search_evals,
                )
            )
            phaseC_rescue_anchor_enabled_cfg = int(
                two_phase_followup.get(
                    "phaseC_rescue_anchor_enabled_cfg",
                    phaseC_rescue_anchor_enabled_cfg,
                )
            )
            phaseC_rescue_phaseb_topk_min_rank_cfg = int(
                two_phase_followup.get(
                    "phaseC_rescue_phaseb_topk_min_rank_cfg",
                    phaseC_rescue_phaseb_topk_min_rank_cfg,
                )
            )
            phaseC_rescue_max_starts_cfg = int(
                two_phase_followup.get(
                    "phaseC_rescue_max_starts_cfg",
                    phaseC_rescue_max_starts_cfg,
                )
            )
            phaseC_rescue_eligible_starts = int(
                two_phase_followup.get(
                    "phaseC_rescue_eligible_starts",
                    phaseC_rescue_eligible_starts,
                )
            )
            phaseC_rescue_search_score_max_drop_cfg = float(
                two_phase_followup.get(
                    "phaseC_rescue_search_score_max_drop_cfg",
                    phaseC_rescue_search_score_max_drop_cfg,
                )
            )
            phaseC_rescue_guard_search_evals = int(
                two_phase_followup.get(
                    "phaseC_rescue_guard_search_evals",
                    phaseC_rescue_guard_search_evals,
                )
            )
            phaseC_rescue_guard_search_passes = int(
                two_phase_followup.get(
                    "phaseC_rescue_guard_search_passes",
                    phaseC_rescue_guard_search_passes,
                )
            )
            phaseC_rescue_guard_search_rejects = int(
                two_phase_followup.get(
                    "phaseC_rescue_guard_search_rejects",
                    phaseC_rescue_guard_search_rejects,
                )
            )
            phaseC_rescue_lexical_requests = int(
                two_phase_followup.get(
                    "phaseC_rescue_lexical_requests",
                    phaseC_rescue_lexical_requests,
                )
            )
            phaseC_rescue_lexical_cache_hits = int(
                two_phase_followup.get(
                    "phaseC_rescue_lexical_cache_hits",
                    phaseC_rescue_lexical_cache_hits,
                )
            )
            phaseC_rescue_lexical_cache_misses = int(
                two_phase_followup.get(
                    "phaseC_rescue_lexical_cache_misses",
                    phaseC_rescue_lexical_cache_misses,
                )
            )
            phaseC_rescue_lexical_tiebreak_decisions = int(
                two_phase_followup.get(
                    "phaseC_rescue_lexical_tiebreak_decisions",
                    phaseC_rescue_lexical_tiebreak_decisions,
                )
            )
            phaseC_rescue_lexical_budget_skips = int(
                two_phase_followup.get(
                    "phaseC_rescue_lexical_budget_skips",
                    phaseC_rescue_lexical_budget_skips,
                )
            )
            phaseC_rescue_lexical_threshold_skips = int(
                two_phase_followup.get(
                    "phaseC_rescue_lexical_threshold_skips",
                    phaseC_rescue_lexical_threshold_skips,
                )
            )
            phaseC_lexical_requests = int(
                two_phase_followup.get("phaseC_lexical_requests", phaseC_lexical_requests)
            )
            phaseC_lexical_cache_hits = int(
                two_phase_followup.get(
                    "phaseC_lexical_cache_hits",
                    phaseC_lexical_cache_hits,
                )
            )
            phaseC_lexical_cache_misses = int(
                two_phase_followup.get(
                    "phaseC_lexical_cache_misses",
                    phaseC_lexical_cache_misses,
                )
            )
            phaseC_lexical_tiebreak_decisions = int(
                two_phase_followup.get(
                    "phaseC_lexical_tiebreak_decisions",
                    phaseC_lexical_tiebreak_decisions,
                )
            )
            phaseC_lexical_budget_skips = int(
                two_phase_followup.get(
                    "phaseC_lexical_budget_skips",
                    phaseC_lexical_budget_skips,
                )
            )
            phaseC_lexical_threshold_skips = int(
                two_phase_followup.get(
                    "phaseC_lexical_threshold_skips",
                    phaseC_lexical_threshold_skips,
                )
            )
            phaseC_candidate_pool_count = int(
                two_phase_followup.get(
                    "phaseC_candidate_pool_count",
                    phaseC_candidate_pool_count,
                )
            )
            phaseC_candidate_pool_unique_keys = int(
                two_phase_followup.get(
                    "phaseC_candidate_pool_unique_keys",
                    phaseC_candidate_pool_unique_keys,
                )
            )
            phaseC_candidate_pool_unique_end_hash = int(
                two_phase_followup.get(
                    "phaseC_candidate_pool_unique_end_hash",
                    phaseC_candidate_pool_unique_end_hash,
                )
            )
            phaseC_candidate_pool_source_counts = dict(
                two_phase_followup.get(
                    "phaseC_candidate_pool_source_counts",
                    phaseC_candidate_pool_source_counts,
                )
            )
            phaseC_candidate_pool_rows = [
                dict(row)
                for row in list(
                    two_phase_followup.get(
                        "phaseC_candidate_pool_rows",
                        phaseC_candidate_pool_rows,
                    )
                    or []
                )
            ]
            phaseC_novel_view_id = str(
                two_phase_followup.get("phaseC_novel_view_id", phaseC_novel_view_id)
            )
            phaseC_anchor_candidate_hash = str(
                two_phase_followup.get(
                    "phaseC_anchor_candidate_hash",
                    phaseC_anchor_candidate_hash,
                )
            )
            phaseC_candidate_pool_eligible_novel_count = int(
                two_phase_followup.get(
                    "phaseC_candidate_pool_eligible_novel_count",
                    phaseC_candidate_pool_eligible_novel_count,
                )
            )
            phaseC_candidate_pool_eligible_novel_row_count = int(
                two_phase_followup.get(
                    "phaseC_candidate_pool_eligible_novel_row_count",
                    phaseC_candidate_pool_eligible_novel_row_count,
                )
            )
            phaseC_candidate_pool_eligible_novel_source_counts = dict(
                two_phase_followup.get(
                    "phaseC_candidate_pool_eligible_novel_source_counts",
                    phaseC_candidate_pool_eligible_novel_source_counts,
                )
            )
            phaseC_start_source_counts = dict(
                two_phase_followup.get(
                    "phaseC_start_source_counts",
                    phaseC_start_source_counts,
                )
            )
            phaseC_start_unique_end_hash = int(
                two_phase_followup.get(
                    "phaseC_start_unique_end_hash",
                    phaseC_start_unique_end_hash,
                )
            )
            phaseC_start_eligible_novel_count = int(
                two_phase_followup.get(
                    "phaseC_start_eligible_novel_count",
                    phaseC_start_eligible_novel_count,
                )
            )
            phaseC_selected_novel_challenger_count = int(
                two_phase_followup.get(
                    "phaseC_selected_novel_challenger_count",
                    phaseC_selected_novel_challenger_count,
                )
            )
            phaseC_eligible_novel_not_selected_count = int(
                two_phase_followup.get(
                    "phaseC_eligible_novel_not_selected_count",
                    phaseC_eligible_novel_not_selected_count,
                )
            )
            phaseC_selected_novel_challenger_hashes = [
                str(x)
                for x in list(
                    two_phase_followup.get(
                        "phaseC_selected_novel_challenger_hashes",
                        phaseC_selected_novel_challenger_hashes,
                    )
                )
                if str(x)
            ]
            phaseC_improved_best = int(
                two_phase_followup.get("phaseC_improved_best", phaseC_improved_best)
            )
            phaseC_checkpoint_jsonl_name = str(
                two_phase_followup.get(
                    "phaseC_checkpoint_jsonl_name",
                    phaseC_checkpoint_jsonl_name,
                )
            )
            phaseC_checkpoint_rows_written = int(
                two_phase_followup.get(
                    "phaseC_checkpoint_rows_written",
                    phaseC_checkpoint_rows_written,
                )
            )
            phaseC_anchor_lane_starts = int(
                two_phase_followup.get(
                    "phaseC_anchor_lane_starts",
                    phaseC_anchor_lane_starts,
                )
            )
            phaseC_challenger_lane_starts = int(
                two_phase_followup.get(
                    "phaseC_challenger_lane_starts",
                    phaseC_challenger_lane_starts,
                )
            )
            phaseC_challenger_overtook_anchor_count = int(
                two_phase_followup.get(
                    "phaseC_challenger_overtook_anchor_count",
                    phaseC_challenger_overtook_anchor_count,
                )
            )
            phaseC_final_winner_lane = str(
                two_phase_followup.get(
                    "phaseC_final_winner_lane",
                    phaseC_final_winner_lane,
                )
            )
            phaseC_final_winner_source = str(
                two_phase_followup.get(
                    "phaseC_final_winner_source",
                    phaseC_final_winner_source,
                )
            )
            phaseC_start_summaries = [
                dict(row)
                for row in list(
                    two_phase_followup.get("phaseC_start_summaries", phaseC_start_summaries)
                )
            ]
            stage3_span_basin_judge_k_used = int(
                two_phase_followup.get("stage3_span_basin_judge_k_used", stage3_span_basin_judge_k_used)
            )
            stage3_span_basin_judge_seconds = float(
                two_phase_followup.get("stage3_span_basin_judge_seconds", stage3_span_basin_judge_seconds)
            )
            stage3_basin_judge_span_calls_total = int(
                two_phase_followup.get("stage3_basin_judge_span_calls_total", stage3_basin_judge_span_calls_total)
            )
            stage3_basin_judge_span_calls_active = int(
                two_phase_followup.get("stage3_basin_judge_span_calls_active", stage3_basin_judge_span_calls_active)
            )
            stage3_basin_judge_span_calls_rejected_or_gated = int(
                two_phase_followup.get(
                    "stage3_basin_judge_span_calls_rejected_or_gated",
                    stage3_basin_judge_span_calls_rejected_or_gated,
                )
            )
            stage3_basin_judge_span_seconds_total = float(
                two_phase_followup.get("stage3_basin_judge_span_seconds_total", stage3_basin_judge_span_seconds_total)
            )
            stage3_basin_judge_unique_end_hash = int(
                two_phase_followup.get("stage3_basin_judge_unique_end_hash", stage3_basin_judge_unique_end_hash)
            )
            stage3_word_ngram_rows_scored = int(
                two_phase_followup.get(
                    "stage3_word_ngram_rows_scored",
                    stage3_word_ngram_rows_scored,
                )
            )
            stage3_word_ngram_rows_active = int(
                two_phase_followup.get(
                    "stage3_word_ngram_rows_active",
                    stage3_word_ngram_rows_active,
                )
            )
            best3_score = float(two_phase_followup.get("best3_score", best3_score))
            best3_match = float(two_phase_followup.get("best3_match", best3_match))
            best3_key = two_phase_followup.get("best3_key", best3_key)
            pt3 = np.asarray(two_phase_followup.get("pt3", pt3), dtype=np.uint8).reshape(-1)
            stop_reason_update = str(two_phase_followup.get("stop_reason_update", "")).strip()
            if stop_reason_update:
                stop_reason = str(stop_reason_update)

        if bool(stage35_enabled) and best3_key is not None and int(pt3.size) > 0:
            phasec_score_winner_row = select_phasec_score_winner_row(
                phasec_start_summaries=phaseC_start_summaries,
                best3_key=best3_key,
                phasec_final_winner_lane=str(phaseC_final_winner_lane),
                phasec_final_winner_source=str(phaseC_final_winner_source),
            )
            stage35_baseline_row = select_stage35_baseline_row(
                phasec_start_summaries=phaseC_start_summaries,
                selector=str(stage35_baseline_selector),
                phasec_score_winner_row=phasec_score_winner_row,
            )
            stage35_baseline_key = list(
                map(
                    int,
                    stage35_baseline_row.get("final_key_idx", []) or best3_key,
                )
            )
            stage35_baseline_plaintext_idx = list(
                map(
                    int,
                    stage35_baseline_row.get("final_plaintext_idx", [])
                    or np.asarray(pt3, dtype=np.uint8).astype(int).tolist(),
                )
            )
            stage35_baseline_score_raw = stage35_baseline_row.get(
                "final_score",
                best3_score,
            )
            if stage35_baseline_score_raw is None:
                stage35_baseline_score_raw = best3_score
            stage35_baseline_score_value = float(stage35_baseline_score_raw)
            print(
                f"{log_prefix} stage35-start ts={_stage35_wall_ts()} tier={tier.name} text={text_id} key_seed={key_seed} "
                f"selector={stage35_baseline_selector} "
                f"baseline_hash={str(stage35_baseline_row.get('candidate_hash', '') or 'none')} "
                f"baseline_source={str(stage35_baseline_row.get('source', '') or 'none')} "
                f"baseline_lane={str(stage35_baseline_row.get('lane', '') or 'none')} "
                f"baseline_source_rank={int(stage35_baseline_row.get('source_rank', 0) or 0)} "
                f"baseline_score={fmt_finite_float_fn(stage35_baseline_score_value, digits=6)}",
                flush=True,
            )
            phasec_checkpoint_path = getattr(
                stage3_runtime_call_ctx,
                "phasec_start_checkpoint_path",
                None,
            )
            stage35_partial_state_path = None
            stage35_progress_jsonl_path = None
            if phasec_checkpoint_path is not None:
                stage35_dump_dir = Path(phasec_checkpoint_path).parent
                stage35_partial_state_path = (
                    stage35_dump_dir / "stage35_partial_state.json"
                )
                stage35_progress_jsonl_path = (
                    stage35_dump_dir / "stage35_progress.jsonl"
                )
                for dump_path in (
                    stage35_partial_state_path,
                    stage35_progress_jsonl_path,
                ):
                    try:
                        if dump_path.exists():
                            dump_path.unlink()
                    except OSError:
                        pass

            def _emit_stage35_progress(progress: Mapping[str, Any]) -> None:
                event_name = str(progress.get("event", "") or "")
                if event_name == "seed_rows_scored":
                    print(
                        f"{log_prefix} stage35-heartbeat ts={_stage35_wall_ts()} tier={tier.name} text={text_id} key_seed={key_seed} "
                        f"event=seed_rows_scored "
                        f"seed_rows={int(progress.get('seed_rows_scored_count', 0) or 0)} "
                        f"elapsed={fmt_finite_float_fn(progress.get('elapsed_seconds', 0.0), digits=3)}",
                        flush=True,
                    )
                    return
                if event_name == "mini_search_start":
                    print(
                        f"{log_prefix} stage35-heartbeat ts={_stage35_wall_ts()} tier={tier.name} text={text_id} key_seed={key_seed} "
                        f"event=mini_search_start "
                        f"round={int(progress.get('round_idx', 0) or 0)}/{int(progress.get('rounds_total', 0) or 0)} "
                        f"mini={int(progress.get('mini_search_index_round', 0) or 0)}/{int(progress.get('mini_searches_planned_round', 0) or 0)} "
                        f"slice={int(progress.get('slice_idx', 0) or 0)} "
                        f"parent_hash={str(progress.get('parent_candidate_hash', '') or 'none')} "
                        f"beam={int(progress.get('beam_rows_count', 0) or 0)} "
                        f"archive={int(progress.get('archive_rows_count', 0) or 0)} "
                        f"evals={int(progress.get('total_evals', 0) or 0)} "
                        f"elapsed={fmt_finite_float_fn(progress.get('elapsed_seconds', 0.0), digits=3)}",
                        flush=True,
                    )
                    return
                if event_name == "round_progress":
                    print(
                        f"{log_prefix} stage35-heartbeat ts={_stage35_wall_ts()} tier={tier.name} text={text_id} key_seed={key_seed} "
                        f"event=round_progress "
                        f"round={int(progress.get('round_idx', 0) or 0)}/{int(progress.get('rounds_total', 0) or 0)} "
                        f"mini={int(progress.get('mini_searches_done_round', 0) or 0)}/{int(progress.get('mini_searches_planned_round', 0) or 0)} "
                        f"beam={int(progress.get('beam_rows_count', 0) or 0)} "
                        f"archive={int(progress.get('archive_rows_count', 0) or 0)} "
                        f"evals={int(progress.get('total_evals', 0) or 0)} "
                        f"elapsed={fmt_finite_float_fn(progress.get('elapsed_seconds', 0.0), digits=3)}",
                        flush=True,
                    )
                    return
                if event_name == "round_archive_snapshot":
                    print(
                        f"{log_prefix} stage35-heartbeat ts={_stage35_wall_ts()} tier={tier.name} text={text_id} key_seed={key_seed} "
                        f"event=round_archive_snapshot "
                        f"round={int(progress.get('round_idx', 0) or 0)}/{int(progress.get('rounds_total', 0) or 0)} "
                        f"beam={int(progress.get('beam_rows_count', 0) or 0)} "
                        f"archive={int(progress.get('archive_rows_count', 0) or 0)} "
                        f"evals={int(progress.get('total_evals', 0) or 0)} "
                        f"elapsed={fmt_finite_float_fn(progress.get('elapsed_seconds', 0.0), digits=3)} "
                        f"outcome_status={str(progress.get('outcome_status', '') or 'completed')}",
                        flush=True,
                    )
                    return
                if event_name == "finish":
                    print(
                        f"{log_prefix} stage35-heartbeat ts={_stage35_wall_ts()} tier={tier.name} text={text_id} key_seed={key_seed} "
                        f"event=finish "
                        f"rounds_completed={int(progress.get('rounds_completed', 0) or 0)} "
                        f"archive={int(progress.get('archive_rows_count', 0) or 0)} "
                        f"evals={int(progress.get('total_evals', 0) or 0)} "
                        f"elapsed={fmt_finite_float_fn(progress.get('elapsed_seconds', 0.0), digits=3)} "
                        f"outcome_status={str(progress.get('outcome_status', '') or 'completed')}",
                        flush=True,
                    )

            stage35_followup = run_stage35_live_followup(
                period=int(tier.period),
                columns=int(tier.columns),
                alphabet_size=int(stage3_runtime_call_ctx.alphabet_size),
                ciphertext_idx=np.asarray(ct_idx, dtype=np.uint8),
                baseline_key=stage35_baseline_key,
                baseline_plaintext_idx=stage35_baseline_plaintext_idx,
                baseline_score=float(stage35_baseline_score_value),
                baseline_selector=str(stage35_baseline_selector),
                baseline_summary_row=stage35_baseline_row,
                phasec_score_winner_summary_row=phasec_score_winner_row,
                stage3_topk_rows=stage3_topk_payload,
                phasec_start_summaries=phaseC_start_summaries,
                phasec_final_winner_lane=str(phaseC_final_winner_lane),
                phasec_final_winner_source=str(phaseC_final_winner_source),
                cipher=full_cipher,
                scorer_full=scorer_full_runtime,
                scorer_search=scorer_stage3_search_runtime,
                cfg=dict(stage35_cfg),
                chunk_size=int(stage3_runtime_call_ctx.batch_eval_chunk_size),
                require_batch=bool(stage3_runtime_call_ctx.require_batch_scoring),
                target_plaintext_idx=np.asarray(pt_idx, dtype=np.uint8).astype(int).tolist(),
                progress_callback=_emit_stage35_progress,
                partial_state_path=stage35_partial_state_path,
                progress_jsonl_path=stage35_progress_jsonl_path,
                append_jsonl_row_fn=getattr(
                    stage3_runtime_call_ctx,
                    "append_jsonl_row_fn",
                    None,
                ),
            )
            stage35_enabled_cfg = int(stage35_followup.get("enabled_cfg", stage35_enabled_cfg))
            stage35_ran = int(stage35_followup.get("ran", 0))
            stage35_selected = int(stage35_followup.get("selected", 0))
            stage35_seed_count = int(stage35_followup.get("seed_count", 0))
            stage35_tail_mismatch_count = int(
                stage35_followup.get("tail_mismatch_count", 0)
            )
            stage35_seed_source_counts = dict(
                stage35_followup.get("seed_source_counts", {})
            )
            stage35_archive_count = int(stage35_followup.get("archive_count", 0))
            stage35_rounds_completed = int(
                stage35_followup.get("rounds_completed", 0)
            )
            stage35_evals = int(stage35_followup.get("evals", 0))
            stage35_runtime_seconds = float(
                stage35_followup.get("runtime_seconds", 0.0)
            )
            stage35_outcome_status = str(
                stage35_followup.get("outcome_status", "")
            )
            stage35_outcome_reason = str(
                stage35_followup.get("outcome_reason", "")
            )
            stage35_completed = int(stage35_followup.get("completed", 0))
            stage35_capped = int(stage35_followup.get("capped", 0))
            stage35_partial_state_name = str(
                stage35_followup.get("partial_state_path_name", "")
            )
            stage35_progress_jsonl_name = str(
                stage35_followup.get("progress_jsonl_path_name", "")
            )
            stage35_progress_event_count = int(
                stage35_followup.get("progress_events_written", 0)
            )
            stage35_partial_dump_write_count = int(
                stage35_followup.get("partial_dump_write_count", 0)
            )
            stage35_telemetry_summary = dict(
                stage35_followup.get("telemetry", {}) or {}
            )
            stage35_archive_unique_keys = int(
                stage35_followup.get("archive_unique_keys", 0)
            )
            stage35_archive_unique_seed_sources = int(
                stage35_followup.get("archive_unique_seed_sources", 0)
            )
            stage35_archive_unique_target_slices = int(
                stage35_followup.get("archive_unique_target_slices", 0)
            )
            stage35_archive_mean_substitution_hamming = float(
                stage35_followup.get(
                    "archive_mean_substitution_hamming",
                    0.0,
                )
            )
            stage35_archive_max_substitution_hamming = int(
                stage35_followup.get("archive_max_substitution_hamming", 0)
            )
            stage35_phasec_score_winner_candidate_hash = str(
                stage35_followup.get("phasec_score_winner_candidate_hash", "")
            )
            stage35_phasec_score_winner_candidate_source = str(
                stage35_followup.get("phasec_score_winner_candidate_source", "")
            )
            stage35_phasec_score_winner_candidate_lane = str(
                stage35_followup.get("phasec_score_winner_candidate_lane", "")
            )
            stage35_phasec_score_winner_candidate_final_score = float(
                stage35_followup.get(
                    "phasec_score_winner_candidate_final_score",
                    float("nan"),
                )
            )
            stage35_phasec_score_winner_candidate_final_match = float(
                stage35_followup.get(
                    "phasec_score_winner_candidate_final_match",
                    float("nan"),
                )
            )
            stage35_baseline_candidate_hash = str(
                stage35_followup.get("baseline_candidate_hash", "")
            )
            stage35_baseline_candidate_source = str(
                stage35_followup.get("baseline_candidate_source", "")
            )
            stage35_baseline_candidate_lane = str(
                stage35_followup.get("baseline_candidate_lane", "")
            )
            stage35_baseline_candidate_source_rank = int(
                stage35_followup.get("baseline_candidate_source_rank", 0)
            )
            stage35_baseline_candidate_final_score = float(
                stage35_followup.get(
                    "baseline_candidate_final_score",
                    float("nan"),
                )
            )
            stage35_baseline_candidate_final_match = float(
                stage35_followup.get(
                    "baseline_candidate_final_match",
                    float("nan"),
                )
            )
            stage35_baseline_differs_from_phasec_score_winner = int(
                stage35_followup.get(
                    "baseline_differs_from_phasec_score_winner",
                    0,
                )
            )
            stage35_baseline_search_score = float(
                stage35_followup.get("baseline_search_score", float("nan"))
            )
            stage35_accept_score_min_gain_cfg = float(
                stage35_followup.get("accept_score_min_gain_cfg", 0.0)
            )
            stage35_accept_search_score_max_drop_cfg = float(
                stage35_followup.get("accept_search_score_max_drop_cfg", 0.0)
            )
            stage35_accept_passed = int(stage35_followup.get("accept_passed", 0))
            stage35_accept_reason = str(
                stage35_followup.get("accept_reason", "")
            )
            stage35_mini_search_keep_all_rows_cfg = int(
                stage35_followup.get("mini_search_keep_all_rows_cfg", 0)
            )
            stage35_mini_search_collected_rows = int(
                stage35_followup.get("mini_search_collected_rows", 0)
            )
            stage35_mini_search_rows_kept = int(
                stage35_followup.get("mini_search_rows_kept", 0)
            )
            stage35_best_score = float(
                stage35_followup.get("best_score", float("nan"))
            )
            stage35_best_search_score = float(
                stage35_followup.get("best_search_score", float("nan"))
            )
            stage35_best_seed_source = str(
                stage35_followup.get("best_seed_source", "")
            )
            stage35_best_stage3_source = str(
                stage35_followup.get("best_stage3_source", "")
            )
            stage35_best_lane = str(stage35_followup.get("best_lane", ""))
            stage35_best_source_rank = int(
                stage35_followup.get("best_source_rank", 0)
            )
            stage35_best_target_slice = stage35_followup.get(
                "best_target_slice",
                None,
            )
            stage35_best_depth = int(stage35_followup.get("best_depth", 0))
            stage35_best_move_type = str(
                stage35_followup.get("best_move_type", "")
            )
            stage35_best_candidate_hash = str(
                stage35_followup.get("best_candidate_hash", "")
            )
            stage35_best_match = float(
                stage35_followup.get("best_match", float("nan"))
            )
            stage35_truth_gain_vs_selected_row = float(
                stage35_followup.get("truth_gain_vs_selected_row", float("nan"))
            )
            stage35_truth_gain_vs_phasec_score_winner = float(
                stage35_followup.get(
                    "truth_gain_vs_phasec_score_winner",
                    float("nan"),
                )
            )
            stage35_best_key = (
                list(map(int, stage35_followup.get("best_key", []) or []))
                or None
            )
            stage35_best_plaintext_idx = (
                list(
                    map(
                        int,
                        stage35_followup.get("best_plaintext_idx", []) or [],
                    )
                )
                or None
            )
            stage35_archive_rows = [
                dict(row)
                for row in list(stage35_followup.get("archive_rows", []) or [])
            ]
            stage35_seed_rows = [
                dict(row)
                for row in list(stage35_followup.get("seed_rows_scored", []) or [])
            ]
            ev3 += int(stage35_evals)
            if int(stage35_requested_cfg) == 1:
                if int(stage35_enabled_cfg) != 1:
                    stage35_proof_valid = 0
                    stage35_proof_invalid_reason = "requested_but_effective_disabled"
                elif int(stage35_ran) != 1:
                    not_run_reason = str(stage35_accept_reason).strip()
                    if not not_run_reason:
                        not_run_reason = (
                            "no_stage3_baseline"
                            if best3_key is None or int(pt3.size) <= 0
                            else "not_run"
                        )
                    stage35_proof_valid = 0
                    stage35_proof_invalid_reason = (
                        f"requested_but_not_run:{not_run_reason}"
                    )
                else:
                    stage35_proof_valid = 1
                    stage35_proof_invalid_reason = ""
            if int(stage35_ran) == 1:
                print(
                    f"{log_prefix} stage35-plan tier={tier.name} text={text_id} key_seed={key_seed} "
                    f"seed_count={int(stage35_seed_count)} "
                    f"seed_source_counts={stage35_seed_source_counts} "
                    f"tail_mismatch_count={int(stage35_tail_mismatch_count)} "
                    f"cfg={json.dumps(dict(stage35_cfg), separators=(',', ':'))}",
                    flush=True,
                )
                stages.append(
                    dict(
                        tier=str(tier.name),
                        text_id=int(text_id),
                        key_seed=int(key_seed),
                        stage="stage35_substitution_only",
                        stage35_requested_cfg=int(stage35_requested_cfg),
                        stage35_enabled=int(stage35_enabled_cfg),
                        stage35_ran=int(stage35_ran),
                        stage35_proof_valid=int(stage35_proof_valid),
                        stage35_proof_invalid_reason=str(stage35_proof_invalid_reason),
                        stage35_selected=int(stage35_selected),
                        stage35_seed_count=int(stage35_seed_count),
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
                        stage35_partial_dump_write_count=int(
                            stage35_partial_dump_write_count
                        ),
                        stage35_telemetry_summary=dict(stage35_telemetry_summary),
                        stage35_baseline_selector=str(stage35_baseline_selector),
                        stage35_baseline_candidate_hash=str(
                            stage35_baseline_candidate_hash
                        ),
                        stage35_baseline_differs_from_phasec_score_winner=int(
                            stage35_baseline_differs_from_phasec_score_winner
                        ),
                        stage35_accept_passed=int(stage35_accept_passed),
                        stage35_accept_reason=str(stage35_accept_reason),
                        stage35_best_score=float(stage35_best_score),
                        stage35_best_search_score=float(stage35_best_search_score),
                    )
                )
                print(
                    f"{log_prefix} stage35-finish ts={_stage35_wall_ts()} tier={tier.name} text={text_id} key_seed={key_seed} "
                    f"selector={stage35_baseline_selector} "
                    f"baseline_hash={stage35_baseline_candidate_hash or 'none'} "
                    f"baseline_differs={int(stage35_baseline_differs_from_phasec_score_winner)} "
                    f"selected={int(stage35_selected)} "
                    f"outcome_status={stage35_outcome_status or 'none'} "
                    f"accept_passed={int(stage35_accept_passed)} "
                    f"accept_reason={stage35_accept_reason or 'none'} "
                    f"archive_count={int(stage35_archive_count)} "
                    f"rounds={int(stage35_rounds_completed)} "
                    f"evals={int(stage35_evals)} "
                    f"runtime={fmt_finite_float_fn(stage35_runtime_seconds, digits=3)} "
                    f"baseline_search_score={fmt_finite_float_fn(stage35_baseline_search_score, digits=6)} "
                    f"accept_score_min_gain={fmt_finite_float_fn(stage35_accept_score_min_gain_cfg, digits=6)} "
                    f"accept_search_score_max_drop={fmt_finite_float_fn(stage35_accept_search_score_max_drop_cfg, digits=6)} "
                    f"mini_search_keep_all_rows={int(stage35_mini_search_keep_all_rows_cfg)} "
                    f"mini_search_collected_rows={int(stage35_mini_search_collected_rows)} "
                    f"mini_search_rows_kept={int(stage35_mini_search_rows_kept)} "
                    f"best_seed_source={stage35_best_seed_source or 'none'} "
                    f"best_stage3_source={stage35_best_stage3_source or 'none'} "
                    f"best_lane={stage35_best_lane or 'none'} "
                    f"best_source_rank={int(stage35_best_source_rank)} "
                    f"best_depth={int(stage35_best_depth)} "
                    f"best_target_slice={stage35_best_target_slice if stage35_best_target_slice is not None else 'none'} "
                    f"best_score={fmt_finite_float_fn(stage35_best_score, digits=6)} "
                    f"best_search_score={fmt_finite_float_fn(stage35_best_search_score, digits=6)}",
                    flush=True,
                )
            elif int(stage35_requested_cfg) == 1 and int(stage35_proof_valid) != 1:
                stages.append(
                    dict(
                        tier=str(tier.name),
                        text_id=int(text_id),
                        key_seed=int(key_seed),
                        stage="stage35_substitution_only",
                        stage35_requested_cfg=int(stage35_requested_cfg),
                        stage35_enabled=int(stage35_enabled_cfg),
                        stage35_ran=int(stage35_ran),
                        stage35_proof_valid=int(stage35_proof_valid),
                        stage35_proof_invalid_reason=str(stage35_proof_invalid_reason),
                        stage35_selected=int(stage35_selected),
                        stage35_seed_count=int(stage35_seed_count),
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
                        stage35_partial_dump_write_count=int(
                            stage35_partial_dump_write_count
                        ),
                        stage35_telemetry_summary=dict(stage35_telemetry_summary),
                        stage35_baseline_selector=str(stage35_baseline_selector),
                        stage35_baseline_candidate_hash=str(
                            stage35_baseline_candidate_hash
                        ),
                        stage35_baseline_differs_from_phasec_score_winner=int(
                            stage35_baseline_differs_from_phasec_score_winner
                        ),
                        stage35_accept_passed=int(stage35_accept_passed),
                        stage35_accept_reason=str(stage35_accept_reason),
                    )
                )
                print(
                    f"{log_prefix} stage35-invalid tier={tier.name} text={text_id} key_seed={key_seed} "
                    f"requested={int(stage35_requested_cfg)} "
                    f"enabled={int(stage35_enabled_cfg)} "
                    f"ran={int(stage35_ran)} "
                    f"invalid_reason={stage35_proof_invalid_reason or 'none'}",
                    flush=True,
                )
            if int(stage35_selected) == 1 and stage35_best_key is not None and stage35_best_plaintext_idx is not None:
                best3_key = list(map(int, stage35_best_key))
                pt3 = np.asarray(stage35_best_plaintext_idx, dtype=np.uint8).reshape(-1)
                best3_score = float(stage35_best_score)
        if int(stage35_requested_cfg) == 1 and int(stage35_enabled_cfg) != 1:
            if not str(stage35_outcome_status):
                stage35_outcome_status = "not_run_disabled"
                stage35_outcome_reason = "requested_but_effective_disabled"
            stage35_proof_valid = 0
            stage35_proof_invalid_reason = "requested_but_effective_disabled"
        elif int(stage35_requested_cfg) == 1 and int(stage35_ran) != 1:
            not_run_reason = str(stage35_accept_reason).strip()
            if not not_run_reason:
                not_run_reason = (
                    "no_stage3_baseline"
                    if best3_key is None or int(pt3.size) <= 0
                    else "not_run"
                )
            if not str(stage35_outcome_status):
                stage35_outcome_status = "unfinished_not_run"
                stage35_outcome_reason = str(not_run_reason)
            stage35_proof_valid = 0
            stage35_proof_invalid_reason = f"requested_but_not_run:{not_run_reason}"
        elif int(stage35_requested_cfg) == 1:
            stage35_proof_valid = 1
            stage35_proof_invalid_reason = ""

        if pt3.size > 0:
            print_stage_preview_fn(
                label=(
                    "stage35_substitution_only"
                    if int(stage35_selected) == 1
                    else "stage3_full_refine"
                ),
                pt=pt3.tolist(),
                wli=wli,
                match_ratio=(
                    None
                    if int(stage35_selected) == 1
                    else float(best3_match)
                ),
            )
        if np.isfinite(best3_match) and best3_match >= solve_match_threshold:
            stop_reason = "solved_stage3"
        elif (best3_match - best2_match) <= stall_delta:
            stop_reason = "stalled_no_improve" if int(stall_stage_limit) <= 1 else "unsolved"
        else:
            stop_reason = "unsolved"
    elif stage3_policy_branch != "continue":
        pass
    else:
        stop_reason = "no_stage2_candidate"

    stage3_span_summary = summarize_stage3_span_fn(
        tier_name=str(tier.name),
        text_id=int(text_id),
        key_seed=int(key_seed),
        span_phaseA_eval_total=float(stage3_span_phaseA_eval_total),
        span_phaseA_eval_active=float(stage3_span_phaseA_eval_active),
        span_phaseA_eval_skipped=float(stage3_span_phaseA_eval_skipped),
        span_phaseA_seconds_total=float(stage3_span_phaseA_seconds_total),
        span_phaseA_seconds_active=float(stage3_span_phaseA_seconds_active),
        span_full_eval_total=float(stage3_span_full_eval_total),
        span_full_eval_active=float(stage3_span_full_eval_active),
        span_full_eval_skipped=float(stage3_span_full_eval_skipped),
        span_full_seconds_total=float(stage3_span_full_seconds_total),
        span_full_seconds_active=float(stage3_span_full_seconds_active),
        span_basin_judge_k_used=int(stage3_span_basin_judge_k_used),
        span_basin_judge_seconds=float(stage3_span_basin_judge_seconds),
        basin_judge_span_calls_total=int(stage3_basin_judge_span_calls_total),
        basin_judge_span_calls_active=int(stage3_basin_judge_span_calls_active),
        basin_judge_span_calls_rejected_or_gated=int(stage3_basin_judge_span_calls_rejected_or_gated),
        log_prefix=str(log_prefix),
    )
    stage3_span_eval_total = float(stage3_span_summary["span_eval_total"])
    stage3_span_eval_active = float(stage3_span_summary["span_eval_active"])
    stage3_span_eval_skipped = float(stage3_span_summary["span_eval_skipped"])
    stage3_span_seconds_total = float(stage3_span_summary["span_seconds_total"])
    stage3_span_seconds_active = float(stage3_span_summary["span_seconds_active"])
    stage3_span_active_rate = float(stage3_span_summary["span_active_rate"])
    stage3_span_active_rate_source = str(stage3_span_summary["span_active_rate_source"])

    return dict(
        stop_reason=str(stop_reason),
        ev3=int(ev3),
        best3_match=float(best3_match),
        best3_score=float(best3_score),
        best3_key=best3_key,
        pt3=np.asarray(pt3, dtype=np.uint8).reshape(-1),
        stage2_gap_to_oracle=float(stage2_gap_to_oracle),
        stage3_band_name=str(stage3_band_name),
        stage3_topk_payload=stage3_topk_payload,
        stage3_init_target=int(stage3_init_target),
        stage3_init_actual=int(stage3_init_actual),
        stage3_promoted_keys_count=int(stage3_promoted_keys_count),
        stage3_gate_source=str(stage3_gate_source),
        stage3_entry_allocation_policy=str(stage3_entry_allocation_policy),
        stage3_entry_base_budget=int(stage3_entry_base_budget),
        stage3_entry_target_before_cap=int(stage3_entry_target_before_cap),
        stage3_entry_cap=int(stage3_entry_cap),
        stage3_entry_cap_applied=int(stage3_entry_cap_applied),
        stage3_entry_mutations_per_promoted_cfg=int(stage3_entry_mutations_per_promoted_cfg),
        stage3_entry_mutation_calls_per_promoted=int(
            stage3_entry_mutation_calls_per_promoted
        ),
        stage3_phaseB_top_n_cfg=int(stage3_phaseB_top_n_cfg),
        stage3_phaseB_gate_delta_cfg=float(stage3_phaseB_gate_delta_cfg),
        stage3_phaseB_gate_end_gain_cfg=float(stage3_phaseB_gate_end_gain_cfg),
        stage3_solve_hits=int(stage3_solve_hits),
        stage3_period_init_mult=float(stage3_period_init_mult),
        stage3_period_step_mult=float(stage3_period_step_mult),
        stage3_period_restart_bonus=int(stage3_period_restart_bonus),
        stage3_scan_phaseA_only=bool(stage3_scan_phaseA_only),
        stage3_span_active_rate=float(stage3_span_active_rate),
        stage3_span_active_rate_source=str(stage3_span_active_rate_source),
        stage3_span_eval_total=float(stage3_span_eval_total),
        stage3_span_eval_active=float(stage3_span_eval_active),
        stage3_span_eval_skipped=float(stage3_span_eval_skipped),
        stage3_span_seconds_total=float(stage3_span_seconds_total),
        stage3_span_seconds_active=float(stage3_span_seconds_active),
        stage3_span_phaseA_eval_total=float(stage3_span_phaseA_eval_total),
        stage3_span_phaseA_eval_active=float(stage3_span_phaseA_eval_active),
        stage3_span_phaseA_eval_skipped=float(stage3_span_phaseA_eval_skipped),
        stage3_span_phaseA_seconds_total=float(stage3_span_phaseA_seconds_total),
        stage3_span_phaseA_seconds_active=float(stage3_span_phaseA_seconds_active),
        stage3_span_full_eval_total=float(stage3_span_full_eval_total),
        stage3_span_full_eval_active=float(stage3_span_full_eval_active),
        stage3_span_full_eval_skipped=float(stage3_span_full_eval_skipped),
        stage3_span_full_seconds_total=float(stage3_span_full_seconds_total),
        stage3_span_full_seconds_active=float(stage3_span_full_seconds_active),
        stage3_span_basin_judge_k_cfg=int(stage3_span_basin_judge_k_cfg),
        stage3_span_basin_judge_k_used=int(stage3_span_basin_judge_k_used),
        stage3_span_basin_judge_seconds=float(stage3_span_basin_judge_seconds),
        stage3_basin_judge_span_calls_total=int(stage3_basin_judge_span_calls_total),
        stage3_basin_judge_span_calls_active=int(stage3_basin_judge_span_calls_active),
        stage3_basin_judge_span_calls_rejected_or_gated=int(stage3_basin_judge_span_calls_rejected_or_gated),
        stage3_basin_judge_span_seconds_total=float(stage3_basin_judge_span_seconds_total),
        stage3_basin_judge_unique_end_hash=int(stage3_basin_judge_unique_end_hash),
        stage3_word_ngram_rows_scored=int(stage3_word_ngram_rows_scored),
        stage3_word_ngram_rows_active=int(stage3_word_ngram_rows_active),
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
        phaseC_candidate_pool_source_counts=dict(phaseC_candidate_pool_source_counts),
        phaseC_novel_view_id=str(phaseC_novel_view_id),
        phaseC_anchor_candidate_hash=str(phaseC_anchor_candidate_hash),
        phaseC_candidate_pool_eligible_novel_count=int(
            phaseC_candidate_pool_eligible_novel_count
        ),
        phaseC_candidate_pool_eligible_novel_row_count=int(
            phaseC_candidate_pool_eligible_novel_row_count
        ),
        phaseC_candidate_pool_eligible_novel_source_counts=dict(
            phaseC_candidate_pool_eligible_novel_source_counts
        ),
        phaseC_start_source_counts=dict(phaseC_start_source_counts),
        phaseC_start_unique_end_hash=int(phaseC_start_unique_end_hash),
        phaseC_start_eligible_novel_count=int(phaseC_start_eligible_novel_count),
        phaseC_selected_novel_challenger_count=int(
            phaseC_selected_novel_challenger_count
        ),
        phaseC_eligible_novel_not_selected_count=int(
            phaseC_eligible_novel_not_selected_count
        ),
        phaseC_selected_novel_challenger_hashes=list(
            phaseC_selected_novel_challenger_hashes
        ),
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
        phaseC_start_summaries=[dict(row) for row in phaseC_start_summaries],
        stage35_requested_cfg=int(stage35_requested_cfg),
        stage35_enabled_cfg=int(stage35_enabled_cfg),
        stage35_ran=int(stage35_ran),
        stage35_proof_valid=int(stage35_proof_valid),
        stage35_proof_invalid_reason=str(stage35_proof_invalid_reason),
        stage35_selected=int(stage35_selected),
        stage35_seed_count=int(stage35_seed_count),
        stage35_tail_mismatch_count=int(stage35_tail_mismatch_count),
        stage35_seed_source_counts=dict(stage35_seed_source_counts),
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
        stage35_telemetry_summary=dict(stage35_telemetry_summary),
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
        stage35_best_target_slice=stage35_best_target_slice,
        stage35_best_depth=int(stage35_best_depth),
        stage35_best_move_type=str(stage35_best_move_type),
        stage35_best_candidate_hash=str(stage35_best_candidate_hash),
        stage35_best_match=float(stage35_best_match),
        stage35_truth_gain_vs_selected_row=float(
            stage35_truth_gain_vs_selected_row
        ),
        stage35_truth_gain_vs_phasec_score_winner=float(
            stage35_truth_gain_vs_phasec_score_winner
        ),
        stage35_best_key=stage35_best_key,
        stage35_best_plaintext_idx=stage35_best_plaintext_idx,
        stage35_archive_rows=[dict(row) for row in stage35_archive_rows],
        stage35_seed_rows=[dict(row) for row in stage35_seed_rows],
        stage2_resume_live=dict(stage2_resume_live or {}),
        stage3_prep_live=dict(stage3_prep_live or {}),
    )
