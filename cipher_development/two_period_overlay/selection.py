from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from cipher_development.shared.archive import CandidateArchive, CandidateRecord
from cipher_development.shared.replay import CandidateReplayBatch, select_candidate_batch
from cipher_development.two_period_overlay.config import DECISION_SCORE

SELECTION_COUNT = 8
DIVERSE_SHORTLIST_MULTIPLIER = 2


@dataclass(frozen=True, slots=True)
class SelectionComparison:
    source_candidate_count: int
    selection_count: int
    shortlist_count: int
    top_wli_ids: tuple[str, ...]
    diverse_high_wli_ids: tuple[str, ...]
    overlap_count: int
    identical: bool
    top_score_summary: dict[str, float]
    diverse_score_summary: dict[str, float]
    top_affine_hamming_summary: dict[str, float]
    diverse_affine_hamming_summary: dict[str, float]

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema": "rdp.two_period_overlay.selection_comparison.v1",
            "source_candidate_count": self.source_candidate_count,
            "selection_count": self.selection_count,
            "shortlist_count": self.shortlist_count,
            "top_wli_ids": list(self.top_wli_ids),
            "diverse_high_wli_ids": list(self.diverse_high_wli_ids),
            "overlap_count": self.overlap_count,
            "identical": self.identical,
            "top_score_summary": dict(self.top_score_summary),
            "diverse_score_summary": dict(self.diverse_score_summary),
            "top_affine_hamming_summary": dict(self.top_affine_hamming_summary),
            "diverse_affine_hamming_summary": dict(self.diverse_affine_hamming_summary),
        }


def _variables(record: CandidateRecord) -> tuple[int, ...]:
    payload = record.payload
    if not isinstance(payload, dict) and not hasattr(payload, "get"):
        raise TypeError("candidate payload must be a mapping")
    raw = payload.get("variables")
    if not isinstance(raw, (list, tuple)) or not raw:
        raise ValueError("candidate payload must contain non-empty affine variables")
    values = tuple(int(value) for value in raw)
    if any(value < 0 for value in values):
        raise ValueError("affine variables must be non-negative integers")
    return values


def affine_hamming(left: CandidateRecord, right: CandidateRecord) -> int:
    a = _variables(left)
    b = _variables(right)
    if len(a) != len(b):
        raise ValueError("candidate affine dimensions differ")
    return sum(x != y for x, y in zip(a, b, strict=True))


def top_wli_candidate_ids(
    archive: CandidateArchive,
    count: int = SELECTION_COUNT,
) -> tuple[str, ...]:
    _validate_selection_request(archive, count)
    return tuple(record.candidate_id for record in archive.records[:count])


def diverse_high_wli_candidate_ids(
    archive: CandidateArchive,
    count: int = SELECTION_COUNT,
    shortlist_multiplier: int = DIVERSE_SHORTLIST_MULTIPLIER,
) -> tuple[str, ...]:
    _validate_selection_request(archive, count)
    if isinstance(shortlist_multiplier, bool) or not isinstance(shortlist_multiplier, int):
        raise TypeError("shortlist_multiplier must be a positive integer")
    if shortlist_multiplier <= 0:
        raise ValueError("shortlist_multiplier must be a positive integer")
    shortlist = tuple(archive.records[: min(len(archive.records), count * shortlist_multiplier)])
    selected: list[CandidateRecord] = [shortlist[0]]
    while len(selected) < count:
        remaining = [record for record in shortlist if record not in selected]
        if not remaining:
            raise ValueError("shortlist does not contain enough candidates")
        ranked = sorted(
            remaining,
            key=lambda record: (
                -min(affine_hamming(record, chosen) for chosen in selected),
                -float(record.scores[DECISION_SCORE]),
                record.candidate_id,
            ),
        )
        selected.append(ranked[0])
    return tuple(record.candidate_id for record in selected)


def _validate_selection_request(archive: CandidateArchive, count: int) -> None:
    if not isinstance(archive, CandidateArchive):
        raise TypeError("archive must be a CandidateArchive")
    if isinstance(count, bool) or not isinstance(count, int):
        raise TypeError("count must be a positive integer")
    if count <= 0:
        raise ValueError("count must be a positive integer")
    if len(archive.records) < count:
        raise ValueError("archive does not contain enough candidates")
    if archive.policy.decision_score != DECISION_SCORE:
        raise ValueError("archive decision score does not match the WP6 selection contract")


def _score_summary(records: Sequence[CandidateRecord]) -> dict[str, float]:
    scores = np.asarray([float(record.scores[DECISION_SCORE]) for record in records])
    return {
        "minimum": float(np.min(scores)),
        "median": float(np.median(scores)),
        "maximum": float(np.max(scores)),
    }


def _hamming_summary(records: Sequence[CandidateRecord]) -> dict[str, float]:
    if len(records) < 2:
        return {"minimum": 0.0, "median": 0.0, "maximum": 0.0}
    distances = [
        affine_hamming(records[i], records[j])
        for i in range(len(records))
        for j in range(i + 1, len(records))
    ]
    values = np.asarray(distances, dtype=float)
    return {
        "minimum": float(np.min(values)),
        "median": float(np.median(values)),
        "maximum": float(np.max(values)),
    }


def build_selection_batches(
    archive: CandidateArchive,
    *,
    count: int = SELECTION_COUNT,
    shortlist_multiplier: int = DIVERSE_SHORTLIST_MULTIPLIER,
) -> tuple[CandidateReplayBatch, CandidateReplayBatch, SelectionComparison]:
    top_ids = top_wli_candidate_ids(archive, count)
    diverse_ids = diverse_high_wli_candidate_ids(archive, count, shortlist_multiplier)
    top_batch = select_candidate_batch(
        archive,
        purpose="handoff",
        selection_label="top_wli",
        candidate_ids=top_ids,
    )
    diverse_batch = select_candidate_batch(
        archive,
        purpose="handoff",
        selection_label="diverse_high_wli",
        candidate_ids=diverse_ids,
    )
    top_records = tuple(archive.get(item) for item in top_ids)
    diverse_records = tuple(archive.get(item) for item in diverse_ids)
    comparison = SelectionComparison(
        source_candidate_count=len(archive.records),
        selection_count=count,
        shortlist_count=min(len(archive.records), count * shortlist_multiplier),
        top_wli_ids=top_ids,
        diverse_high_wli_ids=diverse_ids,
        overlap_count=len(set(top_ids) & set(diverse_ids)),
        identical=top_ids == diverse_ids,
        top_score_summary=_score_summary(top_records),
        diverse_score_summary=_score_summary(diverse_records),
        top_affine_hamming_summary=_hamming_summary(top_records),
        diverse_affine_hamming_summary=_hamming_summary(diverse_records),
    )
    return top_batch, diverse_batch, comparison
