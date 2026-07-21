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
    read_candidate_archive,
    write_candidate_archive,
)
from cipher_development.shared.replay import CandidateReplayBatch, select_candidate_batch


def _record(value: int, scores: dict[str, float] | None = None) -> CandidateRecord:
    identity = {"value": value}
    return CandidateRecord(
        candidate_id=candidate_id_for(identity),
        identity=identity,
        payload={"key": [value]},
        scores=scores or {"wli_score": float(value)},
        provenance=CandidateProvenance(source="test"),
    )


def _archive() -> CandidateArchive:
    archive = CandidateArchive(ArchivePolicy(capacity=2, decision_score="wli_score"))
    archive.offer(_record(1))
    return archive


def test_duplicate_score_names_after_normalisation_are_rejected() -> None:
    identity = {"value": 1}
    with pytest.raises(ValueError, match="duplicate normalised"):
        CandidateRecord(
            candidate_id=candidate_id_for(identity),
            identity=identity,
            payload={"key": [1]},
            scores={"wli_score": 1.0, " wli_score ": 2.0},
            provenance=CandidateProvenance(source="test"),
        )


def test_archive_reader_rejects_unknown_top_level_fields(tmp_path: Path) -> None:
    archive = _archive()
    path = tmp_path / "archive.json"
    write_candidate_archive(path, archive)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["truth_key"] = [1, 2, 3]
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="unknown fields"):
        read_candidate_archive(path)


def test_batch_rejects_reference_decision_score() -> None:
    archive = _archive()
    batch = select_candidate_batch(
        archive,
        purpose="replay",
        selection_label="normal",
        limit=1,
    )
    payload = batch.to_json_dict()
    payload["source_decision_score"] = "truth_score"
    payload.pop("batch_id")
    with pytest.raises(ValueError, match="reference"):
        CandidateReplayBatch(
            schema=payload["schema"],
            batch_id="0" * 40,
            purpose=payload["purpose"],
            source_archive_hash=payload["source_archive_hash"],
            source_decision_score=payload["source_decision_score"],
            candidate_ids=batch.candidate_ids,
            candidates=batch.candidates,
            selection_label=payload["selection_label"],
        )


def test_batch_requires_decision_score_in_every_candidate() -> None:
    archive = _archive()
    batch = select_candidate_batch(
        archive,
        purpose="handoff",
        selection_label="normal",
        limit=1,
    )
    payload = batch.to_json_dict()
    payload["source_decision_score"] = "heavy_score"
    with pytest.raises(ValueError, match="every embedded candidate"):
        CandidateReplayBatch(
            schema=payload["schema"],
            batch_id="0" * 40,
            purpose=payload["purpose"],
            source_archive_hash=archive_content_hash(archive),
            source_decision_score=payload["source_decision_score"],
            candidate_ids=batch.candidate_ids,
            candidates=batch.candidates,
            selection_label=payload["selection_label"],
        )
