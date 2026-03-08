from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Callable, Dict, List, Mapping, Sequence, Tuple

import numpy as np

from tools.benchmarks.periodic_sub_trans.no_wli.stage_engine_iteration_bridge import (
    run_iteration_with_stage_engine,
)

@dataclass(frozen=True)
class IterationMatrixConfig:
    stage1_label: str
    stage2_label: str
    stage3_label: str
    stage3_continue_after_solve: bool
    stage3_phaseb_top_n: int
    stage3_phaseb_gate_delta_floor: float
    stage3_phaseb_gate_end_gain_floor: float
    stage3_c1_focus_enabled: bool
    stage3_span_char_pct_min_override: float | None
    scoring_experiment_c_char_pct_min: float
    oracle_stage3_floor_guard_eps: float
    stage3_two_phase_enabled: bool
    stage3_phasea_cfg_default: Dict[str, Any]
    stage3_phaseb_cfg_default: Dict[str, Any]
    solver_stage3_default_cfg: Dict[str, Any]
    stage3_span_basin_judge_k: int
    tier_heartbeat_seconds: float
    solve_match_threshold: float
    stall_delta: float
    stall_stage_limit: int
    scan_stage3_gate_low_match: float
    scan_stage3_gate_high_match: float
    oracle_mode: str
    oracle_decision_paths_enabled: bool
    oracle_assist_selection_effective: bool
    stage3_span_aux_role: str
    stage3_span_aux_scope: str
    stage3_span_aux_profile: str
    stage3_span_aux_budget_ms: float
    stage3_span_aux_two_pass: bool
    stage3_span_aux_full_top_m: int
    span_decision_role_enabled: bool
    span_reps_per_basin: int
    span_selection_top_k: int
    span_p90_call_ms: float | None


@dataclass(frozen=True)
class IterationMatrixFns:
    slice_word_aligned_fn: Callable[..., Tuple[np.ndarray, Any, int]]
    get_oracle_consulted_in_decisions_fn: Callable[[], bool]
    handle_autoskip_proven_iteration_fn: Callable[..., None]
    run_iteration_pre_stage3_fn: Callable[..., Dict[str, Any]]
    run_stage3_iteration_flow_fn: Callable[..., Dict[str, Any]]
    finalize_iteration_post_stage3_fn: Callable[..., None]
    build_iteration_payloads_fn: Callable[..., Any]
    derive_outcome_code_fn: Callable[..., str]
    commit_iteration_with_checkpoint_fn: Callable[..., None]
    build_iteration_runtime_fn: Callable[..., Dict[str, Any]]
    evaluate_oracle_precheck_fn: Callable[..., Dict[str, Any]]
    handle_oracle_floor_guard_if_triggered_fn: Callable[..., bool]
    run_stage12_pipeline_fn: Callable[..., Dict[str, Any]]
    scorer_objective_summary_fn: Callable[[Dict[str, Any]], str]
    oracle_score_for_stage_fn: Callable[..., float]
    weights_text_fn: Callable[..., str]
    mark_oracle_decision_use_fn: Callable[[], None]
    print_stage_preview_fn: Callable[..., None]
    build_oracle_floor_guard_result_fn: Callable[..., Dict[str, Any]]
    run_stage1_substitution_fn: Callable[..., Dict[str, Any]]
    run_stage2_search_fn: Callable[..., Dict[str, Any]]
    finalize_stage2_archive_fn: Callable[..., Dict[str, Any]]
    evaluate_stage3_entry_policy_fn: Callable[..., Dict[str, Any]]
    prepare_stage3_refine_inputs_fn: Callable[..., Dict[str, Any]]
    summarize_stage3_span_fn: Callable[..., Dict[str, Any]]
    fmt_finite_float_fn: Callable[..., str]
    build_stage2_diagnostics_fn: Callable[..., Dict[str, Any]]
    build_stage3_diagnostics_fn: Callable[..., Dict[str, Any]]
    finalize_iteration_and_commit_fn: Callable[..., Dict[str, Any]]
    safe_preview_latin_fn: Callable[[Any, Any], str]
    stage_engine_trace_emit_fn: Callable[..., None]


def run_iteration_matrix(
    *,
    tiers: Sequence[Any],
    text_offsets: Sequence[int],
    key_seeds: Sequence[int],
    pt_base: Sequence[int],
    wli_base: Sequence[Sequence[int]],
    direction: Any,
    span_assets_dir: Any,
    scoring_experiment_meta: Dict[str, Any],
    autoskip_effective: bool,
    proven_index: Mapping[Tuple[str, int, int], Dict[str, Any]],
    instances: List[Dict[str, Any]],
    stages: List[Dict[str, Any]],
    stage3_runtime_call_ctx: Any,
    config: IterationMatrixConfig,
    fns: IterationMatrixFns,
    log_prefix: str = "[pipeline_no_wli]",
) -> None:
    for tier in tiers:
        for text_id, off in enumerate(text_offsets):
            pt_idx, wli, offset_used = fns.slice_word_aligned_fn(
                pt_base,
                wli_base,
                length=tier.length,
                offset_hint=int(off),
            )
            for key_seed in key_seeds:
                t0_i = float(time.time())
                proven_key = (str(tier.name), int(text_id), int(key_seed))
                oracle_mode = str(config.oracle_mode)
                oracle_decision_paths_enabled = bool(
                    config.oracle_decision_paths_enabled
                )
                oracle_assist_selection_effective = bool(
                    config.oracle_assist_selection_effective
                )
                oracle_consulted_in_decisions = bool(
                    fns.get_oracle_consulted_in_decisions_fn()
                )
                if bool(autoskip_effective) and (proven_key in proven_index):
                    fns.handle_autoskip_proven_iteration_fn(
                        tier=tier,
                        text_id=int(text_id),
                        key_seed=int(key_seed),
                        off=int(off),
                        offset_used=int(offset_used),
                        source_row=dict(proven_index.get(proven_key, {})),
                        stage3_continue_after_solve=bool(config.stage3_continue_after_solve),
                        stage3_phaseb_top_n=int(config.stage3_phaseb_top_n),
                        stage3_phaseb_gate_delta_floor=float(config.stage3_phaseb_gate_delta_floor),
                        stage3_phaseb_gate_end_gain_floor=float(config.stage3_phaseb_gate_end_gain_floor),
                        stage3_c1_focus_enabled=bool(config.stage3_c1_focus_enabled),
                        oracle_mode=str(oracle_mode),
                        oracle_consulted_in_decisions=bool(
                            oracle_consulted_in_decisions
                        ),
                        build_iteration_payloads_fn=fns.build_iteration_payloads_fn,
                        derive_outcome_code_fn=fns.derive_outcome_code_fn,
                        commit_iteration_with_checkpoint_fn=fns.commit_iteration_with_checkpoint_fn,
                        instances=instances,
                        stages=stages,
                        log_prefix=str(log_prefix),
                    )
                    continue

                stage_engine_result = run_iteration_with_stage_engine(
                    state=dict(locals()),
                    config=config,
                    fns=fns,
                    stage3_runtime_call_ctx=stage3_runtime_call_ctx,
                    log_prefix=str(log_prefix),
                )
                for _evt in stage_engine_result.events:
                    fns.stage_engine_trace_emit_fn(
                        event=dict(_evt),
                        tier_name=str(tier.name),
                        text_id=int(text_id),
                        key_seed=int(key_seed),
                    )
                pre_stage3 = dict(stage_engine_result.pre_stage3)
                if bool(pre_stage3.get("continue_iteration", False)):
                    continue

                key_len = int(pre_stage3["key_len"])
                full_cipher = pre_stage3["full_cipher"]
                ct_idx = np.asarray(pre_stage3["ct_idx"], dtype=np.uint8)
                scorer_stage2 = dict(pre_stage3["scorer_stage2"])
                scorer_full = dict(pre_stage3["scorer_full"])
                scorer_stage3_phaseA = dict(pre_stage3["scorer_stage3_phaseA"])
                scorer_stage3_phaseB = dict(pre_stage3["scorer_stage3_phaseB"])
                scorer_stage3_search_runtime = pre_stage3["scorer_stage3_search_runtime"]
                scorer_basin_judge_runtime = pre_stage3["scorer_basin_judge_runtime"]
                scorer_full_runtime = pre_stage3["scorer_full_runtime"]
                scorer_stage3_phaseA_runtime = pre_stage3["scorer_stage3_phaseA_runtime"]
                oracle_s1 = float(pre_stage3["oracle_s1"])
                oracle_s2 = float(pre_stage3["oracle_s2"])
                oracle_s3 = float(pre_stage3["oracle_s3"])
                stage3_phaseA_experiment = str(pre_stage3["stage3_phaseA_experiment"])
                stage3_phaseB_experiment = str(pre_stage3["stage3_phaseB_experiment"])
                stage3_phaseB_char_pct_min_dynamic = float(
                    pre_stage3["stage3_phaseB_char_pct_min_dynamic"]
                )
                stage3_phaseB_char_pct_min_source = str(
                    pre_stage3["stage3_phaseB_char_pct_min_source"]
                )
                sub_key_match = float(pre_stage3["sub_key_match"])
                stage1_best_score = float(pre_stage3["stage1_best_score"])
                ev1 = int(pre_stage3["ev1"])
                best2_match = float(pre_stage3["best2_match"])
                best2_score = float(pre_stage3["best2_score"])
                best2_key = pre_stage3["best2_key"]
                best2_pt = pre_stage3["best2_pt"]
                best2_preview = str(pre_stage3["best2_preview"])
                stage2_evals_total = int(pre_stage3["stage2_evals_total"])
                stage2_archive = dict(pre_stage3["stage2_archive"])
                stage2_continue_to_gate = bool(pre_stage3["stage2_continue_to_gate"])
                stage2_continue_stop_reason = str(pre_stage3["stage2_continue_stop_reason"])
                stage2_ranked = list(pre_stage3["stage2_ranked"])
                stage2_promoted = list(pre_stage3["stage2_promoted"])
                stage2_entry_score = float(pre_stage3["stage2_entry_score"])
                stage2_entry_score_judge = float(pre_stage3["stage2_entry_score_judge"])
                stage2_score_match_spearman = float(pre_stage3["stage2_score_match_spearman"])
                stage2_topk_payload = list(pre_stage3["stage2_topk_payload"])
                stage2_topk_has_best_match = bool(pre_stage3["stage2_topk_has_best_match"])

                stage3_flow = dict(stage_engine_result.stage3_flow)
                if stage3_flow:
                    fns.stage_engine_trace_emit_fn(
                        event=dict(
                            event="span_runtime_telemetry",
                            stage_id="stage_c_refine",
                            span_active_rate=float(stage3_flow.get("stage3_span_active_rate", 0.0)),
                            span_active_rate_source=str(
                                stage3_flow.get(
                                    "stage3_span_active_rate_source",
                                    "stage3_flow_missing",
                                )
                            ),
                            span_eval_total=float(stage3_flow.get("stage3_span_eval_total", 0.0)),
                            span_eval_active=float(stage3_flow.get("stage3_span_eval_active", 0.0)),
                            span_eval_skipped=float(
                                stage3_flow.get("stage3_span_eval_skipped", 0.0)
                            ),
                            span_seconds_total=float(
                                stage3_flow.get("stage3_span_seconds_total", 0.0)
                            ),
                            span_seconds_active=float(
                                stage3_flow.get("stage3_span_seconds_active", 0.0)
                            ),
                            basin_judge_span_calls_total=int(
                                stage3_flow.get("stage3_basin_judge_span_calls_total", 0)
                            ),
                            basin_judge_span_calls_active=int(
                                stage3_flow.get("stage3_basin_judge_span_calls_active", 0)
                            ),
                            basin_judge_span_calls_rejected_or_gated=int(
                                stage3_flow.get(
                                    "stage3_basin_judge_span_calls_rejected_or_gated",
                                    0,
                                )
                            ),
                            basin_judge_span_seconds_total=float(
                                stage3_flow.get("stage3_basin_judge_span_seconds_total", 0.0)
                            ),
                        ),
                        tier_name=str(tier.name),
                        text_id=int(text_id),
                        key_seed=int(key_seed),
                    )
                oracle_consulted_in_decisions = bool(
                    fns.get_oracle_consulted_in_decisions_fn()
                )
                iteration_state = dict(locals())
                iteration_state.update(dict(pre_stage3))
                iteration_state.update(dict(stage3_flow))

                fns.finalize_iteration_post_stage3_fn(
                    state=iteration_state,
                    stage3_continue_after_solve=bool(config.stage3_continue_after_solve),
                    scan_stage3_gate_low_match=float(config.scan_stage3_gate_low_match),
                    scan_stage3_gate_high_match=float(config.scan_stage3_gate_high_match),
                    stage3_c1_focus_enabled=bool(config.stage3_c1_focus_enabled),
                    solve_match_threshold=float(config.solve_match_threshold),
                    build_stage2_diagnostics_fn=fns.build_stage2_diagnostics_fn,
                    build_stage3_diagnostics_fn=fns.build_stage3_diagnostics_fn,
                    finalize_iteration_and_commit_fn=fns.finalize_iteration_and_commit_fn,
                    build_iteration_payloads_fn=fns.build_iteration_payloads_fn,
                    commit_iteration_with_checkpoint_fn=fns.commit_iteration_with_checkpoint_fn,
                    derive_outcome_code_fn=fns.derive_outcome_code_fn,
                    safe_preview_latin_fn=fns.safe_preview_latin_fn,
                )
