"""Immutable public result returned by every successful run."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from numbers import Integral, Real
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
    WordLengthInformation,
    freeze_parameter_items,
    normalize_concrete_key,
    normalize_rune_indices,
    thaw_parameter_items,
)
from rdp.scoring.scorer_report import ScorerReport


@dataclass(frozen=True, slots=True)
class RunResult:
    """The best candidate and the evidence produced by one run.

    Plaintext is exposed in four explicit, mutually consistent forms. RuneLatin
    uses ``·`` between rune tokens, so it remains distinct from natural English.
    """

    plaintext_indices: RuneIndices | None
    word_length_information: WordLengthInformation | None
    plaintext_runes: str | None
    plaintext_rune_latin: str | None
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
        if self.plaintext_indices is not None:
            object.__setattr__(
                self,
                "plaintext_indices",
                normalize_rune_indices(
                    self.plaintext_indices, field_name="plaintext_indices"
                ),
            )
        wli = _normalize_word_length_information(self.word_length_information)
        if (
            self.plaintext_indices is not None
            and wli is not None
            and len(wli) != len(self.plaintext_indices)
        ):
            raise ValueError(
                "word_length_information length must match plaintext_indices length"
            )
        object.__setattr__(self, "word_length_information", wli)
        for field_name in ("plaintext_runes", "plaintext_rune_latin"):
            value = getattr(self, field_name)
            if value is not None and not isinstance(value, str):
                raise TypeError(f"{field_name} must be a string or None")
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


def _normalize_word_length_information(
    value: object,
) -> WordLengthInformation | None:
    if value is None:
        return None
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError("word_length_information must be an ordered sequence or None")
    normalized: list[tuple[int, int]] = []
    for index, raw_pair in enumerate(value):
        field_name = f"word_length_information[{index}]"
        if isinstance(raw_pair, (str, bytes)) or not isinstance(raw_pair, Sequence):
            raise TypeError(f"{field_name} must be an ordered sequence")
        if len(raw_pair) != 2:
            raise ValueError(f"{field_name} must contain exactly two items")
        if any(
            isinstance(item, bool) or not isinstance(item, Integral)
            for item in raw_pair
        ):
            raise TypeError(f"{field_name} items must be integers")
        pair = (int(raw_pair[0]), int(raw_pair[1]))
        if pair[0] < 0 or pair[1] <= 0 or pair[0] >= pair[1]:
            raise ValueError(
                f"{field_name} must be (position, word_length) with "
                "0 <= position < word_length"
            )
        normalized.append(pair)
    return tuple(normalized)


__all__ = ["RunResult"]
