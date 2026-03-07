from __future__ import annotations

from typing import Any, Callable, Mapping, MutableMapping

from tools.benchmarks.periodic_sub_trans.no_wli.iteration_matrix_flow import (
    IterationMatrixConfig,
    IterationMatrixFns,
)


def build_iteration_matrix_config(
    *,
    state: MutableMapping[str, Any],
    oracle_mode: str,
    oracle_decision_paths_enabled: bool,
    oracle_assist_selection_effective: bool,
) -> IterationMatrixConfig:
    return IterationMatrixConfig(
        stage1_label=str(state["SCORER_STAGE1_LABEL"]),
        stage2_label=str(state["SCORER_STAGE2_LABEL"]),
        stage3_label=str(state["SCORER_STAGE3_LABEL"]),
        stage3_continue_after_solve=bool(state["STAGE3_CONTINUE_AFTER_SOLVE"]),
        stage3_phaseb_top_n=int(state["STAGE3_PHASEB_TOP_N"]),
        stage3_phaseb_gate_delta_floor=float(state["STAGE3_PHASEB_GATE_DELTA_FLOOR"]),
        stage3_phaseb_gate_end_gain_floor=float(
            state["STAGE3_PHASEB_GATE_END_GAIN_FLOOR"]
        ),
        stage3_c1_focus_enabled=bool(state["STAGE3_C1_FOCUS_ENABLED"]),
        stage3_span_char_pct_min_override=(
            float(state["STAGE3_SPAN_CHAR_PCT_MIN_OVERRIDE"])
            if state["STAGE3_SPAN_CHAR_PCT_MIN_OVERRIDE"] is not None
            else None
        ),
        scoring_experiment_c_char_pct_min=float(state["SCORING_EXPERIMENT_C_CHAR_PCT_MIN"]),
        oracle_stage3_floor_guard_eps=float(state["ORACLE_STAGE3_FLOOR_GUARD_EPS"]),
        stage3_two_phase_enabled=bool(state["STAGE3_TWO_PHASE_ENABLED"]),
        stage3_phasea_cfg_default=dict(state["STAGE3_PHASEA_CFG"]),
        stage3_phaseb_cfg_default=dict(state["STAGE3_PHASEB_CFG"]),
        solver_stage3_default_cfg=dict(state["SOLVER_STAGE3"]),
        stage3_span_basin_judge_k=int(state["STAGE3_SPAN_BASIN_JUDGE_K"]),
        tier_heartbeat_seconds=float(state["TIER_HEARTBEAT_SECONDS"]),
        solve_match_threshold=float(state["SOLVE_MATCH_THRESHOLD"]),
        stall_delta=float(state["STALL_DELTA"]),
        stall_stage_limit=int(state["STALL_STAGE_LIMIT"]),
        scan_stage3_gate_low_match=float(state["SCAN_STAGE3_GATE_LOW_MATCH"]),
        scan_stage3_gate_high_match=float(
            max(
                float(state["SCAN_STAGE3_GATE_LOW_MATCH"]),
                float(state["SCAN_STAGE3_GATE_HIGH_MATCH"]),
            )
        ),
        oracle_mode=str(oracle_mode),
        oracle_decision_paths_enabled=bool(oracle_decision_paths_enabled),
        oracle_assist_selection_effective=bool(oracle_assist_selection_effective),
    )


def build_iteration_matrix_fns(
    *,
    get_oracle_consulted_in_decisions_fn: Callable[[], bool],
    build_iteration_payloads_fn: Callable[..., Any],
    derive_outcome_code_fn: Callable[..., str],
    commit_iteration_with_checkpoint_fn: Callable[..., None],
    build_iteration_runtime_fn: Callable[..., Mapping[str, Any]],
    scorer_objective_summary_fn: Callable[[dict[str, Any]], str],
    oracle_score_for_stage_fn: Callable[..., float],
    weights_text_fn: Callable[..., str],
    mark_oracle_decision_use_fn: Callable[[], None],
    print_stage_preview_fn: Callable[..., None],
    run_stage1_substitution_fn: Callable[..., Mapping[str, Any]],
    run_stage2_search_fn: Callable[..., Mapping[str, Any]],
    finalize_stage2_archive_fn: Callable[..., Mapping[str, Any]],
    evaluate_stage3_entry_policy_fn: Callable[..., Mapping[str, Any]],
    prepare_stage3_refine_inputs_fn: Callable[..., Mapping[str, Any]],
    fmt_finite_float_fn: Callable[..., str],
    handlers: Mapping[str, Any],
) -> IterationMatrixFns:
    return IterationMatrixFns(
        slice_word_aligned_fn=handlers["slice_word_aligned_fn"],
        get_oracle_consulted_in_decisions_fn=get_oracle_consulted_in_decisions_fn,
        handle_autoskip_proven_iteration_fn=handlers["handle_autoskip_proven_iteration_fn"],
        run_iteration_pre_stage3_fn=handlers["run_iteration_pre_stage3_fn"],
        run_stage3_iteration_flow_fn=handlers["run_stage3_iteration_flow_fn"],
        finalize_iteration_post_stage3_fn=handlers["finalize_iteration_post_stage3_fn"],
        build_iteration_payloads_fn=build_iteration_payloads_fn,
        derive_outcome_code_fn=derive_outcome_code_fn,
        commit_iteration_with_checkpoint_fn=commit_iteration_with_checkpoint_fn,
        build_iteration_runtime_fn=build_iteration_runtime_fn,
        evaluate_oracle_precheck_fn=handlers["evaluate_oracle_precheck_fn"],
        handle_oracle_floor_guard_if_triggered_fn=handlers[
            "handle_oracle_floor_guard_if_triggered_fn"
        ],
        run_stage12_pipeline_fn=handlers["run_stage12_pipeline_fn"],
        scorer_objective_summary_fn=scorer_objective_summary_fn,
        oracle_score_for_stage_fn=oracle_score_for_stage_fn,
        weights_text_fn=weights_text_fn,
        mark_oracle_decision_use_fn=mark_oracle_decision_use_fn,
        print_stage_preview_fn=print_stage_preview_fn,
        build_oracle_floor_guard_result_fn=handlers["build_oracle_floor_guard_result_fn"],
        run_stage1_substitution_fn=run_stage1_substitution_fn,
        run_stage2_search_fn=run_stage2_search_fn,
        finalize_stage2_archive_fn=finalize_stage2_archive_fn,
        evaluate_stage3_entry_policy_fn=evaluate_stage3_entry_policy_fn,
        prepare_stage3_refine_inputs_fn=prepare_stage3_refine_inputs_fn,
        summarize_stage3_span_fn=handlers["summarize_stage3_span_fn"],
        fmt_finite_float_fn=fmt_finite_float_fn,
        build_stage2_diagnostics_fn=handlers["build_stage2_diagnostics_fn"],
        build_stage3_diagnostics_fn=handlers["build_stage3_diagnostics_fn"],
        finalize_iteration_and_commit_fn=handlers["finalize_iteration_and_commit_fn"],
        safe_preview_latin_fn=handlers["safe_preview_latin_fn"],
    )
