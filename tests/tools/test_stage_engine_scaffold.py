from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.benchmarks.periodic_sub_trans.common import (
    AdaptivePolicySpec,
    CandidatePool,
    CandidateRecord,
    ObjectiveRef,
    SpanRole,
    SpanScope,
    SpanProfile,
    AuxObjectiveBinding,
    StageEngine,
    StageSpec,
    StageTraceWriter,
)
from tools.benchmarks.periodic_sub_trans.common.pool import basin_id_from_payload


pytestmark = pytest.mark.tier_a


def test_stage_spec_json_roundtrip_is_stable() -> None:
    spec = StageSpec(
        stage_id="stage_a",
        search_objective=ObjectiveRef("A_char1", "char_ngram", "avg", "full_text"),
        decision_objective=ObjectiveRef("M_char12", "char_ngram", "avg", "full_text"),
        aux_objectives=(
            AuxObjectiveBinding(
                objective=ObjectiveRef("span", "span_hamming", "avg", "full_text"),
                role=SpanRole.SHADOW,
                cadence_every=5,
                budget_ms=2.5,
            ),
        ),
        pool_keep=16,
        promote_top=8,
        basin_cap=4,
        params={"k": 1},
    )
    payload = spec.to_json_dict()
    cloned = StageSpec.from_json_dict(payload)
    assert cloned.to_json_dict() == payload


def test_candidate_pool_dedupe_and_basin_cap() -> None:
    pool = CandidatePool(
        [
            CandidateRecord("a", "b1", 0.9, 0.6),
            CandidateRecord("a", "b1", 0.8, 0.5),
            CandidateRecord("b", "b1", 0.7, 0.4),
            CandidateRecord("c", "b2", 0.6, 0.3),
        ]
    )
    out = pool.dedupe().cap_per_basin(1)
    ids = [row.candidate_id for row in out.sorted_by_decision()]
    assert ids == ["a", "c"]


def test_stage_engine_emits_trace_and_shapes_pool(tmp_path: Path) -> None:
    trace_file = tmp_path / "trace.jsonl"
    writer = StageTraceWriter(trace_file)
    stages = [
        StageSpec(
            stage_id="stage_a",
            search_objective=ObjectiveRef("A", "char_ngram", "avg", "full_text"),
            decision_objective=ObjectiveRef("A", "char_ngram", "avg", "full_text"),
            pool_keep=2,
            basin_cap=1,
        ),
    ]
    policy = AdaptivePolicySpec(policy_id="default")

    def _runner(stage: StageSpec, pool: CandidatePool, _ctx):
        return CandidatePool(
            [
                CandidateRecord("k1", "b1", 0.9, 0.3),
                CandidateRecord("k2", "b1", 0.8, 0.2),
                CandidateRecord("k3", "b2", 0.7, 0.1),
            ]
        )

    engine = StageEngine(stages=stages, policy=policy, run_stage_fn=_runner, trace_writer=writer)
    out = engine.run(seed_pool=CandidatePool([]), context={})
    assert [row.candidate_id for row in out.sorted_by_decision()] == ["k1", "k3"]
    lines = trace_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert '"event":"stage_start"' in lines[0]
    assert '"event":"stage_end"' in lines[1]


def test_stage_trace_writer_path_payloads_are_trace_root_relative(tmp_path: Path) -> None:
    trace_file = tmp_path / "trace" / "stage_engine_trace.jsonl"
    writer = StageTraceWriter(trace_file)
    artifact = tmp_path / "trace" / "artifacts" / "stage_a.json"

    writer.append(
        {
            "event": "artifact",
            "path": artifact,
            "nested": {"paths": [artifact]},
        }
    )

    row = json.loads(trace_file.read_text(encoding="utf-8"))
    assert row["path"] == "artifacts/stage_a.json"
    assert row["nested"]["paths"] == ["artifacts/stage_a.json"]


def test_stage_trace_writer_relative_path_payloads_are_preserved(tmp_path: Path) -> None:
    trace_file = tmp_path / "trace" / "stage_engine_trace.jsonl"
    writer = StageTraceWriter(trace_file)

    writer.append({"event": "artifact", "path": Path("artifacts/stage_a.json")})

    row = json.loads(trace_file.read_text(encoding="utf-8"))
    assert row["path"] == "artifacts/stage_a.json"


def test_stage_trace_writer_external_path_payloads_are_redacted(tmp_path: Path) -> None:
    trace_file = tmp_path / "trace" / "stage_engine_trace.jsonl"
    writer = StageTraceWriter(trace_file)
    external_path = tmp_path / "outside-trace-root.json"

    writer.append({"event": "artifact", "path": external_path})

    row = json.loads(trace_file.read_text(encoding="utf-8"))
    assert row["path"] == "<external>"


def test_stage_engine_emits_error_event_before_raising(tmp_path: Path) -> None:
    trace_file = tmp_path / "trace.jsonl"
    writer = StageTraceWriter(trace_file)
    stages = [
        StageSpec(
            stage_id="stage_a",
            search_objective=ObjectiveRef("A", "char_ngram", "avg", "full_text"),
            decision_objective=ObjectiveRef("A", "char_ngram", "avg", "full_text"),
        ),
    ]
    policy = AdaptivePolicySpec(policy_id="default")

    def _runner(stage: StageSpec, pool: CandidatePool, _ctx):
        _ = stage, pool, _ctx
        raise RuntimeError("boom")

    engine = StageEngine(stages=stages, policy=policy, run_stage_fn=_runner, trace_writer=writer)
    with pytest.raises(RuntimeError):
        engine.run(seed_pool=CandidatePool([]), context={})
    lines = trace_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert '"event":"stage_start"' in lines[0]
    assert '"event":"error"' in lines[1]


def test_candidate_record_from_payload_prefers_end_hash_for_basin() -> None:
    payload = {"start_hash": "s1", "end_hash": "e1"}
    row = CandidateRecord.from_payload(
        candidate_id="k1",
        decision_score=1.0,
        match_ratio=0.5,
        payload=payload,
    )
    assert row.basin_id == "e1"
    assert basin_id_from_payload(payload, fallback="x") == "e1"


def test_stage_engine_optional_dedupe_by_basin() -> None:
    stages = [
        StageSpec(
            stage_id="stage_a",
            search_objective=ObjectiveRef("A", "char_ngram", "avg", "full_text"),
            decision_objective=ObjectiveRef("A", "char_ngram", "avg", "full_text"),
            params={"dedupe_by_basin": True},
            pool_keep=16,
            basin_cap=0,
        ),
    ]
    policy = AdaptivePolicySpec(policy_id="default")

    def _runner(stage: StageSpec, pool: CandidatePool, _ctx):
        _ = stage, pool, _ctx
        return CandidatePool(
            [
                CandidateRecord("k1", "b1", 0.9, 0.3),
                CandidateRecord("k2", "b1", 0.8, 0.2),
                CandidateRecord("k3", "b2", 0.7, 0.1),
            ]
        )

    engine = StageEngine(stages=stages, policy=policy, run_stage_fn=_runner)
    out = engine.run(seed_pool=CandidatePool([]), context={})
    assert [row.candidate_id for row in out.sorted_by_decision()] == ["k1", "k3"]


def test_stage_engine_shadow_aux_does_not_change_pool_outcome() -> None:
    obj = ObjectiveRef("span", "span_hamming", "avg", "full_text")
    stage_plain = StageSpec(
        stage_id="stage_a",
        search_objective=ObjectiveRef("A", "char_ngram", "avg", "full_text"),
        decision_objective=ObjectiveRef("A", "char_ngram", "avg", "full_text"),
        params={"dedupe_by_basin": True},
        pool_keep=2,
        basin_cap=1,
    )
    stage_shadow = StageSpec(
        stage_id="stage_a",
        search_objective=ObjectiveRef("A", "char_ngram", "avg", "full_text"),
        decision_objective=ObjectiveRef("A", "char_ngram", "avg", "full_text"),
        aux_objectives=(
            AuxObjectiveBinding(
                objective=obj,
                role=SpanRole.SHADOW,
                scope=SpanScope.BASIN_REP,
                span_profile=SpanProfile.LITE,
                cadence_every=1,
                budget_ms=3.0,
            ),
        ),
        params={"dedupe_by_basin": True},
        pool_keep=2,
        basin_cap=1,
    )
    policy = AdaptivePolicySpec(policy_id="default")

    def _runner(stage: StageSpec, pool: CandidatePool, _ctx):
        _ = stage, pool, _ctx
        return CandidatePool(
            [
                CandidateRecord("k1", "b1", 0.9, 0.3),
                CandidateRecord("k2", "b1", 0.8, 0.2),
                CandidateRecord("k3", "b2", 0.7, 0.1),
            ]
        )

    out_plain = StageEngine(stages=[stage_plain], policy=policy, run_stage_fn=_runner).run(
        seed_pool=CandidatePool([]),
        context={},
    )
    out_shadow = StageEngine(stages=[stage_shadow], policy=policy, run_stage_fn=_runner).run(
        seed_pool=CandidatePool([]),
        context={},
    )
    ids_plain = [row.candidate_id for row in out_plain.sorted_by_decision()]
    ids_shadow = [row.candidate_id for row in out_shadow.sorted_by_decision()]
    assert ids_plain == ids_shadow


def test_stage_engine_stage_start_includes_aux_shadow_contract() -> None:
    stage = StageSpec(
        stage_id="stage_a",
        search_objective=ObjectiveRef("A", "char_ngram", "avg", "full_text"),
        decision_objective=ObjectiveRef("A", "char_ngram", "avg", "full_text"),
        aux_objectives=(
            AuxObjectiveBinding(
                objective=ObjectiveRef("span", "span_hamming", "avg", "full_text"),
                role=SpanRole.SHADOW,
                scope=SpanScope.TOPK,
                span_profile=SpanProfile.FULL,
                two_pass_enabled=True,
                full_top_m=10,
                cadence_every=2,
                budget_ms=4.0,
            ),
        ),
    )
    policy = AdaptivePolicySpec(policy_id="default")

    def _runner(stage: StageSpec, pool: CandidatePool, _ctx):
        _ = stage, pool, _ctx
        return CandidatePool([])

    engine = StageEngine(stages=[stage], policy=policy, run_stage_fn=_runner)
    engine.run(seed_pool=CandidatePool([]), context={})
    stage_start = next(evt for evt in engine.events if evt.get("event") == "stage_start")
    stage_end = next(evt for evt in engine.events if evt.get("event") == "stage_end")
    assert stage_start["aux_decision_influence"] is False
    assert stage_start["span_decision_role_enabled"] is False
    assert stage_start["shadow_mode_active"] is True
    assert isinstance(stage_start["aux_bindings"], list)
    assert stage_start["aux_bindings"][0]["role"] == "shadow"
    assert stage_start["aux_bindings"][0]["span_profile"] == "full"
    assert stage_start["aux_bindings"][0]["two_pass_enabled"] is True
    assert stage_start["aux_bindings"][0]["full_top_m"] == 10
    assert stage_start["span_calls_total"] == 0
    assert stage_start["span_calls_active"] == 0
    assert stage_start["span_calls_rejected_or_gated"] == 0
    assert stage_start["span_seconds_total"] == 0.0
    assert stage_start["span_active_rate"] == 0.0
    assert stage_start["span_active_rate_source"] == "stage_engine_default_zero_enabled"
    assert stage_end["span_active_rate"] == 0.0
    assert stage_end["span_active_rate_source"] == "stage_engine_default_zero_enabled"


def test_stage_engine_span_telemetry_defaults_when_aux_disabled() -> None:
    stage = StageSpec(
        stage_id="stage_a",
        search_objective=ObjectiveRef("A", "char_ngram", "avg", "full_text"),
        decision_objective=ObjectiveRef("A", "char_ngram", "avg", "full_text"),
    )
    policy = AdaptivePolicySpec(policy_id="default")

    def _runner(stage: StageSpec, pool: CandidatePool, _ctx):
        _ = stage, pool, _ctx
        return CandidatePool([])

    engine = StageEngine(stages=[stage], policy=policy, run_stage_fn=_runner)
    engine.run(seed_pool=CandidatePool([]), context={})
    stage_start = next(evt for evt in engine.events if evt.get("event") == "stage_start")
    assert stage_start["span_calls_total"] == 0
    assert stage_start["span_active_rate"] == 0.0
    assert stage_start["span_active_rate_source"] == "stage_engine_default_zero_disabled"


def test_stage_engine_emits_shadow_counterfactual_event_from_context_hook() -> None:
    stage = StageSpec(
        stage_id="stage_a",
        search_objective=ObjectiveRef("A", "char_ngram", "avg", "full_text"),
        decision_objective=ObjectiveRef("A", "char_ngram", "avg", "full_text"),
        aux_objectives=(
            AuxObjectiveBinding(
                objective=ObjectiveRef("span", "span_hamming", "avg", "full_text"),
                role=SpanRole.SHADOW,
                scope=SpanScope.BASIN_REP,
                span_profile=SpanProfile.LITE,
                cadence_every=1,
                budget_ms=2.0,
            ),
        ),
    )
    policy = AdaptivePolicySpec(policy_id="default")

    def _runner(stage: StageSpec, pool: CandidatePool, _ctx):
        _ = stage, pool, _ctx
        return CandidatePool(
            [
                CandidateRecord("k1", "b1", 0.9, 0.3),
                CandidateRecord("k2", "b2", 0.8, 0.2),
            ]
        )

    def _shadow_hook(*, stage: StageSpec, pool_before: CandidatePool, pool_after: CandidatePool, policy):
        _ = policy
        return dict(
            shadow_span_winner_id="k2",
            shadow_span_changed_winner=True,
            shadow_span_rank_of_actual_winner=2,
            in_candidates=len(pool_before.candidates),
            out_candidates=len(pool_after.candidates),
            stage=str(stage.stage_id),
        )

    engine = StageEngine(stages=[stage], policy=policy, run_stage_fn=_runner)
    engine.run(
        seed_pool=CandidatePool([]),
        context={"span_shadow_counterfactual_fn": _shadow_hook},
    )
    evt = next(e for e in engine.events if e.get("event") == "span_shadow_counterfactual")
    assert evt["stage_id"] == "stage_a"
    assert evt["shadow_span_winner_id"] == "k2"
    assert evt["shadow_span_changed_winner"] is True
    assert evt["shadow_span_rank_of_actual_winner"] == 2


def test_stage_engine_emits_span_budget_plan_with_affordable_calls() -> None:
    stage = StageSpec(
        stage_id="stage_a",
        search_objective=ObjectiveRef("A", "char_ngram", "avg", "full_text"),
        decision_objective=ObjectiveRef("A", "char_ngram", "avg", "full_text"),
        aux_objectives=(
            AuxObjectiveBinding(
                objective=ObjectiveRef("span", "span_hamming", "avg", "full_text"),
                role=SpanRole.SHADOW,
                scope=SpanScope.TOPK,
                span_profile=SpanProfile.LITE,
                cadence_every=1,
                budget_ms=25.0,
            ),
        ),
    )
    policy = AdaptivePolicySpec(policy_id="default")

    def _runner(stage: StageSpec, pool: CandidatePool, _ctx):
        _ = stage, pool, _ctx
        return CandidatePool([])

    engine = StageEngine(stages=[stage], policy=policy, run_stage_fn=_runner)
    engine.run(seed_pool=CandidatePool([]), context={"span_p90_call_ms": 4.0})
    evt = next(e for e in engine.events if e.get("event") == "span_budget_plan")
    budgets = evt["budgets"]
    assert isinstance(budgets, list) and len(budgets) == 1
    assert budgets[0]["objective_id"] == "span"
    assert budgets[0]["calls_affordable"] == 6


def test_candidate_pool_select_basin_representatives() -> None:
    pool = CandidatePool(
        [
            CandidateRecord("k1", "b1", 0.9, 0.3),
            CandidateRecord("k2", "b1", 0.8, 0.2),
            CandidateRecord("k3", "b2", 0.7, 0.1),
            CandidateRecord("k4", "b2", 0.6, 0.1),
        ]
    )
    reps = pool.select_basin_representatives(reps_per_basin=1)
    assert [row.candidate_id for row in reps.sorted_by_decision()] == ["k1", "k3"]


def test_stage_engine_emits_span_eval_selection_plan_for_basin_rep_scope() -> None:
    stage = StageSpec(
        stage_id="stage_a",
        search_objective=ObjectiveRef("A", "char_ngram", "avg", "full_text"),
        decision_objective=ObjectiveRef("A", "char_ngram", "avg", "full_text"),
        aux_objectives=(
            AuxObjectiveBinding(
                objective=ObjectiveRef("span", "span_hamming", "avg", "full_text"),
                role=SpanRole.SHADOW,
                scope=SpanScope.BASIN_REP,
                span_profile=SpanProfile.LITE,
                cadence_every=1,
                budget_ms=5.0,
            ),
        ),
    )
    policy = AdaptivePolicySpec(policy_id="default")

    def _runner(stage: StageSpec, pool: CandidatePool, _ctx):
        _ = stage, pool, _ctx
        return CandidatePool(
            [
                CandidateRecord("k1", "b1", 0.9, 0.3),
                CandidateRecord("k2", "b1", 0.8, 0.2),
                CandidateRecord("k3", "b2", 0.7, 0.1),
            ]
        )

    engine = StageEngine(stages=[stage], policy=policy, run_stage_fn=_runner)
    engine.run(seed_pool=CandidatePool([]), context={"span_reps_per_basin": 1})
    evt = next(e for e in engine.events if e.get("event") == "span_eval_selection_plan")
    assert evt["scope"] == "basin_rep"
    assert evt["selected_count"] == 2
    assert evt["total_candidates"] == 3
    assert evt["selected_candidate_ids"] == ["k1", "k3"]
    assert evt["ambiguity_expand_top_k"] == 0


def test_stage_engine_basin_rep_selection_supports_ambiguity_expansion() -> None:
    stage = StageSpec(
        stage_id="stage_a",
        search_objective=ObjectiveRef("A", "char_ngram", "avg", "full_text"),
        decision_objective=ObjectiveRef("A", "char_ngram", "avg", "full_text"),
        aux_objectives=(
            AuxObjectiveBinding(
                objective=ObjectiveRef("span", "span_hamming", "avg", "full_text"),
                role=SpanRole.SHADOW,
                scope=SpanScope.BASIN_REP,
                span_profile=SpanProfile.LITE,
                cadence_every=1,
                budget_ms=20.0,
            ),
        ),
    )
    policy = AdaptivePolicySpec(policy_id="default", ambiguity_expand_top_k=3)

    def _runner(stage: StageSpec, pool: CandidatePool, _ctx):
        _ = stage, pool, _ctx
        return CandidatePool(
            [
                CandidateRecord("k1", "b1", 0.9, 0.3),
                CandidateRecord("k2", "b1", 0.85, 0.25),
                CandidateRecord("k3", "b2", 0.8, 0.2),
                CandidateRecord("k4", "b3", 0.7, 0.1),
            ]
        )

    engine = StageEngine(stages=[stage], policy=policy, run_stage_fn=_runner)
    engine.run(seed_pool=CandidatePool([]), context={"span_reps_per_basin": 1})
    evt = next(e for e in engine.events if e.get("event") == "span_eval_selection_plan")
    assert evt["scope"] == "basin_rep"
    assert evt["ambiguity_expand_top_k"] == 3
    assert evt["selected_count"] >= 3
    assert "k2" in evt["selected_candidate_ids"]


def test_stage_engine_span_eval_selection_plan_respects_budget_clamp() -> None:
    stage = StageSpec(
        stage_id="stage_a",
        search_objective=ObjectiveRef("A", "char_ngram", "avg", "full_text"),
        decision_objective=ObjectiveRef("A", "char_ngram", "avg", "full_text"),
        aux_objectives=(
            AuxObjectiveBinding(
                objective=ObjectiveRef("span", "span_hamming", "avg", "full_text"),
                role=SpanRole.SHADOW,
                scope=SpanScope.TOPK,
                span_profile=SpanProfile.LITE,
                cadence_every=1,
                budget_ms=5.0,
            ),
        ),
        pool_keep=5,
    )
    policy = AdaptivePolicySpec(policy_id="default")

    def _runner(stage: StageSpec, pool: CandidatePool, _ctx):
        _ = stage, pool, _ctx
        return CandidatePool(
            [
                CandidateRecord("k1", "b1", 0.9, 0.3),
                CandidateRecord("k2", "b1", 0.8, 0.2),
                CandidateRecord("k3", "b2", 0.7, 0.1),
            ]
        )

    engine = StageEngine(stages=[stage], policy=policy, run_stage_fn=_runner)
    engine.run(seed_pool=CandidatePool([]), context={"span_p90_call_ms": 2.0, "span_selection_top_k": 3})
    evt = next(e for e in engine.events if e.get("event") == "span_eval_selection_plan")
    assert evt["calls_affordable"] == 2
    assert evt["budget_clamped"] is True
    assert evt["selected_count"] == 2


def test_stage_engine_emits_two_pass_plan_event() -> None:
    stage = StageSpec(
        stage_id="stage_a",
        search_objective=ObjectiveRef("A", "char_ngram", "avg", "full_text"),
        decision_objective=ObjectiveRef("A", "char_ngram", "avg", "full_text"),
        aux_objectives=(
            AuxObjectiveBinding(
                objective=ObjectiveRef("span", "span_hamming", "avg", "full_text"),
                role=SpanRole.SHADOW,
                scope=SpanScope.TOPK,
                span_profile=SpanProfile.LITE,
                two_pass_enabled=True,
                full_top_m=7,
                cadence_every=1,
                budget_ms=5.0,
            ),
        ),
    )
    policy = AdaptivePolicySpec(policy_id="default")

    def _runner(stage: StageSpec, pool: CandidatePool, _ctx):
        _ = stage, pool, _ctx
        return CandidatePool([CandidateRecord("k1", "b1", 1.0, 0.5)])

    engine = StageEngine(stages=[stage], policy=policy, run_stage_fn=_runner)
    engine.run(seed_pool=CandidatePool([]), context={})
    evt = next(e for e in engine.events if e.get("event") == "span_two_pass_plan")
    assert evt["objective_id"] == "span"
    assert evt["lite_scope"] == "topk"
    assert evt["full_top_m"] == 7


def test_stage_engine_decision_role_influence_requires_enable_flag() -> None:
    stage = StageSpec(
        stage_id="stage_a",
        search_objective=ObjectiveRef("A", "char_ngram", "avg", "full_text"),
        decision_objective=ObjectiveRef("A", "char_ngram", "avg", "full_text"),
        aux_objectives=(
            AuxObjectiveBinding(
                objective=ObjectiveRef("span", "span_hamming", "avg", "full_text"),
                role=SpanRole.PRUNE,
                scope=SpanScope.TOPK,
                span_profile=SpanProfile.FULL,
                cadence_every=1,
                budget_ms=5.0,
            ),
        ),
    )
    policy = AdaptivePolicySpec(policy_id="default")

    def _runner(stage: StageSpec, pool: CandidatePool, _ctx):
        _ = stage, pool, _ctx
        return CandidatePool([])

    engine_disabled = StageEngine(stages=[stage], policy=policy, run_stage_fn=_runner)
    engine_disabled.run(seed_pool=CandidatePool([]), context={"span_decision_role_enabled": False})
    evt_disabled = next(e for e in engine_disabled.events if e.get("event") == "stage_start")
    assert evt_disabled["aux_decision_influence"] is False

    engine_enabled = StageEngine(stages=[stage], policy=policy, run_stage_fn=_runner)
    engine_enabled.run(seed_pool=CandidatePool([]), context={"span_decision_role_enabled": True})
    evt_enabled = next(e for e in engine_enabled.events if e.get("event") == "stage_start")
    mode_evt = next(e for e in engine_enabled.events if e.get("event") == "span_decision_mode")
    assert evt_enabled["aux_decision_influence"] is True
    assert mode_evt["span_decision_role_enabled"] is True
    assert mode_evt["aux_decision_influence"] is True
