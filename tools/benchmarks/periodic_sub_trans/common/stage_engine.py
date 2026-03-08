from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from tools.benchmarks.periodic_sub_trans.common.policy_spec import AdaptivePolicySpec
from tools.benchmarks.periodic_sub_trans.common.pool import CandidatePool
from tools.benchmarks.periodic_sub_trans.common.stage_spec import SpanRole, SpanScope, StageSpec
from tools.benchmarks.periodic_sub_trans.common.trace_writer import StageTraceWriter


StageRunnerFn = Callable[[StageSpec, CandidatePool, Mapping[str, Any]], CandidatePool]


@dataclass
class StageEngine:
    stages: list[StageSpec]
    policy: AdaptivePolicySpec
    run_stage_fn: StageRunnerFn
    trace_writer: StageTraceWriter | None = None
    events: list[dict[str, Any]] = field(default_factory=list)

    def run(self, *, seed_pool: CandidatePool, context: Mapping[str, Any]) -> CandidatePool:
        pool = CandidatePool(list(seed_pool.candidates))
        for index, stage in enumerate(self.stages):
            aux_bindings = [
                dict(
                    objective_id=str(binding.objective.objective_id),
                    role=str(binding.role.value),
                    scope=str(binding.scope.value),
                    span_profile=str(binding.span_profile.value),
                    two_pass_enabled=bool(binding.two_pass_enabled),
                    full_top_m=int(binding.full_top_m),
                    cadence_every=int(binding.cadence_every),
                    budget_ms=float(binding.budget_ms),
                )
                for binding in stage.aux_objectives
            ]
            aux_roles = {str(binding.role.value) for binding in stage.aux_objectives}
            span_decision_role_enabled = bool(context.get("span_decision_role_enabled", False))
            decision_roles = {
                SpanRole.PRUNE,
                SpanRole.GATE,
                SpanRole.COMBINED,
                SpanRole.JUDGE,
            }
            aux_decision_influence = bool(
                span_decision_role_enabled
                and any(binding.role in decision_roles for binding in stage.aux_objectives)
            )
            span_enabled = bool(
                stage.aux_objectives
                and any(binding.role != SpanRole.OFF for binding in stage.aux_objectives)
            )
            span_telemetry = dict(
                span_calls_total=0,
                span_calls_active=0,
                span_calls_rejected_or_gated=0,
                span_seconds_total=0.0,
                span_active_rate=0.0,
                span_active_rate_source=(
                    "stage_engine_default_zero_enabled" if span_enabled else "stage_engine_default_zero_disabled"
                ),
            )
            self._emit(
                dict(
                    event="stage_start",
                    stage_id=stage.stage_id,
                    stage_index=int(index),
                    in_pool_size=int(len(pool.candidates)),
                    aux_bindings=aux_bindings,
                    aux_decision_influence=bool(aux_decision_influence),
                    span_decision_role_enabled=bool(span_decision_role_enabled),
                    shadow_mode_active=bool(SpanRole.SHADOW.value in aux_roles),
                    **span_telemetry,
                )
            )
            if span_enabled:
                self._emit(
                    dict(
                        event="span_decision_mode",
                        stage_id=stage.stage_id,
                        stage_index=int(index),
                        span_decision_role_enabled=bool(span_decision_role_enabled),
                        aux_decision_influence=bool(aux_decision_influence),
                    )
                )
            span_p90_call_ms_raw = context.get("span_p90_call_ms", None)
            span_p90_call_ms = (
                float(span_p90_call_ms_raw)
                if span_p90_call_ms_raw is not None
                else None
            )
            if span_p90_call_ms is not None and span_p90_call_ms <= 0.0:
                span_p90_call_ms = None
            budget_rows: list[dict[str, Any]] = []
            for binding in stage.aux_objectives:
                if binding.role == SpanRole.OFF:
                    continue
                calls_affordable: int | None = None
                if span_p90_call_ms is not None:
                    calls_affordable = int(max(0, int(binding.budget_ms // span_p90_call_ms)))
                budget_rows.append(
                    dict(
                        objective_id=str(binding.objective.objective_id),
                        role=str(binding.role.value),
                        budget_ms=float(binding.budget_ms),
                        span_p90_call_ms=span_p90_call_ms,
                        calls_affordable=calls_affordable,
                    )
                )
                if bool(binding.two_pass_enabled):
                    self._emit(
                        dict(
                            event="span_two_pass_plan",
                            stage_id=stage.stage_id,
                            stage_index=int(index),
                            objective_id=str(binding.objective.objective_id),
                            role=str(binding.role.value),
                            lite_scope=str(binding.scope.value),
                            full_top_m=int(binding.full_top_m),
                        )
                    )
            if budget_rows:
                self._emit(
                    dict(
                        event="span_budget_plan",
                        stage_id=stage.stage_id,
                        stage_index=int(index),
                        budgets=budget_rows,
                    )
                )
            try:
                out = self.run_stage_fn(stage, pool, context)
            except Exception as exc:
                self._emit(
                    dict(
                        event="error",
                        stage_id=stage.stage_id,
                        stage_index=int(index),
                        error_type=str(type(exc).__name__),
                        error_message=str(exc),
                    )
                )
                raise
            in_pool_before_shape = CandidatePool(list(out.candidates))
            if span_enabled and stage.aux_objectives:
                selection_top_k = int(
                    max(
                        0,
                        int(context.get("span_selection_top_k", 0) or 0),
                    )
                )
                reps_per_basin = int(
                    max(
                        1,
                        int(context.get("span_reps_per_basin", 1) or 1),
                    )
                )
                for binding in stage.aux_objectives:
                    if binding.role == SpanRole.OFF:
                        continue
                    scope = binding.scope
                    selected_pool = in_pool_before_shape
                    ambiguity_expand_top_k = int(
                        max(0, int(getattr(self.policy, "ambiguity_expand_top_k", 0)))
                    )
                    if scope == SpanScope.BASIN_REP:
                        selected_pool = in_pool_before_shape.select_basin_representatives(
                            reps_per_basin=reps_per_basin
                        )
                        if ambiguity_expand_top_k > 0:
                            expanded = in_pool_before_shape.promote_top(
                                int(ambiguity_expand_top_k)
                            )
                            merged = CandidatePool(
                                list(selected_pool.candidates) + list(expanded.candidates)
                            )
                            selected_pool = merged.dedupe()
                    elif scope == SpanScope.TOPK:
                        k_eff = selection_top_k if selection_top_k > 0 else int(stage.pool_keep)
                        if k_eff > 0:
                            selected_pool = in_pool_before_shape.promote_top(k_eff)
                    calls_affordable: int | None = None
                    if span_p90_call_ms is not None:
                        calls_affordable = int(
                            max(0, int(float(binding.budget_ms) // float(span_p90_call_ms)))
                        )
                    budget_clamped = False
                    if calls_affordable is not None:
                        before_n = int(len(selected_pool.candidates))
                        selected_pool = selected_pool.promote_top(int(calls_affordable))
                        budget_clamped = int(len(selected_pool.candidates)) < before_n
                    selected_ids = [str(row.candidate_id) for row in selected_pool.sorted_by_decision()[:32]]
                    self._emit(
                        dict(
                            event="span_eval_selection_plan",
                            stage_id=stage.stage_id,
                            stage_index=int(index),
                            objective_id=str(binding.objective.objective_id),
                            role=str(binding.role.value),
                            scope=str(binding.scope.value),
                            reps_per_basin=int(reps_per_basin),
                            top_k=int(selection_top_k),
                            ambiguity_expand_top_k=int(ambiguity_expand_top_k),
                            selected_count=int(len(selected_pool.candidates)),
                            total_candidates=int(len(in_pool_before_shape.candidates)),
                            calls_affordable=calls_affordable,
                            budget_clamped=bool(budget_clamped),
                            selected_candidate_ids=selected_ids,
                        )
                    )
            # Apply common dedupe/diversity/promotion shaping.
            out = out.dedupe()
            if bool(dict(stage.params).get("dedupe_by_basin", False)):
                out = out.dedupe_by_basin()
            if int(stage.basin_cap) > 0:
                out = out.cap_per_basin(int(stage.basin_cap))
            if int(stage.pool_keep) > 0:
                out = out.promote_top(int(stage.pool_keep))

            shadow_counterfactual_fn = context.get("span_shadow_counterfactual_fn")
            if span_enabled and callable(shadow_counterfactual_fn):
                try:
                    payload_raw = shadow_counterfactual_fn(
                        stage=stage,
                        pool_before=in_pool_before_shape,
                        pool_after=out,
                        policy=self.policy,
                    )
                    payload = dict(payload_raw) if isinstance(payload_raw, Mapping) else {}
                except Exception as exc:
                    payload = dict(error_type=str(type(exc).__name__), error_message=str(exc))
                self._emit(
                    dict(
                        event="span_shadow_counterfactual",
                        stage_id=stage.stage_id,
                        stage_index=int(index),
                        **payload,
                    )
                )
            pool = out
            self._emit(
                dict(
                    event="stage_end",
                    stage_id=stage.stage_id,
                    stage_index=int(index),
                    out_pool_size=int(len(pool.candidates)),
                    policy_id=str(self.policy.policy_id),
                    **span_telemetry,
                )
            )
        return pool

    def _emit(self, event: dict[str, Any]) -> None:
        payload = dict(event)
        self.events.append(payload)
        if self.trace_writer is not None:
            self.trace_writer.append(payload)
