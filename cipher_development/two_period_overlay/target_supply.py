from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Mapping

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np

from cipher_development.shared.archive import (
    ArchivePolicy,
    CandidateArchive,
    write_candidate_archive,
)
from cipher_development.shared.replay import write_replay_context
from cipher_development.shared.replay_provenance import build_evaluator_provenance
from cipher_development.two_period_overlay.benchmark import (
    build_rdp_case,
    reference_metrics,
)
from cipher_development.two_period_overlay.config import (
    ARCHIVE_CAPACITY,
    DECISION_SCORE,
    MASTER_SEED,
    SCORING_CONTRACT,
    benchmark_for,
)
from cipher_development.two_period_overlay.coordinate_supply import (
    coordinate_supply_evaluation_budget,
    run_coordinate_supply,
    write_coordinate_supply_artifacts,
)
from cipher_development.two_period_overlay.diagnostics import discovery_diagnostics
from cipher_development.two_period_overlay.replay import make_replay_context
from cipher_development.two_period_overlay.review_pack import write_review_pack_after_run

TARGET_SUPPLY_BENCHMARK_ID = "alice_308_p13_p17_d16"
TARGET_SUPPLY_SEED_BLOCKS = (0, 1)
TARGET_SUPPLY_RESTARTS_PER_BLOCK = 32
TARGET_SUPPLY_SWEEPS = 12
TARGET_SUPPLY_MIN_UNIQUE_PER_BLOCK = 16
TARGET_SUPPLY_MIN_COMBINED_UNIQUE = 32
TARGET_SUPPLY_WALLCLOCK_LIMIT_S_PER_BLOCK = 1_800.0



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


def target_supply_evaluation_ceiling() -> int:
    return len(TARGET_SUPPLY_SEED_BLOCKS) * coordinate_supply_evaluation_budget(
        (TARGET_SUPPLY_BENCHMARK_ID,),
        restarts=TARGET_SUPPLY_RESTARTS_PER_BLOCK,
        sweeps=TARGET_SUPPLY_SWEEPS,
    )



def target_supply_gate(
    block_unique_counts: Mapping[int, int],
    combined_unique: int,
    total_evaluations: int,
) -> bool:
    if tuple(sorted(block_unique_counts)) != tuple(sorted(TARGET_SUPPLY_SEED_BLOCKS)):
        raise ValueError("target supply gate requires both declared seed blocks")
    for value in (*block_unique_counts.values(), combined_unique, total_evaluations):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError("target supply gate counts must be non-negative integers")
    return (
        all(
            block_unique_counts[seed_block]
            >= TARGET_SUPPLY_MIN_UNIQUE_PER_BLOCK
            for seed_block in TARGET_SUPPLY_SEED_BLOCKS
        )
        and combined_unique >= TARGET_SUPPLY_MIN_COMBINED_UNIQUE
        and total_evaluations <= target_supply_evaluation_ceiling()
    )

def _combined_archive(block_archives: Mapping[int, CandidateArchive]) -> CandidateArchive:
    capacity = sum(len(archive.records) for archive in block_archives.values())
    combined = CandidateArchive(
        ArchivePolicy(
            capacity=max(1, min(capacity, ARCHIVE_CAPACITY)),
            decision_score=DECISION_SCORE,
            higher_is_better=True,
            family_limit=None,
        )
    )
    for seed_block in sorted(block_archives):
        for record in block_archives[seed_block].records:
            combined.offer(record)
    return combined


def _combined_restart_rows(
    block_rows: Mapping[int, tuple[Mapping[str, Any], ...]],
) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    cumulative = 0
    for seed_block in sorted(block_rows):
        for row in block_rows[seed_block]:
            copied = dict(row)
            block_evaluation_index = int(copied["evaluation_index"])
            copied["block_evaluation_index"] = block_evaluation_index
            copied["global_evaluation_index"] = cumulative + block_evaluation_index
            rows.append(copied)
        if block_rows[seed_block]:
            cumulative += int(block_rows[seed_block][-1]["evaluation_index"])
    return tuple(rows)


def run_target_supply_experiment(repo_root: Path) -> Path:
    from cipher_development.shared.experiment import (
        ExperimentDecision,
        ExperimentRun,
        ExperimentSpec,
        FailureMechanism,
        TruthPolicy,
        WliMode,
    )

    repo_root = repo_root.resolve()
    benchmark = benchmark_for(TARGET_SUPPLY_BENCHMARK_ID)
    evaluation_ceiling = target_supply_evaluation_ceiling()
    spec = ExperimentSpec(
        campaign_id="two_period_overlay",
        experiment_id="target_coordinate_supply_v1",
        benchmark_id=benchmark.benchmark_id,
        question=(
            "Can two independent fixed-budget coordinate-search seed blocks supply a "
            "large, diverse and reproducible P13/P17 candidate pool?"
        ),
        hypothesis=(
            "Both seed blocks produce at least sixteen unique coordinate optima and "
            "the combined surface contains at least thirty-two unique candidates."
        ),
        alternative=(
            "P13/P17 coordinate descent repeatedly collapses to too few optima, so "
            "selection and exploitation would recycle an inadequate candidate surface."
        ),
        decision_rule=(
            "This first target-supply panel always refines. Report each block and the "
            "combined pool separately. Do not promote or close a solver mechanism from "
            "this run alone."
        ),
        wli_mode=WliMode.WITH_WLI,
        truth_policy=TruthPolicy.BENCHMARK_ONLY,
        mechanisms=(
            FailureMechanism.CANDIDATE_SUPPLY,
            FailureMechanism.DIVERSITY_COLLAPSE,
        ),
        budget_seconds=(
            TARGET_SUPPLY_WALLCLOCK_LIMIT_S_PER_BLOCK
            * len(TARGET_SUPPLY_SEED_BLOCKS)
        ),
        budget_evaluations=evaluation_ceiling,
        lesson_ids=("CSL-001", "CSL-002", "CSL-004", "CSL-005", "CSL-007"),
    )
    configuration = {
        "run_experiment": "target_coordinate_supply",
        "benchmark": benchmark.to_json_dict(),
        "seed_blocks": list(TARGET_SUPPLY_SEED_BLOCKS),
        "budget": {
            "restarts_per_block": TARGET_SUPPLY_RESTARTS_PER_BLOCK,
            "sweeps": TARGET_SUPPLY_SWEEPS,
            "wallclock_limit_s_per_block": (
                TARGET_SUPPLY_WALLCLOCK_LIMIT_S_PER_BLOCK
            ),
        },
        "minimum_unique_per_block": TARGET_SUPPLY_MIN_UNIQUE_PER_BLOCK,
        "minimum_combined_unique": TARGET_SUPPLY_MIN_COMBINED_UNIQUE,
        "evaluation_budget_upper_bound": evaluation_ceiling,
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
            search_case, reference = build_rdp_case(benchmark)
            replay_context = make_replay_context(
                search_case,
                run_id=run_dir.name,
                configuration_hash=run.configuration_hash,
                evaluator_provenance=evaluator_provenance,
            )
            write_replay_context(
                run_dir / "artifacts/replay_context.json",
                replay_context,
            )

            block_archives: dict[int, CandidateArchive] = {}
            block_rows: dict[int, tuple[Mapping[str, Any], ...]] = {}
            block_summaries: dict[str, Any] = {}
            total_evaluations = 0
            for seed_block in TARGET_SUPPLY_SEED_BLOCKS:
                run.snapshot(
                    label="target_supply_seed_block_started",
                    metrics={
                        "benchmark_id": benchmark.benchmark_id,
                        "seed_block": seed_block,
                        "restarts": TARGET_SUPPLY_RESTARTS_PER_BLOCK,
                        "sweeps": TARGET_SUPPLY_SWEEPS,
                    },
                )
                outcome = run_coordinate_supply(
                    search_case.evaluate_variables,
                    search_case.particular,
                    search_case.basis,
                    benchmark,
                    restarts=TARGET_SUPPLY_RESTARTS_PER_BLOCK,
                    sweeps=TARGET_SUPPLY_SWEEPS,
                    seed_block=seed_block,
                    wallclock_limit_s=TARGET_SUPPLY_WALLCLOCK_LIMIT_S_PER_BLOCK,
                    progress=lambda label, metrics: run.snapshot(
                        label=label, metrics=metrics
                    ),
                )
                diagnostics = discovery_diagnostics(
                    outcome.pool_archive,
                    outcome.restart_rows,
                )
                artifact_root = (
                    run_dir
                    / "artifacts/target_coordinate_supply"
                    / f"seed_block_{seed_block}"
                )
                names = write_coordinate_supply_artifacts(
                    artifact_root,
                    outcome,
                    diagnostics,
                )
                block_archives[seed_block] = outcome.pool_archive
                block_rows[seed_block] = outcome.restart_rows
                total_evaluations += outcome.evaluations
                summary = outcome.summary()
                summary.update({
                    "seed_block": seed_block,
                    "minimum_unique_candidates": (
                        TARGET_SUPPLY_MIN_UNIQUE_PER_BLOCK
                    ),
                    "unique_threshold_met": (
                        outcome.unique_candidates
                        >= TARGET_SUPPLY_MIN_UNIQUE_PER_BLOCK
                    ),
                    "duplicate_rate": (
                        outcome.duplicate_candidates
                        / outcome.generated_candidates
                    ),
                    "nearest_neighbour_summary": diagnostics[
                        "nearest_neighbour_summary"
                    ],
                    "source_archive_hash": diagnostics["source_archive_hash"],
                    "artifacts": {
                        name: (
                            "artifacts/target_coordinate_supply/"
                            f"seed_block_{seed_block}/{filename}"
                        )
                        for name, filename in names.items()
                    },
                })
                block_summaries[str(seed_block)] = summary
                run.snapshot(
                    label="target_supply_seed_block_completed",
                    metrics={
                        "seed_block": seed_block,
                        "generated_candidates": outcome.generated_candidates,
                        "unique_candidates": outcome.unique_candidates,
                        "duplicate_candidates": outcome.duplicate_candidates,
                        "best_candidate_id": outcome.best_candidate_id,
                        "best_score": outcome.best_score,
                        "evaluations": outcome.evaluations,
                    },
                )

            combined = _combined_archive(block_archives)
            combined_rows = _combined_restart_rows(block_rows)
            combined_diagnostics = discovery_diagnostics(combined, combined_rows)
            combined_archive_path = (
                run_dir
                / "artifacts/target_coordinate_supply/combined_pool_archive.json"
            )
            write_candidate_archive(combined_archive_path, combined)
            combined_diagnostics_path = (
                run_dir
                / "artifacts/target_coordinate_supply/combined_diagnostics.json"
            )
            _write_json(combined_diagnostics_path, combined_diagnostics)

            candidate_sets = {
                seed_block: {
                    record.candidate_id
                    for record in archive.records
                }
                for seed_block, archive in block_archives.items()
            }
            first_block, second_block = TARGET_SUPPLY_SEED_BLOCKS
            overlap_ids = sorted(
                candidate_sets[first_block] & candidate_sets[second_block]
            )
            combined_scores = [
                float(record.scores[DECISION_SCORE])
                for record in combined.records
            ]
            best_record = combined.records[0]
            combined_summary = {
                "generated_candidates": (
                    len(TARGET_SUPPLY_SEED_BLOCKS)
                    * TARGET_SUPPLY_RESTARTS_PER_BLOCK
                ),
                "unique_candidates": len(combined.records),
                "duplicate_candidates": (
                    len(TARGET_SUPPLY_SEED_BLOCKS)
                    * TARGET_SUPPLY_RESTARTS_PER_BLOCK
                    - len(combined.records)
                ),
                "minimum_unique_candidates": TARGET_SUPPLY_MIN_COMBINED_UNIQUE,
                "unique_threshold_met": (
                    len(combined.records) >= TARGET_SUPPLY_MIN_COMBINED_UNIQUE
                ),
                "cross_block_overlap_count": len(overlap_ids),
                "cross_block_overlap_candidate_ids": overlap_ids,
                "best_candidate_id": best_record.candidate_id,
                "best_score": float(best_record.scores[DECISION_SCORE]),
                "median_unique_score": float(np.median(combined_scores)),
                "nearest_neighbour_summary": combined_diagnostics[
                    "nearest_neighbour_summary"
                ],
                "source_archive_hash": combined_diagnostics[
                    "source_archive_hash"
                ],
                "archive_artifact": (
                    "artifacts/target_coordinate_supply/"
                    "combined_pool_archive.json"
                ),
                "diagnostics_artifact": (
                    "artifacts/target_coordinate_supply/"
                    "combined_diagnostics.json"
                ),
            }
            all_block_thresholds_met = all(
                summary["unique_threshold_met"]
                for summary in block_summaries.values()
            )
            target_supply_gate_passed = target_supply_gate(
                {
                    seed_block: len(block_archives[seed_block].records)
                    for seed_block in TARGET_SUPPLY_SEED_BLOCKS
                },
                len(combined.records),
                total_evaluations,
            )
            summary_artifact = (
                run_dir / "artifacts/target_coordinate_supply_summary.json"
            )
            _write_json(summary_artifact, {
                "schema": (
                    "rdp.two_period_overlay.target_coordinate_supply_summary.v1"
                ),
                "benchmark_id": benchmark.benchmark_id,
                "seed_blocks": list(TARGET_SUPPLY_SEED_BLOCKS),
                "budget": configuration["budget"],
                "evaluation_budget_upper_bound": evaluation_ceiling,
                "total_evaluations": total_evaluations,
                "all_block_thresholds_met": all_block_thresholds_met,
                "target_supply_gate_passed": target_supply_gate_passed,
                "blocks": block_summaries,
                "combined": combined_summary,
            })

            result_path = run.finish(
                decision=ExperimentDecision.REFINE,
                stop_reason="max_rounds",
                result_summary={
                    "benchmark_id": benchmark.benchmark_id,
                    "seed_blocks": list(TARGET_SUPPLY_SEED_BLOCKS),
                    "restarts_per_block": (
                        TARGET_SUPPLY_RESTARTS_PER_BLOCK
                    ),
                    "sweeps": TARGET_SUPPLY_SWEEPS,
                    "minimum_unique_per_block": (
                        TARGET_SUPPLY_MIN_UNIQUE_PER_BLOCK
                    ),
                    "minimum_combined_unique": (
                        TARGET_SUPPLY_MIN_COMBINED_UNIQUE
                    ),
                    "total_evaluations": total_evaluations,
                    "evaluation_budget_upper_bound": evaluation_ceiling,
                    "all_block_thresholds_met": all_block_thresholds_met,
                    "target_supply_gate_passed": target_supply_gate_passed,
                    "blocks": block_summaries,
                    "combined": combined_summary,
                    "replay_context_id": replay_context.context_id,
                    "replay_context_artifact": (
                        "artifacts/replay_context.json"
                    ),
                    "artifact": (
                        "artifacts/target_coordinate_supply_summary.json"
                    ),
                },
                reference_evaluation={
                    "best_combined_candidate": reference_metrics(
                        reference,
                        np.asarray(
                            best_record.payload["variables"],
                            dtype=np.uint8,
                        ),
                        search_case.particular,
                        search_case.basis,
                    )
                },
            )
    except BaseException as exc:
        if run_dir is not None:
            write_review_pack_after_run(
                repo_root,
                run_dir,
                original_error=exc,
            )
        raise
    assert run_dir is not None and result_path is not None
    write_review_pack_after_run(repo_root, run_dir)
    return result_path


def main() -> int:
    run_target_supply_experiment(Path(__file__).resolve().parents[2])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
