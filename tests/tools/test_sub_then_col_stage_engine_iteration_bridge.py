from __future__ import annotations

import pytest

from tools.benchmarks.periodic_sub_trans.common.policy_spec import AdaptivePolicySpec
from tools.benchmarks.periodic_sub_trans.sub_then_col.stage_engine_contract import (
    build_sub_then_col_stage_specs,
)
from tools.benchmarks.periodic_sub_trans.sub_then_col.stage_engine_iteration_bridge import (
    SubThenColStageEngineFns,
    run_iteration_with_stage_engine,
)


pytestmark = pytest.mark.tier_a


def test_sub_then_col_iteration_bridge_runs_stages_in_order() -> None:
    calls: list[str] = []

    fns = SubThenColStageEngineFns(
        run_stage_a_fn=lambda _state: (calls.append("A") or {"a": 1}),
        run_stage_b_fn=lambda _state, a: (calls.append("B") or {"b": int(a["a"]) + 1}),
        run_stage_c_fn=lambda _state, a, b: (calls.append("C") or {"c": int(a["a"]) + int(b["b"])}),
    )
    specs = build_sub_then_col_stage_specs(
        state=dict(
            SCORER_SUB={"objective": "pct.logp.win10"},
            SCORER_FULL={"objective": "pct.logp.win10"},
            COL_KEEP=3,
            STAGE3_INITIAL_KEYS=8,
        )
    )
    out = run_iteration_with_stage_engine(
        state={"tier": "x"},
        stage_specs=specs,
        fns=fns,
        policy=AdaptivePolicySpec(policy_id="test"),
    )
    assert calls == ["A", "B", "C"]
    assert out.stage_a["a"] == 1
    assert out.stage_b["b"] == 2
    assert out.stage_c["c"] == 3
    assert len(out.events) == 6


def test_sub_then_col_iteration_bridge_skips_stage_c_when_requested() -> None:
    calls: list[str] = []
    fns = SubThenColStageEngineFns(
        run_stage_a_fn=lambda _state: (calls.append("A") or {"a": 1}),
        run_stage_b_fn=lambda _state, _a: (calls.append("B") or {"skip_stage_c": True}),
        run_stage_c_fn=lambda _state, _a, _b: (calls.append("C") or {"c": 1}),
    )
    specs = build_sub_then_col_stage_specs(
        state=dict(
            SCORER_SUB={"objective": "pct.logp.win10"},
            SCORER_FULL={"objective": "pct.logp.win10"},
            COL_KEEP=3,
            STAGE3_INITIAL_KEYS=8,
        )
    )
    out = run_iteration_with_stage_engine(
        state={},
        stage_specs=specs,
        fns=fns,
    )
    assert calls == ["A", "B"]
    assert out.stage_c == {}


def test_sub_then_col_iteration_bridge_applies_basin_dedupe_on_stage_b_pool() -> None:
    fns = SubThenColStageEngineFns(
        run_stage_a_fn=lambda _state: {"a": 1},
        run_stage_b_fn=lambda _state, _a: {
            "b": 2,
            "pool_candidates": [
                {"candidate_id": "k1", "score": 1.0, "match": 0.1, "end_hash": "h1"},
                {"candidate_id": "k2", "score": 0.9, "match": 0.1, "end_hash": "h1"},
                {"candidate_id": "k3", "score": 0.8, "match": 0.2, "end_hash": "h2"},
            ],
        },
        run_stage_c_fn=lambda _state, _a, _b: {"c": 3},
    )
    specs = build_sub_then_col_stage_specs(
        state=dict(
            SCORER_SUB={"objective": "pct.logp.win10"},
            SCORER_FULL={"objective": "pct.logp.win10"},
            COL_KEEP=8,
            STAGE3_INITIAL_KEYS=8,
        )
    )
    out = run_iteration_with_stage_engine(state={}, stage_specs=specs, fns=fns)
    evt = next(
        e
        for e in out.events
        if str(e.get("event")) == "stage_end" and str(e.get("stage_id")) == "stage_b_sub_refine"
    )
    assert int(evt["out_pool_size"]) == 2
