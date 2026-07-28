from __future__ import annotations

import json
import math
import shutil
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np

from cipher_development.shared.archive import archive_content_hash, read_candidate_archive
from cipher_development.shared.replay import (
    CandidateReplayContext,
    read_replay_context,
    select_candidate_batch,
    write_candidate_batch,
    write_replay_context,
)
from cipher_development.shared.replay_binding import (
    CandidateReplayBinding,
    write_replay_binding,
)
from cipher_development.shared.replay_evidence import ReplayMode, write_candidate_replay
from cipher_development.shared.replay_execution import replay_candidate_batch
from cipher_development.two_period_overlay.benchmark import build_rdp_case, reference_metrics
from cipher_development.two_period_overlay.config import DECISION_SCORE, TARGET_BENCHMARK
from cipher_development.two_period_overlay.review_pack import write_review_pack_after_run
from cipher_development.two_period_overlay.replay_suite import (
    _evaluator_context,
    _portable_json,
)

SOURCE_ARCHIVE_RELPATH = Path(
    "artifacts/target_coordinate_supply/combined_pool_archive.json"
)
SOURCE_DIAGNOSTICS_RELPATH = Path(
    "artifacts/target_coordinate_supply/combined_diagnostics.json"
)
SOURCE_SUMMARY_RELPATH = Path("artifacts/target_coordinate_supply_summary.json")
SOURCE_CONTEXT_RELPATH = Path("artifacts/replay_context.json")
REPLAY_REPEAT_COUNT = 2
ABSOLUTE_TOLERANCE = 1e-12
RELATIVE_TOLERANCE = 1e-12
TOP_K_VALUES = (8, 16, 32)


def _ciphertext_matches(saved: Sequence[int], expected: Sequence[int]) -> bool:
    return tuple(int(value) for value in saved) == tuple(
        int(value) for value in expected
    )


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def _campaign_root(repo_root: Path) -> Path:
    return (repo_root.resolve() / "output/cipher_development/two_period_overlay").resolve()


def latest_completed_target_supply(repo_root: Path) -> str:
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
        summary = result.get("result_summary")
        if not isinstance(experiment, Mapping) or not isinstance(summary, Mapping):
            continue
        if (
            experiment.get("experiment_id") == "target_coordinate_supply_v1"
            and result.get("status") == "completed"
            and result.get("run_id") == run_dir.name
            and summary.get("target_supply_gate_passed") is True
        ):
            candidates.append(run_dir.name)
    if not candidates:
        raise FileNotFoundError("no completed target_coordinate_supply_v1 run was found")
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
        "source_target_coordinate_supply_summary": SOURCE_SUMMARY_RELPATH,
        "source_combined_pool_archive": SOURCE_ARCHIVE_RELPATH,
        "source_combined_diagnostics": SOURCE_DIAGNOSTICS_RELPATH,
        "source_replay_context": SOURCE_CONTEXT_RELPATH,
    }
    copied: dict[str, str] = {}
    for label, relative in paths.items():
        source = source_run / relative
        if not source.is_file():
            raise FileNotFoundError(f"missing target-supply source artifact {relative.as_posix()}")
        destination = artifact_dir / f"{label}.json"
        shutil.copyfile(source, destination)
        copied[label] = destination.name
    return copied


def average_ranks(values: Sequence[float], *, higher_is_better: bool = True) -> tuple[float, ...]:
    numbers = tuple(float(value) for value in values)
    if not numbers:
        raise ValueError("rank values must not be empty")
    if not all(math.isfinite(value) for value in numbers):
        raise ValueError("rank values must be finite")
    order = sorted(
        range(len(numbers)),
        key=lambda index: (
            -numbers[index] if higher_is_better else numbers[index],
            index,
        ),
    )
    ranks = [0.0] * len(numbers)
    position = 0
    while position < len(order):
        end = position + 1
        value = numbers[order[position]]
        while end < len(order) and numbers[order[end]] == value:
            end += 1
        average = (position + 1 + end) / 2.0
        for offset in range(position, end):
            ranks[order[offset]] = average
        position = end
    return tuple(ranks)


def _pearson(left: Sequence[float], right: Sequence[float]) -> float | None:
    a = np.asarray(left, dtype=np.float64)
    b = np.asarray(right, dtype=np.float64)
    if a.shape != b.shape or a.ndim != 1 or a.size < 2:
        raise ValueError("correlation inputs must be equal-length vectors with at least two values")
    a = a - np.mean(a)
    b = b - np.mean(b)
    denominator = float(np.sqrt(np.dot(a, a) * np.dot(b, b)))
    if denominator == 0.0:
        return None
    return float(np.dot(a, b) / denominator)


def spearman_rank_correlation(
    left: Sequence[float],
    right: Sequence[float],
    *,
    left_higher_is_better: bool = True,
    right_higher_is_better: bool = True,
) -> float | None:
    if len(left) != len(right):
        raise ValueError("Spearman inputs must have the same length")
    return _pearson(
        average_ranks(left, higher_is_better=left_higher_is_better),
        average_ranks(right, higher_is_better=right_higher_is_better),
    )


def _numeric_summary(values: Sequence[int | float]) -> dict[str, float]:
    array = np.asarray(tuple(values), dtype=np.float64)
    if array.ndim != 1 or array.size == 0 or not np.all(np.isfinite(array)):
        raise ValueError("summary values must be a non-empty finite vector")
    return {
        "minimum": float(np.min(array)),
        "q25": float(np.quantile(array, 0.25)),
        "median": float(np.median(array)),
        "q75": float(np.quantile(array, 0.75)),
        "maximum": float(np.max(array)),
        "mean": float(np.mean(array)),
    }


def _top_k_overlap(
    candidate_ids: Sequence[str],
    scores: Sequence[float],
    terminal_values: Sequence[int],
    k: int,
) -> int:
    if not 0 < k <= len(candidate_ids):
        raise ValueError("top-k value is outside the candidate surface")
    score_order = sorted(
        range(len(candidate_ids)),
        key=lambda index: (-float(scores[index]), str(candidate_ids[index])),
    )
    terminal_order = sorted(
        range(len(candidate_ids)),
        key=lambda index: (-int(terminal_values[index]), str(candidate_ids[index])),
    )
    return len(set(score_order[:k]) & set(terminal_order[:k]))


def _best_terminal_wli_rank(
    scores: Sequence[float],
    terminal_values: Sequence[int],
) -> int:
    score_ranks = average_ranks(scores, higher_is_better=True)
    best = max(int(value) for value in terminal_values)
    return int(min(
        math.ceil(score_ranks[index])
        for index, value in enumerate(terminal_values)
        if int(value) == best
    ))


def _pairwise_concordance(
    scores: Sequence[float],
    terminal_values: Sequence[int],
) -> dict[str, float | int | None]:
    concordant = discordant = score_ties = terminal_ties = comparable = 0
    for left in range(len(scores)):
        for right in range(left + 1, len(scores)):
            score_delta = float(scores[left]) - float(scores[right])
            terminal_delta = int(terminal_values[left]) - int(terminal_values[right])
            if score_delta == 0.0:
                score_ties += 1
                continue
            if terminal_delta == 0:
                terminal_ties += 1
                continue
            comparable += 1
            if score_delta * terminal_delta > 0:
                concordant += 1
            else:
                discordant += 1
    fraction = None if comparable == 0 else concordant / comparable
    return {
        "concordant_pairs": concordant,
        "discordant_pairs": discordant,
        "score_ties": score_ties,
        "terminal_ties": terminal_ties,
        "comparable_pairs": comparable,
        "concordant_fraction": fraction,
    }


def aggregate_terminal_ranking(
    candidate_ids: Sequence[str],
    scores: Sequence[float],
    terminal_metrics: Sequence[Mapping[str, Any]],
    *,
    top_k_values: Sequence[int] = TOP_K_VALUES,
) -> dict[str, Any]:
    ids = tuple(str(value) for value in candidate_ids)
    score_values = tuple(float(value) for value in scores)
    metrics = tuple(dict(value) for value in terminal_metrics)
    if not ids or len(set(ids)) != len(ids):
        raise ValueError("candidate IDs must be non-empty and unique")
    if len(ids) != len(score_values) or len(ids) != len(metrics):
        raise ValueError("candidate IDs, scores and terminal metrics must align")
    if not all(math.isfinite(value) for value in score_values):
        raise ValueError("scores must be finite")

    rune_matches = tuple(int(row["rune_matches"]) for row in metrics)
    word_matches = tuple(int(row["complete_word_matches"]) for row in metrics)
    affine_matches = tuple(int(row["affine_variable_matches"]) for row in metrics)
    exact = sum(bool(row["exact_plaintext"]) for row in metrics)
    canonical = sum(bool(row["canonical_key_equal"]) for row in metrics)
    combined = sum(bool(row["combined_shift_equal"]) for row in metrics)

    score_order = sorted(
        range(len(ids)),
        key=lambda index: (-score_values[index], ids[index]),
    )
    top = score_order[0]
    top_k: dict[str, Any] = {}
    for raw_k in top_k_values:
        k = int(raw_k)
        if not 0 < k <= len(ids):
            continue
        selected = score_order[:k]
        top_k[str(k)] = {
            "rune_match_summary": _numeric_summary([rune_matches[index] for index in selected]),
            "complete_word_match_summary": _numeric_summary(
                [word_matches[index] for index in selected]
            ),
            "affine_variable_match_summary": _numeric_summary(
                [affine_matches[index] for index in selected]
            ),
            "rune_top_k_overlap_count": _top_k_overlap(
                ids, score_values, rune_matches, k
            ),
            "complete_word_top_k_overlap_count": _top_k_overlap(
                ids, score_values, word_matches, k
            ),
        }

    return {
        "schema": "rdp.two_period_overlay.target_ranking_diagnostic.v1",
        "candidate_count": len(ids),
        "candidate_specific_truth_emitted": False,
        "score_summary": _numeric_summary(score_values),
        "rune_match_summary": _numeric_summary(rune_matches),
        "complete_word_match_summary": _numeric_summary(word_matches),
        "affine_variable_match_summary": _numeric_summary(affine_matches),
        "score_vs_rune_spearman": spearman_rank_correlation(
            score_values, rune_matches
        ),
        "score_vs_complete_word_spearman": spearman_rank_correlation(
            score_values, word_matches
        ),
        "score_vs_affine_variable_match_spearman": spearman_rank_correlation(
            score_values, affine_matches
        ),
        "score_vs_rune_pairwise": _pairwise_concordance(
            score_values, rune_matches
        ),
        "score_vs_complete_word_pairwise": _pairwise_concordance(
            score_values, word_matches
        ),
        "best_rune_matches": max(rune_matches),
        "best_rune_candidate_count": sum(
            value == max(rune_matches) for value in rune_matches
        ),
        "best_rune_candidate_wli_rank": _best_terminal_wli_rank(
            score_values, rune_matches
        ),
        "best_complete_word_matches": max(word_matches),
        "best_complete_word_candidate_count": sum(
            value == max(word_matches) for value in word_matches
        ),
        "best_complete_word_candidate_wli_rank": _best_terminal_wli_rank(
            score_values, word_matches
        ),
        "top_wli_candidate_terminal": {
            "rune_matches": rune_matches[top],
            "complete_word_matches": word_matches[top],
            "affine_variable_matches": affine_matches[top],
            "exact_plaintext": bool(metrics[top]["exact_plaintext"]),
            "canonical_key_equal": bool(metrics[top]["canonical_key_equal"]),
            "combined_shift_equal": bool(metrics[top]["combined_shift_equal"]),
        },
        "exact_plaintext_count": exact,
        "canonical_key_count": canonical,
        "combined_shift_count": combined,
        "top_k": top_k,
    }


def _replay_summary(evidence, artifact: str) -> dict[str, Any]:
    return {
        "replay_id": evidence.replay_id,
        "candidate_count": len(evidence.candidate_ids),
        "repeat_count": evidence.repeat_count,
        "deterministic": evidence.deterministic,
        "stored_scores_verified": evidence.stored_scores_verified,
        "artifact": artifact,
    }


def run_target_ranking_diagnostic(
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
    selected_source_run = source_run_id or latest_completed_target_supply(repo_root)
    source_run = _source_run(repo_root, selected_source_run)
    source_result = _read_json(source_run / "artifacts/experiment_result.json")
    source_summary = _read_json(source_run / SOURCE_SUMMARY_RELPATH)
    source_diagnostics = _read_json(source_run / SOURCE_DIAGNOSTICS_RELPATH)
    archive = read_candidate_archive(source_run / SOURCE_ARCHIVE_RELPATH)
    source_context = read_replay_context(source_run / SOURCE_CONTEXT_RELPATH)

    if source_result.get("status") != "completed":
        raise ValueError("target-supply source run is not completed")
    if source_summary.get("target_supply_gate_passed") is not True:
        raise ValueError("target-supply source gate did not pass")
    if source_context.payload.get("benchmark_id") != TARGET_BENCHMARK.benchmark_id:
        raise ValueError("target-supply replay context identifies the wrong benchmark")
    if source_diagnostics.get("source_archive_hash") != archive_content_hash(archive):
        raise ValueError("target-supply diagnostics do not bind the combined archive")
    if len(archive.records) != int(source_summary["combined"]["unique_candidates"]):
        raise ValueError("combined target archive count does not match its summary")

    batch = select_candidate_batch(
        archive,
        purpose="replay",
        selection_label="all_target_coordinate_candidates",
        candidate_ids=tuple(record.candidate_id for record in archive.records),
    )
    replay_evaluations = len(batch.candidates) * REPLAY_REPEAT_COUNT
    terminal_evaluations = len(batch.candidates)
    total_budget = replay_evaluations + terminal_evaluations
    spec = ExperimentSpec(
        campaign_id="two_period_overlay",
        experiment_id="target_ranking_diagnostic_v1",
        benchmark_id=TARGET_BENCHMARK.benchmark_id,
        question=(
            "Does the recorded WLI score meaningfully enrich for terminal benchmark proximity "
            "across the complete sixty-four-candidate P13/P17 coordinate surface?"
        ),
        hypothesis=(
            "Higher WLI scores have positive rank association with terminal rune and complete-"
            "word matches, and the score-ranked top subsets are enriched for the strongest "
            "terminal candidates."
        ),
        alternative=(
            "WLI ordering is weak or misleading on P13/P17, so score-only selection can discard "
            "more truth-adjacent candidates even though candidate supply is broad."
        ),
        decision_rule=(
            "Ranking diagnostics always refine. The evidence gate passes only when all sixty-four "
            "candidates replay twice, stored scores verify, and terminal output contains aggregate "
            "ranking diagnostics without candidate-specific truth mappings."
        ),
        wli_mode=WliMode.WITH_WLI,
        truth_policy=TruthPolicy.BENCHMARK_ONLY,
        mechanisms=(FailureMechanism.RANKING, FailureMechanism.EVIDENCE_REPRODUCIBILITY),
        budget_evaluations=total_budget,
        lesson_ids=("CSL-001", "CSL-002", "CSL-004", "CSL-005", "CSL-007"),
    )
    configuration = {
        "source_run_id": selected_source_run,
        "source_archive_artifact": SOURCE_ARCHIVE_RELPATH.as_posix(),
        "source_archive_hash": archive_content_hash(archive),
        "candidate_count": len(batch.candidates),
        "replay_repeat_count": REPLAY_REPEAT_COUNT,
        "top_k_values": list(TOP_K_VALUES),
        "replay_evaluation_budget": replay_evaluations,
        "terminal_evaluation_budget": terminal_evaluations,
        "evaluation_budget_upper_bound": total_budget,
        "candidate_specific_truth_output": False,
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
            batch_artifact = "artifacts/all_candidates_batch.json"
            binding_artifact = "artifacts/all_candidates_binding.json"
            replay_artifact = "artifacts/all_candidates_replay.json"
            write_replay_context(run_dir / context_artifact, context)
            write_candidate_batch(run_dir / batch_artifact, batch)
            binding = CandidateReplayBinding.create(
                campaign_id="two_period_overlay",
                source_run_id=run_dir.name,
                configuration_hash=run.configuration_hash,
                benchmark_id=TARGET_BENCHMARK.benchmark_id,
                context=context,
                batch=batch,
                context_artifact=context_artifact,
                batch_artifact=batch_artifact,
            )
            write_replay_binding(run_dir / binding_artifact, binding)

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
            evidence = replay_candidate_batch(
                batch,
                context,
                binding,
                evaluator=build_replay_evaluator(_evaluator_context(context)),
                mode=ReplayMode.VERIFY,
                decision_score=DECISION_SCORE,
                higher_is_better=True,
                evaluator_configuration={
                    "campaign": "two_period_overlay",
                    "experiment": "target_ranking_diagnostic_v1",
                    "source_run_id": selected_source_run,
                    "binding_id": binding.binding_id,
                    "context_id": context.context_id,
                    "evaluator_provenance": actual_provenance,
                },
                repeat_count=REPLAY_REPEAT_COUNT,
                absolute_tolerance=ABSOLUTE_TOLERANCE,
                relative_tolerance=RELATIVE_TOLERANCE,
            )
            write_candidate_replay(run_dir / replay_artifact, evidence)
            replay_summary = _replay_summary(evidence, replay_artifact)

            # Benchmark truth is opened only after every search-visible artifact and replay
            # record has been finalised.
            search_case, reference = build_rdp_case(TARGET_BENCHMARK)
            if not _ciphertext_matches(
                context.payload.get("ciphertext", ()),
                search_case.ciphertext.astype(int).tolist(),
            ):
                raise ValueError("source replay context ciphertext no longer matches the benchmark")
            true_variables = np.asarray(
                [reference.true_key[index] for index in search_case.free_columns],
                dtype=np.uint8,
            )
            terminal_rows: list[dict[str, Any]] = []
            for record in batch.candidates:
                variables = np.asarray(record.payload["variables"], dtype=np.uint8)
                row = reference_metrics(
                    reference,
                    variables,
                    search_case.particular,
                    search_case.basis,
                )
                row["affine_variable_matches"] = int(
                    np.count_nonzero(variables == true_variables)
                )
                terminal_rows.append(row)
            terminal_summary = aggregate_terminal_ranking(
                batch.candidate_ids,
                [float(record.scores[DECISION_SCORE]) for record in batch.candidates],
                terminal_rows,
            )
            gate_passed = (
                replay_summary["candidate_count"] == len(archive.records)
                and replay_summary["deterministic"] is True
                and replay_summary["stored_scores_verified"] is True
                and terminal_summary["candidate_count"] == len(archive.records)
                and terminal_summary["candidate_specific_truth_emitted"] is False
            )
            run.snapshot(
                label="target_ranking_replay_completed",
                metrics={
                    "source_run_id": selected_source_run,
                    "candidate_count": len(batch.candidates),
                    "replay_deterministic": replay_summary["deterministic"],
                    "stored_scores_verified": replay_summary["stored_scores_verified"],
                    "ranking_diagnostic_gate_passed": gate_passed,
                },
            )
            result_path = run.finish(
                decision=ExperimentDecision.REFINE,
                stop_reason="done",
                result_summary={
                    "source_run_id": selected_source_run,
                    "source_archive_hash": archive_content_hash(archive),
                    "candidate_count": len(batch.candidates),
                    "repeat_count": REPLAY_REPEAT_COUNT,
                    "replay_evaluations": replay_evaluations,
                    "terminal_evaluations": terminal_evaluations,
                    "evaluation_budget_upper_bound": total_budget,
                    "batch_id": batch.batch_id,
                    "binding_id": binding.binding_id,
                    "replay_id": evidence.replay_id,
                    "deterministic": evidence.deterministic,
                    "stored_scores_verified": evidence.stored_scores_verified,
                    "ranking_diagnostic_gate_passed": gate_passed,
                    "source_artifacts": copied,
                    "batch_artifact": batch_artifact,
                    "binding_artifact": binding_artifact,
                    "replay_artifact": replay_artifact,
                },
                reference_evaluation={
                    "aggregate_terminal_ranking": terminal_summary,
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
    run_target_ranking_diagnostic(repo_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
