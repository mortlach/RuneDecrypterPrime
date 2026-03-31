from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Mapping

import numpy as np

from tools.benchmarks.periodic_sub_trans.common.policy_spec import AdaptivePolicySpec
from tools.benchmarks.periodic_sub_trans.common.pool import CandidatePool
from tools.benchmarks.periodic_sub_trans.common.stage_engine import StageEngine
from tools.benchmarks.periodic_sub_trans.common.stage_spec import (
    AuxObjectiveBinding,
    ObjectiveRef,
    SpanProfile,
    SpanRole,
    SpanScope,
    StageSpec,
)
from tools.benchmarks.periodic_sub_trans.no_wli.stage3_runtime_state_contract import (
    extract_stage3_runtime_config_state,
)


@dataclass(frozen=True)
class IterationStageEngineResult:
    pre_stage3: Dict[str, Any]
    stage3_flow: Dict[str, Any]
    events: list[Dict[str, Any]]


_PRE_STAGE3_STATE_KEYS = (
    "tier",
    "text_id",
    "key_seed",
    "off",
    "offset_used",
    "pt_idx",
    "wli",
    "direction",
    "span_assets_dir",
    "scoring_experiment_meta",
    "oracle_mode",
    "oracle_consulted_in_decisions",
    "oracle_decision_paths_enabled",
    "oracle_assist_selection_effective",
    "stages",
    "instances",
)

_STAGE3_BASE_STATE_KEYS = (
    "tier",
    "text_id",
    "key_seed",
    "t0_i",
    "pt_idx",
    "wli",
    "direction",
    "oracle_decision_paths_enabled",
    "oracle_assist_selection_effective",
    "stages",
)

def _select_state_keys(
    *,
    state: Mapping[str, Any],
    keys: tuple[str, ...],
) -> Dict[str, Any]:
    return {key: state[key] for key in keys}


def _build_pre_stage3_state(
    *,
    state: Mapping[str, Any],
) -> Dict[str, Any]:
    selected = _select_state_keys(state=state, keys=_PRE_STAGE3_STATE_KEYS)
    selected["pt_idx"] = np.asarray(selected["pt_idx"], dtype=np.uint8)
    selected["scoring_experiment_meta"] = dict(selected["scoring_experiment_meta"])
    return selected


def _build_stage3_state(
    *,
    state: Mapping[str, Any],
    pre_stage3_out: Mapping[str, Any],
    config: Any,
) -> Dict[str, Any]:
    stage3_state = _select_state_keys(state=state, keys=_STAGE3_BASE_STATE_KEYS)
    stage3_state.update(extract_stage3_runtime_config_state(state=state))
    stage3_state["pt_idx"] = np.asarray(stage3_state["pt_idx"], dtype=np.uint8)
    stage3_state["STAGE35_ENABLED"] = bool(
        state.get(
            "STAGE35_ENABLED",
            getattr(config, "stage35_enabled", False),
        )
    )
    stage3_state["STAGE35_CFG"] = dict(
        state.get(
            "STAGE35_CFG",
            getattr(config, "stage35_cfg", {}),
        )
        or {}
    )
    stage3_state["key_len"] = int(pre_stage3_out["key_len"])
    stage3_state["full_cipher"] = pre_stage3_out["full_cipher"]
    stage3_state["ct_idx"] = np.asarray(pre_stage3_out["ct_idx"], dtype=np.uint8)
    stage3_state["scorer_stage2"] = dict(pre_stage3_out["scorer_stage2"])
    stage3_state["scorer_full"] = dict(pre_stage3_out["scorer_full"])
    stage3_state["scorer_stage3_phaseA"] = dict(pre_stage3_out["scorer_stage3_phaseA"])
    stage3_state["scorer_stage3_phaseB"] = dict(pre_stage3_out["scorer_stage3_phaseB"])
    stage3_state["scorer_stage3_search_runtime"] = pre_stage3_out["scorer_stage3_search_runtime"]
    stage3_state["scorer_basin_judge_runtime"] = pre_stage3_out["scorer_basin_judge_runtime"]
    stage3_state["scorer_full_runtime"] = pre_stage3_out["scorer_full_runtime"]
    stage3_state["scorer_stage3_phaseA_runtime"] = pre_stage3_out["scorer_stage3_phaseA_runtime"]
    stage3_state["scorer_word_ngram_report_runtime"] = pre_stage3_out.get(
        "scorer_word_ngram_report_runtime",
        None,
    )
    stage3_state["oracle_s1"] = float(pre_stage3_out["oracle_s1"])
    stage3_state["oracle_s2"] = float(pre_stage3_out["oracle_s2"])
    stage3_state["oracle_s3"] = float(pre_stage3_out["oracle_s3"])
    stage3_state["stage3_phaseA_experiment"] = str(pre_stage3_out["stage3_phaseA_experiment"])
    stage3_state["stage3_phaseB_experiment"] = str(pre_stage3_out["stage3_phaseB_experiment"])
    stage3_state["stage3_phaseB_char_pct_min_dynamic"] = float(
        pre_stage3_out["stage3_phaseB_char_pct_min_dynamic"]
    )
    stage3_state["stage3_phaseB_char_pct_min_source"] = str(
        pre_stage3_out["stage3_phaseB_char_pct_min_source"]
    )
    stage3_state["sub_key_match"] = float(pre_stage3_out["sub_key_match"])
    stage3_state["stage1_best_score"] = float(pre_stage3_out["stage1_best_score"])
    stage3_state["ev1"] = int(pre_stage3_out["ev1"])
    stage3_state["best2_match"] = float(pre_stage3_out["best2_match"])
    stage3_state["best2_score"] = float(pre_stage3_out["best2_score"])
    stage3_state["best2_key"] = pre_stage3_out["best2_key"]
    stage3_state["best2_pt"] = pre_stage3_out["best2_pt"]
    stage3_state["best2_preview"] = str(pre_stage3_out["best2_preview"])
    stage3_state["stage2_evals_total"] = int(pre_stage3_out["stage2_evals_total"])
    stage3_state["stage2_archive"] = dict(pre_stage3_out["stage2_archive"])
    stage3_state["stage2_continue_to_gate"] = bool(pre_stage3_out["stage2_continue_to_gate"])
    stage3_state["stage2_continue_stop_reason"] = str(pre_stage3_out["stage2_continue_stop_reason"])
    stage3_state["stage2_ranked"] = list(pre_stage3_out["stage2_ranked"])
    stage3_state["stage2_promoted"] = list(pre_stage3_out["stage2_promoted"])
    stage3_state["stage2_entry_score"] = float(pre_stage3_out["stage2_entry_score"])
    stage3_state["stage2_entry_score_judge"] = float(pre_stage3_out["stage2_entry_score_judge"])
    stage3_state["stage2_score_match_spearman"] = float(pre_stage3_out["stage2_score_match_spearman"])
    stage3_state["stage2_topk_payload"] = list(pre_stage3_out["stage2_topk_payload"])
    stage3_state["stage2_topk_has_best_match"] = bool(pre_stage3_out["stage2_topk_has_best_match"])
    return stage3_state


def _validate_stage_engine_fns(fns: Any) -> None:
    required = (
        "run_iteration_pre_stage3_fn",
        "run_stage3_iteration_flow_fn",
        "build_iteration_runtime_fn",
        "evaluate_oracle_precheck_fn",
        "handle_oracle_floor_guard_if_triggered_fn",
        "run_stage12_pipeline_fn",
        "scorer_objective_summary_fn",
        "oracle_score_for_stage_fn",
        "weights_text_fn",
        "mark_oracle_decision_use_fn",
        "print_stage_preview_fn",
        "build_oracle_floor_guard_result_fn",
        "build_iteration_payloads_fn",
        "derive_outcome_code_fn",
        "commit_iteration_with_checkpoint_fn",
        "run_stage1_substitution_fn",
        "run_stage2_search_fn",
        "finalize_stage2_archive_fn",
        "evaluate_stage3_entry_policy_fn",
        "prepare_stage3_refine_inputs_fn",
        "summarize_stage3_span_fn",
        "fmt_finite_float_fn",
    )
    for name in required:
        value = getattr(fns, name, None)
        if not callable(value):
            raise TypeError(
                f"StageEngine bridge requires callable '{name}' on fns object"
            )


def run_iteration_with_stage_engine(
    *,
    state: Mapping[str, Any],
    config: Any,
    fns: Any,
    stage3_runtime_call_ctx: Any,
    log_prefix: str = "[pipeline_no_wli]",
) -> IterationStageEngineResult:
    _validate_stage_engine_fns(fns)
    pre_stage3_out: Dict[str, Any] = {}
    stage3_flow_out: Dict[str, Any] = {}

    def _shadow_counterfactual_fn(
        *,
        stage: StageSpec,
        pool_before: CandidatePool,
        pool_after: CandidatePool,
        policy: AdaptivePolicySpec,
    ) -> Dict[str, Any]:
        _ = pool_before, pool_after, policy
        if str(stage.stage_id) != "stage_c_refine":
            return {}
        stage2_topk = list(pre_stage3_out.get("stage2_topk_payload", []))
        stage3_topk = list(stage3_flow_out.get("stage3_topk_payload", []))

        def _winner_id(rows: list[Mapping[str, Any]]) -> str:
            if not rows:
                return ""
            row0 = dict(rows[0])
            end_hash = str(row0.get("end_hash", "")).strip()
            if end_hash:
                return end_hash
            return str(row0.get("key", ""))[:128]

        actual_winner_id = _winner_id(stage3_topk)
        shadow_winner_id = _winner_id(stage2_topk)
        actual_rank = None
        if actual_winner_id:
            for idx, row in enumerate(stage2_topk, start=1):
                if str(dict(row).get("end_hash", "")).strip() == actual_winner_id:
                    actual_rank = int(idx)
                    break
        return dict(
            shadow_span_winner_id=str(shadow_winner_id),
            shadow_span_changed_winner=bool(
                bool(actual_winner_id)
                and bool(shadow_winner_id)
                and str(actual_winner_id) != str(shadow_winner_id)
            ),
            shadow_span_rank_of_actual_winner=(
                int(actual_rank) if actual_rank is not None else None
            ),
            shadow_keep_ids=[str(dict(r).get("end_hash", "")).strip() for r in stage2_topk[:5]],
            shadow_drop_ids=[str(dict(r).get("end_hash", "")).strip() for r in stage2_topk[5:10]],
            stage2_topk_count=int(len(stage2_topk)),
            stage3_topk_count=int(len(stage3_topk)),
        )

    role_raw = str(getattr(config, "stage3_span_aux_role", "off")).strip().lower()
    scope_raw = str(getattr(config, "stage3_span_aux_scope", "basin_rep")).strip().lower()
    profile_raw = str(getattr(config, "stage3_span_aux_profile", "lite")).strip().lower()
    role = SpanRole(role_raw) if role_raw in {r.value for r in SpanRole} else SpanRole.OFF
    scope = SpanScope(scope_raw) if scope_raw in {s.value for s in SpanScope} else SpanScope.BASIN_REP
    profile = (
        SpanProfile(profile_raw)
        if profile_raw in {p.value for p in SpanProfile}
        else SpanProfile.LITE
    )
    aux_stage3 = tuple()
    if role != SpanRole.OFF:
        aux_stage3 = (
            AuxObjectiveBinding(
                objective=ObjectiveRef(
                    objective_id="span_hamming",
                    family="span_hamming",
                    normalisation="avg",
                    window_policy="full_text",
                ),
                role=role,
                scope=scope,
                span_profile=profile,
                two_pass_enabled=bool(getattr(config, "stage3_span_aux_two_pass", False)),
                full_top_m=int(getattr(config, "stage3_span_aux_full_top_m", 0)),
                cadence_every=1,
                budget_ms=float(max(0.0, float(getattr(config, "stage3_span_aux_budget_ms", 0.0)))),
            ),
        )

    stages = [
        StageSpec(
            stage_id="stage_ab_pre_stage3",
            search_objective=ObjectiveRef(
                objective_id=str(config.stage1_label),
                family="char_ngram",
                normalisation="avg",
                window_policy="full_text",
            ),
            decision_objective=ObjectiveRef(
                objective_id=str(config.stage2_label),
                family="char_ngram",
                normalisation="avg",
                window_policy="full_text",
            ),
        ),
        StageSpec(
            stage_id="stage_c_refine",
            search_objective=ObjectiveRef(
                objective_id=str(config.stage3_label),
                family="char_ngram",
                normalisation="avg",
                window_policy="full_text",
            ),
            decision_objective=ObjectiveRef(
                objective_id=str(config.stage3_label),
                family="char_ngram",
                normalisation="avg",
                window_policy="full_text",
            ),
            aux_objectives=aux_stage3,
        ),
    ]
    policy = AdaptivePolicySpec(
        policy_id="no_wli_iter_orch_v1",
        ambiguity_expand_top_k=int(max(0, int(getattr(config, "span_selection_top_k", 0)))),
    )

    def _run_stage(stage: StageSpec, _pool: CandidatePool, _ctx: Mapping[str, Any]) -> CandidatePool:
        nonlocal pre_stage3_out, stage3_flow_out
        if str(stage.stage_id) == "stage_ab_pre_stage3":
            pre_stage3_out = fns.run_iteration_pre_stage3_fn(
                state=_build_pre_stage3_state(state=state),
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
            return CandidatePool([])

        if bool(pre_stage3_out.get("continue_iteration", False)):
            stage3_flow_out = {}
            return CandidatePool([])

        stage3_state = _build_stage3_state(
            state=state,
            pre_stage3_out=pre_stage3_out,
            config=config,
        )

        aux_two_pass_enabled = bool(getattr(config, "stage3_span_aux_two_pass", False))
        effective_two_phase_enabled = bool(config.stage3_two_phase_enabled) or bool(
            aux_two_pass_enabled
        )
        effective_phaseb_top_n = int(config.stage3_phaseb_top_n)
        if bool(aux_two_pass_enabled):
            full_top_m = int(max(0, int(getattr(config, "stage3_span_aux_full_top_m", 0))))
            if full_top_m > 0:
                effective_phaseb_top_n = int(max(1, full_top_m))

        stage3_flow_out = fns.run_stage3_iteration_flow_fn(
            state=stage3_state,
            stage3_runtime_call_ctx=stage3_runtime_call_ctx,
            stage3_two_phase_enabled=bool(effective_two_phase_enabled),
            stage3_continue_after_solve=bool(config.stage3_continue_after_solve),
            stage3_phasea_cfg_default=dict(config.stage3_phasea_cfg_default),
            stage3_phaseb_cfg_default=dict(config.stage3_phaseb_cfg_default),
            stage3_phaseb_top_n_default=int(effective_phaseb_top_n),
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
        return CandidatePool([])

    engine = StageEngine(stages=stages, policy=policy, run_stage_fn=_run_stage)
    engine.run(
        seed_pool=CandidatePool([]),
        context=dict(
            span_decision_role_enabled=bool(
                getattr(config, "span_decision_role_enabled", False)
            ),
            span_reps_per_basin=int(max(1, int(getattr(config, "span_reps_per_basin", 1)))),
            span_selection_top_k=int(max(0, int(getattr(config, "span_selection_top_k", 0)))),
            span_p90_call_ms=getattr(config, "span_p90_call_ms", None),
            span_shadow_counterfactual_fn=_shadow_counterfactual_fn,
        ),
    )
    return IterationStageEngineResult(
        pre_stage3=dict(pre_stage3_out),
        stage3_flow=dict(stage3_flow_out),
        events=[dict(evt) for evt in engine.events],
    )
