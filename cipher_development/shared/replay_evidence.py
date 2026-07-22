from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Any

from cipher_development.shared.archive import (
    CandidateRecord,
    _atomic_write_json,
    _candidate_id,
    _canonical_json,
    _snapshot_json,
    _thaw_json,
)
from cipher_development.shared.replay import (
    CandidateReplayBatch,
    CandidateReplayContext,
    _finite,
    _hash40,
    _identifier,
    _non_negative,
    _reject_replay_reference_fields,
    _strict_keys,
    _text,
)

EVIDENCE_SCHEMA = "rdp_cipher_development_candidate_replay_evidence.v1"
_EVIDENCE_KEYS = frozenset({
    "schema", "replay_id", "mode", "source_batch_id", "source_archive_hash",
    "source_context_id", "evaluator_id", "configuration_hash", "decision_score",
    "higher_is_better", "repeat_count", "absolute_tolerance", "relative_tolerance",
    "candidate_ids", "observations", "ranking", "deterministic",
    "stored_scores_verified", "evaluator_configuration",
})

class ReplayMode(StrEnum):
    VERIFY = "verify"
    RERANK = "rerank"


@dataclass(frozen=True, slots=True)
class ReplayEvaluation:
    scores: Mapping[str, float]
    stable_metrics: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.scores, Mapping) or not self.scores:
            raise ValueError("scores must be a non-empty mapping")
        scores: dict[str, float] = {}
        for raw_name, raw_value in self.scores.items():
            name = _text(raw_name, "score name")
            _reject_replay_reference_fields({name: 0}, "scores")
            if name in scores:
                raise ValueError(f"scores contain duplicate normalised name {name!r}")
            scores[name] = _finite(raw_value, f"score {name!r}")
        if not isinstance(self.stable_metrics, Mapping):
            raise TypeError("stable_metrics must be a mapping")
        metrics = _snapshot_json(self.stable_metrics, "stable_metrics")
        _reject_replay_reference_fields(metrics, "stable_metrics")
        object.__setattr__(self, "scores", MappingProxyType(scores))
        object.__setattr__(self, "stable_metrics", metrics)

    def to_json_dict(self) -> dict[str, Any]:
        return {"scores": dict(self.scores), "stable_metrics": _thaw_json(self.stable_metrics)}


@dataclass(frozen=True, slots=True)
class CandidateReplayObservation:
    candidate_id: str
    stored_scores: Mapping[str, float]
    observed_scores: Mapping[str, float]
    repeat_scores: tuple[Mapping[str, float], ...]
    stable_metrics: Mapping[str, Any]
    maximum_repeat_delta: float
    stored_score_delta: float | None

    def __post_init__(self) -> None:
        candidate_id = _candidate_id(self.candidate_id)
        stored = ReplayEvaluation(self.stored_scores).scores
        observed = ReplayEvaluation(self.observed_scores).scores
        repeats = tuple(ReplayEvaluation(item).scores for item in self.repeat_scores)
        if not repeats:
            raise ValueError("repeat_scores must not be empty")
        if any(tuple(item) != tuple(observed) for item in repeats):
            raise ValueError("repeat scores must use the same score names and order")
        if dict(repeats[0]) != dict(observed):
            raise ValueError("observed_scores must equal the first repeat score mapping")
        metrics = _snapshot_json(self.stable_metrics, "stable_metrics")
        _reject_replay_reference_fields(metrics, "stable_metrics")
        maximum = _non_negative(self.maximum_repeat_delta, "maximum_repeat_delta")
        calculated_maximum = max(
            (abs(item[name] - repeats[0][name]) for item in repeats[1:] for name in observed),
            default=0.0,
        )
        if maximum != calculated_maximum:
            raise ValueError("maximum_repeat_delta contradicts repeat_scores")
        stored_delta = (
            None if self.stored_score_delta is None
            else _non_negative(self.stored_score_delta, "stored_score_delta")
        )
        object.__setattr__(self, "candidate_id", candidate_id)
        object.__setattr__(self, "stored_scores", stored)
        object.__setattr__(self, "observed_scores", observed)
        object.__setattr__(self, "repeat_scores", repeats)
        object.__setattr__(self, "stable_metrics", metrics)
        object.__setattr__(self, "maximum_repeat_delta", maximum)
        object.__setattr__(self, "stored_score_delta", stored_delta)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "stored_scores": dict(self.stored_scores),
            "observed_scores": dict(self.observed_scores),
            "repeat_scores": [dict(item) for item in self.repeat_scores],
            "stable_metrics": _thaw_json(self.stable_metrics),
            "maximum_repeat_delta": self.maximum_repeat_delta,
            "stored_score_delta": self.stored_score_delta,
        }

    @classmethod
    def from_json_dict(cls, payload: Mapping[str, Any]) -> "CandidateReplayObservation":
        if not isinstance(payload, Mapping):
            raise TypeError("replay observation must be a mapping")
        expected = frozenset({
            "candidate_id", "stored_scores", "observed_scores", "repeat_scores",
            "stable_metrics", "maximum_repeat_delta", "stored_score_delta",
        })
        _strict_keys(payload, expected, "replay observation")
        values = dict(payload)
        repeats = values.get("repeat_scores")
        if not isinstance(repeats, list):
            raise TypeError("repeat_scores must be a list")
        values["repeat_scores"] = tuple(repeats)
        return cls(**values)


def _evidence_content(evidence: "CandidateReplayEvidence") -> dict[str, Any]:
    return {
        "schema": EVIDENCE_SCHEMA,
        "mode": evidence.mode.value,
        "source_batch_id": evidence.source_batch_id,
        "source_archive_hash": evidence.source_archive_hash,
        "source_context_id": evidence.source_context_id,
        "evaluator_id": evidence.evaluator_id,
        "configuration_hash": evidence.configuration_hash,
        "decision_score": evidence.decision_score,
        "higher_is_better": evidence.higher_is_better,
        "repeat_count": evidence.repeat_count,
        "absolute_tolerance": evidence.absolute_tolerance,
        "relative_tolerance": evidence.relative_tolerance,
        "candidate_ids": list(evidence.candidate_ids),
        "observations": [item.to_json_dict() for item in evidence.observations],
        "ranking": list(evidence.ranking),
        "deterministic": evidence.deterministic,
        "stored_scores_verified": evidence.stored_scores_verified,
        "evaluator_configuration": _thaw_json(evidence.evaluator_configuration),
    }


def _replay_id(content: Mapping[str, Any]) -> str:
    return hashlib.blake2b(
        _canonical_json(content, "replay_evidence").encode("utf-8"),
        digest_size=20,
        person=b"rdp-evidence-v1",
    ).hexdigest()


def _within_tolerance(a: float, b: float, absolute: float, relative: float) -> bool:
    return math.isclose(a, b, abs_tol=absolute, rel_tol=relative)


@dataclass(frozen=True, slots=True)
class CandidateReplayEvidence:
    schema: str
    replay_id: str
    mode: ReplayMode
    source_batch_id: str
    source_archive_hash: str
    source_context_id: str
    evaluator_id: str
    configuration_hash: str
    decision_score: str
    higher_is_better: bool
    repeat_count: int
    absolute_tolerance: float
    relative_tolerance: float
    candidate_ids: tuple[str, ...]
    observations: tuple[CandidateReplayObservation, ...]
    ranking: tuple[str, ...]
    deterministic: bool
    stored_scores_verified: bool | None
    evaluator_configuration: Mapping[str, Any]

    def __post_init__(self) -> None:
        if self.schema != EVIDENCE_SCHEMA:
            raise ValueError(f"schema must be {EVIDENCE_SCHEMA!r}")
        try:
            mode = self.mode if isinstance(self.mode, ReplayMode) else ReplayMode(str(self.mode))
        except ValueError as exc:
            raise ValueError("mode must be verify or rerank") from exc
        source_batch_id = _hash40(self.source_batch_id, "source_batch_id")
        source_archive_hash = _hash40(self.source_archive_hash, "source_archive_hash")
        source_context_id = _hash40(self.source_context_id, "source_context_id")
        evaluator_id = _identifier(self.evaluator_id, "evaluator_id")
        configuration_hash = _hash40(self.configuration_hash, "configuration_hash")
        decision_score = _text(self.decision_score, "decision_score")
        _reject_replay_reference_fields({decision_score: 0}, "decision_score")
        if type(self.higher_is_better) is not bool:
            raise TypeError("higher_is_better must be a bool")
        if isinstance(self.repeat_count, bool) or not isinstance(self.repeat_count, int):
            raise TypeError("repeat_count must be an integer")
        if self.repeat_count < 2:
            raise ValueError("repeat_count must be at least 2")
        absolute_tolerance = _non_negative(self.absolute_tolerance, "absolute_tolerance")
        relative_tolerance = _non_negative(self.relative_tolerance, "relative_tolerance")
        candidate_ids = tuple(_candidate_id(item, "candidate_ids[]") for item in self.candidate_ids)
        if not candidate_ids or len(set(candidate_ids)) != len(candidate_ids):
            raise ValueError("candidate_ids must be non-empty and unique")
        observations = tuple(self.observations)
        if not all(isinstance(item, CandidateReplayObservation) for item in observations):
            raise TypeError("observations must contain CandidateReplayObservation values")
        if tuple(item.candidate_id for item in observations) != candidate_ids:
            raise ValueError("observations must correspond exactly to candidate_ids")
        if any(len(item.repeat_scores) != self.repeat_count for item in observations):
            raise ValueError("every observation must contain repeat_count score mappings")
        if any(decision_score not in item.observed_scores for item in observations):
            raise ValueError("decision_score must exist in every observed score mapping")
        ranking = tuple(_candidate_id(item, "ranking[]") for item in self.ranking)
        if set(ranking) != set(candidate_ids) or len(ranking) != len(candidate_ids):
            raise ValueError("ranking must contain every candidate exactly once")
        calculated_ranking = tuple(
            item.candidate_id
            for item in sorted(
                observations,
                key=lambda item: (
                    -item.observed_scores[decision_score]
                    if self.higher_is_better
                    else item.observed_scores[decision_score],
                    item.candidate_id,
                ),
            )
        )
        if ranking != calculated_ranking:
            raise ValueError("ranking contradicts observed decision scores")
        if type(self.deterministic) is not bool:
            raise TypeError("deterministic must be a bool")
        calculated_deterministic = all(
            all(
                _within_tolerance(
                    repeat[name],
                    observation.repeat_scores[0][name],
                    absolute_tolerance,
                    relative_tolerance,
                )
                for repeat in observation.repeat_scores[1:]
                for name in observation.observed_scores
            )
            for observation in observations
        )
        if self.deterministic != calculated_deterministic:
            raise ValueError("deterministic flag contradicts repeat scores")
        if (
            self.stored_scores_verified is not None
            and type(self.stored_scores_verified) is not bool
        ):
            raise TypeError("stored_scores_verified must be bool or None")
        if mode is ReplayMode.RERANK:
            if self.stored_scores_verified is not None:
                raise ValueError("rerank evidence must not verify stored scores")
            if any(item.stored_score_delta is not None for item in observations):
                raise ValueError("rerank observations must not contain stored score deltas")
        else:
            calculated_verified = all(
                decision_score in item.stored_scores
                and all(
                    _within_tolerance(
                        repeat[decision_score],
                        item.stored_scores[decision_score],
                        absolute_tolerance,
                        relative_tolerance,
                    )
                    for repeat in item.repeat_scores
                )
                for item in observations
            )
            if self.stored_scores_verified != calculated_verified:
                raise ValueError(
                    "stored_scores_verified contradicts stored and observed scores"
                )
            for item in observations:
                expected_delta = max(
                    abs(
                        repeat[decision_score]
                        - item.stored_scores[decision_score]
                    )
                    for repeat in item.repeat_scores
                )
                if item.stored_score_delta != expected_delta:
                    raise ValueError(
                        "stored_score_delta contradicts stored and observed scores"
                    )
        evaluator_configuration = _snapshot_json(
            self.evaluator_configuration, "evaluator_configuration"
        )
        _reject_replay_reference_fields(evaluator_configuration, "evaluator_configuration")

        object.__setattr__(self, "mode", mode)
        object.__setattr__(self, "source_batch_id", source_batch_id)
        object.__setattr__(self, "source_archive_hash", source_archive_hash)
        object.__setattr__(self, "source_context_id", source_context_id)
        object.__setattr__(self, "evaluator_id", evaluator_id)
        object.__setattr__(self, "configuration_hash", configuration_hash)
        object.__setattr__(self, "decision_score", decision_score)
        object.__setattr__(self, "absolute_tolerance", absolute_tolerance)
        object.__setattr__(self, "relative_tolerance", relative_tolerance)
        object.__setattr__(self, "candidate_ids", candidate_ids)
        object.__setattr__(self, "observations", observations)
        object.__setattr__(self, "ranking", ranking)
        object.__setattr__(self, "evaluator_configuration", evaluator_configuration)
        expected = _replay_id(_evidence_content(self))
        if str(self.replay_id) != expected:
            raise ValueError("replay_id does not match replay evidence content")
        object.__setattr__(self, "replay_id", expected)

    def to_json_dict(self) -> dict[str, Any]:
        return {"replay_id": self.replay_id, **_evidence_content(self)}

    @classmethod
    def from_json_dict(cls, payload: Mapping[str, Any]) -> "CandidateReplayEvidence":
        if not isinstance(payload, Mapping):
            raise TypeError("candidate replay evidence must be a mapping")
        _strict_keys(payload, _EVIDENCE_KEYS, "candidate replay evidence")
        values = dict(payload)
        raw_observations = values.get("observations")
        if not isinstance(raw_observations, list):
            raise TypeError("observations must be a list")
        values["observations"] = tuple(
            CandidateReplayObservation.from_json_dict(item) for item in raw_observations
        )
        values["candidate_ids"] = tuple(values.get("candidate_ids", ()))
        values["ranking"] = tuple(values.get("ranking", ()))
        return cls(**values)



def write_candidate_replay(path: Path, evidence: CandidateReplayEvidence) -> None:
    if not isinstance(evidence, CandidateReplayEvidence):
        raise TypeError("evidence must be CandidateReplayEvidence")
    _atomic_write_json(path, evidence.to_json_dict())


def read_candidate_replay(path: Path) -> CandidateReplayEvidence:
    if not isinstance(path, Path):
        raise TypeError("path must be a Path")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"malformed candidate replay JSON: {exc.msg}") from exc
    if not isinstance(payload, Mapping) or payload.get("schema") != EVIDENCE_SCHEMA:
        raise ValueError(f"candidate replay schema must be {EVIDENCE_SCHEMA!r}")
    return CandidateReplayEvidence.from_json_dict(payload)



__all__ = [
    "EVIDENCE_SCHEMA",
    "CandidateReplayEvidence",
    "CandidateReplayObservation",
    "ReplayEvaluation",
    "ReplayMode",
    "read_candidate_replay",
    "write_candidate_replay",
]
