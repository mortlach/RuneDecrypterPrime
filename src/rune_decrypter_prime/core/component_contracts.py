from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, StrEnum
from collections.abc import Mapping, Sequence
from types import MappingProxyType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rdp.api.specs import CipherSpec, KeySpec
    from rdp.api.stop_reason_contract import RunStatus
    from rune_decrypter_prime.core.types import ConcreteKey, JsonObject


class ComponentKind(StrEnum):
    SCORER_LANE = "scorer_lane"
    SCORER_RUNTIME = "scorer_runtime"
    CIPHER = "cipher"
    SOLVER = "solver"
    ASSET = "asset"
    ARTIFACT = "artifact"


class ReleaseStatus(StrEnum):
    V1_CORE = "v1_core"
    V1_OPTIONAL = "v1_optional"
    EXPERIMENTAL_REPORT_ONLY = "experimental_report_only"
    EXPERIMENTAL = "experimental"
    ROADMAP = "roadmap"
    DEPRECATED = "deprecated"
    REMOVED = "removed"


class RankingEffect(StrEnum):
    PRODUCTION = "production"
    REPORT_ONLY = "report_only"
    NONE = "none"


class CapabilityRequestState(StrEnum):
    NOT_REQUESTED = "not_requested"
    REQUESTED = "requested"
    REQUIRED = "required"


class CapabilityEffectiveState(StrEnum):
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


class ScoringLane(StrEnum):
    LANGUAGE_MODEL_CHARACTER_AND_WORD_LENGTH = "language_model_character_and_word_length"
    HAMMING = "hamming"
    SPAN_HAMMING_RAW = "span_hamming_raw"
    SPAN_HAMMING_CALIBRATED = "span_hamming_calibrated"
    WORD_NGRAM_JUDGE_REPORT_ONLY = "word_ngram_judge_report_only"
    NGRAM_HAMMING_EXPERIMENTAL_REPORT_ONLY = "ngram_hamming_experimental_report_only"


class RequestedLaneUnavailableError(RuntimeError):
    """Raised when a requested V1 scorer lane cannot run and fallback is not allowed."""


class RdpError(Exception):
    """Base class for stable public RDP failures."""

    def __init__(self, message: str, /) -> None:
        if not isinstance(message, str) or not message:
            raise ValueError("message must be a non-empty string")
        super().__init__(message)


class ConfigurationError(RdpError):
    def __init__(
        self,
        message: str,
        /,
        *,
        field_path: str | None = None,
        issues: Sequence["CapabilityIssue"] = (),
    ) -> None:
        super().__init__(message)
        if field_path is not None and (not isinstance(field_path, str) or not field_path):
            raise ValueError("field_path must be a non-empty string or None")
        self.field_path = field_path
        self.issues = _copy_issues(issues)


class CapabilityUnavailableError(RdpError):
    def __init__(
        self,
        message: str,
        /,
        *,
        status: "RunStatus",
        issues: Sequence["CapabilityIssue"],
    ) -> None:
        super().__init__(message)
        self.status = status
        self.issues = _copy_issues(issues)


class AssetUnavailableError(CapabilityUnavailableError):
    pass


class NonInvertibleCipherError(CapabilityUnavailableError):
    pass


class ExecutionError(RdpError):
    def __init__(
        self,
        message: str,
        /,
        *,
        status: "RunStatus",
        phase: str,
        context: "JsonObject | None" = None,
    ) -> None:
        super().__init__(message)
        if not isinstance(phase, str) or not phase:
            raise ValueError("phase must be a non-empty string")
        if context is not None and not isinstance(context, Mapping):
            raise TypeError("context must be a mapping or None")
        self.status = status
        self.phase = phase
        self.context = MappingProxyType({} if context is None else dict(context))


class UnknownComponentError(RdpError):
    def __init__(self, message: str, /, *, component_kind: ComponentKind, token: str) -> None:
        super().__init__(message)
        _require_enum(component_kind, ComponentKind, "component_kind")
        _require_non_empty_str(token, "token")
        self.component_kind = component_kind
        self.token = token


class UnsupportedConfigurationError(ConfigurationError):
    def __init__(
        self,
        message: str,
        /,
        *,
        field_paths: Sequence[str],
        issues: Sequence["CapabilityIssue"] = (),
    ) -> None:
        paths = tuple(field_paths)
        if not paths or any(not isinstance(path, str) or not path for path in paths):
            raise ValueError("field_paths must contain non-empty strings")
        super().__init__(message, field_path=paths[0], issues=issues)
        self.field_paths = paths


class CipherKeyMismatchError(ConfigurationError):
    def __init__(
        self,
        message: str,
        /,
        *,
        cipher: "CipherSpec",
        key_space: "KeySpec | None" = None,
        key: "ConcreteKey | None" = None,
    ) -> None:
        super().__init__(message)
        self.cipher = cipher
        self.key_space = key_space
        self.key = key


class InvalidConcreteKeyError(ConfigurationError):
    def __init__(
        self,
        message: str,
        /,
        *,
        index: int | None = None,
        value: int | None = None,
        expected_domain: str | None = None,
    ) -> None:
        super().__init__(message)
        self.index = index
        self.value = value
        self.expected_domain = expected_domain


class CipherRegistrationError(ConfigurationError):
    def __init__(
        self,
        message: str,
        /,
        *,
        identity: str,
        owner: str | None = None,
    ) -> None:
        super().__init__(message)
        _require_non_empty_str(identity, "identity")
        if owner is not None and (not isinstance(owner, str) or not owner):
            raise ValueError("owner must be a non-empty string or None")
        self.identity = identity
        self.owner = owner


def _copy_issues(issues: Sequence["CapabilityIssue"]) -> tuple["CapabilityIssue", ...]:
    copied = tuple(issues)
    if any(not isinstance(issue, CapabilityIssue) for issue in copied):
        raise TypeError("issues must contain CapabilityIssue values")
    return copied


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
class ScoringLaneStatus:
    lane: ScoringLane
    request_state: CapabilityRequestState
    effective_state: CapabilityEffectiveState
    ranking_effect: RankingEffect
    fallback_policy: FallbackPolicy
    issues: tuple[CapabilityIssue, ...] = field(default_factory=tuple)
    report_section: str | None = None

    def __post_init__(self) -> None:
        _require_enum(self.lane, ScoringLane, "ScoringLaneStatus.lane")
        _require_enum(self.request_state, CapabilityRequestState, "ScoringLaneStatus.request_state")
        _require_enum(self.effective_state, CapabilityEffectiveState, "ScoringLaneStatus.effective_state")
        _require_enum(self.ranking_effect, RankingEffect, "ScoringLaneStatus.ranking_effect")
        _require_enum(self.fallback_policy, FallbackPolicy, "ScoringLaneStatus.fallback_policy")
        for issue in self.issues:
            if not isinstance(issue, CapabilityIssue):
                raise TypeError("ScoringLaneStatus.issues must contain CapabilityIssue entries")
        if self.report_section is not None and not isinstance(self.report_section, str):
            raise TypeError("ScoringLaneStatus.report_section must be str or None")

    @property
    def is_blocking(self) -> bool:
        return self.effective_state is CapabilityEffectiveState.BLOCKED

    def to_json_dict(self) -> dict[str, object]:
        return {
            "lane": self.lane.value,
            "request_state": self.request_state.value,
            "effective_state": self.effective_state.value,
            "ranking_effect": self.ranking_effect.value,
            "fallback_policy": self.fallback_policy.value,
            "issues": [issue.to_json_dict() for issue in self.issues],
            "report_section": self.report_section,
        }


@dataclass(frozen=True, slots=True)
class ComponentContract:
    component_id: str
    kind: ComponentKind
    release_status: ReleaseStatus
    ranking_effect: RankingEffect
    required_if_requested: bool
    default_fallback_policy: FallbackPolicy
    owner_module: str
    notes: str = ""

    def __post_init__(self) -> None:
        _require_non_empty_str(self.component_id, "component_id")
        _require_enum(self.kind, ComponentKind, "kind")
        _require_enum(self.release_status, ReleaseStatus, "release_status")
        _require_enum(self.ranking_effect, RankingEffect, "ranking_effect")
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
            "release_status": self.release_status.value,
            "ranking_effect": self.ranking_effect.value,
            "required_if_requested": self.required_if_requested,
            "default_fallback_policy": self.default_fallback_policy.value,
            "owner_module": self.owner_module,
            "notes": self.notes,
        }


@dataclass(frozen=True, slots=True)
class ScorerCapabilityReport:
    lanes: tuple[ScoringLaneStatus, ...]
    components: tuple[ComponentContract, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        for lane in self.lanes:
            if not isinstance(lane, ScoringLaneStatus):
                raise TypeError("ScorerCapabilityReport.lanes must contain ScoringLaneStatus entries")
        for component in self.components:
            if not isinstance(component, ComponentContract):
                raise TypeError("ScorerCapabilityReport.components must contain ComponentContract entries")

    def blocked_lanes(self) -> tuple[ScoringLaneStatus, ...]:
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
