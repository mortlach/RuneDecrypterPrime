from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

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
    BENCHMARK_LADDER,
    DECISION_SCORE,
    MASTER_SEED,
    RUN_BENCHMARK_ID,
    RUN_EXPERIMENT,
    RUN_PROFILE,
    SCORING_CONTRACT,
    TARGET_BENCHMARK,
    RunBudget,
    benchmark_for,
    budget_for,
)
from cipher_development.two_period_overlay.replay import make_replay_context
from cipher_development.two_period_overlay.review_pack import write_review_pack_after_run
from cipher_development.two_period_overlay.search import (
    campaign_decision,
    comparison_summary,
    run_search,
    write_search_artifacts,
)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _portable_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _portable_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_portable_json(item) for item in value]
    return value


def _portable_hash(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


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


def _pack_after_success(repo_root: Path, run_dir: Path) -> None:
    write_review_pack_after_run(repo_root, run_dir)


def _pack_after_failure(repo_root: Path, run_dir: Path | None, exc: BaseException) -> None:
    if run_dir is not None:
        write_review_pack_after_run(repo_root, run_dir, original_error=exc)


def run_benchmark_contract_canary(repo_root: Path) -> Path:
    from cipher_development.shared.experiment import (
        ExperimentDecision,
        ExperimentRun,
        ExperimentSpec,
        FailureMechanism,
        TruthPolicy,
        WliMode,
    )

    spec = ExperimentSpec(
        campaign_id="two_period_overlay",
        experiment_id="benchmark_contract_canary_v1",
        benchmark_id="alice_308_two_period_ladder",
        question=(
            "Do all four two-period benchmark ladder rungs reconstruct, score and replay "
            "deterministically under the frozen RDP contracts?"
        ),
        hypothesis=(
            "Every ladder rung has the declared affine dimension and produces identical "
            "search-visible evidence across two builds."
        ),
        alternative=(
            "At least one ladder rung disagrees with its declared affine, scorer or replay "
            "contract."
        ),
        decision_rule="Contract canaries always refine; any mismatch blocks solver experiments.",
        wli_mode=WliMode.WITH_WLI,
        truth_policy=TruthPolicy.BENCHMARK_ONLY,
        mechanisms=(
            FailureMechanism.CONTRACT,
            FailureMechanism.EVIDENCE_REPRODUCIBILITY,
        ),
        budget_seconds=1_800.0,
        budget_evaluations=2 * len(BENCHMARK_LADDER),
        lesson_ids=("CSL-001", "CSL-002", "CSL-004", "CSL-005", "CSL-007"),
    )
    configuration = {
        "run_experiment": "benchmark_contract_canary",
        "repeat_count": 2,
        "benchmarks": [item.to_json_dict() for item in BENCHMARK_LADDER],
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
            contract_rows: list[dict[str, Any]] = []
            reference_rows: dict[str, Any] = {}
            context_artifacts: dict[str, str] = {}
            for benchmark in BENCHMARK_LADDER:
                first, first_reference = build_rdp_case(benchmark)
                second, second_reference = build_rdp_case(benchmark)
                first_variables = np.asarray(
                    [first_reference.true_key[index] for index in first.free_columns],
                    dtype=np.uint8,
                )
                second_variables = np.asarray(
                    [second_reference.true_key[index] for index in second.free_columns],
                    dtype=np.uint8,
                )
                first_score = float(first.evaluate_variables(first_variables[None, :])[0])
                second_score = float(second.evaluate_variables(second_variables[None, :])[0])
                first_context = make_replay_context(
                    first,
                    run_id=run_dir.name,
                    configuration_hash=run.configuration_hash,
                    evaluator_provenance=evaluator_provenance,
                )
                second_context = make_replay_context(
                    second,
                    run_id=run_dir.name,
                    configuration_hash=run.configuration_hash,
                    evaluator_provenance=evaluator_provenance,
                )
                structural_equal = all((
                    first.sample_start == second.sample_start,
                    first.wli == second.wli,
                    first.free_columns == second.free_columns,
                    np.array_equal(first.ciphertext, second.ciphertext),
                    np.array_equal(first.crib, second.crib),
                    np.array_equal(first.particular, second.particular),
                    np.array_equal(first.basis, second.basis),
                    first_context.context_id == second_context.context_id,
                ))
                if not structural_equal:
                    raise RuntimeError(
                        f"benchmark contract drifted between builds: {benchmark.benchmark_id}"
                    )
                if not np.isfinite(first_score) or not np.isfinite(second_score):
                    raise RuntimeError(
                        f"known benchmark score is non-finite: {benchmark.benchmark_id}"
                    )
                if first_score != second_score:
                    raise RuntimeError(
                        f"benchmark score drifted between builds: {benchmark.benchmark_id}"
                    )
                if not np.array_equal(
                    first_reference.true_key, second_reference.true_key
                ):
                    raise RuntimeError(
                        f"benchmark key drifted between builds: {benchmark.benchmark_id}"
                    )
                context_relative = Path(
                    "artifacts/replay_contexts"
                ) / f"{benchmark.benchmark_id}.json"
                write_replay_context(run_dir / context_relative, first_context)
                context_artifacts[benchmark.benchmark_id] = context_relative.as_posix()
                contract_rows.append({
                    "benchmark": benchmark.to_json_dict(),
                    "sample_start": first.sample_start,
                    "derived_free_dimension": len(first.free_columns),
                    "free_columns": list(first.free_columns),
                    "ciphertext_sha256": _portable_hash(first.ciphertext.astype(int).tolist()),
                    "wli_sha256": _portable_hash([list(pair) for pair in first.wli]),
                    "crib_sha256": _portable_hash(first.crib.astype(int).tolist()),
                    "particular_sha256": _portable_hash(first.particular.astype(int).tolist()),
                    "basis_sha256": _portable_hash(first.basis.astype(int).tolist()),
                    "replay_context_id": first_context.context_id,
                    "repeat_context_id": second_context.context_id,
                    "structural_repeat_equal": structural_equal,
                    "replay_context_artifact": context_relative.as_posix(),
                })
                metrics = reference_metrics(
                    first_reference,
                    first_variables,
                    first.particular,
                    first.basis,
                )
                if not all((
                    metrics["exact_plaintext"],
                    metrics["canonical_key_equal"],
                    metrics["combined_shift_equal"],
                )):
                    raise RuntimeError(
                        f"known benchmark reference contract failed: {benchmark.benchmark_id}"
                    )
                reference_rows[benchmark.benchmark_id] = {
                    **metrics,
                    "known_score_finite": True,
                    "known_score_repeat_equal": first_score == second_score,
                    "known_key_repeat_equal": np.array_equal(
                        first_reference.true_key, second_reference.true_key
                    ),
                }
                run.snapshot(label="benchmark_contract_validated", metrics={
                    "benchmark_id": benchmark.benchmark_id,
                    "derived_free_dimension": len(first.free_columns),
                    "structural_repeat_equal": structural_equal,
                    "replay_context_id": first_context.context_id,
                })
            artifact = run_dir / "artifacts/benchmark_contract.json"
            _write_json(artifact, {
                "schema": "rdp.two_period_overlay.benchmark_contract.v1",
                "repeat_count": 2,
                "benchmarks": contract_rows,
                "context_artifacts": context_artifacts,
            })
            result_path = run.finish(
                decision=ExperimentDecision.REFINE,
                stop_reason="done",
                result_summary={
                    "benchmark_count": len(contract_rows),
                    "repeat_count": 2,
                    "all_structural_repeats_equal": all(
                        row["structural_repeat_equal"] for row in contract_rows
                    ),
                    "artifact": "artifacts/benchmark_contract.json",
                    "replay_context_artifacts": context_artifacts,
                },
                reference_evaluation={"benchmarks": reference_rows},
            )
    except BaseException as exc:
        _pack_after_failure(repo_root, run_dir, exc)
        raise
    assert run_dir is not None and result_path is not None
    _pack_after_success(repo_root, run_dir)
    return result_path


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
        "run_experiment": "archive_handoff",
        "profile": profile,
        "benchmark": benchmark.to_json_dict(),
        "master_seed": MASTER_SEED,
        "archive_capacity": ARCHIVE_CAPACITY,
        "decision_score": DECISION_SCORE,
        "budget": _budget_configuration(budget),
        "evaluation_budget_upper_bound": evaluation_budget,
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
            replay_context = make_replay_context(
                search_case,
                run_id=run_dir.name,
                configuration_hash=run.configuration_hash,
                evaluator_provenance=evaluator_provenance,
            )
            write_replay_context(
                run_dir / "artifacts/replay_context.json", replay_context
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
            artifact_names = dict(write_search_artifacts(run_dir / "artifacts", outcome))
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
                    source_run_id=run_dir.name,
                    configuration_hash=run.configuration_hash,
                    benchmark_id=benchmark.benchmark_id,
                    context=replay_context,
                    batch=batch,
                    context_artifact="artifacts/replay_context.json",
                    batch_artifact=f"artifacts/{batch_filename}",
                )
                write_replay_binding(run_dir / "artifacts" / binding_filename, binding)
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
            result_path = run.finish(
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
                        name: f"artifacts/{filename}"
                        for name, filename in artifact_names.items()
                    },
                },
                reference_evaluation=reference_evaluation,
            )
    except BaseException as exc:
        _pack_after_failure(repo_root, run_dir, exc)
        raise
    assert run_dir is not None and result_path is not None
    _pack_after_success(repo_root, run_dir)
    return result_path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    if RUN_EXPERIMENT == "benchmark_contract_canary":
        run_benchmark_contract_canary(repo_root)
    elif RUN_EXPERIMENT == "archive_handoff":
        run_rdp_campaign(repo_root, RUN_PROFILE)
    else:
        raise ValueError(
            "RUN_EXPERIMENT must be 'benchmark_contract_canary' or 'archive_handoff'"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
