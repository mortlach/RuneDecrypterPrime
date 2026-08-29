from __future__ import annotations
import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any
from cipher_development.shared.archive import (
    CandidateArchive,
    CandidateRecord,
    _atomic_write_json,
    _canonical_json,
    _candidate_id,
    _reject_reference_fields,
    _snapshot_json,
    _thaw_json,
    archive_content_hash,
)

SCHEMA = "rdp_cipher_development_candidate_replay_batch.v1"
CONTEXT_SCHEMA = "rdp_cipher_development_replay_context.v1"
_HASH_RE = re.compile("^[0-9a-f]{40}$")
_ID_RE = re.compile("^[a-z0-9][a-z0-9_-]*$")
_BATCH_KEYS = frozenset(
    {
        "batch_id",
        "schema",
        "purpose",
        "source_archive_hash",
        "source_decision_score",
        "candidate_ids",
        "candidates",
        "selection_label",
    }
)
_CONTEXT_KEYS = frozenset(
    {
        "schema",
        "context_id",
        "campaign_id",
        "run_id",
        "configuration_hash",
        "evaluator_id",
        "payload",
    }
)
_EXTRA_REFERENCE_KEYS = {
    "exact_matches",
    "exact_plaintext",
    "rune_matches",
    "word_matches",
    "complete_word_matches",
    "canonical_key_equal",
    "combined_shift_equal",
}
_CONTEXT_ONLY_REFERENCE_KEYS = {
    "plaintext",
    "decoded_plaintext",
    "benchmark_plaintext",
    "benchmark_key",
    "true_key",
    "truth_key_seed",
    "true_key_seed",
    "expected_solution",
}


def _reject_replay_reference_fields(value: Any, name: str) -> None:
    _reject_reference_fields(value, name)
    if isinstance(value, Mapping):
        for key, item in value.items():
            token = str(key).strip().lower()
            if token in _EXTRA_REFERENCE_KEYS:
                raise ValueError(
                    f"{name} must not contain reference or truth field {key!r}"
                )
            _reject_replay_reference_fields(item, name)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _reject_replay_reference_fields(item, name)


def _reject_replay_context_fields(value: Any, name: str) -> None:
    _reject_replay_reference_fields(value, name)
    if isinstance(value, Mapping):
        for key, item in value.items():
            token = str(key).strip().lower()
            if token in _CONTEXT_ONLY_REFERENCE_KEYS:
                raise ValueError(
                    f"{name} must not contain replay-context truth field {key!r}"
                )
            _reject_replay_context_fields(item, name)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _reject_replay_context_fields(item, name)


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _identifier(value: Any, name: str) -> str:
    value = _text(value, name)
    if not _ID_RE.fullmatch(value):
        raise ValueError(f"{name} must use lowercase letters, numbers, '_' or '-'")
    return value


def _hash40(value: Any, name: str) -> str:
    value = _text(value, name)
    if not _HASH_RE.fullmatch(value):
        raise ValueError(f"{name} must be a 40-character lowercase hexadecimal digest")
    return value


def _finite(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be a finite number")
    return result


def _non_negative(value: Any, name: str) -> float:
    result = _finite(value, name)
    if result < 0:
        raise ValueError(f"{name} must be non-negative")
    return result


def _strict_keys(
    payload: Mapping[str, Any], expected: frozenset[str], name: str
) -> None:
    keys = frozenset(payload)
    unknown = keys - expected
    missing = expected - keys
    if unknown:
        raise ValueError(f"{name} contains unknown fields: {sorted(unknown)}")
    if missing:
        raise ValueError(f"{name} is missing required fields: {sorted(missing)}")


def _decision_score(value: Any) -> str:
    score = _text(value, "source_decision_score")
    _reject_replay_reference_fields({score: 0}, "source_decision_score")
    return score


def _content_payload(
    *,
    purpose: str,
    source_archive_hash: str,
    source_decision_score: str,
    candidate_ids: Sequence[str],
    candidates: Sequence[CandidateRecord],
    selection_label: str,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "purpose": purpose,
        "source_archive_hash": source_archive_hash,
        "source_decision_score": source_decision_score,
        "candidate_ids": list(candidate_ids),
        "candidates": [candidate.to_json_dict() for candidate in candidates],
        "selection_label": selection_label,
    }


def _batch_id(payload: Mapping[str, Any]) -> str:
    encoded = _canonical_json(payload, "batch").encode("utf-8")
    return hashlib.blake2b(encoded, digest_size=20, person=b"rdp-replay-v1").hexdigest()


class CandidateBatchPurpose(StrEnum):
    REPLAY = "replay"
    HANDOFF = "handoff"


@dataclass(frozen=True, slots=True)
class CandidateReplayBatch:
    schema: str
    batch_id: str
    purpose: CandidateBatchPurpose
    source_archive_hash: str
    source_decision_score: str
    candidate_ids: tuple[str, ...]
    candidates: tuple[CandidateRecord, ...]
    selection_label: str

    def __post_init__(self) -> None:
        if self.schema != SCHEMA:
            raise ValueError(f"schema must be {SCHEMA!r}")
        try:
            purpose = (
                self.purpose
                if isinstance(self.purpose, CandidateBatchPurpose)
                else CandidateBatchPurpose(str(self.purpose))
            )
        except ValueError as exc:
            raise ValueError("purpose must be replay or handoff") from exc
        source_archive_hash = _hash40(self.source_archive_hash, "source_archive_hash")
        source_decision_score = _decision_score(self.source_decision_score)
        selection_label = _text(self.selection_label, "selection_label")
        candidate_ids = tuple(
            (_candidate_id(item, "candidate_ids[]") for item in self.candidate_ids)
        )
        if len(set(candidate_ids)) != len(candidate_ids):
            raise ValueError("candidate_ids must be unique")
        candidates = tuple(self.candidates)
        if not candidates:
            raise ValueError("candidates must not be empty")
        if not all((isinstance(item, CandidateRecord) for item in candidates)):
            raise TypeError("candidates must contain CandidateRecord values")
        if tuple((item.candidate_id for item in candidates)) != candidate_ids:
            raise ValueError(
                "candidate_ids must correspond exactly to embedded candidates"
            )
        missing_score = [
            candidate.candidate_id
            for candidate in candidates
            if source_decision_score not in candidate.scores
        ]
        if missing_score:
            raise ValueError(
                f"source_decision_score must exist in every embedded candidate; missing from {missing_score}"
            )
        payload = _content_payload(
            purpose=purpose.value,
            source_archive_hash=source_archive_hash,
            source_decision_score=source_decision_score,
            candidate_ids=candidate_ids,
            candidates=candidates,
            selection_label=selection_label,
        )
        expected = _batch_id(payload)
        if str(self.batch_id) != expected:
            raise ValueError("batch_id does not match batch content")
        object.__setattr__(self, "purpose", purpose)
        object.__setattr__(self, "source_archive_hash", source_archive_hash)
        object.__setattr__(self, "source_decision_score", source_decision_score)
        object.__setattr__(self, "candidate_ids", candidate_ids)
        object.__setattr__(self, "candidates", candidates)
        object.__setattr__(self, "selection_label", selection_label)
        object.__setattr__(self, "batch_id", expected)

    def to_json_dict(self) -> dict[str, Any]:
        payload = _content_payload(
            purpose=self.purpose.value,
            source_archive_hash=self.source_archive_hash,
            source_decision_score=self.source_decision_score,
            candidate_ids=self.candidate_ids,
            candidates=self.candidates,
            selection_label=self.selection_label,
        )
        return {"batch_id": self.batch_id, **payload}

    @classmethod
    def from_json_dict(cls, payload: Mapping[str, Any]) -> "CandidateReplayBatch":
        if not isinstance(payload, Mapping):
            raise TypeError("candidate batch must be a mapping")
        _strict_keys(payload, _BATCH_KEYS, "candidate batch")
        values = dict(payload)
        raw_candidates = values.get("candidates")
        if not isinstance(raw_candidates, list):
            raise TypeError("candidate batch candidates must be a list")
        values["candidates"] = tuple(
            (CandidateRecord.from_json_dict(item) for item in raw_candidates)
        )
        return cls(**values)

    def matches_archive(self, archive: CandidateArchive) -> bool:
        return self.source_archive_hash == archive_content_hash(archive)


def select_candidate_batch(
    archive: CandidateArchive,
    *,
    purpose: CandidateBatchPurpose | str,
    selection_label: str,
    limit: int | None = None,
    candidate_ids: Sequence[str] | None = None,
) -> CandidateReplayBatch:
    if not isinstance(archive, CandidateArchive):
        raise TypeError("archive must be a CandidateArchive")
    try:
        purpose_value = (
            purpose
            if isinstance(purpose, CandidateBatchPurpose)
            else CandidateBatchPurpose(str(purpose))
        )
    except ValueError as exc:
        raise ValueError("purpose must be replay or handoff") from exc
    selection_label = _text(selection_label, "selection_label")
    if (limit is None) == (candidate_ids is None):
        raise ValueError("provide exactly one of limit or candidate_ids")
    if limit is not None:
        if isinstance(limit, bool) or not isinstance(limit, int):
            raise TypeError("limit must be a positive integer")
        if limit <= 0:
            raise ValueError("limit must be a positive integer")
        candidates = archive.records[:limit]
    else:
        assert candidate_ids is not None
        ids = tuple((_candidate_id(item, "candidate_ids[]") for item in candidate_ids))
        if not ids:
            raise ValueError("candidate_ids must not be empty")
        if len(set(ids)) != len(ids):
            raise ValueError("candidate_ids must be unique")
        try:
            candidates = tuple((archive.get(item) for item in ids))
        except KeyError as exc:
            raise ValueError(f"unknown candidate ID {exc.args[0]!r}") from exc
    if not candidates:
        raise ValueError("archive selection produced no candidates")
    ids = tuple((candidate.candidate_id for candidate in candidates))
    source_hash = archive_content_hash(archive)
    content = _content_payload(
        purpose=purpose_value.value,
        source_archive_hash=source_hash,
        source_decision_score=archive.policy.decision_score,
        candidate_ids=ids,
        candidates=candidates,
        selection_label=selection_label,
    )
    return CandidateReplayBatch(
        schema=SCHEMA,
        batch_id=_batch_id(content),
        purpose=purpose_value,
        source_archive_hash=source_hash,
        source_decision_score=archive.policy.decision_score,
        candidate_ids=ids,
        candidates=candidates,
        selection_label=selection_label,
    )


def write_candidate_batch(path: Path, batch: CandidateReplayBatch) -> None:
    if not isinstance(batch, CandidateReplayBatch):
        raise TypeError("batch must be a CandidateReplayBatch")
    _atomic_write_json(path, batch.to_json_dict())


def read_candidate_batch(path: Path) -> CandidateReplayBatch:
    if not isinstance(path, Path):
        raise TypeError("path must be a Path")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"malformed candidate batch JSON: {exc.msg}") from exc
    if not isinstance(payload, Mapping) or payload.get("schema") != SCHEMA:
        raise ValueError(f"candidate batch schema must be {SCHEMA!r}")
    return CandidateReplayBatch.from_json_dict(payload)


def _context_content(
    *,
    campaign_id: str,
    run_id: str,
    configuration_hash: str,
    evaluator_id: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema": CONTEXT_SCHEMA,
        "campaign_id": campaign_id,
        "run_id": run_id,
        "configuration_hash": configuration_hash,
        "evaluator_id": evaluator_id,
        "payload": _thaw_json(payload),
    }


def _context_id(content: Mapping[str, Any]) -> str:
    return hashlib.blake2b(
        _canonical_json(content, "replay_context").encode("utf-8"),
        digest_size=20,
        person=b"rdp-context-v1",
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class CandidateReplayContext:
    schema: str
    context_id: str
    campaign_id: str
    run_id: str
    configuration_hash: str
    evaluator_id: str
    payload: Mapping[str, Any]

    def __post_init__(self) -> None:
        if self.schema != CONTEXT_SCHEMA:
            raise ValueError(f"schema must be {CONTEXT_SCHEMA!r}")
        campaign_id = _identifier(self.campaign_id, "campaign_id")
        run_id = _text(self.run_id, "run_id")
        configuration_hash = _hash40(self.configuration_hash, "configuration_hash")
        evaluator_id = _identifier(self.evaluator_id, "evaluator_id")
        if not isinstance(self.payload, Mapping):
            raise TypeError("payload must be a mapping")
        payload = _snapshot_json(self.payload, "payload")
        _reject_replay_context_fields(payload, "payload")
        content = _context_content(
            campaign_id=campaign_id,
            run_id=run_id,
            configuration_hash=configuration_hash,
            evaluator_id=evaluator_id,
            payload=payload,
        )
        expected = _context_id(content)
        if str(self.context_id) != expected:
            raise ValueError("context_id does not match replay context content")
        object.__setattr__(self, "campaign_id", campaign_id)
        object.__setattr__(self, "run_id", run_id)
        object.__setattr__(self, "configuration_hash", configuration_hash)
        object.__setattr__(self, "evaluator_id", evaluator_id)
        object.__setattr__(self, "payload", payload)
        object.__setattr__(self, "context_id", expected)

    @classmethod
    def create(
        cls,
        *,
        campaign_id: str,
        run_id: str,
        configuration_hash: str,
        evaluator_id: str,
        payload: Mapping[str, Any],
    ) -> "CandidateReplayContext":
        frozen = _snapshot_json(payload, "payload")
        _reject_replay_context_fields(frozen, "payload")
        content = _context_content(
            campaign_id=_identifier(campaign_id, "campaign_id"),
            run_id=_text(run_id, "run_id"),
            configuration_hash=_hash40(configuration_hash, "configuration_hash"),
            evaluator_id=_identifier(evaluator_id, "evaluator_id"),
            payload=frozen,
        )
        return cls(context_id=_context_id(content), **content)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "context_id": self.context_id,
            **_context_content(
                campaign_id=self.campaign_id,
                run_id=self.run_id,
                configuration_hash=self.configuration_hash,
                evaluator_id=self.evaluator_id,
                payload=self.payload,
            ),
        }

    @classmethod
    def from_json_dict(cls, payload: Mapping[str, Any]) -> "CandidateReplayContext":
        if not isinstance(payload, Mapping):
            raise TypeError("replay context must be a mapping")
        _strict_keys(payload, _CONTEXT_KEYS, "replay context")
        return cls(**dict(payload))


def write_replay_context(path: Path, context: CandidateReplayContext) -> None:
    if not isinstance(context, CandidateReplayContext):
        raise TypeError("context must be a CandidateReplayContext")
    _atomic_write_json(path, context.to_json_dict())


def read_replay_context(path: Path) -> CandidateReplayContext:
    if not isinstance(path, Path):
        raise TypeError("path must be a Path")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"malformed replay context JSON: {exc.msg}") from exc
    if not isinstance(payload, Mapping) or payload.get("schema") != CONTEXT_SCHEMA:
        raise ValueError(f"replay context schema must be {CONTEXT_SCHEMA!r}")
    return CandidateReplayContext.from_json_dict(payload)


__all__ = [
    "CONTEXT_SCHEMA",
    "CandidateBatchPurpose",
    "CandidateReplayBatch",
    "CandidateReplayContext",
    "read_candidate_batch",
    "read_replay_context",
    "select_candidate_batch",
    "write_candidate_batch",
    "write_replay_context",
]
