from __future__ import annotations

import pytest

from tools.benchmarks.periodic_sub_trans.common.stage_spec import (
    AuxObjectiveBinding,
    ObjectiveRef,
    SpanRole,
    SpanScope,
    StageSpec,
)
from tools.benchmarks.periodic_sub_trans.no_wli.runs.span_ab_harness import (
    build_span_shadow_vs_decision_cases,
    case_ids,
)


pytestmark = pytest.mark.tier_a


def _base_specs() -> list[StageSpec]:
    obj_main = ObjectiveRef("A", "char_ngram", "avg", "full_text")
    obj_span = ObjectiveRef("span", "span_hamming", "avg", "full_text")
    return [
        StageSpec(
            stage_id="stage_a",
            search_objective=obj_main,
            decision_objective=obj_main,
        ),
        StageSpec(
            stage_id="stage_b",
            search_objective=obj_main,
            decision_objective=obj_main,
            aux_objectives=(
                AuxObjectiveBinding(
                    objective=obj_span,
                    role=SpanRole.SHADOW,
                    scope=SpanScope.BASIN_REP,
                    cadence_every=1,
                    budget_ms=5.0,
                ),
            ),
        ),
    ]


def test_build_span_shadow_vs_decision_cases() -> None:
    shadow_case, decision_case = build_span_shadow_vs_decision_cases(stage_specs=_base_specs())
    assert shadow_case.case_id == "span_shadow"
    assert decision_case.case_id == "span_prune"
    assert shadow_case.context_overrides["span_decision_role_enabled"] is False
    assert decision_case.context_overrides["span_decision_role_enabled"] is True
    assert shadow_case.stage_specs[1].aux_objectives[0].role == SpanRole.SHADOW
    assert decision_case.stage_specs[1].aux_objectives[0].role == SpanRole.PRUNE
    assert case_ids((shadow_case, decision_case)) == ["span_shadow", "span_prune"]
