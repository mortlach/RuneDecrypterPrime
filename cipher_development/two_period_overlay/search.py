from __future__ import annotations

import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

import numpy as np

from cipher_development.shared.archive import (
    ArchivePolicy,
    CandidateArchive,
    CandidateRecord,
    write_candidate_archive,
)
from cipher_development.shared.replay import (
    CandidateReplayBatch,
    select_candidate_batch,
    write_candidate_batch,
)
from cipher_development.two_period_overlay.config import (
    ALPHABET_SIZE,
    ARCHIVE_CAPACITY,
    DECISION_SCORE,
    MASTER_SEED,
    RunBudget,
)
from cipher_development.two_period_overlay.keyspace import (
    ScoreVariables,
    _check_deadline,
    _score,
    anneal_and_polish,
    candidate_record,
    comparison_seed,
    control_start_seed,
    coordinate_search,
)

ProgressCallback = Callable[[str, Mapping[str, Any]], None]


@dataclass(frozen=True, slots=True)
class DiscoveryEvidence:
    generated_candidates: int
    unique_candidates: int
    retained_candidates: int
    best_score: float
    median_score: float
    score_distribution: tuple[float, ...]
    last_archive_improvement_evaluation: int | None

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "generated_candidates": self.generated_candidates,
            "unique_candidates": self.unique_candidates,
            "retained_candidates": self.retained_candidates,
            "best_score": self.best_score,
            "median_score": self.median_score,
            "score_distribution": list(self.score_distribution),
            "last_archive_improvement_evaluation": self.last_archive_improvement_evaluation,
        }


@dataclass(frozen=True, slots=True)
class SearchOutcome:
    discovery_archive: CandidateArchive
    archive: CandidateArchive
    control_archive: CandidateArchive
    handoff_batch: CandidateReplayBatch
    control_batch: CandidateReplayBatch
    comparisons: tuple[Mapping[str, Any], ...]
    discovery: DiscoveryEvidence
    best_variables: tuple[int, ...]
    best_score: float
    best_candidate_id: str
    best_arm: str
    evaluations: int
    requested_comparisons: int
    minimum_comparisons: int
    elapsed_s: float


def _archive_policy(capacity: int) -> ArchivePolicy:
    return ArchivePolicy(
        capacity=capacity,
        decision_score=DECISION_SCORE,
        higher_is_better=True,
        family_limit=None,
    )


def discover_archive(
    evaluate: ScoreVariables,
    particular: np.ndarray,
    basis: np.ndarray,
    budget: RunBudget,
    *,
    deadline: float | None = None,
) -> tuple[CandidateArchive, int, DiscoveryEvidence]:
    archive = CandidateArchive(_archive_policy(ARCHIVE_CAPACITY))
    evaluations = 0
    candidate_ids: set[str] = set()
    scores: list[float] = []
    last_improvement: int | None = None
    for restart in range(budget.coordinate_restarts):
        _check_deadline(deadline)
        rng = np.random.default_rng(MASTER_SEED + restart)
        start = rng.integers(0, ALPHABET_SIZE, size=basis.shape[1], dtype=np.uint8)
        variables, score, used = coordinate_search(
            evaluate, rng, start, budget.coordinate_sweeps, deadline=deadline
        )
        evaluations += used
        record = candidate_record(
            variables,
            score,
            particular,
            basis,
            source="coordinate_discovery",
            operation="coordinate_descent",
            evaluation_index=evaluations,
        )
        candidate_ids.add(record.candidate_id)
        scores.append(float(score))
        result = archive.offer(record)
        if result.retained and result.action.value != "unchanged":
            last_improvement = evaluations

    ordered_scores = tuple(sorted(scores, reverse=True))
    evidence = DiscoveryEvidence(
        generated_candidates=len(scores),
        unique_candidates=len(candidate_ids),
        retained_candidates=len(archive.records),
        best_score=max(scores),
        median_score=float(np.median(scores)),
        score_distribution=ordered_scores,
        last_archive_improvement_evaluation=last_improvement,
    )
    return archive, evaluations, evidence


def _control_archive(
    evaluate: ScoreVariables,
    particular: np.ndarray,
    basis: np.ndarray,
    count: int,
    evaluation_index: int,
    *,
    deadline: float | None = None,
) -> tuple[CandidateArchive, int]:
    archive = CandidateArchive(_archive_policy(count))
    attempts = evaluations = 0
    while len(archive.records) < count:
        _check_deadline(deadline)
        rng = np.random.default_rng(control_start_seed(attempts))
        variables = rng.integers(0, ALPHABET_SIZE, size=basis.shape[1], dtype=np.uint8)
        score = float(_score(evaluate, variables)[0])
        evaluations += 1
        archive.offer(candidate_record(
            variables,
            score,
            particular,
            basis,
            source="independent_control",
            operation="random_start",
            evaluation_index=evaluation_index + evaluations,
        ))
        attempts += 1
        if attempts > count * 100:
            raise RuntimeError("could not construct the required unique control starts")
    return archive, evaluations


def _best_record(outcome: SearchOutcome) -> CandidateRecord:
    archive = outcome.archive if outcome.best_arm == "archive" else outcome.control_archive
    return archive.get(outcome.best_candidate_id)


def run_search(
    evaluate: ScoreVariables,
    particular: np.ndarray,
    basis: np.ndarray,
    budget: RunBudget,
    progress: ProgressCallback | None = None,
) -> SearchOutcome:
    started = time.monotonic()
    deadline = started + budget.wallclock_limit_s
    discovery_archive, evaluations, discovery = discover_archive(
        evaluate, particular, basis, budget, deadline=deadline
    )
    if progress is not None:
        progress("discovery_completed", {
            **discovery.to_json_dict(),
            "coordinate_restarts": budget.coordinate_restarts,
            "evaluations": evaluations,
        })

    handoff = select_candidate_batch(
        discovery_archive,
        purpose="handoff",
        selection_label="coordinate_to_sa",
        limit=budget.handoff_candidates,
    )
    archive = CandidateArchive(discovery_archive.policy)
    for record in discovery_archive.records:
        archive.offer(record)

    controls, control_start_evaluations = _control_archive(
        evaluate,
        particular,
        basis,
        len(handoff.candidates),
        evaluations,
        deadline=deadline,
    )
    control_batch = select_candidate_batch(
        controls,
        purpose="handoff",
        selection_label="independent_control_starts",
        limit=len(handoff.candidates),
    )
    control_finals = CandidateArchive(_archive_policy(max(1, len(control_batch.candidates))))
    evaluations += control_start_evaluations
    if progress is not None:
        progress("handoff_batches_prepared", {
            "archive_candidates": len(handoff.candidates),
            "control_candidates": len(control_batch.candidates),
            "requested_candidates": budget.handoff_candidates,
            "minimum_comparisons": budget.minimum_comparisons,
        })

    comparisons: list[Mapping[str, Any]] = []
    best_variables: np.ndarray | None = None
    best_score = -math.inf
    best_candidate_id: str | None = None
    best_arm: str | None = None
    for index, (archive_start, control_start) in enumerate(zip(
        handoff.candidates, control_batch.candidates, strict=True
    )):
        _check_deadline(deadline)
        seed = comparison_seed(index)
        archive_variables = np.asarray(archive_start.payload["variables"], dtype=np.uint8)
        control_variables = np.asarray(control_start.payload["variables"], dtype=np.uint8)
        archive_final, archive_score, archive_diag = anneal_and_polish(
            evaluate, archive_variables, budget, seed, deadline=deadline
        )
        control_final, control_score, control_diag = anneal_and_polish(
            evaluate, control_variables, budget, seed, deadline=deadline
        )
        evaluations += int(archive_diag["evaluations"]) + int(control_diag["evaluations"])

        archive_record = candidate_record(
            archive_final,
            archive_score,
            particular,
            basis,
            source="archive_exploitation",
            operation="short_sa_coordinate_polish",
            evaluation_index=evaluations,
            parent_ids=(archive_start.candidate_id,),
        )
        control_record = candidate_record(
            control_final,
            control_score,
            particular,
            basis,
            source="control_exploitation",
            operation="short_sa_coordinate_polish",
            evaluation_index=evaluations,
            parent_ids=(control_start.candidate_id,),
        )
        archive_offer = archive.offer(archive_record)
        control_offer = control_finals.offer(control_record)

        if archive_score > best_score + 1e-15:
            best_variables = archive_final.copy()
            best_score = archive_score
            best_candidate_id = archive_record.candidate_id
            best_arm = "archive"
        if control_score > best_score + 1e-15:
            best_variables = control_final.copy()
            best_score = control_score
            best_candidate_id = control_record.candidate_id
            best_arm = "control"

        comparison = {
            "comparison_index": index,
            "matched_seed": seed,
            "archive_parent_id": archive_start.candidate_id,
            "archive_final_id": archive_record.candidate_id,
            "archive_start_score": archive_start.scores[DECISION_SCORE],
            "archive_final_score": archive_score,
            "archive_gain": archive_score - archive_start.scores[DECISION_SCORE],
            "archive_offer_action": archive_offer.action.value,
            "archive_retained": archive_offer.retained,
            "control_start_id": control_start.candidate_id,
            "control_final_id": control_record.candidate_id,
            "control_start_score": control_start.scores[DECISION_SCORE],
            "control_final_score": control_score,
            "control_gain": control_score - control_start.scores[DECISION_SCORE],
            "control_offer_action": control_offer.action.value,
            "control_retained": control_offer.retained,
            "archive_diagnostics": dict(archive_diag),
            "control_diagnostics": dict(control_diag),
        }
        comparisons.append(comparison)
        if progress is not None:
            progress("paired_exploitation_result", {
                "comparison_index": index,
                "archive_final_score": archive_score,
                "control_final_score": control_score,
                "archive_final_id": archive_record.candidate_id,
                "control_final_id": control_record.candidate_id,
                "evaluations": evaluations,
            })

    if best_variables is None or best_candidate_id is None or best_arm is None:
        raise RuntimeError("paired search produced no final candidates")
    outcome = SearchOutcome(
        discovery_archive=discovery_archive,
        archive=archive,
        control_archive=control_finals,
        handoff_batch=handoff,
        control_batch=control_batch,
        comparisons=tuple(comparisons),
        discovery=discovery,
        best_variables=tuple(int(value) for value in best_variables),
        best_score=float(best_score),
        best_candidate_id=best_candidate_id,
        best_arm=best_arm,
        evaluations=evaluations,
        requested_comparisons=budget.handoff_candidates,
        minimum_comparisons=budget.minimum_comparisons,
        elapsed_s=float(time.monotonic() - started),
    )
    # Evidence invariant: the candidate used for terminal reference evaluation is persisted.
    _best_record(outcome)
    return outcome


def comparison_summary(outcome: SearchOutcome) -> dict[str, Any]:
    archive_wins = sum(
        row["archive_final_score"] > row["control_final_score"] + 1e-15
        for row in outcome.comparisons
    )
    control_wins = sum(
        row["control_final_score"] > row["archive_final_score"] + 1e-15
        for row in outcome.comparisons
    )
    ties = len(outcome.comparisons) - archive_wins - control_wins
    archive_scores = [float(row["archive_final_score"]) for row in outcome.comparisons]
    control_scores = [float(row["control_final_score"]) for row in outcome.comparisons]
    archive_gains = [float(row["archive_gain"]) for row in outcome.comparisons]
    control_gains = [float(row["control_gain"]) for row in outcome.comparisons]
    comparison_count = len(outcome.comparisons)
    return {
        "comparison_count": comparison_count,
        "requested_comparisons": outcome.requested_comparisons,
        "minimum_comparisons": outcome.minimum_comparisons,
        "underpowered": comparison_count < outcome.minimum_comparisons,
        "archive_wins": archive_wins,
        "control_wins": control_wins,
        "ties": ties,
        "archive_best_final_score": max(archive_scores),
        "control_best_final_score": max(control_scores),
        "archive_median_final_score": float(np.median(archive_scores)),
        "control_median_final_score": float(np.median(control_scores)),
        "archive_median_gain": float(np.median(archive_gains)),
        "control_median_gain": float(np.median(control_gains)),
    }


def campaign_decision(summary: Mapping[str, Any], profile: str) -> str:
    if profile == "canary" or bool(summary["underpowered"]):
        return "refine"
    if (summary["archive_wins"] > summary["control_wins"]
            and summary["archive_best_final_score"] >= summary["control_best_final_score"]):
        return "promote"
    if (summary["archive_wins"] == 0
            and summary["archive_best_final_score"] <= summary["control_best_final_score"]):
        return "close"
    return "refine"


def write_search_artifacts(artifact_dir: Path, outcome: SearchOutcome) -> dict[str, str]:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "coordinate_archive": artifact_dir / "coordinate_archive.json",
        "archive_handoff_batch": artifact_dir / "archive_handoff_batch.json",
        "control_start_batch": artifact_dir / "control_start_batch.json",
        "final_archive": artifact_dir / "final_archive.json",
        "control_final_archive": artifact_dir / "control_final_archive.json",
    }
    write_candidate_archive(paths["coordinate_archive"], outcome.discovery_archive)
    write_candidate_batch(paths["archive_handoff_batch"], outcome.handoff_batch)
    write_candidate_batch(paths["control_start_batch"], outcome.control_batch)
    write_candidate_archive(paths["final_archive"], outcome.archive)
    write_candidate_archive(paths["control_final_archive"], outcome.control_archive)
    return {name: path.name for name, path in paths.items()}
