from __future__ import annotations

import hashlib
import json
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
    archive_content_hash,
)

SCHEMA = "rdp_cipher_development_candidate_replay_batch.v1"
_HASH_RE = re.compile(r"^[0-9a-f]{40}$")


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _content_payload(*, purpose: str, source_archive_hash: str, source_decision_score: str,
                     candidate_ids: Sequence[str], candidates: Sequence[CandidateRecord],
                     selection_label: str) -> dict[str, Any]:
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
            purpose = self.purpose if isinstance(self.purpose, CandidateBatchPurpose) \
                else CandidateBatchPurpose(str(self.purpose))
        except ValueError as exc:
            raise ValueError("purpose must be replay or handoff") from exc
        source_archive_hash = str(self.source_archive_hash)
        if not _HASH_RE.fullmatch(source_archive_hash):
            raise ValueError(
                "source_archive_hash must be a 40-character lowercase hexadecimal digest"
            )
        source_decision_score = _text(self.source_decision_score, "source_decision_score")
        selection_label = _text(self.selection_label, "selection_label")
        candidate_ids = tuple(_candidate_id(item, "candidate_ids[]") for item in self.candidate_ids)
        if len(set(candidate_ids)) != len(candidate_ids):
            raise ValueError("candidate_ids must be unique")
        candidates = tuple(self.candidates)
        if not candidates:
            raise ValueError("candidates must not be empty")
        if not all(isinstance(item, CandidateRecord) for item in candidates):
            raise TypeError("candidates must contain CandidateRecord values")
        if tuple(item.candidate_id for item in candidates) != candidate_ids:
            raise ValueError("candidate_ids must correspond exactly to embedded candidates")
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
        values = dict(payload)
        raw_candidates = values.get("candidates")
        if not isinstance(raw_candidates, list):
            raise TypeError("candidate batch candidates must be a list")
        values["candidates"] = tuple(
            CandidateRecord.from_json_dict(item) for item in raw_candidates
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
        purpose_value = purpose if isinstance(purpose, CandidateBatchPurpose) \
            else CandidateBatchPurpose(str(purpose))
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
        ids = tuple(_candidate_id(item, "candidate_ids[]") for item in candidate_ids)
        if not ids:
            raise ValueError("candidate_ids must not be empty")
        if len(set(ids)) != len(ids):
            raise ValueError("candidate_ids must be unique")
        try:
            candidates = tuple(archive.get(item) for item in ids)
        except KeyError as exc:
            raise ValueError(f"unknown candidate ID {exc.args[0]!r}") from exc
    if not candidates:
        raise ValueError("archive selection produced no candidates")
    ids = tuple(candidate.candidate_id for candidate in candidates)
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


__all__ = [
    "CandidateBatchPurpose", "CandidateReplayBatch", "read_candidate_batch",
    "select_candidate_batch", "write_candidate_batch",
]
