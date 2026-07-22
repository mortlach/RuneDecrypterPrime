from __future__ import annotations

from pathlib import Path
from typing import Any

from cipher_development.periodic_sub_trans_wli.benchmark import (
    build_rdp_case,
    reference_metrics,
)
from cipher_development.periodic_sub_trans_wli.config import (
    ALPHABET_SIZE,
    ARCHIVE_CAPACITY,
    KAEDING_SOLVER_CONTRACT,
    MASTER_SEED,
    ORDER,
    RAW_SCORE,
    RAW_SCORING_CONTRACT,
    RUN_PROFILE,
    WLI_SCORE,
    WLI_SCORING_CONTRACT,
    BenchmarkSpec,
    RunBudget,
    budget_for,
    cases_for,
)
from cipher_development.periodic_sub_trans_wli.replay import make_replay_context
from cipher_development.periodic_sub_trans_wli.search import (
    case_summary,
    panel_decision,
    run_case,
    write_case_artifacts,
)
from cipher_development.shared.replay import write_replay_context


def _case_configuration(spec: BenchmarkSpec) -> dict[str, Any]:
    return {
        "benchmark_id": spec.benchmark_id,
        "family": spec.family,
        "period": spec.period,
        "columns": spec.columns,
        "length": spec.length,
        "text_offset_hint": spec.text_offset_hint,
        "order": ORDER,
    }


def _budget_configuration(budget: RunBudget) -> dict[str, Any]:
    return {
        "candidate_pool_size": budget.candidate_pool_size,
        "handoff_candidates": budget.handoff_candidates,
        "exploitation_replicates": budget.exploitation_replicates,
        "solver_restarts": budget.solver_restarts,
        "solver_steps": budget.solver_steps,
        "solver_inner_batch": budget.solver_inner_batch,
        "minimum_policy_exclusive": budget.minimum_policy_exclusive,
        "minimum_completed_target_cases": budget.minimum_completed_target_cases,
        "minimum_completed_positive_controls": budget.minimum_completed_positive_controls,
        "wallclock_overrun_limit_s": budget.wallclock_overrun_limit_s,
        "seed_plan": {
            "n_block_seeds": budget.seed_plan.n_block_seeds,
            "n_tail_seeds": budget.seed_plan.n_tail_seeds,
            "n_starts": budget.seed_plan.n_starts,
            "refine_steps": budget.seed_plan.refine_steps,
            "tail_move_prob": budget.seed_plan.tail_move_prob,
            "temp_start": budget.seed_plan.temp_start,
            "temp_end": budget.seed_plan.temp_end,
        },
    }


def _archive_reference_metrics(reference: Any, archive: Any) -> dict[str, Any]:
    candidates: dict[str, dict[str, Any]] = {}
    for record in archive.records:
        candidates[record.candidate_id] = reference_metrics(
            reference, record.payload["expanded_key"]
        )
    rows = list(candidates.values())
    return {
        "candidate_count": len(rows),
        "exact_solve_count": sum(bool(row["exact_plaintext"]) for row in rows),
        "best_rune_matches": max((int(row["rune_matches"]) for row in rows), default=0),
        "best_complete_word_matches": max(
            (int(row["complete_word_matches"]) for row in rows), default=0
        ),
        "canonical_key_equal_count": sum(
            bool(row["canonical_key_equal"]) for row in rows
        ),
        "candidates": candidates,
    }


def run_rdp_campaign(repo_root: Path, profile: str = RUN_PROFILE) -> Path:
    from cipher_development.shared.experiment import (
        ExperimentDecision,
        ExperimentRun,
        ExperimentSpec,
        FailureMechanism,
        TruthPolicy,
        WliMode,
    )

    budget = budget_for(profile)
    specs = cases_for(profile)
    experiment = ExperimentSpec(
        campaign_id="periodic_sub_trans_wli",
        experiment_id=f"wp4_periodic_columnar_{profile}",
        benchmark_id="periodic_columnar_ranking_panel",
        question=(
            "Does full-WLI reranking of one fixed periodic-columnar candidate pool "
            "improve downstream solving over raw character-score ranking?"
        ),
        hypothesis=(
            "Useful structured candidates are generated but raw seed ranking fails to "
            "handoff the most exploitable keys."
        ),
        decision_rule=(
            "Canaries and invalid or policy-no-op panels refine. A valid full panel promotes "
            "when WLI ranking wins more target cases than it loses without positive-control "
            "regression; it closes when no target case improves; otherwise it refines."
        ),
        wli_mode=WliMode.WITH_WLI,
        truth_policy=TruthPolicy.BENCHMARK_ONLY,
        mechanisms=(
            FailureMechanism.CANDIDATE_SUPPLY,
            FailureMechanism.RANKING,
            FailureMechanism.HANDOFF,
            FailureMechanism.EXPLOITATION,
        ),
        budget_seconds=budget.wallclock_overrun_limit_s * len(specs),
    )
    configuration = {
        "profile": profile,
        "alphabet_size": ALPHABET_SIZE,
        "order": ORDER,
        "master_seed": MASTER_SEED,
        "archive_capacity": ARCHIVE_CAPACITY,
        "raw_score": RAW_SCORE,
        "wli_score": WLI_SCORE,
        "benchmarks": [_case_configuration(spec) for spec in specs],
        "budget": _budget_configuration(budget),
        "raw_scoring": RAW_SCORING_CONTRACT,
        "wli_scoring": WLI_SCORING_CONTRACT,
        "kaeding_solver": KAEDING_SOLVER_CONTRACT,
    }

    with ExperimentRun(spec=experiment, configuration=configuration, repo_root=repo_root) as run:
        case_summaries: list[dict[str, Any]] = []
        reference_cases: dict[str, Any] = {}
        artifacts: dict[str, dict[str, str]] = {}
        best_candidates: dict[str, dict[str, Any]] = {}

        for index, benchmark_spec in enumerate(specs):
            run.snapshot(label="benchmark_build_started", metrics={
                "case_index": index,
                "benchmark_id": benchmark_spec.benchmark_id,
                "period": benchmark_spec.period,
                "columns": benchmark_spec.columns,
                "length": benchmark_spec.length,
            })
            search_case, reference = build_rdp_case(benchmark_spec, budget)
            assert run.run_dir is not None
            case_dir = run.run_dir / "artifacts" / search_case.benchmark_id
            replay_context = make_replay_context(
                search_case,
                run_id=run.run_dir.name,
                configuration_hash=run.configuration_hash,
                raw_scoring=RAW_SCORING_CONTRACT,
                wli_scoring=WLI_SCORING_CONTRACT,
            )
            write_replay_context(case_dir / "replay_context.json", replay_context)
            run.snapshot(label="benchmark_built", metrics={
                "case_index": index,
                "benchmark_id": search_case.benchmark_id,
                "sample_start": search_case.sample_start,
                "text_length": search_case.length,
                "replay_context_id": replay_context.context_id,
            })
            outcome = run_case(search_case, budget)
            names = dict(write_case_artifacts(case_dir, outcome))
            names["replay_context"] = "replay_context.json"
            artifacts[search_case.benchmark_id] = {
                name: f"artifacts/{search_case.benchmark_id}/{filename}"
                for name, filename in names.items()
            }
            summary = case_summary(search_case, outcome)
            summary["replay_context_id"] = replay_context.context_id
            case_summaries.append(summary)

            reference_cases[search_case.benchmark_id] = {
                "raw_arm": _archive_reference_metrics(
                    reference, outcome.raw_final_archive
                ),
                "wli_arm": _archive_reference_metrics(
                    reference, outcome.wli_final_archive
                ),
            }
            best_candidates[search_case.benchmark_id] = {
                "candidate_id": outcome.best_candidate_id,
                "membership": list(outcome.best_membership),
                "artifact": (
                    artifacts[search_case.benchmark_id]["wli_final_archive"]
                    if "wli" in outcome.best_membership
                    else artifacts[search_case.benchmark_id]["raw_final_archive"]
                ),
            }
            run.snapshot(label="case_completed", metrics={
                "case_index": index,
                "benchmark_id": search_case.benchmark_id,
                "unique_candidates": outcome.supply.unique_candidates,
                "raw_handoff": len(outcome.raw_handoff_batch.candidates),
                "wli_handoff": len(outcome.wli_handoff_batch.candidates),
                "policy_exclusive_minimum": outcome.selection.policy_exclusive_minimum,
                "valid": outcome.selection.ranking_test_valid,
                "best_candidate_id": outcome.best_candidate_id,
                "elapsed_s": outcome.elapsed_s,
            })

        decision = panel_decision(case_summaries, profile, budget)
        run.snapshot(label="campaign_completed", metrics={
            "case_count": len(case_summaries),
            "valid_case_count": sum(bool(row["valid"]) for row in case_summaries),
            "target_case_count": sum(row["family"] == "target" for row in case_summaries),
            "decision": decision,
        })
        return run.finish(
            decision=ExperimentDecision(decision),
            stop_reason="max_rounds",
            result_summary={
                "case_count": len(case_summaries),
                "cases": case_summaries,
                "best_candidates": best_candidates,
                "artifacts": artifacts,
            },
            reference_evaluation={"cases": reference_cases},
        )


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    run_rdp_campaign(repo_root, RUN_PROFILE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
