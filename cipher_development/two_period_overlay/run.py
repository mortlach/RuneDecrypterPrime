from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from cipher_development.shared.replay import write_replay_context
from cipher_development.shared.replay_binding import (
    CandidateReplayBinding,
    write_replay_binding,
)
from cipher_development.shared.replay_provenance import build_evaluator_provenance
from cipher_development.two_period_overlay.benchmark import (
    build_rdp_case,
    reference_metrics,
)
from cipher_development.two_period_overlay.config import (
    ARCHIVE_CAPACITY,
    DECISION_SCORE,
    MASTER_SEED,
    RUN_BENCHMARK_ID,
    RUN_PROFILE,
    SCORING_CONTRACT,
    TARGET_BENCHMARK,
    RunBudget,
    benchmark_for,
    budget_for,
)
from cipher_development.two_period_overlay.replay import make_replay_context
from cipher_development.two_period_overlay.search import (
    campaign_decision,
    comparison_summary,
    run_search,
    write_search_artifacts,
)


def _budget_configuration(budget: RunBudget) -> dict[str, int | float]:
    return {
        "coordinate_restarts": budget.coordinate_restarts,
        "coordinate_sweeps": budget.coordinate_sweeps,
        "handoff_candidates": budget.handoff_candidates,
        "minimum_comparisons": budget.minimum_comparisons,
        "sa_steps": budget.sa_steps,
        "sa_cycles": budget.sa_cycles,
        "sa_t0": budget.sa_t0,
        "sa_tmin": budget.sa_tmin,
        "wallclock_limit_s": budget.wallclock_limit_s,
    }


def _evaluation_budget_upper_bound(budget: RunBudget, free_dimension: int) -> int:
    coordinate_pass = 1 + budget.coordinate_sweeps * free_dimension * TARGET_BENCHMARK.alphabet_size
    discovery = budget.coordinate_restarts * coordinate_pass
    control_starts = budget.handoff_candidates
    exploitation_per_arm = 2 + budget.sa_steps * budget.sa_cycles + (
        budget.coordinate_sweeps * free_dimension * TARGET_BENCHMARK.alphabet_size
    )
    exploitation = budget.handoff_candidates * 2 * exploitation_per_arm
    return discovery + control_starts + exploitation


def run_rdp_campaign(repo_root: Path, profile: str = RUN_PROFILE) -> Path:
    from cipher_development.shared.experiment import (
        ExperimentDecision,
        ExperimentRun,
        ExperimentSpec,
        FailureMechanism,
        TruthPolicy,
        WliMode,
    )

    benchmark = benchmark_for(RUN_BENCHMARK_ID)
    if benchmark != TARGET_BENCHMARK:
        raise ValueError(
            "the archive-handoff runner is frozen to the P13/P17 target; "
            "lower ladder rungs are contract canaries until their search profiles are reviewed"
        )
    budget = budget_for(profile)
    search_case, reference = build_rdp_case(benchmark)
    experiment_id = "technical_canary_v1" if profile == "canary" else "archive_handoff_v1"
    evaluation_budget = _evaluation_budget_upper_bound(
        budget, benchmark.expected_free_dimension
    )
    spec = ExperimentSpec(
        campaign_id="two_period_overlay",
        experiment_id=experiment_id,
        benchmark_id=benchmark.benchmark_id,
        question=(
            "Does a retained full-WLI coordinate archive outperform "
            "independent exploitation starts?"
        ),
        hypothesis="Useful coordinate basins are discarded between independent methods.",
        alternative=(
            "Coordinate discovery never reaches useful candidate regions, so archive "
            "handoff will not improve exploitation."
        ),
        decision_rule=(
            "Canaries always refine. A valid full comparison promotes when archive wins exceed "
            "control wins and archive best is no worse; it closes when there are no archive "
            "wins and archive best is no better; otherwise it refines."
        ),
        wli_mode=WliMode.WITH_WLI,
        truth_policy=TruthPolicy.BENCHMARK_ONLY,
        mechanisms=(
            FailureMechanism.CANDIDATE_SUPPLY,
            FailureMechanism.DIVERSITY_COLLAPSE,
            FailureMechanism.HANDOFF,
            FailureMechanism.EXPLOITATION,
        ),
        budget_seconds=budget.wallclock_limit_s,
        budget_evaluations=evaluation_budget,
        lesson_ids=("CSL-001", "CSL-002", "CSL-004", "CSL-005", "CSL-007"),
    )
    configuration = {
        "profile": profile,
        "benchmark": benchmark.to_json_dict(),
        "master_seed": MASTER_SEED,
        "archive_capacity": ARCHIVE_CAPACITY,
        "decision_score": DECISION_SCORE,
        "budget": _budget_configuration(budget),
        "evaluation_budget_upper_bound": evaluation_budget,
        "scoring": SCORING_CONTRACT,
    }
    with ExperimentRun(spec=spec, configuration=configuration, repo_root=repo_root) as run:
        assert run.run_dir is not None
        run_meta = json.loads((run.run_dir / "META.json").read_text(encoding="utf-8"))
        evaluator_provenance = build_evaluator_provenance(
            repo_root=repo_root,
            evaluator_source=Path(__file__).with_name("replay.py"),
            scoring_contracts=(SCORING_CONTRACT,),
            run_meta=run_meta,
            require_assets=True,
        )
        replay_context = make_replay_context(
            search_case,
            run_id=run.run_dir.name,
            configuration_hash=run.configuration_hash,
            evaluator_provenance=evaluator_provenance,
        )
        write_replay_context(
            run.run_dir / "artifacts/replay_context.json", replay_context
        )
        run.snapshot(label="benchmark_built", metrics={
            "benchmark_id": benchmark.benchmark_id,
            "free_dimension": len(search_case.free_columns),
            "sample_start": search_case.sample_start,
            "replay_context_id": replay_context.context_id,
        })
        run.snapshot(label="discovery_started", metrics={
            "coordinate_restarts": budget.coordinate_restarts,
            "coordinate_sweeps": budget.coordinate_sweeps,
        })
        outcome = run_search(
            search_case.evaluate_variables,
            search_case.particular,
            search_case.basis,
            budget,
            progress=lambda label, metrics: run.snapshot(label=label, metrics=metrics),
        )
        artifact_names = dict(write_search_artifacts(run.run_dir / "artifacts", outcome))
        artifact_names["replay_context"] = "replay_context.json"
        bindings: dict[str, dict[str, str]] = {}
        for name, batch, batch_filename, binding_filename in (
            (
                "archive_handoff",
                outcome.handoff_batch,
                "archive_handoff_batch.json",
                "archive_handoff_binding.json",
            ),
            (
                "control_start",
                outcome.control_batch,
                "control_start_batch.json",
                "control_start_binding.json",
            ),
        ):
            binding = CandidateReplayBinding.create(
                campaign_id="two_period_overlay",
                source_run_id=run.run_dir.name,
                configuration_hash=run.configuration_hash,
                benchmark_id=benchmark.benchmark_id,
                context=replay_context,
                batch=batch,
                context_artifact="artifacts/replay_context.json",
                batch_artifact=f"artifacts/{batch_filename}",
            )
            write_replay_binding(run.run_dir / "artifacts" / binding_filename, binding)
            artifact_names[f"{name}_binding"] = binding_filename
            bindings[name] = {
                "binding_id": binding.binding_id,
                "artifact": f"artifacts/{binding_filename}",
                "batch_id": batch.batch_id,
                "context_id": replay_context.context_id,
            }
        run.snapshot(label="handoff_batches_written", metrics={
            "archive_candidates": len(outcome.handoff_batch.candidates),
            "control_candidates": len(outcome.control_batch.candidates),
            "control_final_candidates": len(outcome.control_archive.records),
            "archive_binding_id": bindings["archive_handoff"]["binding_id"],
        })
        summary = comparison_summary(outcome)
        decision = campaign_decision(summary, profile)
        run.snapshot(label="campaign_completed", metrics={
            **summary,
            "archive_retained": len(outcome.archive.records),
            "control_final_retained": len(outcome.control_archive.records),
            "best_candidate_id": outcome.best_candidate_id,
            "best_arm": outcome.best_arm,
        })
        reference_evaluation = reference_metrics(
            reference,
            np.asarray(outcome.best_variables, dtype=np.uint8),
            search_case.particular,
            search_case.basis,
        )
        best_artifact = (
            "artifacts/final_archive.json"
            if outcome.best_arm == "archive"
            else "artifacts/control_final_archive.json"
        )
        return run.finish(
            decision=ExperimentDecision(decision),
            stop_reason="max_rounds",
            result_summary={
                **summary,
                "benchmark_id": benchmark.benchmark_id,
                "best_score": outcome.best_score,
                "best_candidate_id": outcome.best_candidate_id,
                "best_arm": outcome.best_arm,
                "best_candidate_artifact": best_artifact,
                "replay_context_id": replay_context.context_id,
                "replay_context_artifact": "artifacts/replay_context.json",
                "replay_bindings": bindings,
                "evaluations": outcome.evaluations,
                "evaluation_budget_upper_bound": evaluation_budget,
                "elapsed_s": outcome.elapsed_s,
                "coordinate_restarts": budget.coordinate_restarts,
                "discovery": outcome.discovery.to_json_dict(),
                "archive_retained": len(outcome.archive.records),
                "control_final_retained": len(outcome.control_archive.records),
                "paired_comparisons": [dict(row) for row in outcome.comparisons],
                "artifacts": {
                    name: f"artifacts/{filename}" for name, filename in artifact_names.items()
                },
            },
            reference_evaluation=reference_evaluation,
        )


def main() -> int:
    run_rdp_campaign(Path(__file__).resolve().parents[2], RUN_PROFILE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
