from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Iterable, Sequence

from tools.benchmarks.periodic_sub_trans.common.stage_spec import (
    AuxObjectiveBinding,
    SpanRole,
    StageSpec,
)


@dataclass(frozen=True)
class SpanABCase:
    case_id: str
    stage_specs: tuple[StageSpec, ...]
    context_overrides: dict[str, Any]
    note: str


def _replace_first_aux_role(
    stage_specs: Sequence[StageSpec],
    *,
    role: SpanRole,
) -> tuple[StageSpec, ...]:
    out: list[StageSpec] = []
    replaced = False
    for spec in stage_specs:
        if (not replaced) and spec.aux_objectives:
            aux = list(spec.aux_objectives)
            first = AuxObjectiveBinding(
                objective=aux[0].objective,
                role=role,
                scope=aux[0].scope,
                span_profile=aux[0].span_profile,
                two_pass_enabled=bool(aux[0].two_pass_enabled),
                full_top_m=int(aux[0].full_top_m),
                cadence_every=int(aux[0].cadence_every),
                budget_ms=float(aux[0].budget_ms),
            )
            aux[0] = first
            out.append(replace(spec, aux_objectives=tuple(aux)))
            replaced = True
            continue
        out.append(spec)
    return tuple(out)


def build_span_shadow_vs_decision_cases(
    *,
    stage_specs: Sequence[StageSpec],
    decision_role: SpanRole = SpanRole.PRUNE,
) -> tuple[SpanABCase, SpanABCase]:
    specs_shadow = _replace_first_aux_role(stage_specs, role=SpanRole.SHADOW)
    specs_decision = _replace_first_aux_role(stage_specs, role=decision_role)
    return (
        SpanABCase(
            case_id="span_shadow",
            stage_specs=specs_shadow,
            context_overrides=dict(span_decision_role_enabled=False),
            note="Shadow-only span path; decision influence disabled.",
        ),
        SpanABCase(
            case_id=f"span_{decision_role.value}",
            stage_specs=specs_decision,
            context_overrides=dict(span_decision_role_enabled=True),
            note=f"Decision-role span path enabled ({decision_role.value}).",
        ),
    )


def case_ids(cases: Iterable[SpanABCase]) -> list[str]:
    return [str(c.case_id) for c in cases]

