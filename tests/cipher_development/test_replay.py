from __future__ import annotations

import json
from pathlib import Path

import pytest

from cipher_development.shared.archive import (
    ArchivePolicy,
    CandidateArchive,
    CandidateProvenance,
    CandidateRecord,
    archive_content_hash,
    candidate_id_for,
)
from cipher_development.shared.replay import (
    CandidateBatchPurpose,
    CandidateReplayBatch,
    read_candidate_batch,
    select_candidate_batch,
    write_candidate_batch,
)


def _record(value: int, score: float) -> CandidateRecord:
    identity = {"value": value}
    return CandidateRecord(
        candidate_id=candidate_id_for(identity),
        identity=identity,
        payload={"key": [value, value + 1]},
        scores={"wli_score": score, "cheap_score": score / 2},
        provenance=CandidateProvenance(source="test", evaluation_index=value),
    )


def _archive() -> CandidateArchive:
    archive = CandidateArchive(ArchivePolicy(capacity=5, decision_score="wli_score"))
    for record in (_record(1, 1.0), _record(2, 3.0), _record(3, 2.0)):
        archive.offer(record)
    return archive


def test_ranked_selection_uses_archive_order_and_limit() -> None:
    archive = _archive()
    batch = select_candidate_batch(
        archive, purpose="replay", selection_label="top_two", limit=2,
    )
    assert batch.purpose is CandidateBatchPurpose.REPLAY
    assert batch.candidate_ids == tuple(record.candidate_id for record in archive.records[:2])
    assert [record.scores["wli_score"] for record in batch.candidates] == [3.0, 2.0]


def test_large_ranked_limit_returns_all_available_candidates() -> None:
    archive = _archive()
    batch = select_candidate_batch(
        archive, purpose="handoff", selection_label="all", limit=99,
    )
    assert batch.purpose is CandidateBatchPurpose.HANDOFF
    assert len(batch.candidates) == len(archive.records)


def test_explicit_selection_preserves_requested_order() -> None:
    archive = _archive()
    requested = (archive.records[2].candidate_id, archive.records[0].candidate_id)
    batch = select_candidate_batch(
        archive, purpose="handoff", selection_label="selected", candidate_ids=requested,
    )
    assert batch.candidate_ids == requested
    assert tuple(record.candidate_id for record in batch.candidates) == requested


def test_selection_rejects_unknown_duplicate_or_ambiguous_requests() -> None:
    archive = _archive()
    known = archive.records[0].candidate_id
    unknown = candidate_id_for({"missing": 1})
    with pytest.raises(ValueError, match="unknown"):
        select_candidate_batch(
            archive, purpose="replay", selection_label="bad", candidate_ids=(unknown,),
        )
    with pytest.raises(ValueError, match="unique"):
        select_candidate_batch(
            archive, purpose="replay", selection_label="bad", candidate_ids=(known, known),
        )
    with pytest.raises(ValueError, match="exactly one"):
        select_candidate_batch(
            archive, purpose="replay", selection_label="bad", limit=1,
            candidate_ids=(known,),
        )
    with pytest.raises(ValueError, match="exactly one"):
        select_candidate_batch(archive, purpose="replay", selection_label="bad")


@pytest.mark.parametrize("bad", [0, -1, True, 1.5])
def test_ranked_limit_must_be_positive_integer(bad) -> None:
    with pytest.raises((TypeError, ValueError)):
        select_candidate_batch(_archive(), purpose="replay", selection_label="bad", limit=bad)


def test_batch_id_is_deterministic_and_candidate_order_is_significant() -> None:
    archive = _archive()
    first = select_candidate_batch(archive, purpose="replay", selection_label="same", limit=3)
    second = select_candidate_batch(archive, purpose="replay", selection_label="same", limit=3)
    reversed_batch = select_candidate_batch(
        archive,
        purpose="replay",
        selection_label="same",
        candidate_ids=tuple(reversed(first.candidate_ids)),
    )
    assert first.batch_id == second.batch_id
    assert first.batch_id != reversed_batch.batch_id


def test_batch_is_independent_of_later_archive_changes_and_detects_source_mismatch() -> None:
    archive = _archive()
    batch = select_candidate_batch(archive, purpose="handoff", selection_label="handoff", limit=2)
    assert batch.matches_archive(archive)
    saved = batch.to_json_dict()
    archive.offer(_record(4, 10.0))
    assert not batch.matches_archive(archive)
    assert batch.to_json_dict() == saved


def test_batch_requires_valid_purpose_and_matching_embedded_ids() -> None:
    archive = _archive()
    batch = select_candidate_batch(archive, purpose="replay", selection_label="batch", limit=1)
    values = batch.to_json_dict()
    values["purpose"] = "unknown"
    with pytest.raises(ValueError, match="purpose"):
        CandidateReplayBatch.from_json_dict(values)

    values = batch.to_json_dict()
    values["candidate_ids"] = [candidate_id_for({"other": 1})]
    with pytest.raises(ValueError, match="correspond"):
        CandidateReplayBatch.from_json_dict(values)


def test_batch_cannot_contain_reference_material() -> None:
    identity = {"value": 1}
    with pytest.raises(ValueError, match="reference"):
        CandidateRecord(
            candidate_id=candidate_id_for(identity),
            identity=identity,
            payload={"oracle_key": [1]},
            scores={"wli_score": 1.0},
            provenance=CandidateProvenance(source="test"),
        )


def test_batch_atomic_round_trip_and_source_identity(tmp_path: Path) -> None:
    archive = _archive()
    batch = select_candidate_batch(archive, purpose="replay", selection_label="round_trip", limit=2)
    path = tmp_path / "candidate_batch.json"
    write_candidate_batch(path, batch)
    assert not list(tmp_path.glob("*.tmp"))
    restored = read_candidate_batch(path)
    assert restored.to_json_dict() == batch.to_json_dict()
    assert restored.source_archive_hash == archive_content_hash(archive)
    assert restored.matches_archive(archive)


def test_read_batch_rejects_schema_and_batch_id_tampering(tmp_path: Path) -> None:
    batch = select_candidate_batch(
        _archive(), purpose="replay", selection_label="tamper", limit=2,
    )
    path = tmp_path / "batch.json"
    write_candidate_batch(path, batch)
    original = json.loads(path.read_text(encoding="utf-8"))

    payload = dict(original)
    payload["schema"] = "unknown"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="schema"):
        read_candidate_batch(path)

    payload = json.loads(json.dumps(original))
    payload["batch_id"] = "0" * 40
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="does not match"):
        read_candidate_batch(path)


def test_read_batch_rejects_duplicate_ids_and_record_tampering(tmp_path: Path) -> None:
    batch = select_candidate_batch(
        _archive(), purpose="handoff", selection_label="tamper", limit=2,
    )
    path = tmp_path / "batch.json"
    write_candidate_batch(path, batch)
    original = json.loads(path.read_text(encoding="utf-8"))

    payload = json.loads(json.dumps(original))
    payload["candidate_ids"][1] = payload["candidate_ids"][0]
    payload["candidates"][1] = payload["candidates"][0]
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="unique"):
        read_candidate_batch(path)

    payload = json.loads(json.dumps(original))
    payload["candidates"][0]["candidate_id"] = "0" * 40
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="does not match"):
        read_candidate_batch(path)


def test_read_batch_rejects_malformed_json_and_invalid_source_hash(tmp_path: Path) -> None:
    path = tmp_path / "batch.json"
    path.write_text("{broken", encoding="utf-8")
    with pytest.raises(ValueError, match="malformed"):
        read_candidate_batch(path)

    batch = select_candidate_batch(
        _archive(), purpose="replay", selection_label="invalid_source", limit=1,
    )
    payload = batch.to_json_dict()
    payload["source_archive_hash"] = "bad"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="source_archive_hash"):
        read_candidate_batch(path)
