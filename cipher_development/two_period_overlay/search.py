from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

import numpy as np

from cipher_development.shared.archive import (
    ArchivePolicy,
    CandidateArchive,
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
    _score,
    anneal_and_polish,
    candidate_record,
    comparison_seed,
    control_start_seed,
    coordinate_search,
)

ProgressCallback = Callable[[str, Mapping[str, Any]], None]


@dataclass(frozen=True, slots=True)
class SearchOutcome:
    discovery_archive: CandidateArchive
    archive: CandidateArchive
    handoff_batch: CandidateReplayBatch
    control_batch: CandidateReplayBatch
    comparisons: tuple[Mapping[str, Any], ...]
    best_variables: tuple[int, ...]
    best_score: float
    evaluations: int


def discover_archive(
    evaluate: ScoreVariables,
    particular: np.ndarray,
    basis: np.ndarray,
    budget: RunBudget,
) -> tuple[CandidateArchive, int]:
    archive = CandidateArchive(ArchivePolicy(
        capacity=ARCHIVE_CAPACITY,
        decision_score=DECISION_SCORE,
        higher_is_better=True,
        family_limit=None,
    ))
    evaluations = 0
    for restart in range(budget.coordinate_restarts):
        rng = np.random.default_rng(MASTER_SEED + restart)
        start = rng.integers(0, ALPHABET_SIZE, size=basis.shape[1], dtype=np.uint8)
        variables, score, used = coordinate_search(evaluate, rng, start, budget.coordinate_sweeps)
        evaluations += used
        archive.offer(candidate_record(
            variables,
            score,
            particular,
            basis,
            source="coordinate_discovery",
            operation="coordinate_descent",
            evaluation_index=evaluations,
        ))
    return archive, evaluations


def _control_archive(
    evaluate: ScoreVariables,
    particular: np.ndarray,
    basis: np.ndarray,
    count: int,
    evaluation_index: int,
) -> tuple[CandidateArchive, int]:
    archive = CandidateArchive(ArchivePolicy(
        capacity=count,
        decision_score=DECISION_SCORE,
        higher_is_better=True,
        family_limit=None,
    ))
    attempts = evaluations = 0
    while len(archive.records) < count:
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


def run_search(
    evaluate: ScoreVariables,
    particular: np.ndarray,
    basis: np.ndarray,
    budget: RunBudget,
    progress: ProgressCallback | None = None,
) -> SearchOutcome:
    discovery_archive, evaluations = discover_archive(evaluate, particular, basis, budget)
    if progress is not None:
        progress("discovery_completed", {
            "coordinate_restarts": budget.coordinate_restarts,
            "retained": len(discovery_archive.records),
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
        evaluate, particular, basis, len(handoff.candidates), evaluations
    )
    control_batch = select_candidate_batch(
        controls,
        purpose="handoff",
        selection_label="independent_control_starts",
        limit=len(handoff.candidates),
    )
    evaluations += control_start_evaluations
    if progress is not None:
        progress("handoff_batches_prepared", {
            "archive_candidates": len(handoff.candidates),
            "control_candidates": len(control_batch.candidates),
        })

    comparisons: list[Mapping[str, Any]] = []
    best_variables: np.ndarray | None = None
    best_score = -math.inf
    for index, (archive_start, control_start) in enumerate(zip(
        handoff.candidates, control_batch.candidates, strict=True
    )):
        seed = comparison_seed(index)
        archive_variables = np.asarray(archive_start.payload["variables"], dtype=np.uint8)
        control_variables = np.asarray(control_start.payload["variables"], dtype=np.uint8)
        archive_final, archive_score, archive_diag = anneal_and_polish(
            evaluate, archive_variables, budget, seed
        )
        control_final, control_score, control_diag = anneal_and_polish(
            evaluate, control_variables, budget, seed
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
        offer_result = archive.offer(archive_record)
        if archive_score > best_score:
            best_variables, best_score = archive_final.copy(), archive_score
        if control_score > best_score:
            best_variables, best_score = control_final.copy(), control_score
        comparison = {
            "comparison_index": index,
            "matched_seed": seed,
            "archive_parent_id": archive_start.candidate_id,
            "archive_final_id": archive_record.candidate_id,
            "archive_start_score": archive_start.scores[DECISION_SCORE],
            "archive_final_score": archive_score,
            "archive_gain": archive_score - archive_start.scores[DECISION_SCORE],
            "archive_offer_action": offer_result.action.value,
            "archive_retained": offer_result.retained,
            "control_start_id": control_start.candidate_id,
            "control_start_score": control_start.scores[DECISION_SCORE],
            "control_final_score": control_score,
            "control_gain": control_score - control_start.scores[DECISION_SCORE],
            "archive_diagnostics": dict(archive_diag),
            "control_diagnostics": dict(control_diag),
        }
        comparisons.append(comparison)
        if progress is not None:
            progress("paired_exploitation_result", {
                "comparison_index": index,
                "archive_final_score": archive_score,
                "control_final_score": control_score,
                "evaluations": evaluations,
            })

    assert best_variables is not None
    return SearchOutcome(
        discovery_archive=discovery_archive,
        archive=archive,
        handoff_batch=handoff,
        control_batch=control_batch,
        comparisons=tuple(comparisons),
        best_variables=tuple(int(value) for value in best_variables),
        best_score=float(best_score),
        evaluations=evaluations,
    )


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
    return {
        "comparison_count": len(outcome.comparisons),
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
    if profile == "canary":
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
    }
    write_candidate_archive(paths["coordinate_archive"], outcome.discovery_archive)
    write_candidate_batch(paths["archive_handoff_batch"], outcome.handoff_batch)
    write_candidate_batch(paths["control_start_batch"], outcome.control_batch)
    write_candidate_archive(paths["final_archive"], outcome.archive)
    return {name: path.name for name, path in paths.items()}

