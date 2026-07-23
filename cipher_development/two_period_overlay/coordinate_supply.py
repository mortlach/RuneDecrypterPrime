from __future__ import annotations

import hashlib
import json
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np

from cipher_development.shared.archive import (
    ArchivePolicy,
    CandidateArchive,
    CandidateProvenance,
    CandidateRecord,
    candidate_id_for,
    write_candidate_archive,
)
from cipher_development.shared.replay import write_replay_context
from cipher_development.shared.replay_provenance import build_evaluator_provenance
from cipher_development.two_period_overlay.benchmark import (
    build_rdp_case,
    reference_metrics,
)
from cipher_development.two_period_overlay.config import (
    ALPHABET_SIZE,
    ARCHIVE_CAPACITY,
    DECISION_SCORE,
    MASTER_SEED,
    SCORING_CONTRACT,
    BenchmarkSpec,
    benchmark_for,
)
from cipher_development.two_period_overlay.diagnostics import discovery_diagnostics
from cipher_development.two_period_overlay.keyspace import (
    CampaignWallclockExceeded,
    coordinate_search,
    expand,
)
from cipher_development.two_period_overlay.replay import make_replay_context
from cipher_development.two_period_overlay.review_pack import write_review_pack_after_run

SUPPLY_BENCHMARK_IDS = (
    "alice_308_p05_p13_d04",
    "alice_308_p09_p13_d08",
)
SUPPLY_RESTARTS = 32
SUPPLY_SWEEPS = 8
SUPPLY_SEED_BLOCK = 0
SUPPLY_MIN_UNIQUE = 16
SUPPLY_WALLCLOCK_LIMIT_S = 900.0

ScoreVariables = Callable[[np.ndarray], np.ndarray]
ProgressCallback = Callable[[str, Mapping[str, Any]], None]


@dataclass(frozen=True, slots=True)
class CoordinateSupplyOutcome:
    benchmark_id: str
    pool_archive: CandidateArchive
    coordinate_archive: CandidateArchive
    restart_rows: tuple[Mapping[str, Any], ...]
    generated_candidates: int
    unique_candidates: int
    duplicate_candidates: int
    evaluations: int
    best_candidate_id: str
    best_variables: tuple[int, ...]
    best_score: float
    last_best_improvement_evaluation: int | None
    last_archive_change_evaluation: int | None
    improvement_points: tuple[Mapping[str, Any], ...]
    elapsed_s: float

    def summary(self) -> dict[str, Any]:
        scores = [
            float(record.scores[DECISION_SCORE])
            for record in self.pool_archive.records
        ]
        return {
            "benchmark_id": self.benchmark_id,
            "generated_candidates": self.generated_candidates,
            "unique_candidates": self.unique_candidates,
            "duplicate_candidates": self.duplicate_candidates,
            "pool_retained": len(self.pool_archive.records),
            "coordinate_archive_retained": len(self.coordinate_archive.records),
            "evaluations": self.evaluations,
            "best_candidate_id": self.best_candidate_id,
            "best_score": self.best_score,
            "median_unique_score": float(np.median(scores)),
            "last_best_improvement_evaluation": self.last_best_improvement_evaluation,
            "last_archive_change_evaluation": self.last_archive_change_evaluation,
            "elapsed_s": self.elapsed_s,
        }


def _portable_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _portable_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_portable_json(item) for item in value]
    return value


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            dict(payload),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


def coordinate_supply_seed(
    benchmark_id: str,
    seed_block: int,
    restart_index: int,
) -> int:
    if not isinstance(benchmark_id, str) or not benchmark_id:
        raise ValueError("benchmark_id must be a non-empty string")
    for name, value in (("seed_block", seed_block), ("restart_index", restart_index)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{name} must be a non-negative integer")
    benchmark_token = int.from_bytes(
        hashlib.blake2b(
            benchmark_id.encode("utf-8"),
            digest_size=4,
            person=b"rdp-wp6-seed",
        ).digest(),
        "big",
    )
    return MASTER_SEED + benchmark_token + seed_block * 1_000_000 + restart_index


def coordinate_supply_evaluation_budget(
    benchmark_ids: tuple[str, ...] = SUPPLY_BENCHMARK_IDS,
) -> int:
    return sum(
        SUPPLY_RESTARTS
        * (
            1
            + SUPPLY_SWEEPS
            * benchmark_for(benchmark_id).expected_free_dimension
            * benchmark_for(benchmark_id).alphabet_size
        )
        for benchmark_id in benchmark_ids
    )


def _archive_policy(capacity: int) -> ArchivePolicy:
    return ArchivePolicy(
        capacity=capacity,
        decision_score=DECISION_SCORE,
        higher_is_better=True,
        family_limit=None,
    )


def _candidate_record(
    variables: np.ndarray,
    score: float,
    particular: np.ndarray,
    basis: np.ndarray,
    benchmark: BenchmarkSpec,
    *,
    evaluation_index: int,
    details: Mapping[str, Any],
) -> CandidateRecord:
    variable_values = np.asarray(variables, dtype=np.uint8)
    expanded = expand(variable_values, particular, basis, benchmark)
    identity = {"expanded_key": expanded.astype(int).tolist()}
    return CandidateRecord(
        candidate_id=candidate_id_for(identity),
        identity=identity,
        payload={
            "variables": variable_values.astype(int).tolist(),
            "expanded_key": expanded.astype(int).tolist(),
            "benchmark_id": benchmark.benchmark_id,
        },
        scores={DECISION_SCORE: float(score)},
        provenance=CandidateProvenance(
            source="coordinate_supply",
            operation="coordinate_descent",
            evaluation_index=evaluation_index,
            details=details,
        ),
    )


def run_coordinate_supply(
    evaluate: ScoreVariables,
    particular: np.ndarray,
    basis: np.ndarray,
    benchmark: BenchmarkSpec,
    *,
    progress: ProgressCallback | None = None,
) -> CoordinateSupplyOutcome:
    dimension = benchmark.expected_free_dimension
    if basis.shape != (benchmark.key_length, dimension):
        raise ValueError("coordinate supply basis does not match benchmark dimension")
    if dimension <= 0:
        raise ValueError("coordinate supply requires a positive affine dimension")

    started = time.monotonic()
    deadline = started + SUPPLY_WALLCLOCK_LIMIT_S
    pool = CandidateArchive(_archive_policy(SUPPLY_RESTARTS))
    bounded = CandidateArchive(_archive_policy(min(ARCHIVE_CAPACITY, SUPPLY_RESTARTS)))
    restart_rows: list[dict[str, Any]] = []
    improvement_points: list[dict[str, Any]] = []
    evaluations = 0
    best_score = -math.inf
    best_candidate_id: str | None = None
    best_variables: tuple[int, ...] | None = None
    last_best_improvement: int | None = None
    last_archive_change: int | None = None

    for restart_index in range(SUPPLY_RESTARTS):
        if time.monotonic() >= deadline:
            raise CampaignWallclockExceeded(
                "coordinate-supply wall-clock safety limit reached"
            )
        seed = coordinate_supply_seed(
            benchmark.benchmark_id, SUPPLY_SEED_BLOCK, restart_index
        )
        rng = np.random.default_rng(seed)
        starting = rng.integers(
            0,
            benchmark.alphabet_size,
            size=dimension,
            dtype=np.uint8,
        )
        ending, score, used = coordinate_search(
            evaluate,
            rng,
            starting,
            SUPPLY_SWEEPS,
            deadline=deadline,
        )
        coordinate_batch_size = dimension * benchmark.alphabet_size
        if (used - 1) % coordinate_batch_size:
            raise RuntimeError("coordinate-search evaluation accounting is inconsistent")
        sweeps_completed = (used - 1) // coordinate_batch_size
        if not 1 <= sweeps_completed <= SUPPLY_SWEEPS:
            raise RuntimeError("coordinate-search completed-sweep count is invalid")

        evaluations += used
        details = {
            "benchmark_id": benchmark.benchmark_id,
            "restart_index": restart_index,
            "restart_seed": seed,
            "seed_block": SUPPLY_SEED_BLOCK,
            "starting_variables": starting.astype(int).tolist(),
            "ending_variables": ending.astype(int).tolist(),
            "evaluations_used": used,
            "sweeps_requested": SUPPLY_SWEEPS,
            "sweeps_completed": sweeps_completed,
            "coordinate_batches": sweeps_completed * dimension,
        }
        record = _candidate_record(
            ending,
            score,
            particular,
            basis,
            benchmark,
            evaluation_index=evaluations,
            details=details,
        )
        pool_offer = pool.offer(record)
        bounded_offer = bounded.offer(record)
        if bounded_offer.action.value in {"added", "updated", "evicted"}:
            last_archive_change = evaluations

        candidate_rank = (-float(score), record.candidate_id)
        current_rank = (
            None if best_candidate_id is None else (-best_score, best_candidate_id)
        )
        if current_rank is None or candidate_rank < current_rank:
            best_score = float(score)
            best_candidate_id = record.candidate_id
            best_variables = tuple(int(value) for value in ending)
            last_best_improvement = evaluations
            improvement_points.append({
                "restart_index": restart_index,
                "evaluation_index": evaluations,
                "candidate_id": record.candidate_id,
                "score": float(score),
            })

        row = {
            **details,
            "candidate_id": record.candidate_id,
            "score": float(score),
            "evaluation_index": evaluations,
            "pool_offer_action": pool_offer.action.value,
            "coordinate_archive_offer_action": bounded_offer.action.value,
        }
        restart_rows.append(row)
        if progress is not None:
            progress("coordinate_supply_restart_completed", {
                "benchmark_id": benchmark.benchmark_id,
                "restart_index": restart_index,
                "candidate_id": record.candidate_id,
                "score": float(score),
                "unique_candidates": len(pool.records),
                "evaluations": evaluations,
            })

    if best_candidate_id is None or best_variables is None:
        raise RuntimeError("coordinate supply produced no candidates")
    outcome = CoordinateSupplyOutcome(
        benchmark_id=benchmark.benchmark_id,
        pool_archive=pool,
        coordinate_archive=bounded,
        restart_rows=tuple(restart_rows),
        generated_candidates=len(restart_rows),
        unique_candidates=len(pool.records),
        duplicate_candidates=len(restart_rows) - len(pool.records),
        evaluations=evaluations,
        best_candidate_id=best_candidate_id,
        best_variables=best_variables,
        best_score=best_score,
        last_best_improvement_evaluation=last_best_improvement,
        last_archive_change_evaluation=last_archive_change,
        improvement_points=tuple(improvement_points),
        elapsed_s=float(time.monotonic() - started),
    )
    pool.get(best_candidate_id)
    return outcome


def write_coordinate_supply_artifacts(
    artifact_dir: Path,
    outcome: CoordinateSupplyOutcome,
    diagnostics: Mapping[str, Any],
) -> dict[str, str]:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "discovery_pool_archive": artifact_dir / "discovery_pool_archive.json",
        "coordinate_archive": artifact_dir / "coordinate_archive.json",
        "discovery_restarts": artifact_dir / "discovery_restarts.json",
        "discovery_diagnostics": artifact_dir / "discovery_diagnostics.json",
    }
    write_candidate_archive(paths["discovery_pool_archive"], outcome.pool_archive)
    write_candidate_archive(paths["coordinate_archive"], outcome.coordinate_archive)
    _write_json(paths["discovery_restarts"], {
        "schema": "rdp.two_period_overlay.discovery_restarts.v1",
        "benchmark_id": outcome.benchmark_id,
        "generated_candidates": outcome.generated_candidates,
        "unique_candidates": outcome.unique_candidates,
        "duplicate_candidates": outcome.duplicate_candidates,
        "evaluations": outcome.evaluations,
        "last_best_improvement_evaluation": (
            outcome.last_best_improvement_evaluation
        ),
        "last_archive_change_evaluation": outcome.last_archive_change_evaluation,
        "improvement_points": [dict(row) for row in outcome.improvement_points],
        "restarts": [dict(row) for row in outcome.restart_rows],
    })
    _write_json(paths["discovery_diagnostics"], diagnostics)
    return {name: path.name for name, path in paths.items()}


def run_coordinate_supply_experiment(repo_root: Path) -> Path:
    from cipher_development.shared.experiment import (
        ExperimentDecision,
        ExperimentRun,
        ExperimentSpec,
        FailureMechanism,
        TruthPolicy,
        WliMode,
    )

    benchmarks = tuple(benchmark_for(item) for item in SUPPLY_BENCHMARK_IDS)
    evaluation_budget = coordinate_supply_evaluation_budget()
    spec = ExperimentSpec(
        campaign_id="two_period_overlay",
        experiment_id="coordinate_supply_v1",
        benchmark_id="alice_308_coordinate_supply_d04_d08",
        question=(
            "Does coordinate descent supply enough distinct, reproducible candidate basins "
            "on the dimension-4 and dimension-8 ladder rungs to justify later selection tests?"
        ),
        hypothesis=(
            "Fixed coordinate restarts produce a materially diverse pool on at least the "
            "dimension-8 rung, rather than repeatedly returning one local basin."
        ),
        alternative=(
            "Coordinate descent collapses to too few unique optima, so later ranking and "
            "handoff experiments would only recycle the same candidate surface."
        ),
        decision_rule=(
            "This evidence-gathering experiment always refines. Report candidate supply and "
            "diversity separately for each rung; do not launch P13/P17 supply until review."
        ),
        wli_mode=WliMode.WITH_WLI,
        truth_policy=TruthPolicy.BENCHMARK_ONLY,
        mechanisms=(
            FailureMechanism.CANDIDATE_SUPPLY,
            FailureMechanism.DIVERSITY_COLLAPSE,
            FailureMechanism.BUDGET,
        ),
        budget_seconds=SUPPLY_WALLCLOCK_LIMIT_S * len(benchmarks),
        budget_evaluations=evaluation_budget,
        lesson_ids=("CSL-001", "CSL-002", "CSL-004", "CSL-005", "CSL-007"),
    )
    configuration = {
        "run_experiment": "coordinate_supply",
        "benchmarks": [benchmark.to_json_dict() for benchmark in benchmarks],
        "budget": {
            "restarts": SUPPLY_RESTARTS,
            "sweeps": SUPPLY_SWEEPS,
            "seed_block": SUPPLY_SEED_BLOCK,
            "wallclock_limit_s_per_benchmark": SUPPLY_WALLCLOCK_LIMIT_S,
        },
        "minimum_unique_candidates": SUPPLY_MIN_UNIQUE,
        "evaluation_budget_upper_bound": evaluation_budget,
        "master_seed": MASTER_SEED,
        "archive_capacity": ARCHIVE_CAPACITY,
        "decision_score": DECISION_SCORE,
        "scoring": _portable_json(SCORING_CONTRACT),
    }

    run_dir: Path | None = None
    result_path: Path | None = None
    try:
        with ExperimentRun(spec=spec, configuration=configuration, repo_root=repo_root) as run:
            assert run.run_dir is not None
            run_dir = run.run_dir
            run_meta = json.loads((run_dir / "META.json").read_text(encoding="utf-8"))
            evaluator_provenance = build_evaluator_provenance(
                repo_root=repo_root,
                evaluator_source=Path(__file__).with_name("replay.py"),
                scoring_contracts=(SCORING_CONTRACT,),
                run_meta=run_meta,
                require_assets=True,
            )

            results: dict[str, Any] = {}
            references: dict[str, Any] = {}
            total_evaluations = 0
            total_generated = 0
            total_unique = 0
            for benchmark in benchmarks:
                search_case, reference = build_rdp_case(benchmark)
                replay_context = make_replay_context(
                    search_case,
                    run_id=run_dir.name,
                    configuration_hash=run.configuration_hash,
                    evaluator_provenance=evaluator_provenance,
                )
                context_artifact = (
                    run_dir
                    / "artifacts/replay_contexts"
                    / f"{benchmark.benchmark_id}.json"
                )
                write_replay_context(context_artifact, replay_context)
                run.snapshot(label="coordinate_supply_benchmark_started", metrics={
                    "benchmark_id": benchmark.benchmark_id,
                    "free_dimension": benchmark.expected_free_dimension,
                    "restarts": SUPPLY_RESTARTS,
                    "sweeps": SUPPLY_SWEEPS,
                    "replay_context_id": replay_context.context_id,
                })
                outcome = run_coordinate_supply(
                    search_case.evaluate_variables,
                    search_case.particular,
                    search_case.basis,
                    benchmark,
                    progress=lambda label, metrics: run.snapshot(
                        label=label, metrics=metrics
                    ),
                )
                diagnostics = discovery_diagnostics(
                    outcome.pool_archive, outcome.restart_rows
                )
                artifact_root = (
                    run_dir
                    / "artifacts/coordinate_supply"
                    / benchmark.benchmark_id
                )
                names = write_coordinate_supply_artifacts(
                    artifact_root, outcome, diagnostics
                )
                benchmark_summary = outcome.summary()
                benchmark_summary.update({
                    "minimum_unique_candidates": SUPPLY_MIN_UNIQUE,
                    "unique_threshold_met": (
                        outcome.unique_candidates >= SUPPLY_MIN_UNIQUE
                    ),
                    "duplicate_rate": (
                        outcome.duplicate_candidates / outcome.generated_candidates
                    ),
                    "nearest_neighbour_summary": diagnostics[
                        "nearest_neighbour_summary"
                    ],
                    "source_archive_hash": diagnostics["source_archive_hash"],
                    "replay_context_id": replay_context.context_id,
                    "replay_context_artifact": (
                        "artifacts/replay_contexts/"
                        f"{benchmark.benchmark_id}.json"
                    ),
                    "artifacts": {
                        name: (
                            "artifacts/coordinate_supply/"
                            f"{benchmark.benchmark_id}/{filename}"
                        )
                        for name, filename in names.items()
                    },
                })
                results[benchmark.benchmark_id] = benchmark_summary
                references[benchmark.benchmark_id] = reference_metrics(
                    reference,
                    np.asarray(outcome.best_variables, dtype=np.uint8),
                    search_case.particular,
                    search_case.basis,
                )
                total_evaluations += outcome.evaluations
                total_generated += outcome.generated_candidates
                total_unique += outcome.unique_candidates
                run.snapshot(label="coordinate_supply_benchmark_completed", metrics={
                    "benchmark_id": benchmark.benchmark_id,
                    "generated_candidates": outcome.generated_candidates,
                    "unique_candidates": outcome.unique_candidates,
                    "duplicate_candidates": outcome.duplicate_candidates,
                    "best_candidate_id": outcome.best_candidate_id,
                    "best_score": outcome.best_score,
                    "evaluations": outcome.evaluations,
                })

            summary_artifact = run_dir / "artifacts/coordinate_supply_summary.json"
            _write_json(summary_artifact, {
                "schema": "rdp.two_period_overlay.coordinate_supply_summary.v1",
                "benchmark_ids": list(SUPPLY_BENCHMARK_IDS),
                "minimum_unique_candidates": SUPPLY_MIN_UNIQUE,
                "budget": configuration["budget"],
                "evaluation_budget_upper_bound": evaluation_budget,
                "total_evaluations": total_evaluations,
                "total_generated_candidates": total_generated,
                "total_unique_candidates": total_unique,
                "benchmarks": results,
            })
            result_path = run.finish(
                decision=ExperimentDecision.REFINE,
                stop_reason="max_rounds",
                result_summary={
                    "benchmark_count": len(results),
                    "benchmark_ids": list(SUPPLY_BENCHMARK_IDS),
                    "minimum_unique_candidates": SUPPLY_MIN_UNIQUE,
                    "total_evaluations": total_evaluations,
                    "evaluation_budget_upper_bound": evaluation_budget,
                    "total_generated_candidates": total_generated,
                    "total_unique_candidates": total_unique,
                    "all_unique_thresholds_met": all(
                        row["unique_threshold_met"] for row in results.values()
                    ),
                    "benchmarks": results,
                    "artifact": "artifacts/coordinate_supply_summary.json",
                },
                reference_evaluation={"benchmarks": references},
            )
    except BaseException as exc:
        if run_dir is not None:
            write_review_pack_after_run(repo_root, run_dir, original_error=exc)
        raise
    assert run_dir is not None and result_path is not None
    write_review_pack_after_run(repo_root, run_dir)
    return result_path


def main() -> int:
    run_coordinate_supply_experiment(Path(__file__).resolve().parents[2])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
