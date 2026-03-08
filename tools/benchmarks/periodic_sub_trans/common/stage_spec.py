from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class SpanRole(str, Enum):
    OFF = "off"
    SHADOW = "shadow"
    PRUNE = "prune"
    GATE = "gate"
    COMBINED = "combined"
    JUDGE = "judge"


class SpanScope(str, Enum):
    CANDIDATE = "candidate"
    BASIN_REP = "basin_rep"
    TOPK = "topk"


class SpanProfile(str, Enum):
    LITE = "lite"
    FULL = "full"


@dataclass(frozen=True)
class ObjectiveRef:
    objective_id: str
    family: str
    normalisation: str
    window_policy: str
    calibration_id: str = ""

    def __post_init__(self) -> None:
        if not str(self.objective_id).strip():
            raise ValueError("ObjectiveRef.objective_id must be non-empty")
        if not str(self.family).strip():
            raise ValueError("ObjectiveRef.family must be non-empty")
        if not str(self.normalisation).strip():
            raise ValueError("ObjectiveRef.normalisation must be non-empty")
        if not str(self.window_policy).strip():
            raise ValueError("ObjectiveRef.window_policy must be non-empty")

    def to_json_dict(self) -> dict[str, Any]:
        return dict(
            objective_id=str(self.objective_id),
            family=str(self.family),
            normalisation=str(self.normalisation),
            window_policy=str(self.window_policy),
            calibration_id=str(self.calibration_id),
        )

    @classmethod
    def from_json_dict(cls, payload: Mapping[str, Any]) -> "ObjectiveRef":
        return cls(
            objective_id=str(payload.get("objective_id", "")),
            family=str(payload.get("family", "")),
            normalisation=str(payload.get("normalisation", "")),
            window_policy=str(payload.get("window_policy", "")),
            calibration_id=str(payload.get("calibration_id", "")),
        )


@dataclass(frozen=True)
class AuxObjectiveBinding:
    objective: ObjectiveRef
    role: SpanRole = SpanRole.OFF
    scope: SpanScope = SpanScope.CANDIDATE
    span_profile: SpanProfile = SpanProfile.FULL
    two_pass_enabled: bool = False
    full_top_m: int = 0
    cadence_every: int = 0
    budget_ms: float = 0.0

    def __post_init__(self) -> None:
        if int(self.cadence_every) < 0:
            raise ValueError("AuxObjectiveBinding.cadence_every must be >= 0")
        if float(self.budget_ms) < 0.0:
            raise ValueError("AuxObjectiveBinding.budget_ms must be >= 0")
        if int(self.full_top_m) < 0:
            raise ValueError("AuxObjectiveBinding.full_top_m must be >= 0")
        if self.role != SpanRole.OFF:
            if int(self.cadence_every) <= 0:
                raise ValueError(
                    "AuxObjectiveBinding.cadence_every must be > 0 when role is enabled"
                )
            if float(self.budget_ms) <= 0.0:
                raise ValueError(
                    "AuxObjectiveBinding.budget_ms must be > 0 when role is enabled"
                )

    def to_json_dict(self) -> dict[str, Any]:
        return dict(
            objective=self.objective.to_json_dict(),
            role=str(self.role.value),
            scope=str(self.scope.value),
            span_profile=str(self.span_profile.value),
            two_pass_enabled=bool(self.two_pass_enabled),
            full_top_m=int(self.full_top_m),
            cadence_every=int(self.cadence_every),
            budget_ms=float(self.budget_ms),
        )

    @classmethod
    def from_json_dict(cls, payload: Mapping[str, Any]) -> "AuxObjectiveBinding":
        role_raw = str(payload.get("role", SpanRole.OFF.value))
        role = SpanRole(role_raw) if role_raw in {r.value for r in SpanRole} else SpanRole.OFF
        scope_raw = str(payload.get("scope", SpanScope.CANDIDATE.value))
        scope = SpanScope(scope_raw) if scope_raw in {s.value for s in SpanScope} else SpanScope.CANDIDATE
        span_profile_raw = str(payload.get("span_profile", SpanProfile.FULL.value))
        span_profile = (
            SpanProfile(span_profile_raw)
            if span_profile_raw in {p.value for p in SpanProfile}
            else SpanProfile.FULL
        )
        return cls(
            objective=ObjectiveRef.from_json_dict(payload.get("objective", {})),
            role=role,
            scope=scope,
            span_profile=span_profile,
            two_pass_enabled=bool(payload.get("two_pass_enabled", False)),
            full_top_m=int(payload.get("full_top_m", 0)),
            cadence_every=int(payload.get("cadence_every", 0)),
            budget_ms=float(payload.get("budget_ms", 0.0)),
        )


@dataclass(frozen=True)
class StageSpec:
    stage_id: str
    search_objective: ObjectiveRef
    decision_objective: ObjectiveRef
    aux_objectives: tuple[AuxObjectiveBinding, ...] = field(default_factory=tuple)
    pool_keep: int = 0
    promote_top: int = 0
    basin_cap: int = 0
    params: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not str(self.stage_id).strip():
            raise ValueError("StageSpec.stage_id must be non-empty")
        if int(self.pool_keep) < 0:
            raise ValueError("StageSpec.pool_keep must be >= 0")
        if int(self.promote_top) < 0:
            raise ValueError("StageSpec.promote_top must be >= 0")
        if int(self.basin_cap) < 0:
            raise ValueError("StageSpec.basin_cap must be >= 0")
        if (int(self.promote_top) > 0) and (int(self.pool_keep) > 0) and (int(self.promote_top) > int(self.pool_keep)):
            raise ValueError("StageSpec.promote_top cannot exceed pool_keep when both are set")

    def to_json_dict(self) -> dict[str, Any]:
        return dict(
            stage_id=str(self.stage_id),
            search_objective=self.search_objective.to_json_dict(),
            decision_objective=self.decision_objective.to_json_dict(),
            aux_objectives=[entry.to_json_dict() for entry in self.aux_objectives],
            pool_keep=int(self.pool_keep),
            promote_top=int(self.promote_top),
            basin_cap=int(self.basin_cap),
            params={str(k): self.params[k] for k in sorted(self.params.keys(), key=lambda x: str(x))},
        )

    @classmethod
    def from_json_dict(cls, payload: Mapping[str, Any]) -> "StageSpec":
        aux = tuple(
            AuxObjectiveBinding.from_json_dict(item)
            for item in list(payload.get("aux_objectives", []))
        )
        return cls(
            stage_id=str(payload.get("stage_id", "")),
            search_objective=ObjectiveRef.from_json_dict(payload.get("search_objective", {})),
            decision_objective=ObjectiveRef.from_json_dict(payload.get("decision_objective", {})),
            aux_objectives=aux,
            pool_keep=int(payload.get("pool_keep", 0)),
            promote_top=int(payload.get("promote_top", 0)),
            basin_cap=int(payload.get("basin_cap", 0)),
            params=dict(payload.get("params", {})),
        )
