from __future__ import annotations

import json
from pathlib import Path
import sys
from types import SimpleNamespace
from typing import Any, Mapping

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

REPLAY_MODE = "verify"
ABSOLUTE_TOLERANCE = 1e-12
RELATIVE_TOLERANCE = 1e-12


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"malformed JSON in {path.name}: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return payload


def _campaign_root(repo_root: Path) -> Path:
    return (repo_root.resolve() / "output/cipher_development/two_period_overlay").resolve()


def latest_completed_technical_canary(repo_root: Path) -> str:
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
            experiment.get("experiment_id") == "technical_canary_v1"
            and result.get("status") == "completed"
            and result.get("run_id") == run_dir.name
        ):
            candidates.append(run_dir.name)
    if not candidates:
        raise FileNotFoundError("no completed technical_canary_v1 run was found")
    return max(candidates)


def _source_run(repo_root: Path, source_run_id: str) -> Path:
    if not source_run_id or source_run_id in {".", ".."} or "/" in source_run_id or "\\" in source_run_id:
        raise ValueError("source_run_id must be one directory name")
    root = _campaign_root(repo_root)
    run_dir = (root / source_run_id).resolve()
    if root not in run_dir.parents:
        raise ValueError("source_run_id escaped the campaign output root")
    return run_dir


def _replay_summary(evidence, artifact: str) -> dict[str, Any]:
    return {
        "source_binding_id": evidence.source_binding_id,
        "source_batch_id": evidence.source_batch_id,
        "source_context_id": evidence.source_context_id,
        "replay_id": evidence.replay_id,
        "candidate_count": len(evidence.candidate_ids),
        "repeat_count": evidence.repeat_count,
        "deterministic": evidence.deterministic,
        "stored_scores_verified": evidence.stored_scores_verified,
        "ranking": list(evidence.ranking),
        "artifact": artifact,
    }


def _portable_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _portable_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_portable_json(item) for item in value]
    return value


def _evaluator_context(context: Any) -> Any:
    payload = _portable_json(context.payload)
    scoring = dict(payload["scoring"])
    for field in ("char_weights", "wli_weights"):
        weights = scoring.get(field)
        if isinstance(weights, Mapping):
            scoring[field] = {int(n): weight for n, weight in weights.items()}
    payload["scoring"] = scoring
    return SimpleNamespace(campaign_id=context.campaign_id, payload=payload)


def run_required_replay_suite(
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
    from cipher_development.shared.replay import write_replay_context
    from cipher_development.shared.replay_binding import load_bound_replay_source
    from cipher_development.shared.replay_evidence import (
        ReplayMode,
        write_candidate_replay,
    )
    from cipher_development.shared.replay_execution import replay_candidate_batch
    from cipher_development.shared.replay_provenance import (
        build_evaluator_provenance,
        validate_evaluator_provenance,
    )
    from cipher_development.two_period_overlay.config import (
        DECISION_SCORE,
        REQUIRED_REPLAY_BINDING_ARTIFACTS,
        REQUIRED_REPLAY_REPEAT_COUNT,
    )
    from cipher_development.two_period_overlay.replay import build_replay_evaluator
    from cipher_development.two_period_overlay.review_pack import write_review_pack_after_run

    replay_mode = ReplayMode(REPLAY_MODE)
    repo_root = repo_root.resolve()
    selected_run_id = source_run_id or latest_completed_technical_canary(repo_root)
    source_run = _source_run(repo_root, selected_run_id)

    loaded: dict[str, tuple[Any, Any, Any]] = {}
    source_manifest: Mapping[str, Any] | None = None
    source_result: Mapping[str, Any] | None = None
    for binding_artifact in REQUIRED_REPLAY_BINDING_ARTIFACTS:
        manifest, result, binding, context, batch = load_bound_replay_source(
            source_run,
            binding_artifact,
            expected_campaign_id="two_period_overlay",
            expected_run_id=selected_run_id,
        )
        if source_manifest is None:
            source_manifest, source_result = manifest, result
        elif manifest != source_manifest or result != source_result:
            raise ValueError("required replay bindings do not identify the same source run")
        loaded[binding_artifact] = (binding, context, batch)

    if len(loaded) != len(REQUIRED_REPLAY_BINDING_ARTIFACTS):
        raise ValueError("the technical-canary replay suite requires both starting-batch bindings")
    context_ids = {context.context_id for _, context, _ in loaded.values()}
    if len(context_ids) != 1:
        raise ValueError("required replay bindings do not share one replay context")

    first_binding, first_context, _ = loaded[REQUIRED_REPLAY_BINDING_ARTIFACTS[0]]
    total_candidates = sum(len(batch.candidates) for _, _, batch in loaded.values())
    budget_evaluations = total_candidates * REQUIRED_REPLAY_REPEAT_COUNT
    spec = ExperimentSpec(
        campaign_id="two_period_overlay",
        experiment_id="technical_canary_replay_suite_v1",
        benchmark_id=first_binding.benchmark_id,
        question=(
            "Can both bound technical-canary starting surfaces be rescored exactly and "
            "deterministically without discovery or exploitation?"
        ),
        hypothesis=(
            "Both archive-handoff and independent-control batches reproduce their stored "
            "scores and ranking under the recorded evaluator provenance."
        ),
        alternative=(
            "At least one saved batch, binding or evaluator provenance record is insufficient "
            "to reproduce its stored candidate surface."
        ),
        decision_rule=(
            "Replay suites always refine. The technical replay gate passes only when both "
            "bindings are deterministic and every stored decision score is verified."
        ),
        wli_mode=WliMode.WITH_WLI,
        truth_policy=TruthPolicy.NONE,
        mechanisms=(FailureMechanism.EVIDENCE_REPRODUCIBILITY,),
        budget_evaluations=budget_evaluations,
        lesson_ids=("CSL-001", "CSL-002", "CSL-004", "CSL-005", "CSL-007"),
    )
    configuration = {
        "source_run_id": selected_run_id,
        "required_binding_artifacts": list(REQUIRED_REPLAY_BINDING_ARTIFACTS),
        "repeat_count": REQUIRED_REPLAY_REPEAT_COUNT,
        "mode": replay_mode.value,
        "decision_score": DECISION_SCORE,
        "absolute_tolerance": ABSOLUTE_TOLERANCE,
        "relative_tolerance": RELATIVE_TOLERANCE,
    }

    run_dir: Path | None = None
    result_path: Path | None = None
    try:
        with ExperimentRun(spec=spec, configuration=configuration, repo_root=repo_root) as run:
            assert run.run_dir is not None
            run_dir = run.run_dir
            write_replay_context(run_dir / "artifacts/source_replay_context.json", first_context)
            expected_provenance = _portable_json(
                first_context.payload["evaluator_provenance"]
            )
            actual_provenance = build_evaluator_provenance(
                repo_root=repo_root,
                evaluator_source=Path(__file__).with_name("replay.py"),
                scoring_contracts=(dict(first_context.payload["scoring"]),),
                run_meta={
                    "git": {
                        "commit": expected_provenance.get("git_commit"),
                        "dirty": expected_provenance.get("git_dirty"),
                    }
                },
                require_assets=True,
            )
            validate_evaluator_provenance(
                expected_provenance, actual_provenance
            )

            summaries: dict[str, dict[str, Any]] = {}
            for binding_artifact in REQUIRED_REPLAY_BINDING_ARTIFACTS:
                binding, context, batch = loaded[binding_artifact]
                validate_evaluator_provenance(
                    _portable_json(context.payload["evaluator_provenance"]),
                    actual_provenance,
                )
                evidence = replay_candidate_batch(
                    batch,
                    context,
                    binding,
                    evaluator=build_replay_evaluator(_evaluator_context(context)),
                    mode=replay_mode,
                    decision_score=DECISION_SCORE,
                    higher_is_better=True,
                    evaluator_configuration={
                        "campaign": "two_period_overlay",
                        "suite": "technical_canary_replay_suite_v1",
                        "source_run_id": selected_run_id,
                        "binding_artifact": binding_artifact,
                        "binding_id": binding.binding_id,
                        "context_id": context.context_id,
                        "decision_score": DECISION_SCORE,
                        "evaluator_provenance": actual_provenance,
                    },
                    repeat_count=REQUIRED_REPLAY_REPEAT_COUNT,
                    absolute_tolerance=ABSOLUTE_TOLERANCE,
                    relative_tolerance=RELATIVE_TOLERANCE,
                )
                label = Path(binding_artifact).stem.removesuffix("_binding")
                artifact = f"artifacts/{label}_replay.json"
                write_candidate_replay(run_dir / artifact, evidence)
                summaries[label] = _replay_summary(evidence, artifact)

            all_deterministic = all(item["deterministic"] for item in summaries.values())
            all_scores_verified = all(
                item["stored_scores_verified"] is True for item in summaries.values()
            )
            run.snapshot(
                label="required_replays_completed",
                metrics={
                    "source_run_id": selected_run_id,
                    "replay_count": len(summaries),
                    "all_deterministic": all_deterministic,
                    "all_stored_scores_verified": all_scores_verified,
                },
            )
            result_path = run.finish(
                decision=ExperimentDecision.REFINE,
                stop_reason="done",
                result_summary={
                    "source_run_id": selected_run_id,
                    "source_run_result_artifact": "source_run/artifacts/experiment_result.json",
                    "required_binding_artifacts": list(REQUIRED_REPLAY_BINDING_ARTIFACTS),
                    "repeat_count": REQUIRED_REPLAY_REPEAT_COUNT,
                    "replay_count": len(summaries),
                    "all_deterministic": all_deterministic,
                    "all_stored_scores_verified": all_scores_verified,
                    "technical_replay_gate_passed": (
                        len(summaries) == len(REQUIRED_REPLAY_BINDING_ARTIFACTS)
                        and all_deterministic
                        and all_scores_verified
                    ),
                    "replays": summaries,
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
    run_required_replay_suite(repo_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
