from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable


def basin_id_from_payload(payload: dict[str, Any], *, fallback: str) -> str:
    end_hash = str(payload.get("end_hash", "")).strip()
    if end_hash:
        return end_hash
    start_hash = str(payload.get("start_hash", "")).strip()
    if start_hash:
        return start_hash
    return str(fallback)


@dataclass(frozen=True)
class CandidateRecord:
    candidate_id: str
    basin_id: str
    decision_score: float
    match_ratio: float
    payload: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(
        cls,
        *,
        candidate_id: str,
        decision_score: float,
        match_ratio: float,
        payload: dict[str, Any],
    ) -> "CandidateRecord":
        return cls(
            candidate_id=str(candidate_id),
            basin_id=basin_id_from_payload(payload, fallback=str(candidate_id)),
            decision_score=float(decision_score),
            match_ratio=float(match_ratio),
            payload=dict(payload),
        )


@dataclass
class CandidatePool:
    candidates: list[CandidateRecord] = field(default_factory=list)

    def add(self, record: CandidateRecord) -> None:
        self.candidates.append(record)

    def extend(self, records: Iterable[CandidateRecord]) -> None:
        for row in records:
            self.add(row)

    def dedupe(self) -> "CandidatePool":
        seen: set[str] = set()
        out: list[CandidateRecord] = []
        for row in self.sorted_by_decision():
            if row.candidate_id in seen:
                continue
            seen.add(row.candidate_id)
            out.append(row)
        return CandidatePool(out)

    def dedupe_by_basin(self) -> "CandidatePool":
        seen: set[str] = set()
        out: list[CandidateRecord] = []
        for row in self.sorted_by_decision():
            basin = str(row.basin_id)
            if basin in seen:
                continue
            seen.add(basin)
            out.append(row)
        return CandidatePool(out)

    def cap_per_basin(self, cap: int) -> "CandidatePool":
        if int(cap) <= 0:
            return CandidatePool(list(self.candidates))
        kept: list[CandidateRecord] = []
        counts: dict[str, int] = {}
        for row in self.sorted_by_decision():
            c = int(counts.get(row.basin_id, 0))
            if c >= int(cap):
                continue
            counts[row.basin_id] = c + 1
            kept.append(row)
        return CandidatePool(kept)

    def promote_top(self, n: int) -> "CandidatePool":
        top_n = max(0, int(n))
        if top_n == 0:
            return CandidatePool([])
        return CandidatePool(self.sorted_by_decision()[:top_n])

    def select_basin_representatives(self, *, reps_per_basin: int = 1) -> "CandidatePool":
        reps = max(1, int(reps_per_basin))
        kept: list[CandidateRecord] = []
        counts: dict[str, int] = {}
        for row in self.sorted_by_decision():
            basin = str(row.basin_id)
            c = int(counts.get(basin, 0))
            if c >= reps:
                continue
            counts[basin] = c + 1
            kept.append(row)
        return CandidatePool(kept)

    def sorted_by_decision(self) -> list[CandidateRecord]:
        return sorted(
            self.candidates,
            key=lambda row: (float(row.decision_score), float(row.match_ratio), str(row.candidate_id)),
            reverse=True,
        )
