from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any, Mapping

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cipher_development.shared.archive import archive_content_hash, read_candidate_archive
from cipher_development.shared.replay import (
    CandidateReplayContext,
    read_replay_context,
    write_candidate_batch,
    write_replay_context,
)
from cipher_development.shared.replay_binding import (
    CandidateReplayBinding,
    write_replay_binding,
)
from cipher_development.shared.replay_evidence import ReplayMode, write_candidate_replay
from cipher_development.shared.replay_execution import replay_candidate_batch
from cipher_development.two_period_overlay.config import DECISION_SCORE
from cipher_development.two_period_overlay.review_pack import write_review_pack_after_run
from cipher_development.two_period_overlay.replay_suite import (
    _evaluator_context,
    _portable_json,
)
from cipher_development.two_period_overlay.selection import (
    DIVERSE_SHORTLIST_MULTIPLIER,
    SELECTION_COUNT,
    build_selection_batches,
)

SOURCE_BENCHMARK_ID = "alice_308_p09_p13_d08"
SOURCE_ARCHIVE_RELPATH = Path(
    f"artifacts/coordinate_supply/{SOURCE_BENCHMARK_ID}/discovery_pool_archive.json"
)
SOURCE_DIAGNOSTICS_RELPATH = Path(
    f"artifacts/coordinate_supply/{SOURCE_BENCHMARK_ID}/discovery_diagnostics.json"
)
SOURCE_CONTEXT_RELPATH = Path(f"artifacts/replay_contexts/{SOURCE_BENCHMARK_ID}.json")
REPLAY_REPEAT_COUNT = 2
ABSOLUTE_TOLERANCE = 1e-12
RELATIVE_TOLERANCE = 1e-12


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(payload), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _campaign_root(repo_root: Path) -> Path:
    return (repo_root.resolve() / "output/cipher_development/two_period_overlay").resolve()


def latest_completed_coordinate_supply(repo_root: Path) -> str:
    root = _campaign_root(repo_root)
    candidates: list[str] = []
    if not root.is_dir():
        raise FileNotFoundError("the two-period campaign output directory does not exist")
    for run_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        manifest_path = run_dir / "artifacts/experiment_manifest.json"
        result_path = run_dir / "artifacts/experiment_result.json"
        if not manifest_path.is_file() or not result_path.is_file():
            continue
        manifest = _read_json(manifest_path)
        result = _read_json(result_path)
        experiment = manifest.get("experiment")
        if not isinstance(experiment, Mapping):
            continue
        if (
            experiment.get("experiment_id") == "coordinate_supply_v1"
            and result.get("status") == "completed"
            and result.get("run_id") == run_dir.name
            and result.get("result_summary", {}).get("all_unique_thresholds_met") is True
        ):
            candidates.append(run_dir.name)
    if not candidates:
        raise FileNotFoundError("no completed coordinate_supply_v1 run was found")
    return max(candidates)


def _source_run(repo_root: Path, source_run_id: str) -> Path:
    if not source_run_id or source_run_id in {".", ".."} or "/" in source_run_id or "\\" in source_run_id:
        raise ValueError("source_run_id must be one directory name")
    root = _campaign_root(repo_root)
    run_dir = (root / source_run_id).resolve()
    if root not in run_dir.parents:
        raise ValueError("source_run_id escaped the campaign output root")
    return run_dir


def _copy_source_evidence(source_run: Path, artifact_dir: Path) -> dict[str, str]:
    paths = {
        "source_experiment_manifest": Path("artifacts/experiment_manifest.json"),
        "source_experiment_result": Path("artifacts/experiment_result.json"),
        "source_discovery_pool_archive": SOURCE_ARCHIVE_RELPATH,
        "source_discovery_diagnostics": SOURCE_DIAGNOSTICS_RELPATH,
        "source_replay_context": SOURCE_CONTEXT_RELPATH,
    }
    copied: dict[str, str] = {}
    for label, relative in paths.items():
        source = source_run / relative
        if not source.is_file():
            raise FileNotFoundError(f"missing coordinate-supply source artifact {relative.as_posix()}")
        destination = artifact_dir / f"{label}.json"
        shutil.copyfile(source, destination)
        copied[label] = destination.name
    return copied


def _replay_summary(evidence, artifact: str) -> dict[str, Any]:
    return {
        "replay_id": evidence.replay_id,
        "candidate_count": len(evidence.candidate_ids),
        "repeat_count": evidence.repeat_count,
        "deterministic": evidence.deterministic,
        "stored_scores_verified": evidence.stored_scores_verified,
        "ranking": list(evidence.ranking),
        "artifact": artifact,
    }


def run_candidate_selection_experiment(
    repo_root: Path,
    source_run_id: str | None = None,
) -> Path:
    from cipher_development.shared.experiment import (
        ExperimentDecision,
        ExperimentRun,
        ExperimentSpec,
        FailureMechanism,
        TruthPolicy,
        WliMode,
    )
    from cipher_development.shared.replay_provenance import (
        build_evaluator_provenance,
        validate_evaluator_provenance,
    )
    from cipher_development.two_period_overlay.replay import build_replay_evaluator

    repo_root = repo_root.resolve()
    selected_source_run = source_run_id or latest_completed_coordinate_supply(repo_root)
    source_run = _source_run(repo_root, selected_source_run)
    source_manifest = _read_json(source_run / "artifacts/experiment_manifest.json")
    source_result = _read_json(source_run / "artifacts/experiment_result.json")
    archive = read_candidate_archive(source_run / SOURCE_ARCHIVE_RELPATH)
    source_diagnostics = _read_json(source_run / SOURCE_DIAGNOSTICS_RELPATH)
    source_context = read_replay_context(source_run / SOURCE_CONTEXT_RELPATH)
    if source_context.payload.get("benchmark_id") != SOURCE_BENCHMARK_ID:
        raise ValueError("coordinate-supply replay context identifies the wrong benchmark")
    if source_diagnostics.get("source_archive_hash") != archive_content_hash(archive):
        raise ValueError("coordinate-supply diagnostics do not bind the selected archive")
    if source_result.get("status") != "completed":
        raise ValueError("coordinate-supply source run is not completed")

    top_batch, diverse_batch, comparison = build_selection_batches(archive)
    budget_evaluations = (
        len(top_batch.candidates) + len(diverse_batch.candidates)
    ) * REPLAY_REPEAT_COUNT
    spec = ExperimentSpec(
        campaign_id="two_period_overlay",
        experiment_id="candidate_selection_v1",
        benchmark_id=SOURCE_BENCHMARK_ID,
        question=(
            "Does deterministic diversity-aware selection produce a genuinely different, "
            "reproducible d8 handoff surface from simply taking the eight highest WLI scores?"
        ),
        hypothesis=(
            "Greedy max-min affine selection from the top sixteen candidates preserves the "
            "best candidate while increasing within-batch basin separation."
        ),
        alternative=(
            "The score-ranked top eight are already as diverse as the shortlist permits, so "
            "the diversity policy produces no meaningful candidate-set contrast."
        ),
        decision_rule=(
            "Selection studies always refine. Proceed to matched exploitation only when the "
            "two batches differ, both replay twice, and all stored scores and rankings verify."
        ),
        wli_mode=WliMode.WITH_WLI,
        truth_policy=TruthPolicy.NONE,
        mechanisms=(FailureMechanism.DIVERSITY_COLLAPSE, FailureMechanism.RANKING),
        budget_evaluations=budget_evaluations,
        lesson_ids=("CSL-001", "CSL-002", "CSL-004", "CSL-005", "CSL-007"),
    )
    configuration = {
        "source_run_id": selected_source_run,
        "source_benchmark_id": SOURCE_BENCHMARK_ID,
        "source_archive_artifact": SOURCE_ARCHIVE_RELPATH.as_posix(),
        "source_archive_hash": archive_content_hash(archive),
        "selection_count": SELECTION_COUNT,
        "diverse_shortlist_multiplier": DIVERSE_SHORTLIST_MULTIPLIER,
        "replay_repeat_count": REPLAY_REPEAT_COUNT,
        "absolute_tolerance": ABSOLUTE_TOLERANCE,
        "relative_tolerance": RELATIVE_TOLERANCE,
    }

    run_dir: Path | None = None
    result_path: Path | None = None
    try:
        with ExperimentRun(spec=spec, configuration=configuration, repo_root=repo_root) as run:
            assert run.run_dir is not None
            run_dir = run.run_dir
            artifact_dir = run_dir / "artifacts"
            copied = _copy_source_evidence(source_run, artifact_dir)
            context = CandidateReplayContext.create(
                campaign_id="two_period_overlay",
                run_id=run_dir.name,
                configuration_hash=run.configuration_hash,
                evaluator_id=source_context.evaluator_id,
                payload=dict(source_context.payload),
            )
            context_artifact = "artifacts/replay_context.json"
            write_replay_context(run_dir / context_artifact, context)

            batches = {
                "top_wli": top_batch,
                "diverse_high_wli": diverse_batch,
            }
            bindings: dict[str, CandidateReplayBinding] = {}
            for label, batch in batches.items():
                batch_artifact = f"artifacts/{label}_batch.json"
                binding_artifact = f"artifacts/{label}_binding.json"
                write_candidate_batch(run_dir / batch_artifact, batch)
                binding = CandidateReplayBinding.create(
                    campaign_id="two_period_overlay",
                    source_run_id=run_dir.name,
                    configuration_hash=run.configuration_hash,
                    benchmark_id=SOURCE_BENCHMARK_ID,
                    context=context,
                    batch=batch,
                    context_artifact=context_artifact,
                    batch_artifact=batch_artifact,
                )
                write_replay_binding(run_dir / binding_artifact, binding)
                bindings[label] = binding

            _write_json(artifact_dir / "selection_comparison.json", comparison.to_json_dict())
            actual_provenance = build_evaluator_provenance(
                repo_root=repo_root,
                evaluator_source=Path(__file__).with_name("replay.py"),
                scoring_contracts=(dict(context.payload["scoring"]),),
                require_assets=True,
            )
            validate_evaluator_provenance(
                _portable_json(context.payload["evaluator_provenance"]),
                actual_provenance,
            )
            evaluator = build_replay_evaluator(_evaluator_context(context))
            replay_summaries: dict[str, dict[str, Any]] = {}
            for label, batch in batches.items():
                evidence = replay_candidate_batch(
                    batch,
                    context,
                    bindings[label],
                    evaluator=evaluator,
                    mode=ReplayMode.VERIFY,
                    decision_score=DECISION_SCORE,
                    higher_is_better=True,
                    evaluator_configuration={
                        "campaign": "two_period_overlay",
                        "experiment": "candidate_selection_v1",
                        "selection_label": label,
                        "source_run_id": selected_source_run,
                        "binding_id": bindings[label].binding_id,
                        "context_id": context.context_id,
                        "evaluator_provenance": actual_provenance,
                    },
                    repeat_count=REPLAY_REPEAT_COUNT,
                    absolute_tolerance=ABSOLUTE_TOLERANCE,
                    relative_tolerance=RELATIVE_TOLERANCE,
                )
                replay_artifact = f"artifacts/{label}_replay.json"
                write_candidate_replay(run_dir / replay_artifact, evidence)
                replay_summaries[label] = _replay_summary(evidence, replay_artifact)

            replay_gate = all(
                row["deterministic"] and row["stored_scores_verified"] is True
                for row in replay_summaries.values()
            )
            selection_gate = (not comparison.identical) and replay_gate
            run.snapshot(
                label="selection_and_replay_completed",
                metrics={
                    "source_run_id": selected_source_run,
                    "overlap_count": comparison.overlap_count,
                    "identical": comparison.identical,
                    "selection_gate_passed": selection_gate,
                },
            )
            result_path = run.finish(
                decision=ExperimentDecision.REFINE,
                stop_reason="done",
                result_summary={
                    "source_run_id": selected_source_run,
                    "source_archive_hash": archive_content_hash(archive),
                    "selection_count": SELECTION_COUNT,
                    "shortlist_count": comparison.shortlist_count,
                    "overlap_count": comparison.overlap_count,
                    "selection_sets_identical": comparison.identical,
                    "top_wli_batch_id": top_batch.batch_id,
                    "diverse_high_wli_batch_id": diverse_batch.batch_id,
                    "top_wli_binding_id": bindings["top_wli"].binding_id,
                    "diverse_high_wli_binding_id": bindings["diverse_high_wli"].binding_id,
                    "top_score_summary": comparison.top_score_summary,
                    "diverse_score_summary": comparison.diverse_score_summary,
                    "top_affine_hamming_summary": comparison.top_affine_hamming_summary,
                    "diverse_affine_hamming_summary": comparison.diverse_affine_hamming_summary,
                    "replay_count": len(replay_summaries),
                    "all_deterministic": all(row["deterministic"] for row in replay_summaries.values()),
                    "all_stored_scores_verified": all(
                        row["stored_scores_verified"] is True
                        for row in replay_summaries.values()
                    ),
                    "selection_gate_passed": selection_gate,
                    "replays": replay_summaries,
                    "source_artifacts": copied,
                    "selection_comparison_artifact": "artifacts/selection_comparison.json",
                },
            )
    except BaseException as exc:
        if run_dir is not None:
            write_review_pack_after_run(repo_root, run_dir, original_error=exc)
        raise
    assert run_dir is not None and result_path is not None
    write_review_pack_after_run(repo_root, run_dir)
    return result_path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    run_candidate_selection_experiment(repo_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
