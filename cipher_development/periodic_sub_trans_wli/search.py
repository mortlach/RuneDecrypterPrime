from __future__ import annotations

import hashlib
import json
import math
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from cipher_development.periodic_sub_trans_wli.benchmark import SearchCase, SolverEvidence
from cipher_development.periodic_sub_trans_wli.config import (
    ALPHABET_SIZE,
    ARCHIVE_CAPACITY,
    MASTER_SEED,
    ORDER,
    RAW_SCORE,
    WLI_SCORE,
    RunBudget,
)
from cipher_development.shared.archive import (
    ArchivePolicy,
    CandidateArchive,
    CandidateProvenance,
    CandidateRecord,
    candidate_id_for,
    write_candidate_archive,
)
from cipher_development.shared.replay import (
    CandidateReplayBatch,
    select_candidate_batch,
    write_candidate_batch,
)


class CampaignWallclockExceeded(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class SupplyEvidence:
    requested_candidates: int
    generated_candidates: int
    invalid_candidates: int
    duplicate_candidates: int
    unique_candidates: int
    retained_candidates: int
    best_raw_score: float
    best_wli_score: float
    raw_score_distribution: tuple[float, ...]
    wli_score_distribution: tuple[float, ...]
    duplicate_rate: float
    raw_wli_rank_correlation: float
    last_retained_improvement_evaluation: int | None

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "requested_candidates": self.requested_candidates,
            "generated_candidates": self.generated_candidates,
            "invalid_candidates": self.invalid_candidates,
            "duplicate_candidates": self.duplicate_candidates,
            "unique_candidates": self.unique_candidates,
            "retained_candidates": self.retained_candidates,
            "best_raw_score": self.best_raw_score,
            "best_wli_score": self.best_wli_score,
            "raw_score_distribution": list(self.raw_score_distribution),
            "wli_score_distribution": list(self.wli_score_distribution),
            "duplicate_rate": self.duplicate_rate,
            "raw_wli_rank_correlation": self.raw_wli_rank_correlation,
            "last_retained_improvement_evaluation": self.last_retained_improvement_evaluation,
        }


@dataclass(frozen=True, slots=True)
class SelectionEvidence:
    requested_handoff: int
    actual_raw_handoff: int
    actual_wli_handoff: int
    raw_candidate_ids: tuple[str, ...]
    wli_candidate_ids: tuple[str, ...]
    intersection_ids: tuple[str, ...]
    raw_only_ids: tuple[str, ...]
    wli_only_ids: tuple[str, ...]
    union_count: int
    jaccard_overlap: float
    same_rank_matches: int
    raw_rank_of_wli: Mapping[str, int]
    wli_rank_of_raw: Mapping[str, int]
    minimum_policy_exclusive: int

    @property
    def policy_exclusive_minimum(self) -> int:
        return min(len(self.raw_only_ids), len(self.wli_only_ids))

    @property
    def ranking_test_valid(self) -> bool:
        return (
            self.actual_raw_handoff == self.requested_handoff
            and self.actual_wli_handoff == self.requested_handoff
            and self.policy_exclusive_minimum >= self.minimum_policy_exclusive
        )

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "requested_handoff": self.requested_handoff,
            "actual_raw_handoff": self.actual_raw_handoff,
            "actual_wli_handoff": self.actual_wli_handoff,
            "raw_candidate_ids": list(self.raw_candidate_ids),
            "wli_candidate_ids": list(self.wli_candidate_ids),
            "intersection_ids": list(self.intersection_ids),
            "raw_only_ids": list(self.raw_only_ids),
            "wli_only_ids": list(self.wli_only_ids),
            "union_count": self.union_count,
            "jaccard_overlap": self.jaccard_overlap,
            "same_rank_matches": self.same_rank_matches,
            "raw_rank_of_wli": dict(self.raw_rank_of_wli),
            "wli_rank_of_raw": dict(self.wli_rank_of_raw),
            "minimum_policy_exclusive": self.minimum_policy_exclusive,
            "policy_exclusive_minimum": self.policy_exclusive_minimum,
            "ranking_test_valid": self.ranking_test_valid,
        }


@dataclass(frozen=True, slots=True)
class CaseOutcome:
    seed_pool_archive: CandidateArchive
    raw_ranking_archive: CandidateArchive
    raw_handoff_batch: CandidateReplayBatch
    wli_handoff_batch: CandidateReplayBatch
    raw_final_archive: CandidateArchive
    wli_final_archive: CandidateArchive
    supply: SupplyEvidence
    selection: SelectionEvidence
    exploitation_rows: tuple[Mapping[str, Any], ...]
    best_candidate_id: str
    best_key: tuple[int, ...]
    best_membership: tuple[str, ...]
    elapsed_s: float


def _archive_policy(decision_score: str, capacity: int = ARCHIVE_CAPACITY) -> ArchivePolicy:
    return ArchivePolicy(
        capacity=capacity,
        decision_score=decision_score,
        higher_is_better=True,
        family_limit=None,
    )


def candidate_record_for_key(
    case: SearchCase,
    key: Sequence[int] | np.ndarray,
    *,
    raw_score: float,
    wli_score: float,
    source: str,
    operation: str,
    evaluation_index: int,
    parent_ids: tuple[str, ...] = (),
    details: Mapping[str, Any] | None = None,
) -> CandidateRecord:
    values = case.validate_key(key).astype(int).tolist()
    identity = {
        "cipher": "periodic_columnar",
        "order": case.order,
        "period": case.period,
        "columns": case.columns,
        "expanded_key": values,
    }
    return CandidateRecord(
        candidate_id=candidate_id_for(identity),
        identity=identity,
        payload={
            "expanded_key": values,
            "period": case.period,
            "columns": case.columns,
            "order": case.order,
        },
        scores={RAW_SCORE: float(raw_score), WLI_SCORE: float(wli_score)},
        provenance=CandidateProvenance(
            source=source,
            operation=operation,
            parent_ids=parent_ids,
            evaluation_index=evaluation_index,
            details={} if details is None else details,
        ),
    )


def _rank_ids(records: Sequence[CandidateRecord], score_name: str) -> tuple[str, ...]:
    return tuple(
        record.candidate_id
        for record in sorted(
            records,
            key=lambda record: (-float(record.scores[score_name]), record.candidate_id),
        )
    )


def _rank_correlation(records: Sequence[CandidateRecord]) -> float:
    if len(records) < 2:
        return 1.0
    raw = _rank_ids(records, RAW_SCORE)
    wli = _rank_ids(records, WLI_SCORE)
    raw_rank = {candidate_id: index for index, candidate_id in enumerate(raw)}
    wli_rank = {candidate_id: index for index, candidate_id in enumerate(wli)}
    left = np.asarray([raw_rank[candidate_id] for candidate_id in raw], dtype=np.float64)
    right = np.asarray([wli_rank[candidate_id] for candidate_id in raw], dtype=np.float64)
    corr = float(np.corrcoef(left, right)[0, 1])
    return 0.0 if not math.isfinite(corr) else corr


def generate_seed_pool(
    case: SearchCase,
    budget: RunBudget,
) -> tuple[CandidateArchive, CandidateArchive, SupplyEvidence]:
    generated = case.generate_seed_keys(budget.candidate_pool_size)
    valid_keys: list[np.ndarray] = []
    invalid = 0
    seen: set[tuple[int, ...]] = set()
    duplicates = 0
    for key in generated:
        try:
            valid = case.validate_key(key)
        except (TypeError, ValueError):
            invalid += 1
            continue
        identity = tuple(int(value) for value in valid)
        if identity in seen:
            duplicates += 1
            continue
        seen.add(identity)
        valid_keys.append(valid)
    if not valid_keys:
        raise RuntimeError("periodic-columnar seed generation produced no valid unique candidates")

    raw_scores, wli_scores = case.score_keys(np.stack(valid_keys))
    if raw_scores.shape != (len(valid_keys),) or wli_scores.shape != (len(valid_keys),):
        raise RuntimeError("candidate scorer returned an invalid score shape")
    if not np.all(np.isfinite(raw_scores)) or not np.all(np.isfinite(wli_scores)):
        raise RuntimeError("candidate scorer returned a non-finite score")

    wli_archive = CandidateArchive(_archive_policy(WLI_SCORE))
    raw_archive = CandidateArchive(_archive_policy(RAW_SCORE))
    records: list[CandidateRecord] = []
    last_improvement: int | None = None
    for index, (key, raw_score, wli_score) in enumerate(
        zip(valid_keys, raw_scores, wli_scores, strict=True), start=1
    ):
        record = candidate_record_for_key(
            case,
            key,
            raw_score=float(raw_score),
            wli_score=float(wli_score),
            source="periodic_columnar_seed_pool",
            operation="structured_seed_generation",
            evaluation_index=index,
            details={"benchmark_id": case.benchmark_id, "pool_index": index - 1},
        )
        records.append(record)
        previous_best = (
            wli_archive.records[0].candidate_id if wli_archive.records else None
        )
        wli_archive.offer(record)
        raw_archive.offer(record)
        current_best = wli_archive.records[0].candidate_id
        if current_best != previous_best:
            last_improvement = index

    evidence = SupplyEvidence(
        requested_candidates=budget.candidate_pool_size,
        generated_candidates=len(generated),
        invalid_candidates=invalid,
        duplicate_candidates=duplicates,
        unique_candidates=len(records),
        retained_candidates=len(wli_archive.records),
        best_raw_score=max(float(record.scores[RAW_SCORE]) for record in records),
        best_wli_score=max(float(record.scores[WLI_SCORE]) for record in records),
        raw_score_distribution=tuple(sorted(
            (float(record.scores[RAW_SCORE]) for record in records), reverse=True
        )),
        wli_score_distribution=tuple(sorted(
            (float(record.scores[WLI_SCORE]) for record in records), reverse=True
        )),
        duplicate_rate=(duplicates / len(generated)) if generated else 0.0,
        raw_wli_rank_correlation=_rank_correlation(records),
        last_retained_improvement_evaluation=last_improvement,
    )
    return wli_archive, raw_archive, evidence


def select_ranking_batches(
    wli_archive: CandidateArchive,
    raw_archive: CandidateArchive,
    budget: RunBudget,
) -> tuple[CandidateReplayBatch, CandidateReplayBatch, SelectionEvidence]:
    count = min(
        budget.handoff_candidates,
        len(wli_archive.records),
        len(raw_archive.records),
    )
    if count <= 0:
        raise RuntimeError("candidate pool produced no handoff candidates")
    wli_batch = select_candidate_batch(
        wli_archive,
        purpose="handoff",
        selection_label="full_wli_ranking",
        limit=count,
    )
    raw_batch = select_candidate_batch(
        raw_archive,
        purpose="handoff",
        selection_label="seed_raw_ranking",
        limit=count,
    )
    wli_ids = tuple(wli_batch.candidate_ids)
    raw_ids = tuple(raw_batch.candidate_ids)
    wli_set = set(wli_ids)
    raw_set = set(raw_ids)
    intersection = tuple(candidate_id for candidate_id in wli_ids if candidate_id in raw_set)
    wli_only = tuple(candidate_id for candidate_id in wli_ids if candidate_id not in raw_set)
    raw_only = tuple(candidate_id for candidate_id in raw_ids if candidate_id not in wli_set)
    union = wli_set | raw_set
    raw_full_ids = _rank_ids(raw_archive.records, RAW_SCORE)
    wli_full_ids = _rank_ids(wli_archive.records, WLI_SCORE)
    raw_ranks = {candidate_id: index + 1 for index, candidate_id in enumerate(raw_full_ids)}
    wli_ranks = {candidate_id: index + 1 for index, candidate_id in enumerate(wli_full_ids)}
    evidence = SelectionEvidence(
        requested_handoff=budget.handoff_candidates,
        actual_raw_handoff=len(raw_ids),
        actual_wli_handoff=len(wli_ids),
        raw_candidate_ids=raw_ids,
        wli_candidate_ids=wli_ids,
        intersection_ids=intersection,
        raw_only_ids=raw_only,
        wli_only_ids=wli_only,
        union_count=len(union),
        jaccard_overlap=(len(intersection) / len(union)) if union else 1.0,
        same_rank_matches=sum(
            left == right for left, right in zip(raw_ids, wli_ids, strict=True)
        ),
        raw_rank_of_wli={candidate_id: raw_ranks.get(candidate_id, 0) for candidate_id in wli_ids},
        wli_rank_of_raw={candidate_id: wli_ranks.get(candidate_id, 0) for candidate_id in raw_ids},
        minimum_policy_exclusive=budget.minimum_policy_exclusive,
    )
    return wli_batch, raw_batch, evidence


def exploitation_seed(benchmark_id: str, candidate_id: str, replicate: int) -> int:
    if isinstance(replicate, bool) or not isinstance(replicate, int) or replicate < 0:
        raise ValueError("replicate must be a non-negative integer")
    payload = f"{MASTER_SEED}:{benchmark_id}:{candidate_id}:{replicate}".encode("ascii")
    return int.from_bytes(
        hashlib.blake2b(payload, digest_size=8, person=b"rdp-wp4-seed").digest(),
        "big",
    )


def _record_membership(
    raw_batch: CandidateReplayBatch, wli_batch: CandidateReplayBatch
) -> dict[str, tuple[str, ...]]:
    membership: dict[str, list[str]] = {}
    for arm, ids in (("wli", wli_batch.candidate_ids), ("raw", raw_batch.candidate_ids)):
        for candidate_id in ids:
            membership.setdefault(candidate_id, []).append(arm)
    return {candidate_id: tuple(arms) for candidate_id, arms in membership.items()}


def _deadline_check(deadline: float) -> None:
    if time.monotonic() >= deadline:
        raise CampaignWallclockExceeded("WP4 campaign wall-clock overrun limit reached")


def run_exploitation(
    case: SearchCase,
    seed_pool_archive: CandidateArchive,
    raw_batch: CandidateReplayBatch,
    wli_batch: CandidateReplayBatch,
    budget: RunBudget,
    *,
    started: float,
) -> tuple[CandidateArchive, CandidateArchive, tuple[Mapping[str, Any], ...]]:
    deadline = started + budget.wallclock_overrun_limit_s
    raw_final = CandidateArchive(_archive_policy(WLI_SCORE))
    wli_final = CandidateArchive(_archive_policy(WLI_SCORE))
    membership = _record_membership(raw_batch, wli_batch)
    ordered_ids = list(wli_batch.candidate_ids)
    ordered_ids.extend(
        candidate_id
        for candidate_id in raw_batch.candidate_ids
        if candidate_id not in wli_batch.candidate_ids
    )
    ordered_ids = list(dict.fromkeys(ordered_ids))

    rows: list[Mapping[str, Any]] = []
    evaluation_index = len(seed_pool_archive.records)
    for candidate_id in ordered_ids:
        parent = seed_pool_archive.get(candidate_id)
        initial_key = parent.payload["expanded_key"]
        for replicate in range(budget.exploitation_replicates):
            _deadline_check(deadline)
            seed = exploitation_seed(case.benchmark_id, candidate_id, replicate)
            solved: SolverEvidence = case.exploit_key(initial_key, seed, budget)
            _deadline_check(deadline)
            raw_scores, wli_scores = case.score_keys([solved.final_key])
            score_delta = float(solved.reported_score) - float(wli_scores[0])
            if not math.isclose(
                float(solved.reported_score),
                float(wli_scores[0]),
                rel_tol=1e-6,
                abs_tol=1e-8,
            ):
                raise RuntimeError(
                    "Kaeding reported score does not match independent WLI rescoring"
                )
            evaluation_index += max(1, solved.evaluations)
            final_record = candidate_record_for_key(
                case,
                solved.final_key,
                raw_score=float(raw_scores[0]),
                wli_score=float(wli_scores[0]),
                source="periodic_columnar_exploitation",
                operation="kaeding_seeded_solve",
                evaluation_index=evaluation_index,
                parent_ids=(candidate_id,),
                details={
                    "benchmark_id": case.benchmark_id,
                    "solver_seed": seed,
                    "replicate": replicate,
                    "policy_membership": list(membership[candidate_id]),
                    "solver_evaluations": solved.evaluations,
                    "solver_elapsed_s": solved.elapsed_s,
                    "solver_stop_reason": solved.stop_reason,
                    "solver_wli_score_delta": score_delta,
                },
            )
            if "raw" in membership[candidate_id]:
                raw_final.offer(final_record)
            if "wli" in membership[candidate_id]:
                wli_final.offer(final_record)
            rows.append({
                "parent_candidate_id": candidate_id,
                "final_candidate_id": final_record.candidate_id,
                "policy_membership": list(membership[candidate_id]),
                "replicate": replicate,
                "solver_seed": seed,
                "start_raw_score": parent.scores[RAW_SCORE],
                "start_wli_score": parent.scores[WLI_SCORE],
                "final_raw_score": final_record.scores[RAW_SCORE],
                "final_wli_score": final_record.scores[WLI_SCORE],
                "wli_gain": final_record.scores[WLI_SCORE] - parent.scores[WLI_SCORE],
                "solver_reported_score": solved.reported_score,
                "solver_wli_score_delta": score_delta,
                "evaluations": solved.evaluations,
                "elapsed_s": solved.elapsed_s,
                "stop_reason": solved.stop_reason,
                "telemetry": dict(solved.telemetry),
            })
    if not raw_final.records or not wli_final.records:
        raise RuntimeError("both ranking arms must produce final candidates")
    return raw_final, wli_final, tuple(rows)


def run_case(case: SearchCase, budget: RunBudget) -> CaseOutcome:
    started = time.monotonic()
    wli_archive, raw_archive, supply = generate_seed_pool(case, budget)
    wli_batch, raw_batch, selection = select_ranking_batches(
        wli_archive, raw_archive, budget
    )
    raw_final, wli_final, rows = run_exploitation(
        case,
        wli_archive,
        raw_batch,
        wli_batch,
        budget,
        started=started,
    )
    all_records = {record.candidate_id: record for record in raw_final.records}
    all_records.update({record.candidate_id: record for record in wli_final.records})
    best = sorted(
        all_records.values(),
        key=lambda record: (-float(record.scores[WLI_SCORE]), record.candidate_id),
    )[0]
    best_membership = tuple(
        arm
        for arm, archive in (("raw", raw_final), ("wli", wli_final))
        if best.candidate_id in {record.candidate_id for record in archive.records}
    )
    return CaseOutcome(
        seed_pool_archive=wli_archive,
        raw_ranking_archive=raw_archive,
        raw_handoff_batch=raw_batch,
        wli_handoff_batch=wli_batch,
        raw_final_archive=raw_final,
        wli_final_archive=wli_final,
        supply=supply,
        selection=selection,
        exploitation_rows=rows,
        best_candidate_id=best.candidate_id,
        best_key=tuple(int(value) for value in best.payload["expanded_key"]),
        best_membership=best_membership,
        elapsed_s=float(time.monotonic() - started),
    )


def _arm_summary(
    archive: CandidateArchive,
    rows: Sequence[Mapping[str, Any]],
    arm: str,
) -> dict[str, Any]:
    relevant = [row for row in rows if arm in row["policy_membership"]]
    if not relevant:
        raise RuntimeError(f"{arm} arm produced no completed exploitation runs")
    scores = [float(row["final_wli_score"]) for row in relevant]
    gains = [float(row["wli_gain"]) for row in relevant]
    return {
        "completed_runs": len(relevant),
        "unique_final_candidates": len(archive.records),
        "best_final_wli_score": max(scores),
        "median_final_wli_score": float(np.median(scores)),
        "mean_wli_gain": float(np.mean(gains)),
        "improving": sum(gain > 1e-15 for gain in gains),
        "unchanged": sum(abs(gain) <= 1e-15 for gain in gains),
        "regressing": sum(gain < -1e-15 for gain in gains),
    }


def case_summary(case: SearchCase, outcome: CaseOutcome) -> dict[str, Any]:
    raw = _arm_summary(outcome.raw_final_archive, outcome.exploitation_rows, "raw")
    wli = _arm_summary(outcome.wli_final_archive, outcome.exploitation_rows, "wli")
    return {
        "benchmark_id": case.benchmark_id,
        "family": case.family,
        "period": case.period,
        "columns": case.columns,
        "length": case.length,
        "sample_start": case.sample_start,
        "supply": outcome.supply.to_json_dict(),
        "selection": outcome.selection.to_json_dict(),
        "raw_arm": raw,
        "wli_arm": wli,
        "wli_best_advantage": wli["best_final_wli_score"] - raw["best_final_wli_score"],
        "wli_median_advantage": wli["median_final_wli_score"] - raw["median_final_wli_score"],
        "best_candidate_id": outcome.best_candidate_id,
        "best_membership": list(outcome.best_membership),
        "elapsed_s": outcome.elapsed_s,
        "valid": outcome.selection.ranking_test_valid,
    }


def panel_decision(
    case_summaries: Sequence[Mapping[str, Any]],
    profile: str,
    budget: RunBudget,
) -> str:
    if profile == "canary":
        return "refine"
    valid = [row for row in case_summaries if bool(row["valid"])]
    targets = [row for row in valid if row["family"] == "target"]
    controls = [row for row in valid if row["family"] == "positive_control"]
    if len(targets) < budget.minimum_completed_target_cases:
        return "refine"
    if len(controls) < budget.minimum_completed_positive_controls:
        return "refine"
    wins = sum(
        row["wli_best_advantage"] >= -1e-15 and row["wli_median_advantage"] > 1e-15
        for row in targets
    )
    losses = sum(
        row["wli_best_advantage"] < -1e-15 or row["wli_median_advantage"] < -1e-15
        for row in targets
    )
    control_regressed = any(
        row["wli_best_advantage"] < -1e-12
        or row["wli_median_advantage"] < -1e-12
        for row in controls
    )
    if wins > losses and not control_regressed:
        return "promote"
    if wins == 0 and all(
        row["wli_best_advantage"] <= 1e-15 and row["wli_median_advantage"] <= 1e-15
        for row in targets
    ):
        return "close"
    return "refine"


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    try:
        temporary.write_text(text, encoding="utf-8", newline="\n")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write_case_artifacts(artifact_dir: Path, outcome: CaseOutcome) -> dict[str, str]:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "seed_pool_archive": artifact_dir / "seed_pool_archive.json",
        "wli_handoff_batch": artifact_dir / "wli_handoff_batch.json",
        "raw_handoff_batch": artifact_dir / "raw_handoff_batch.json",
        "wli_final_archive": artifact_dir / "wli_final_archive.json",
        "raw_final_archive": artifact_dir / "raw_final_archive.json",
        "selection_evidence": artifact_dir / "selection_evidence.json",
    }
    write_candidate_archive(paths["seed_pool_archive"], outcome.seed_pool_archive)
    write_candidate_batch(paths["wli_handoff_batch"], outcome.wli_handoff_batch)
    write_candidate_batch(paths["raw_handoff_batch"], outcome.raw_handoff_batch)
    write_candidate_archive(paths["wli_final_archive"], outcome.wli_final_archive)
    write_candidate_archive(paths["raw_final_archive"], outcome.raw_final_archive)
    _write_json(paths["selection_evidence"], {
        "selection": outcome.selection.to_json_dict(),
        "exploitation": [dict(row) for row in outcome.exploitation_rows],
        "best_candidate_id": outcome.best_candidate_id,
        "best_membership": list(outcome.best_membership),
    })
    return {name: path.name for name, path in paths.items()}
