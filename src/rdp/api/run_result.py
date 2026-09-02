"""Immutable public result returned by every successful run."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from numbers import Real
from types import MappingProxyType

from rdp.api.run_artifact_manifest import RunArtifactManifestRow
from rdp.api.solver_report import (
    OracleReport,
    ReproducibilityMetadata,
    RunConfigurationReport,
    SolverReport,
)
from rdp.api.stop_reason_contract import RunStatus
from rdp.core.types import (
    ConcreteKey,
    JsonValue,
    RuneIndices,
    freeze_parameter_items,
    normalize_concrete_key,
    normalize_rune_indices,
    thaw_parameter_items,
)
from rune_decrypter_prime.scoring.scorer_report import ScorerReport


@dataclass(frozen=True, slots=True)
class RunResult:
    plaintext: RuneIndices | None
    plaintext_text: str | None
    key: ConcreteKey | None
    score: float | None
    status: RunStatus
    solver_report: SolverReport
    scorer_report: ScorerReport
    configuration: RunConfigurationReport
    reproducibility: ReproducibilityMetadata
    oracle: OracleReport
    telemetry: Mapping[str, JsonValue] = field(default_factory=dict)
    artifacts: tuple[RunArtifactManifestRow, ...] = ()

    def __post_init__(self) -> None:
        if self.plaintext is not None:
            object.__setattr__(self, "plaintext", normalize_rune_indices(self.plaintext, field_name="plaintext"))
        if self.plaintext_text is not None and not isinstance(self.plaintext_text, str):
            raise TypeError("plaintext_text must be a string or None")
        if self.key is not None:
            object.__setattr__(self, "key", normalize_concrete_key(self.key))
        if self.score is not None:
            if isinstance(self.score, bool) or not isinstance(self.score, Real):
                raise TypeError("score must be a finite float or None")
            score = float(self.score)
            if not math.isfinite(score):
                raise ValueError("score must be finite")
            object.__setattr__(self, "score", score)
        for field_name, value, expected in (
            ("status", self.status, RunStatus),
            ("solver_report", self.solver_report, SolverReport),
            ("scorer_report", self.scorer_report, ScorerReport),
            ("configuration", self.configuration, RunConfigurationReport),
            ("reproducibility", self.reproducibility, ReproducibilityMetadata),
            ("oracle", self.oracle, OracleReport),
        ):
            if not isinstance(value, expected):
                raise TypeError(f"{field_name} must be {expected.__name__}")
        if self.solver_report.best_key != self.key:
            raise ValueError("RunResult.key must equal SolverReport.best_key")
        if not isinstance(self.telemetry, Mapping):
            raise TypeError("telemetry must be a mapping")
        frozen = freeze_parameter_items(self.telemetry, "telemetry")
        object.__setattr__(
            self,
            "telemetry",
            MappingProxyType(thaw_parameter_items(frozen)),
        )
        artifacts = tuple(self.artifacts)
        if any(not isinstance(row, RunArtifactManifestRow) for row in artifacts):
            raise TypeError("artifacts must contain RunArtifactManifestRow values")
        object.__setattr__(self, "artifacts", artifacts)


__all__ = ["RunResult"]
