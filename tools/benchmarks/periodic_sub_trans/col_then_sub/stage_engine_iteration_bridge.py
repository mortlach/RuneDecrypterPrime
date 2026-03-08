from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Mapping

from tools.benchmarks.periodic_sub_trans.common.policy_spec import AdaptivePolicySpec
from tools.benchmarks.periodic_sub_trans.common.pool import CandidatePool, CandidateRecord
from tools.benchmarks.periodic_sub_trans.common.stage_engine import StageEngine
from tools.benchmarks.periodic_sub_trans.common.stage_spec import StageSpec


@dataclass(frozen=True)
class ColThenSubStageEngineFns:
    run_stage_a_fn: Callable[[Mapping[str, Any]], Dict[str, Any]]
    run_stage_b_fn: Callable[[Mapping[str, Any], Mapping[str, Any]], Dict[str, Any]]
    run_stage_c_fn: Callable[[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]], Dict[str, Any]]


@dataclass(frozen=True)
class ColThenSubIterationStageEngineResult:
    stage_a: Dict[str, Any]
    stage_b: Dict[str, Any]
    stage_c: Dict[str, Any]
    events: list[Dict[str, Any]]


def _pool_from_stage_output(*, stage_id: str, out: Mapping[str, Any]) -> CandidatePool:
    payloads = list(out.get("pool_candidates", []))
    rows: list[CandidateRecord] = []
    for idx, payload in enumerate(payloads):
        if not isinstance(payload, Mapping):
            continue
        p = dict(payload)
        rows.append(
            CandidateRecord.from_payload(
                candidate_id=str(p.get("candidate_id", f"{stage_id}:{idx}")),
                decision_score=float(p.get("decision_score", p.get("score", 0.0))),
                match_ratio=float(p.get("match_ratio", p.get("match", 0.0))),
                payload=p,
            )
        )
    return CandidatePool(rows)


def run_iteration_with_stage_engine(
    *,
    state: Mapping[str, Any],
    stage_specs: list[StageSpec],
    fns: ColThenSubStageEngineFns,
    policy: AdaptivePolicySpec | None = None,
) -> ColThenSubIterationStageEngineResult:
    stage_a_out: Dict[str, Any] = {}
    stage_b_out: Dict[str, Any] = {}
    stage_c_out: Dict[str, Any] = {}

    effective_policy = policy or AdaptivePolicySpec(policy_id="col_then_sub_iter_orch_v1")

    def _run_stage(stage: StageSpec, _pool: CandidatePool, _ctx: Mapping[str, Any]) -> CandidatePool:
        nonlocal stage_a_out, stage_b_out, stage_c_out
        stage_id = str(stage.stage_id)
        if stage_id == "stage_a_sub_discovery":
            stage_a_out = fns.run_stage_a_fn(dict(state))
            return _pool_from_stage_output(stage_id=stage_id, out=stage_a_out)
        if stage_id == "stage_b_col_search":
            stage_b_out = fns.run_stage_b_fn(dict(state), dict(stage_a_out))
            return _pool_from_stage_output(stage_id=stage_id, out=stage_b_out)
        if stage_id == "stage_c_full_refine":
            if bool(stage_b_out.get("skip_stage_c", False)):
                stage_c_out = {}
            else:
                stage_c_out = fns.run_stage_c_fn(dict(state), dict(stage_a_out), dict(stage_b_out))
            return _pool_from_stage_output(stage_id=stage_id, out=stage_c_out)
        raise ValueError(f"Unsupported stage_id in col_then_sub iteration bridge: {stage_id}")

    engine = StageEngine(stages=list(stage_specs), policy=effective_policy, run_stage_fn=_run_stage)
    engine.run(seed_pool=CandidatePool([]), context={})
    return ColThenSubIterationStageEngineResult(
        stage_a=dict(stage_a_out),
        stage_b=dict(stage_b_out),
        stage_c=dict(stage_c_out),
        events=[dict(evt) for evt in engine.events],
    )
