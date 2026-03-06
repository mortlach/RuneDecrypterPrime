from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Callable, Dict, List, Mapping, Sequence, Tuple

import numpy as np


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

                pre_stage3 = fns.run_iteration_pre_stage3_fn(
                    state=dict(locals()),
                    stage1_label=str(config.stage1_label),
                    stage2_label=str(config.stage2_label),
                    stage3_label=str(config.stage3_label),
                    stage3_continue_after_solve=bool(config.stage3_continue_after_solve),
                    stage3_phaseb_top_n=int(config.stage3_phaseb_top_n),
                    stage3_phaseb_gate_delta_floor=float(config.stage3_phaseb_gate_delta_floor),
                    stage3_phaseb_gate_end_gain_floor=float(config.stage3_phaseb_gate_end_gain_floor),
                    stage3_c1_focus_enabled=bool(config.stage3_c1_focus_enabled),
                    stage3_span_char_pct_min_override=(
                        float(config.stage3_span_char_pct_min_override)
                        if config.stage3_span_char_pct_min_override is not None
                        else None
                    ),
                    scoring_experiment_c_char_pct_min=float(config.scoring_experiment_c_char_pct_min),
                    oracle_stage3_floor_guard_eps=float(config.oracle_stage3_floor_guard_eps),
                    build_iteration_runtime_fn=fns.build_iteration_runtime_fn,
                    evaluate_oracle_precheck_fn=fns.evaluate_oracle_precheck_fn,
                    handle_oracle_floor_guard_if_triggered_fn=fns.handle_oracle_floor_guard_if_triggered_fn,
                    run_stage12_pipeline_fn=fns.run_stage12_pipeline_fn,
                    scorer_objective_summary_fn=fns.scorer_objective_summary_fn,
                    oracle_score_for_stage_fn=fns.oracle_score_for_stage_fn,
                    weights_text_fn=fns.weights_text_fn,
                    mark_oracle_decision_use_fn=fns.mark_oracle_decision_use_fn,
                    print_stage_preview_fn=fns.print_stage_preview_fn,
                    build_oracle_floor_guard_result_fn=fns.build_oracle_floor_guard_result_fn,
                    build_iteration_payloads_fn=fns.build_iteration_payloads_fn,
                    derive_outcome_code_fn=fns.derive_outcome_code_fn,
                    commit_iteration_with_checkpoint_fn=fns.commit_iteration_with_checkpoint_fn,
                    run_stage1_substitution_fn=fns.run_stage1_substitution_fn,
                    run_stage2_search_fn=fns.run_stage2_search_fn,
                    finalize_stage2_archive_fn=fns.finalize_stage2_archive_fn,
                )
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

                stage3_flow = fns.run_stage3_iteration_flow_fn(
                    state=dict(locals()),
                    stage3_runtime_call_ctx=stage3_runtime_call_ctx,
                    stage3_two_phase_enabled=bool(config.stage3_two_phase_enabled),
                    stage3_continue_after_solve=bool(config.stage3_continue_after_solve),
                    stage3_phasea_cfg_default=dict(config.stage3_phasea_cfg_default),
                    stage3_phaseb_cfg_default=dict(config.stage3_phaseb_cfg_default),
                    stage3_phaseb_top_n_default=int(config.stage3_phaseb_top_n),
                    stage3_phaseb_gate_delta_floor_default=float(config.stage3_phaseb_gate_delta_floor),
                    stage3_phaseb_gate_end_gain_floor_default=float(config.stage3_phaseb_gate_end_gain_floor),
                    solver_stage3_default_cfg=dict(config.solver_stage3_default_cfg),
                    stage3_span_basin_judge_k=int(config.stage3_span_basin_judge_k),
                    tier_heartbeat_seconds=float(config.tier_heartbeat_seconds),
                    solve_match_threshold=float(config.solve_match_threshold),
                    stall_delta=float(config.stall_delta),
                    stall_stage_limit=int(config.stall_stage_limit),
                    evaluate_stage3_entry_policy_fn=fns.evaluate_stage3_entry_policy_fn,
                    prepare_stage3_refine_inputs_fn=fns.prepare_stage3_refine_inputs_fn,
                    summarize_stage3_span_fn=fns.summarize_stage3_span_fn,
                    mark_oracle_decision_use_fn=fns.mark_oracle_decision_use_fn,
                    print_stage_preview_fn=fns.print_stage_preview_fn,
                    fmt_finite_float_fn=fns.fmt_finite_float_fn,
                    log_prefix=str(log_prefix),
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
