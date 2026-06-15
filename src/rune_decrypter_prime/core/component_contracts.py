from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, StrEnum
from typing import Any


class ComponentKind(StrEnum):
    SCORER_LANE = "scorer_lane"
    SCORER_RUNTIME = "scorer_runtime"
    CIPHER = "cipher"
    SOLVER = "solver"
    ASSET = "asset"
    ARTIFACT = "artifact"


class V1Status(StrEnum):
    V1_CORE = "v1_core"
    V1_OPTIONAL = "v1_optional"
    EXPERIMENTAL_REPORT_ONLY = "experimental_report_only"
    EXPERIMENTAL = "experimental"
    ROADMAP = "roadmap"
    DEPRECATED = "deprecated"
    REMOVED = "removed"


class RankEffect(StrEnum):
    PRODUCTION = "production"
    REPORT_ONLY = "report_only"
    NONE = "none"


class RequestState(StrEnum):
    NOT_REQUESTED = "not_requested"
    REQUESTED = "requested"
    REQUIRED = "required"


class EffectiveState(StrEnum):
    INACTIVE = "inactive"
    ACTIVE = "active"
    BLOCKED = "blocked"
    FALLBACK_REPORTED = "fallback_reported"
    REPORT_ONLY = "report_only"


class CapabilityStatus(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    ASSET_MISSING = "asset_missing"
    ASSET_INVALID = "asset_invalid"
    ASSET_MISMATCH = "asset_mismatch"
    UNSUPPORTED = "unsupported"
    MISCONFIGURED = "misconfigured"


class FallbackPolicy(StrEnum):
    BLOCK = "block"
    EXPLICIT_REPORTED_FALLBACK = "explicit_reported_fallback"
    REPORT_ONLY = "report_only"
    DISABLED = "disabled"


class ScorerLaneName(StrEnum):
    LM_CHAR_WLI = "lm_char_wli"
    HAMMING = "hamming"
    SPAN_HAMMING_RAW = "span_hamming_raw"
    SPAN_HAMMING_CALIBRATED = "span_hamming_calibrated"
    WORD_NGRAM_JUDGE_REPORT_ONLY = "word_ngram_judge_report_only"
    NGRAM_HAMMING_EXPERIMENTAL_REPORT_ONLY = "ngram_hamming_experimental_report_only"


class RequestedLaneUnavailableError(RuntimeError):
    """Raised when a requested V1 scorer lane cannot run and fallback is not allowed."""


def _require_enum(value: object, enum_type: type[Enum], field_name: str) -> None:
    if not isinstance(value, enum_type):
        raise TypeError(f"{field_name} must be {enum_type.__name__}")


def _require_non_empty_str(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string")


@dataclass(frozen=True, slots=True)
class CapabilityIssue:
    code: str
    message: str
    status: CapabilityStatus
    source: str | None = None
    exception_type: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty_str(self.code, "CapabilityIssue.code")
        _require_non_empty_str(self.message, "CapabilityIssue.message")
        _require_enum(self.status, CapabilityStatus, "CapabilityIssue.status")
        if self.source is not None and not isinstance(self.source, str):
            raise TypeError("CapabilityIssue.source must be str or None")
        if self.exception_type is not None and not isinstance(self.exception_type, str):
            raise TypeError("CapabilityIssue.exception_type must be str or None")

    def to_json_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "message": self.message,
            "status": self.status.value,
            "source": self.source,
            "exception_type": self.exception_type,
        }


@dataclass(frozen=True, slots=True)
class LaneStatus:
    lane: ScorerLaneName
    request_state: RequestState
    effective_state: EffectiveState
    rank_effect: RankEffect
    fallback_policy: FallbackPolicy
    issues: tuple[CapabilityIssue, ...] = field(default_factory=tuple)
    report_section: str | None = None

    def __post_init__(self) -> None:
        _require_enum(self.lane, ScorerLaneName, "LaneStatus.lane")
        _require_enum(self.request_state, RequestState, "LaneStatus.request_state")
        _require_enum(self.effective_state, EffectiveState, "LaneStatus.effective_state")
        _require_enum(self.rank_effect, RankEffect, "LaneStatus.rank_effect")
        _require_enum(self.fallback_policy, FallbackPolicy, "LaneStatus.fallback_policy")
        for issue in self.issues:
            if not isinstance(issue, CapabilityIssue):
                raise TypeError("LaneStatus.issues must contain CapabilityIssue entries")
        if self.report_section is not None and not isinstance(self.report_section, str):
            raise TypeError("LaneStatus.report_section must be str or None")

    @property
    def is_blocking(self) -> bool:
        return self.effective_state is EffectiveState.BLOCKED

    def to_json_dict(self) -> dict[str, object]:
        return {
            "lane": self.lane.value,
            "request_state": self.request_state.value,
            "effective_state": self.effective_state.value,
            "rank_effect": self.rank_effect.value,
            "fallback_policy": self.fallback_policy.value,
            "issues": [issue.to_json_dict() for issue in self.issues],
            "report_section": self.report_section,
        }


@dataclass(frozen=True, slots=True)
class ComponentContract:
    component_id: str
    kind: ComponentKind
    v1_status: V1Status
    rank_effect: RankEffect
    required_if_requested: bool
    default_fallback_policy: FallbackPolicy
    owner_module: str
    notes: str = ""

    def __post_init__(self) -> None:
        _require_non_empty_str(self.component_id, "component_id")
        _require_enum(self.kind, ComponentKind, "kind")
        _require_enum(self.v1_status, V1Status, "v1_status")
        _require_enum(self.rank_effect, RankEffect, "rank_effect")
        if type(self.required_if_requested) is not bool:
            raise TypeError("required_if_requested must be bool")
        _require_enum(self.default_fallback_policy, FallbackPolicy, "default_fallback_policy")
        _require_non_empty_str(self.owner_module, "owner_module")
        if not isinstance(self.notes, str):
            raise TypeError("notes must be str")

    def to_json_dict(self) -> dict[str, object]:
        return {
            "component_id": self.component_id,
            "kind": self.kind.value,
            "v1_status": self.v1_status.value,
            "rank_effect": self.rank_effect.value,
            "required_if_requested": self.required_if_requested,
            "default_fallback_policy": self.default_fallback_policy.value,
            "owner_module": self.owner_module,
            "notes": self.notes,
        }


@dataclass(frozen=True, slots=True)
class ScorerCapabilityReport:
    lanes: tuple[LaneStatus, ...]
    components: tuple[ComponentContract, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        for lane in self.lanes:
            if not isinstance(lane, LaneStatus):
                raise TypeError("ScorerCapabilityReport.lanes must contain LaneStatus entries")
        for component in self.components:
            if not isinstance(component, ComponentContract):
                raise TypeError("ScorerCapabilityReport.components must contain ComponentContract entries")

    def blocked_lanes(self) -> tuple[LaneStatus, ...]:
        return tuple(lane for lane in self.lanes if lane.is_blocking)

    def raise_if_blocked(self) -> None:
        blocked = self.blocked_lanes()
        if not blocked:
            return
        names = ", ".join(lane.lane.value for lane in blocked)
        issue_bits: list[str] = []
        for lane in blocked:
            issue_bits.extend(f"{lane.lane.value}:{issue.code}" for issue in lane.issues)
        suffix = f" ({'; '.join(issue_bits)})" if issue_bits else ""
        raise RequestedLaneUnavailableError(f"requested scorer lane unavailable: {names}{suffix}")

    def to_json_dict(self) -> dict[str, object]:
        return {
            "lanes": [lane.to_json_dict() for lane in self.lanes],
            "components": [component.to_json_dict() for component in self.components],
        }
