from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from cipher_development.shared.archive import (
    ArchiveOfferAction,
    ArchivePolicy,
    CandidateArchive,
    CandidateProvenance,
    CandidateRecord,
    archive_content_hash,
    candidate_id_for,
    read_candidate_archive,
    write_candidate_archive,
)


def _record(
    value: int,
    score: float,
    *,
    score_name: str = "wli_score",
    family_id: str | None = None,
    scores: dict[str, float] | None = None,
) -> CandidateRecord:
    identity = {"value": value, "path": [value, value + 1]}
    return CandidateRecord(
        candidate_id=candidate_id_for(identity),
        identity=identity,
        payload={"key": [value, value + 10]},
        scores=scores or {score_name: score, "cheap_score": score / 2},
        provenance=CandidateProvenance(
            source="test",
            operation="mutate",
            evaluation_index=value,
            details={"restart": value % 2},
        ),
        family_id=family_id,
    )


def _archive(*records: CandidateRecord, capacity: int = 8, family_limit: int | None = None,
             higher_is_better: bool = True) -> CandidateArchive:
    archive = CandidateArchive(ArchivePolicy(
        capacity=capacity,
        decision_score="wli_score",
        higher_is_better=higher_is_better,
        family_limit=family_limit,
    ))
    for record in records:
        assert archive.offer(record).retained
    return archive


def test_candidate_id_is_canonical_sensitive_and_ordered() -> None:
    left = {"b": 2, "a": {"values": [1, 2]}}
    right = {"a": {"values": (1, 2)}, "b": 2}
    assert candidate_id_for(left) == candidate_id_for(right)
    assert candidate_id_for(left) != candidate_id_for({"b": 3, "a": right["a"]})
    assert candidate_id_for({"values": [1, 2]}) != candidate_id_for({"values": [2, 1]})


@pytest.mark.parametrize(
    "bad",
    [
        {"path": Path("fixture.json")},
        {"set": {1, 2}},
        {"frozen_set": frozenset({1, 2})},
        {"callable": lambda: None},
        {"object": object()},
        {1: "bad-key"},
        {"number": math.inf},
        {"number": math.nan},
        {"truth_key": [1, 2]},
        {"nested": {"oracle_score": 1}},
    ],
)
def test_candidate_id_rejects_unstable_or_reference_values(bad) -> None:
    with pytest.raises((TypeError, ValueError)):
        candidate_id_for(bad)


def test_candidate_record_validates_id_scores_and_reference_boundaries() -> None:
    identity = {"value": 1}
    with pytest.raises(ValueError, match="does not match"):
        CandidateRecord(
            candidate_id=candidate_id_for({"value": 2}),
            identity=identity,
            payload={"key": [1]},
            scores={"wli_score": 1.0},
            provenance=CandidateProvenance(source="test"),
        )
    for bad_scores in ({}, {"": 1.0}, {"wli_score": math.nan}, {"wli_score": True}):
        with pytest.raises((TypeError, ValueError)):
            CandidateRecord(
                candidate_id=candidate_id_for(identity), identity=identity,
                payload={"key": [1]}, scores=bad_scores,
                provenance=CandidateProvenance(source="test"),
            )
    with pytest.raises(ValueError, match="reference"):
        _record(1, 2.0, scores={"truth_score": 1.0})
    with pytest.raises(ValueError, match="reference"):
        CandidateRecord(
            candidate_id=candidate_id_for(identity), identity=identity,
            payload={"known_plaintext": "answer"}, scores={"wli_score": 1.0},
            provenance=CandidateProvenance(source="test"),
        )


def test_candidate_and_provenance_take_immutable_snapshots() -> None:
    identity = {"value": [1, 2]}
    payload = {"key": [3, 4]}
    scores = {"wli_score": 5.0}
    details = {"restart": [1]}
    provenance = CandidateProvenance(source="test", details=details)
    record = CandidateRecord(
        candidate_id=candidate_id_for(identity), identity=identity, payload=payload,
        scores=scores, provenance=provenance,
    )
    identity["value"].append(9)
    payload["key"].append(9)
    scores["wli_score"] = -1
    details["restart"].append(9)
    stored = record.to_json_dict()
    assert stored["identity"] == {"value": [1, 2]}
    assert stored["payload"] == {"key": [3, 4]}
    assert stored["scores"] == {"wli_score": 5.0}
    assert stored["provenance"]["details"] == {"restart": [1]}


def test_provenance_validates_parent_ids_and_evaluation_index() -> None:
    parent = candidate_id_for({"parent": 1})
    with pytest.raises(ValueError, match="unique"):
        CandidateProvenance(source="test", parent_ids=(parent, parent))
    with pytest.raises(TypeError):
        CandidateProvenance(source="test", evaluation_index=True)
    with pytest.raises(ValueError):
        CandidateProvenance(source="test", evaluation_index=-1)
    with pytest.raises(ValueError, match="reference"):
        CandidateProvenance(source="test", details={"reference_key": [1]})


def test_archive_policy_validation() -> None:
    for capacity in (0, -1):
        with pytest.raises(ValueError):
            ArchivePolicy(capacity=capacity, decision_score="score")
    with pytest.raises(TypeError):
        ArchivePolicy(capacity=True, decision_score="score")
    with pytest.raises(ValueError):
        ArchivePolicy(capacity=2, decision_score=" ")
    with pytest.raises(TypeError):
        ArchivePolicy(capacity=2, decision_score="score", higher_is_better=1)
    with pytest.raises(ValueError):
        ArchivePolicy(capacity=2, decision_score="score", family_limit=3)


def test_offer_rejects_missing_decision_score_without_mutation() -> None:
    archive = CandidateArchive(ArchivePolicy(capacity=2, decision_score="wli_score"))
    record = _record(1, 1.0, score_name="other_score")
    result = archive.offer(record)
    assert result.action is ArchiveOfferAction.REJECTED
    assert not result.retained
    assert archive.records == ()


def test_archive_higher_and_lower_ordering_and_capacity() -> None:
    high = _archive(_record(1, 1.0), _record(2, 3.0), _record(3, 2.0), capacity=2)
    assert [record.scores["wli_score"] for record in high.records] == [3.0, 2.0]
    low = _archive(
        _record(1, 1.0), _record(2, 3.0), _record(3, 2.0),
        capacity=2, higher_is_better=False,
    )
    assert [record.scores["wli_score"] for record in low.records] == [1.0, 2.0]


def test_equal_scores_use_candidate_id_as_stable_tiebreaker() -> None:
    records = (_record(1, 2.0), _record(2, 2.0), _record(3, 2.0))
    forward = _archive(*records)
    reverse = _archive(*reversed(records))
    expected = sorted(record.candidate_id for record in records)
    assert [record.candidate_id for record in forward.records] == expected
    assert [record.candidate_id for record in reverse.records] == expected


def test_same_candidate_updates_only_for_strictly_better_score() -> None:
    archive = _archive(_record(1, 2.0))
    same_id = archive.records[0].candidate_id
    worse = _record(1, 1.0)
    equal = _record(1, 2.0, scores={"wli_score": 2.0, "cheap_score": 99.0})
    better = _record(1, 3.0, scores={"wli_score": 3.0, "heavy_score": 4.0})
    assert archive.offer(worse).action is ArchiveOfferAction.UNCHANGED
    assert archive.offer(equal).action is ArchiveOfferAction.UNCHANGED
    result = archive.offer(better)
    assert result.action is ArchiveOfferAction.UPDATED
    assert result.candidate_id == same_id
    assert dict(archive.records[0].scores) == {"wli_score": 3.0, "heavy_score": 4.0}


def test_offer_reports_addition_and_eviction() -> None:
    archive = _archive(_record(1, 1.0), capacity=1)
    old_id = archive.records[0].candidate_id
    result = archive.offer(_record(2, 2.0))
    assert result.action is ArchiveOfferAction.EVICTED
    assert result.evicted
    assert result.evicted_candidate_ids == (old_id,)
    assert result.size == 1


def test_family_limit_is_optional_and_null_families_are_independent() -> None:
    unrestricted = _archive(
        _record(1, 3.0, family_id="same"),
        _record(2, 2.0, family_id="same"),
        capacity=3,
    )
    assert len(unrestricted.records) == 2

    limited = _archive(
        _record(1, 3.0, family_id="same"),
        _record(2, 4.0, family_id="same"),
        _record(3, 2.0, family_id=None),
        _record(4, 1.0, family_id=None),
        capacity=4,
        family_limit=1,
    )
    assert [record.family_id for record in limited.records].count("same") == 1
    assert sum(record.family_id is None for record in limited.records) == 2
    assert limited.records[0].scores["wli_score"] == 4.0


def test_archive_statistics_are_compact_and_correct() -> None:
    archive = _archive(
        _record(1, 2.0, family_id="a"),
        _record(2, 3.0, family_id="b"),
        capacity=4,
        family_limit=2,
    )
    stats = archive.statistics()
    assert stats == {
        "capacity": 4,
        "retained": 2,
        "decision_score": "wli_score",
        "higher_is_better": True,
        "family_limit": 2,
        "family_count": 2,
        "best_candidate_id": archive.records[0].candidate_id,
        "best_decision_score": 3.0,
    }


def test_archive_atomic_round_trip_and_hash_stability(tmp_path: Path) -> None:
    archive = _archive(_record(1, 2.0), _record(2, 3.0))
    path = tmp_path / "candidate_archive.json"
    write_candidate_archive(path, archive)
    assert not list(tmp_path.glob("*.tmp"))
    restored = read_candidate_archive(path)
    assert restored.to_json_dict() == archive.to_json_dict()
    assert archive_content_hash(restored) == archive_content_hash(archive)

    payload = json.loads(path.read_text(encoding="utf-8"))
    path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    assert archive_content_hash(read_candidate_archive(path)) == archive_content_hash(archive)


def test_archive_hash_changes_with_policy_or_records() -> None:
    first = _archive(_record(1, 2.0))
    second = _archive(_record(2, 2.0))
    lower = _archive(_record(1, 2.0), higher_is_better=False)
    assert archive_content_hash(first) != archive_content_hash(second)
    assert archive_content_hash(first) != archive_content_hash(lower)


def test_read_archive_rejects_schema_tampering_duplicates_and_capacity(tmp_path: Path) -> None:
    archive = _archive(_record(1, 2.0), _record(2, 3.0))
    path = tmp_path / "archive.json"
    write_candidate_archive(path, archive)
    original = json.loads(path.read_text(encoding="utf-8"))

    payload = dict(original)
    payload["schema"] = "unknown"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="schema"):
        read_candidate_archive(path)

    payload = json.loads(json.dumps(original))
    payload["records"][0]["candidate_id"] = "0" * 40
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="does not match"):
        read_candidate_archive(path)

    payload = json.loads(json.dumps(original))
    payload["records"].append(payload["records"][0])
    payload["policy"]["capacity"] = 3
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        read_candidate_archive(path)

    payload = json.loads(json.dumps(original))
    payload["policy"]["capacity"] = 1
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="capacity"):
        read_candidate_archive(path)


def test_read_archive_rejects_family_order_and_statistics_contradictions(tmp_path: Path) -> None:
    archive = _archive(
        _record(1, 3.0, family_id="a"),
        _record(2, 2.0, family_id="b"),
        capacity=3,
        family_limit=1,
    )
    path = tmp_path / "archive.json"
    write_candidate_archive(path, archive)
    original = json.loads(path.read_text(encoding="utf-8"))

    payload = json.loads(json.dumps(original))
    payload["records"][1]["family_id"] = "a"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="family_limit"):
        read_candidate_archive(path)

    payload = json.loads(json.dumps(original))
    payload["records"].reverse()
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="best-first"):
        read_candidate_archive(path)

    payload = json.loads(json.dumps(original))
    payload["statistics"]["retained"] = 99
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="statistics"):
        read_candidate_archive(path)


def test_read_archive_rejects_malformed_json(tmp_path: Path) -> None:
    path = tmp_path / "archive.json"
    path.write_text("{broken", encoding="utf-8")
    with pytest.raises(ValueError, match="malformed"):
        read_candidate_archive(path)


def test_new_wp2_source_has_no_environment_or_cli_configuration() -> None:
    root = Path(__file__).resolve().parents[2]
    forbidden = ("os.environ", "os.getenv", "sys.argv", "argparse")
    for relpath in (
        Path("cipher_development/shared/archive.py"),
        Path("cipher_development/shared/replay.py"),
    ):
        text = (root / relpath).read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text
