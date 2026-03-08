from __future__ import annotations

import pytest

from tools.benchmarks.periodic_sub_trans.col_then_sub.stage_engine_contract import (
    build_col_then_sub_stage_specs,
)
from tools.benchmarks.periodic_sub_trans.col_then_sub.stage_engine_iteration_bridge import (
    ColThenSubStageEngineFns,
    run_iteration_with_stage_engine as run_col_bridge,
)
from tools.benchmarks.periodic_sub_trans.sub_then_col.stage_engine_contract import (
    build_sub_then_col_stage_specs,
)
from tools.benchmarks.periodic_sub_trans.sub_then_col.stage_engine_iteration_bridge import (
    SubThenColStageEngineFns,
    run_iteration_with_stage_engine as run_sub_bridge,
)


pytestmark = pytest.mark.tier_a


def _col_stage_a(state):
    return {"seed": int(state["seed"]), "a_score": float(state["seed"]) + 0.1}


def _col_stage_b(state, a):
    return {"b_score": float(a["a_score"]) + float(state["delta"])}


def _col_stage_c(state, a, b):
    return {"best": float(a["a_score"]) + float(b["b_score"]) + float(state["delta"])}


def _sub_stage_a(state):
    return {"p": int(state["p"])}


def _sub_stage_b(state, a):
    return {"q": int(a["p"]) + int(state["offset"])}


def _sub_stage_c(state, a, b):
    return {"r": int(a["p"]) + int(b["q"]) + int(state["offset"])}


def test_col_then_sub_bridge_parity_smoke() -> None:
    state = {"seed": 11, "delta": 3}
    legacy_a = _col_stage_a(state)
    legacy_b = _col_stage_b(state, legacy_a)
    legacy_c = _col_stage_c(state, legacy_a, legacy_b)

    specs = build_col_then_sub_stage_specs(
        state=dict(
            SCORER_STAGE1={"objective": "pct.logp.win10"},
            SCORER_FULL={"objective": "pct.logp.win10"},
            STAGE12_ARCHIVE_KEEP=4,
            STAGE12_PROMOTE_TOP=2,
            STAGE3_INITIAL_KEYS=8,
        )
    )
    out = run_col_bridge(
        state=state,
        stage_specs=specs,
        fns=ColThenSubStageEngineFns(
            run_stage_a_fn=_col_stage_a,
            run_stage_b_fn=_col_stage_b,
            run_stage_c_fn=_col_stage_c,
        ),
    )
    assert out.stage_a == legacy_a
    assert out.stage_b == legacy_b
    assert out.stage_c == legacy_c


def test_sub_then_col_bridge_parity_smoke() -> None:
    state = {"p": 5, "offset": 2}
    legacy_a = _sub_stage_a(state)
    legacy_b = _sub_stage_b(state, legacy_a)
    legacy_c = _sub_stage_c(state, legacy_a, legacy_b)

    specs = build_sub_then_col_stage_specs(
        state=dict(
            SCORER_SUB={"objective": "pct.logp.win10"},
            SCORER_FULL={"objective": "pct.logp.win10"},
            COL_KEEP=3,
            STAGE3_INITIAL_KEYS=8,
        )
    )
    out = run_sub_bridge(
        state=state,
        stage_specs=specs,
        fns=SubThenColStageEngineFns(
            run_stage_a_fn=_sub_stage_a,
            run_stage_b_fn=_sub_stage_b,
            run_stage_c_fn=_sub_stage_c,
        ),
    )
    assert out.stage_a == legacy_a
    assert out.stage_b == legacy_b
    assert out.stage_c == legacy_c

