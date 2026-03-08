from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from tools.benchmarks.periodic_sub_trans.common.stage_spec import ObjectiveRef, StageSpec


ObjectiveBuilder = Callable[[], Mapping[str, Any]]
OperatorFn = Callable[..., Any]


@dataclass
class ObjectiveCatalog:
    _builders: dict[str, ObjectiveBuilder] = field(default_factory=dict)
    _refs: dict[str, ObjectiveRef] = field(default_factory=dict)

    def register(
        self,
        objective_id: str,
        builder: ObjectiveBuilder,
        *,
        ref: ObjectiveRef | None = None,
    ) -> None:
        key = str(objective_id).strip()
        if not key:
            raise ValueError("objective_id must be non-empty")
        if key in self._builders:
            raise KeyError(f"objective already registered: {key}")
        self._builders[key] = builder
        self._refs[key] = ref or ObjectiveRef(
            objective_id=key,
            family="unknown",
            normalisation="unknown",
            window_policy="unknown",
        )

    def build(self, objective_id: str) -> Mapping[str, Any]:
        key = str(objective_id)
        if key not in self._builders:
            raise KeyError(f"unknown objective id: {key}")
        return dict(self._builders[key]())

    def has(self, objective_id: str) -> bool:
        return str(objective_id) in self._builders

    def get_ref(self, objective_id: str) -> ObjectiveRef:
        key = str(objective_id)
        if key not in self._refs:
            raise KeyError(f"unknown objective id: {key}")
        return self._refs[key]

    def objective_ids(self) -> list[str]:
        return sorted(self._builders.keys())

    def ensure_stage_spec_supported(self, stage: StageSpec) -> None:
        for ref in (stage.search_objective, stage.decision_objective):
            if not self.has(ref.objective_id):
                raise KeyError(f"unknown objective id in StageSpec[{stage.stage_id}]: {ref.objective_id}")

    def ensure_stage_specs_supported(self, stages: list[StageSpec]) -> None:
        for stage in stages:
            self.ensure_stage_spec_supported(stage)


@dataclass
class OperatorCatalog:
    _operators: dict[str, OperatorFn] = field(default_factory=dict)

    def register(self, operator_id: str, operator_fn: OperatorFn) -> None:
        key = str(operator_id).strip()
        if not key:
            raise ValueError("operator_id must be non-empty")
        if key in self._operators:
            raise KeyError(f"operator already registered: {key}")
        self._operators[key] = operator_fn

    def get(self, operator_id: str) -> Callable[..., Any]:
        key = str(operator_id)
        if key not in self._operators:
            raise KeyError(f"unknown operator id: {key}")
        return self._operators[key]

    def has(self, operator_id: str) -> bool:
        return str(operator_id) in self._operators

    def operator_ids(self) -> list[str]:
        return sorted(self._operators.keys())
