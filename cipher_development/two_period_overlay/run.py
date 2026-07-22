from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from cipher_development.two_period_overlay.benchmark import (
    ReferenceCase,
    SearchCase,
    build_rdp_case,
    normalise_baseline_result,
    reference_metrics,
)
from cipher_development.two_period_overlay.config import (
    ALPHABET_SIZE,
    ARCHIVE_CAPACITY,
    BASELINE_RESULT_PATH,
    CRIB_START,
    CRIB_WORD,
    DECISION_SCORE,
    MASTER_SEED,
    PERIOD_A,
    PERIOD_B,
    RUN_PROFILE,
    SCORING_CONTRACT,
    TEXT_LENGTH,
    budget_for,
)
from cipher_development.two_period_overlay.keyspace import (
    candidate_record,
    comparison_seed,
    crib_space,
    deterministic_key,
    expand,
)
from cipher_development.two_period_overlay.search import (
    campaign_decision,
    comparison_summary,
    discover_archive,
    run_search,
    write_search_artifacts,
)


def import_baseline_result(repo_root: Path, source_path: Path = BASELINE_RESULT_PATH) -> Path:
    from cipher_development.shared.experiment import (
        ExperimentDecision,
        ExperimentRun,
        ExperimentSpec,
        FailureMechanism,
        TruthPolicy,
        WliMode,
    )
    from cipher_development.shared.ledger import read_ledger

    raw = source_path.read_bytes()
    source_sha256 = hashlib.sha256(raw).hexdigest()
    payload = json.loads(raw.decode("utf-8"))
    summary, reference = normalise_baseline_result(payload, source_sha256, source_path.name)
    ledger_path = repo_root / "output/cipher_development/two_period_overlay/experiment_ledger.jsonl"
    if any(row.result_summary.get("source_sha256") == source_sha256 for row in read_ledger(ledger_path)):
        raise ValueError("this baseline source hash has already been imported")
    spec = ExperimentSpec(
        campaign_id="two_period_overlay",
        experiment_id="frozen_baseline_import",
        benchmark_id="alice_308_p13_p17",
        question="What ceilings were reached by the frozen independent search mechanisms?",
        hypothesis="The historical run provides a reproducible exploitation baseline.",
        decision_rule="Import evidence only; do not promote a mechanism.",
        wli_mode=WliMode.WITH_WLI,
        truth_policy=TruthPolicy.BENCHMARK_ONLY,
        mechanisms=(FailureMechanism.EXPLOITATION, FailureMechanism.EVIDENCE_REPRODUCIBILITY),
    )
    with ExperimentRun(
        spec=spec,
        configuration={"source_sha256": source_sha256, "source_filename": source_path.name},
        repo_root=repo_root,
    ) as run:
        return run.finish(
            decision=ExperimentDecision.REFINE,
            stop_reason="time_budget",
            result_summary=summary,
            reference_evaluation=reference,
        )


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
    search_case, reference = build_rdp_case()
    spec = ExperimentSpec(
        campaign_id="two_period_overlay",
        experiment_id=f"wp3_archive_handoff_{profile}",
        benchmark_id="alice_308_p13_p17",
        question="Does a retained full-WLI coordinate archive outperform independent exploitation starts?",
        hypothesis="Useful coordinate basins are discarded between independent methods.",
        decision_rule=(
            "Promote when archive wins exceed control wins and archive best is no worse; "
            "close when there are no archive wins and archive best is no better; otherwise refine."
        ),
        wli_mode=WliMode.WITH_WLI,
        truth_policy=TruthPolicy.BENCHMARK_ONLY,
        mechanisms=(FailureMechanism.CANDIDATE_SUPPLY, FailureMechanism.HANDOFF, FailureMechanism.EXPLOITATION),
    )
    configuration = {
        "profile": profile,
        "periods": [PERIOD_A, PERIOD_B],
        "text_length": TEXT_LENGTH,
        "alphabet_size": ALPHABET_SIZE,
        "crib_word": CRIB_WORD,
        "crib_start": CRIB_START,
        "master_seed": MASTER_SEED,
        "archive_capacity": ARCHIVE_CAPACITY,
        "decision_score": DECISION_SCORE,
        "budget": {
            "coordinate_restarts": budget.coordinate_restarts,
            "coordinate_sweeps": budget.coordinate_sweeps,
            "handoff_candidates": budget.handoff_candidates,
            "sa_steps": budget.sa_steps,
            "sa_cycles": budget.sa_cycles,
        },
        "scoring": SCORING_CONTRACT,
    }
    with ExperimentRun(spec=spec, configuration=configuration, repo_root=repo_root) as run:
        run.snapshot(label="benchmark_built", metrics={"free_dimension": len(search_case.free_columns)})
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
        assert run.run_dir is not None
        artifact_names = write_search_artifacts(run.run_dir / "artifacts", outcome)
        run.snapshot(label="handoff_batches_written", metrics={
            "archive_candidates": len(outcome.handoff_batch.candidates),
            "control_candidates": len(outcome.control_batch.candidates),
        })
        summary = comparison_summary(outcome)
        decision = campaign_decision(summary, profile)
        run.snapshot(label="campaign_completed", metrics={**summary, "retained": len(outcome.archive.records)})
        reference_evaluation = reference_metrics(
            reference,
            np.asarray(outcome.best_variables, dtype=np.uint8),
            search_case.particular,
            search_case.basis,
        )
        return run.finish(
            decision=ExperimentDecision(decision),
            stop_reason="time_budget",
            result_summary={
                **summary,
                "best_score": outcome.best_score,
                "evaluations": outcome.evaluations,
                "coordinate_restarts": budget.coordinate_restarts,
                "discovery_retained": len(outcome.discovery_archive.records),
                "archive_retained": len(outcome.archive.records),
                "paired_comparisons": [dict(row) for row in outcome.comparisons],
                "artifacts": {name: f"artifacts/{filename}" for name, filename in artifact_names.items()},
            },
            reference_evaluation=reference_evaluation,
        )


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    if RUN_PROFILE == "baseline_import":
        import_baseline_result(repo_root)
    else:
        run_rdp_campaign(repo_root, RUN_PROFILE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
