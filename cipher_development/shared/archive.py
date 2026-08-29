from __future__ import annotations
import hashlib
import json
import math
import os
import re
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum, StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Any
SCHEMA = 'rdp_cipher_development_candidate_archive.v1'
_ID_RE = re.compile('^[0-9a-f]{40}$')
_REFERENCE_KEYS = {'expected_key', 'expected_plaintext', 'ground_truth', 'known_key', 'known_plaintext', 'match_ratio', 'oracle', 'oracle_key', 'reference', 'reference_evaluation', 'reference_metrics', 'test_key', 'truth', 'truth_key', 'truth_metrics'}
_REFERENCE_PREFIXES = ('oracle_', 'reference_', 'truth_')
_ARCHIVE_KEYS = frozenset({'schema', 'policy', 'records', 'statistics'})
_ARCHIVE_REQUIRED_KEYS = frozenset({'schema', 'policy', 'records'})

def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{name} must be a non-empty string')
    return value.strip()

def _candidate_id(value: Any, name: str='candidate_id') -> str:
    value = _text(value, name)
    if not _ID_RE.fullmatch(value):
        raise ValueError(f'{name} must be a 40-character lowercase hexadecimal digest')
    return value

def _reject_reference_fields(value: Any, name: str) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            token = str(key).strip().lower()
            if token in _REFERENCE_KEYS or token.startswith(_REFERENCE_PREFIXES):
                raise ValueError(f'{name} must not contain reference, truth or oracle field {key!r}')
            _reject_reference_fields(item, name)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _reject_reference_fields(item, name)

def _freeze_json(value: Any, name: str) -> Any:
    if isinstance(value, Path):
        raise TypeError(f'{name} must not contain Path values')
    if isinstance(value, Enum):
        return _freeze_json(value.value, name)
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f'{name} contains a non-finite float')
        return float(value)
    if isinstance(value, Mapping):
        frozen: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str) or not key:
                raise TypeError(f'{name} mapping keys must be non-empty strings')
            frozen[key] = _freeze_json(item, f'{name}.{key}')
        return MappingProxyType(frozen)
    if isinstance(value, (list, tuple)):
        return tuple((_freeze_json(item, f'{name}[]') for item in value))
    if isinstance(value, (set, frozenset)):
        raise TypeError(f'{name} must not contain sets')
    if callable(value):
        raise TypeError(f'{name} must not contain callables')
    raise TypeError(f'{name} contains unsupported value type {type(value).__name__}')

def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value

def _snapshot_json(value: Any, name: str) -> Any:
    frozen = _freeze_json(value, name)
    _reject_reference_fields(frozen, name)
    return frozen

def _canonical_json(value: Any, name: str) -> str:
    frozen = _snapshot_json(value, name)
    return json.dumps(_thaw_json(frozen), ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)

def _digest(value: Any, *, name: str, person: bytes) -> str:
    return hashlib.blake2b(_canonical_json(value, name).encode('utf-8'), digest_size=20, person=person).hexdigest()

def candidate_id_for(identity: Any) -> str:
    return _digest(identity, name='identity', person=b'rdp-candidate-v1')

def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    if not isinstance(path, Path):
        raise TypeError('path must be a Path')
    text = json.dumps(_thaw_json(_snapshot_json(payload, 'payload')), ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + '\n'
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f'.{path.name}.{os.getpid()}.{time.time_ns()}.tmp')
    try:
        with temporary.open('w', encoding='utf-8', newline='\n') as handle:
            handle.write(text)
            handle.flush()
            try:
                os.fsync(handle.fileno())
            except OSError:
                pass
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass

@dataclass(frozen=True, slots=True)
class CandidateProvenance:
    source: str
    operation: str | None = None
    parent_ids: tuple[str, ...] = ()
    evaluation_index: int | None = None
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, 'source', _text(self.source, 'source'))
        if self.operation is not None:
            object.__setattr__(self, 'operation', _text(self.operation, 'operation'))
        parents = tuple((_candidate_id(item, 'parent_ids[]') for item in self.parent_ids))
        if len(set(parents)) != len(parents):
            raise ValueError('parent_ids must be unique')
        object.__setattr__(self, 'parent_ids', parents)
        if self.evaluation_index is not None:
            if isinstance(self.evaluation_index, bool) or not isinstance(self.evaluation_index, int):
                raise TypeError('evaluation_index must be a non-negative integer or None')
            if self.evaluation_index < 0:
                raise ValueError('evaluation_index must be a non-negative integer or None')
        if not isinstance(self.details, Mapping):
            raise TypeError('details must be a mapping')
        object.__setattr__(self, 'details', _snapshot_json(self.details, 'details'))

    def to_json_dict(self) -> dict[str, Any]:
        return {'source': self.source, 'operation': self.operation, 'parent_ids': list(self.parent_ids), 'evaluation_index': self.evaluation_index, 'details': _thaw_json(self.details)}

    @classmethod
    def from_json_dict(cls, payload: Mapping[str, Any]) -> 'CandidateProvenance':
        if not isinstance(payload, Mapping):
            raise TypeError('provenance must be a mapping')
        return cls(**dict(payload))

@dataclass(frozen=True, slots=True)
class CandidateRecord:
    candidate_id: str
    identity: Any
    payload: Any
    scores: Mapping[str, float]
    provenance: CandidateProvenance
    family_id: str | None = None

    def __post_init__(self) -> None:
        identity = _snapshot_json(self.identity, 'identity')
        candidate_id = _candidate_id(self.candidate_id)
        if candidate_id != candidate_id_for(identity):
            raise ValueError('candidate_id does not match identity')
        payload = _snapshot_json(self.payload, 'payload')
        if not isinstance(self.scores, Mapping) or not self.scores:
            raise ValueError('scores must be a non-empty mapping')
        scores: dict[str, float] = {}
        for raw_name, value in self.scores.items():
            name = _text(raw_name, 'score name')
            _reject_reference_fields({name: 0}, 'scores')
            if name in scores:
                raise ValueError(f'scores contain duplicate normalised name {name!r}')
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f'score {name!r} must be a finite number')
            score = float(value)
            if not math.isfinite(score):
                raise ValueError(f'score {name!r} must be a finite number')
            scores[name] = score
        if not isinstance(self.provenance, CandidateProvenance):
            raise TypeError('provenance must be a CandidateProvenance')
        family_id = None if self.family_id is None else _text(self.family_id, 'family_id')
        object.__setattr__(self, 'candidate_id', candidate_id)
        object.__setattr__(self, 'identity', identity)
        object.__setattr__(self, 'payload', payload)
        object.__setattr__(self, 'scores', MappingProxyType(scores))
        object.__setattr__(self, 'family_id', family_id)

    def to_json_dict(self) -> dict[str, Any]:
        return {'candidate_id': self.candidate_id, 'identity': _thaw_json(self.identity), 'payload': _thaw_json(self.payload), 'scores': dict(self.scores), 'provenance': self.provenance.to_json_dict(), 'family_id': self.family_id}

    @classmethod
    def from_json_dict(cls, payload: Mapping[str, Any]) -> 'CandidateRecord':
        if not isinstance(payload, Mapping):
            raise TypeError('candidate record must be a mapping')
        values = dict(payload)
        values['provenance'] = CandidateProvenance.from_json_dict(values.get('provenance'))
        return cls(**values)

@dataclass(frozen=True, slots=True)
class ArchivePolicy:
    capacity: int
    decision_score: str
    higher_is_better: bool = True
    family_limit: int | None = None

    def __post_init__(self) -> None:
        if isinstance(self.capacity, bool) or not isinstance(self.capacity, int):
            raise TypeError('capacity must be a positive integer')
        if self.capacity <= 0:
            raise ValueError('capacity must be a positive integer')
        decision_score = _text(self.decision_score, 'decision_score')
        _reject_reference_fields({decision_score: 0}, 'decision_score')
        object.__setattr__(self, 'decision_score', decision_score)
        if type(self.higher_is_better) is not bool:
            raise TypeError('higher_is_better must be a bool')
        if self.family_limit is not None:
            if isinstance(self.family_limit, bool) or not isinstance(self.family_limit, int):
                raise TypeError('family_limit must be a positive integer or None')
            if self.family_limit <= 0 or self.family_limit > self.capacity:
                raise ValueError('family_limit must be positive and no greater than capacity')

    def to_json_dict(self) -> dict[str, Any]:
        return {'capacity': self.capacity, 'decision_score': self.decision_score, 'higher_is_better': self.higher_is_better, 'family_limit': self.family_limit}

    @classmethod
    def from_json_dict(cls, payload: Mapping[str, Any]) -> 'ArchivePolicy':
        if not isinstance(payload, Mapping):
            raise TypeError('archive policy must be a mapping')
        return cls(**dict(payload))

class ArchiveOfferAction(StrEnum):
    ADDED = 'added'
    UPDATED = 'updated'
    UNCHANGED = 'unchanged'
    EVICTED = 'evicted'
    REJECTED = 'rejected'

@dataclass(frozen=True, slots=True)
class ArchiveOfferResult:
    action: ArchiveOfferAction
    candidate_id: str
    retained: bool
    evicted_candidate_ids: tuple[str, ...]
    size: int

    @property
    def evicted(self) -> bool:
        return bool(self.evicted_candidate_ids)

class CandidateArchive:

    def __init__(self, policy: ArchivePolicy) -> None:
        if not isinstance(policy, ArchivePolicy):
            raise TypeError('policy must be an ArchivePolicy')
        self.policy = policy
        self._records: dict[str, CandidateRecord] = {}

    def _rank_key(self, record: CandidateRecord) -> tuple[float, str]:
        score = record.scores[self.policy.decision_score]
        return (-score if self.policy.higher_is_better else score, record.candidate_id)

    def _select(self, records: Mapping[str, CandidateRecord]) -> tuple[CandidateRecord, ...]:
        ordered = sorted(records.values(), key=self._rank_key)
        if self.policy.family_limit is not None:
            counts: dict[str, int] = {}
            selected: list[CandidateRecord] = []
            for record in ordered:
                if record.family_id is not None:
                    count = counts.get(record.family_id, 0)
                    if count >= self.policy.family_limit:
                        continue
                    counts[record.family_id] = count + 1
                selected.append(record)
            ordered = selected
        return tuple(ordered[:self.policy.capacity])

    @property
    def records(self) -> tuple[CandidateRecord, ...]:
        return self._select(self._records)

    def get(self, candidate_id: str) -> CandidateRecord:
        return self._records[_candidate_id(candidate_id)]

    def offer(self, record: CandidateRecord) -> ArchiveOfferResult:
        if not isinstance(record, CandidateRecord):
            raise TypeError('record must be a CandidateRecord')
        if self.policy.decision_score not in record.scores:
            return ArchiveOfferResult(ArchiveOfferAction.REJECTED, record.candidate_id, False, (), len(self._records))
        existing = self._records.get(record.candidate_id)
        if existing is not None:
            old = existing.scores[self.policy.decision_score]
            new = record.scores[self.policy.decision_score]
            better = new > old if self.policy.higher_is_better else new < old
            if not better:
                return ArchiveOfferResult(ArchiveOfferAction.UNCHANGED, record.candidate_id, True, (), len(self._records))
        proposed = dict(self._records)
        proposed[record.candidate_id] = record
        selected = self._select(proposed)
        selected_ids = {item.candidate_id for item in selected}
        if record.candidate_id not in selected_ids:
            return ArchiveOfferResult(ArchiveOfferAction.REJECTED, record.candidate_id, False, (), len(self._records))
        old_ids = set(self._records)
        self._records = {item.candidate_id: item for item in selected}
        evicted = tuple(sorted(old_ids - set(self._records)))
        if evicted:
            action = ArchiveOfferAction.EVICTED
        elif existing is not None:
            action = ArchiveOfferAction.UPDATED
        else:
            action = ArchiveOfferAction.ADDED
        return ArchiveOfferResult(action, record.candidate_id, True, evicted, len(self._records))

    def statistics(self) -> dict[str, Any]:
        records = self.records
        families = {record.family_id for record in records if record.family_id is not None}
        best = records[0] if records else None
        return {'capacity': self.policy.capacity, 'retained': len(records), 'decision_score': self.policy.decision_score, 'higher_is_better': self.policy.higher_is_better, 'family_limit': self.policy.family_limit, 'family_count': len(families), 'best_candidate_id': None if best is None else best.candidate_id, 'best_decision_score': None if best is None else best.scores[self.policy.decision_score]}

    def to_json_dict(self) -> dict[str, Any]:
        return {'schema': SCHEMA, 'policy': self.policy.to_json_dict(), 'records': [record.to_json_dict() for record in self.records], 'statistics': self.statistics()}

def archive_content_hash(archive: CandidateArchive) -> str:
    if not isinstance(archive, CandidateArchive):
        raise TypeError('archive must be a CandidateArchive')
    return _digest({'schema': SCHEMA, 'policy': archive.policy.to_json_dict(), 'records': [record.to_json_dict() for record in archive.records]}, name='archive', person=b'rdp-archive-v1')

def write_candidate_archive(path: Path, archive: CandidateArchive) -> None:
    if not isinstance(archive, CandidateArchive):
        raise TypeError('archive must be a CandidateArchive')
    _atomic_write_json(path, archive.to_json_dict())

def read_candidate_archive(path: Path) -> CandidateArchive:
    if not isinstance(path, Path):
        raise TypeError('path must be a Path')
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise ValueError(f'malformed candidate archive JSON: {exc.msg}') from exc
    if not isinstance(payload, Mapping):
        raise TypeError('candidate archive must be a mapping')
    keys = frozenset(payload)
    unknown = keys - _ARCHIVE_KEYS
    missing = _ARCHIVE_REQUIRED_KEYS - keys
    if unknown:
        raise ValueError(f'candidate archive contains unknown fields: {sorted(unknown)}')
    if missing:
        raise ValueError(f'candidate archive is missing required fields: {sorted(missing)}')
    if payload.get('schema') != SCHEMA:
        raise ValueError(f'candidate archive schema must be {SCHEMA!r}')
    policy = ArchivePolicy.from_json_dict(payload.get('policy'))
    raw_records = payload.get('records')
    if not isinstance(raw_records, list):
        raise TypeError('candidate archive records must be a list')
    if len(raw_records) > policy.capacity:
        raise ValueError('candidate archive contains more records than policy capacity')
    records = tuple((CandidateRecord.from_json_dict(item) for item in raw_records))
    ids = [record.candidate_id for record in records]
    if len(set(ids)) != len(ids):
        raise ValueError('candidate archive contains duplicate candidate IDs')
    if policy.family_limit is not None:
        counts: dict[str, int] = {}
        for record in records:
            if record.family_id is None:
                continue
            counts[record.family_id] = counts.get(record.family_id, 0) + 1
            if counts[record.family_id] > policy.family_limit:
                raise ValueError('candidate archive contradicts policy family_limit')
    archive = CandidateArchive(policy)
    for record in records:
        result = archive.offer(record)
        if not result.retained or result.evicted:
            raise ValueError('candidate archive records contradict retention policy')
    if [record.candidate_id for record in archive.records] != ids:
        raise ValueError('candidate archive records are not in deterministic best-first order')
    statistics = payload.get('statistics')
    if statistics is not None and statistics != archive.statistics():
        raise ValueError('candidate archive statistics contradict records or policy')
    return archive
__all__ = ['ArchiveOfferAction', 'ArchiveOfferResult', 'ArchivePolicy', 'CandidateArchive', 'CandidateProvenance', 'CandidateRecord', 'archive_content_hash', 'candidate_id_for', 'read_candidate_archive', 'write_candidate_archive']
