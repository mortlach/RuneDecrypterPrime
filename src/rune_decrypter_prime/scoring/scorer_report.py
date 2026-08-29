"""Immutable V1 scorer report."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from rune_decrypter_prime.core.component_contracts import ScorerCapabilityReport
from rune_decrypter_prime.core.config.scoring import ScoringObjective
from rune_decrypter_prime.core.types import JsonObject, JsonValue


def _json_mapping(value: Mapping[str, object], field_name: str) -> Mapping[str, JsonValue]:
    from rdp.api.solver_report import _mapping

    return _mapping(value, field_name)


def _optional_score(value: float | None, field_name: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a number or None")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{field_name} must be finite")
    return result


@dataclass(frozen=True, slots=True)
class ScorerReport:
    objective: ScoringObjective
    score: float | None
    raw_score: float | None = None
    telemetry: Mapping[str, JsonValue] = field(default_factory=dict)
    metrics: Mapping[str, float] = field(default_factory=dict)
    time_seconds: float | None = None
    capabilities: ScorerCapabilityReport = field(default_factory=lambda: ScorerCapabilityReport(lanes=()))
    details: Mapping[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.objective, ScoringObjective):
            raise TypeError("objective must be ScoringObjective")
        object.__setattr__(self, "score", _optional_score(self.score, "score"))
        object.__setattr__(self, "raw_score", _optional_score(self.raw_score, "raw_score"))
        object.__setattr__(self, "time_seconds", _optional_score(self.time_seconds, "time_seconds"))
        if self.time_seconds is not None and self.time_seconds < 0.0:
            raise ValueError("time_seconds must be non-negative")
        object.__setattr__(self, "telemetry", _json_mapping(self.telemetry, "telemetry"))
        metrics = {str(key): _optional_score(value, f"metrics.{key}") for key, value in self.metrics.items()}
        object.__setattr__(self, "metrics", MappingProxyType(metrics))
        if not isinstance(self.capabilities, ScorerCapabilityReport):
            raise TypeError("capabilities must be ScorerCapabilityReport")
        object.__setattr__(self, "details", _json_mapping(self.details, "details"))

    def to_dict(self) -> JsonObject:
        return {
            "objective": self.objective.to_dict(),
            "score": self.score,
            "raw_score": self.raw_score,
            "telemetry": dict(self.telemetry),
            "metrics": dict(self.metrics),
            "time_seconds": self.time_seconds,
            "capabilities": self.capabilities.to_json_dict(),
            "details": dict(self.details),
        }

    def to_json_dict(self) -> JsonObject:
        return self.to_dict()


__all__ = ["ScorerReport"]
