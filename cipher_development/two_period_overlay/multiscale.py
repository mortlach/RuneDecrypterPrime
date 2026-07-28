from __future__ import annotations

import json
import math
import shutil
import sys
import time
import tracemalloc
from dataclasses import dataclass
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
from cipher_development.shared.replay_binding import CandidateReplayBinding, write_replay_binding
from cipher_development.shared.replay_evidence import ReplayMode, write_candidate_replay
from cipher_development.shared.replay_execution import replay_candidate_batch
from cipher_development.shared.replay_provenance import build_evaluator_provenance
from cipher_development.two_period_overlay.benchmark import build_rdp_case, reference_metrics
from cipher_development.two_period_overlay.config import (
    EXACT_EXTRA_CRIB_BENCHMARKS,
    TARGET_BENCHMARK,
    benchmark_for,
)
from cipher_development.two_period_overlay.review_pack import write_review_pack_after_run
from cipher_development.two_period_overlay.replay import build_replay_evaluator
from cipher_development.two_period_overlay.replay_suite import _evaluator_context, _portable_json
from cipher_development.two_period_overlay.scorer_profiles import (
    B1,
    J1,
    RECORDED_J0,
    S1,
    S2,
    S3,
    SCORER_PANEL,
    effective_family_weights,
    portable_contract,
    weighting_contract_note,
)
from cipher_development.two_period_overlay.target_ranking import (
    _pairwise_concordance,
    _top_k_overlap,
    average_ranks,
    latest_completed_target_supply,
    spearman_rank_correlation,
)

REPLAY_REPEAT_COUNT = 2
ABSOLUTE_TOLERANCE = 1e-12
RELATIVE_TOLERANCE = 1e-12
STATIC_SURFACE_IDS = (
    "alice_308_p05_p13_d04",
    "alice_308_p09_p13_d08",
    "alice_308_p13_p17_d16",
)


@dataclass(frozen=True, slots=True)
class SurfaceSource:
    benchmark_id: str
    source_run_id: str
    source_run: Path
    archive_path: Path
    context_path: Path


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def _campaign_root(repo_root: Path) -> Path:
    return (repo_root.resolve() / "output/cipher_development/two_period_overlay").resolve()


def _latest_completed_coordinate_supply(repo_root: Path) -> str:
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
            experiment.get("experiment_id") == "coordinate_supply_v1"
            and result.get("status") == "completed"
            and result.get("run_id") == run_dir.name
            and summary.get("all_unique_thresholds_met") is True
        ):
            candidates.append(run_dir.name)
    if not candidates:
        raise FileNotFoundError("no completed coordinate_supply_v1 run was found")
    return max(candidates)


def _source_run(repo_root: Path, run_id: str) -> Path:
    if not run_id or run_id in {".", ".."} or "/" in run_id or "\\" in run_id:
        raise ValueError("run ID must be one directory name")
    root = _campaign_root(repo_root)
    run = (root / run_id).resolve()
    if root not in run.parents:
        raise ValueError("run ID escaped the campaign output root")
    return run


def static_surface_sources(repo_root: Path) -> tuple[SurfaceSource, ...]:
    lower_id = _latest_completed_coordinate_supply(repo_root)
    target_id = latest_completed_target_supply(repo_root)
    lower_run = _source_run(repo_root, lower_id)
    target_run = _source_run(repo_root, target_id)
    return (
        SurfaceSource(
            "alice_308_p05_p13_d04",
            lower_id,
            lower_run,
            lower_run / "artifacts/coordinate_supply/alice_308_p05_p13_d04/discovery_pool_archive.json",
            lower_run / "artifacts/replay_contexts/alice_308_p05_p13_d04.json",
        ),
        SurfaceSource(
            "alice_308_p09_p13_d08",
            lower_id,
            lower_run,
            lower_run / "artifacts/coordinate_supply/alice_308_p09_p13_d08/discovery_pool_archive.json",
            lower_run / "artifacts/replay_contexts/alice_308_p09_p13_d08.json",
        ),
        SurfaceSource(
            "alice_308_p13_p17_d16",
            target_id,
            target_run,
            target_run / "artifacts/target_coordinate_supply/combined_pool_archive.json",
            target_run / "artifacts/replay_context.json",
        ),
    )


def _profile_vectors(dimension: int) -> np.ndarray:
    if dimension <= 0:
        raise ValueError("scorer canary requires a positive affine dimension")
    return np.asarray(
        [
            [0 for _ in range(dimension)],
            [(3 * index + 1) % 29 for index in range(dimension)],
            [(7 * index + 5) % 29 for index in range(dimension)],
        ],
        dtype=np.uint8,
    )


def run_scorer_contract_canary(repo_root: Path) -> Path:
    from cipher_development.shared.experiment import (
        ExperimentDecision,
        ExperimentRun,
        ExperimentSpec,
        FailureMechanism,
        TruthPolicy,
        WliMode,
    )

    repo_root = repo_root.resolve()
    contracts = tuple(profile.scoring_contract() for profile in SCORER_PANEL)
    evaluation_budget = len(SCORER_PANEL) * 9
    spec = ExperimentSpec(
        campaign_id="two_period_overlay",
        experiment_id="multiscale_scorer_contract_canary_v1",
        benchmark_id=TARGET_BENCHMARK.benchmark_id,
        question="Do all predeclared WP6 multiscale scorer profiles execute deterministically with the installed assets?",
        hypothesis="Every profile builds, scores a fixed batch twice, agrees with scalar scoring and records exact asset provenance.",
        alternative="At least one profile is unavailable, non-deterministic, scalar/batch inconsistent or bound to incomplete assets.",
        decision_rule="Canaries always refine. Pass only when every predeclared profile executes and all deterministic and scalar/batch checks pass.",
        wli_mode=WliMode.WITH_WLI,
        truth_policy=TruthPolicy.NONE,
        mechanisms=(FailureMechanism.EVIDENCE_REPRODUCIBILITY, FailureMechanism.RANKING),
        budget_evaluations=evaluation_budget,
        lesson_ids=("CSL-004", "CSL-005", "CSL-007"),
    )
    configuration = {
        "profiles": [profile.to_json_dict() for profile in SCORER_PANEL],
        "evaluation_budget_upper_bound": evaluation_budget,
        "weighting_contract_resolution": weighting_contract_note(),
    }

    run_dir: Path | None = None
    result_path: Path | None = None
    try:
        with ExperimentRun(spec=spec, configuration=configuration, repo_root=repo_root) as run:
            assert run.run_dir is not None
            run_dir = run.run_dir
            provenance = build_evaluator_provenance(
                repo_root=repo_root,
                evaluator_source=Path(__file__).with_name("replay.py"),
                scoring_contracts=contracts,
                require_assets=True,
            )
            rows: list[dict[str, Any]] = []
            all_passed = True
            for profile in SCORER_PANEL:
                started = time.perf_counter()
                search_case, _reference = build_rdp_case(
                    TARGET_BENCHMARK,
                    scoring_contract=profile.scoring_contract(),
                )
                vectors = _profile_vectors(len(search_case.free_columns))
                first = np.asarray(search_case.evaluate_variables(vectors), dtype=np.float64)
                second = np.asarray(search_case.evaluate_variables(vectors), dtype=np.float64)
                scalar = np.asarray(
                    [float(search_case.evaluate_variables(row)[0]) for row in vectors],
                    dtype=np.float64,
                )
                deterministic = bool(np.allclose(first, second, atol=ABSOLUTE_TOLERANCE, rtol=RELATIVE_TOLERANCE))
                scalar_batch = bool(np.allclose(first, scalar, atol=ABSOLUTE_TOLERANCE, rtol=RELATIVE_TOLERANCE))
                finite = bool(np.all(np.isfinite(first)))
                passed = deterministic and scalar_batch and finite
                all_passed = all_passed and passed
                rows.append({
                    "profile": profile.to_json_dict(),
                    "scores": first.tolist(),
                    "deterministic": deterministic,
                    "scalar_batch_agreement": scalar_batch,
                    "finite": finite,
                    "elapsed_s": time.perf_counter() - started,
                    "passed": passed,
                })
            artifact = run_dir / "artifacts/scorer_contract_canary.json"
            _write_json(artifact, {
                "schema": "rdp.two_period_overlay.multiscale_scorer_canary.v1",
                "profiles": rows,
                "all_profiles_passed": all_passed,
                "asset_provenance": provenance,
                "weighting_contract_resolution": weighting_contract_note(),
            })
            result_path = run.finish(
                decision=ExperimentDecision.REFINE,
                stop_reason="done" if all_passed else "contract_failure",
                result_summary={
                    "profile_count": len(rows),
                    "profile_ids": [profile.profile_id for profile in SCORER_PANEL],
                    "all_profiles_passed": all_passed,
                    "evaluation_budget_upper_bound": evaluation_budget,
                    "artifact": "artifacts/scorer_contract_canary.json",
                    "recorded_baseline_effective_weights": effective_family_weights(RECORDED_J0.scoring_contract()),
                    "intended_judge_effective_weights": effective_family_weights(J1.scoring_contract()),
                },
            )
    except BaseException as exc:
        if run_dir is not None:
            write_review_pack_after_run(repo_root, run_dir, original_error=exc)
        raise
    assert run_dir is not None and result_path is not None
    write_review_pack_after_run(repo_root, run_dir)
    return result_path


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


def aggregate_profile_diagnostic(
    candidate_ids: Sequence[str],
    scores: Sequence[float],
    terminal_metrics: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    ids = tuple(str(value) for value in candidate_ids)
    score_values = tuple(float(value) for value in scores)
    metrics = tuple(dict(value) for value in terminal_metrics)
    if not ids or len(ids) != len(score_values) or len(ids) != len(metrics):
        raise ValueError("profile diagnostic inputs must be equal-length and non-empty")
    rune = tuple(int(row["rune_matches"]) for row in metrics)
    words = tuple(int(row["complete_word_matches"]) for row in metrics)
    affine = tuple(int(row["affine_variable_matches"]) for row in metrics)
    ranks = average_ranks(score_values, higher_is_better=True)
    best_rune = max(rune)
    best_word = max(words)
    top_index = min(range(len(ids)), key=lambda index: (-score_values[index], ids[index]))
    top_k: dict[str, Any] = {}
    for k in (8, 16, 32):
        if k > len(ids):
            continue
        score_order = sorted(range(len(ids)), key=lambda index: (-score_values[index], ids[index]))[:k]
        top_k[str(k)] = {
            "rune_top_k_overlap_count": _top_k_overlap(ids, score_values, rune, k),
            "complete_word_top_k_overlap_count": _top_k_overlap(ids, score_values, words, k),
            "rune_match_summary": _numeric_summary([rune[index] for index in score_order]),
            "complete_word_match_summary": _numeric_summary([words[index] for index in score_order]),
            "affine_variable_match_summary": _numeric_summary([affine[index] for index in score_order]),
        }
    return {
        "candidate_count": len(ids),
        "candidate_specific_truth_emitted": False,
        "score_summary": _numeric_summary(score_values),
        "rune_match_summary": _numeric_summary(rune),
        "complete_word_match_summary": _numeric_summary(words),
        "affine_variable_match_summary": _numeric_summary(affine),
        "score_vs_rune_spearman": spearman_rank_correlation(score_values, rune),
        "score_vs_complete_word_spearman": spearman_rank_correlation(score_values, words),
        "score_vs_affine_variable_match_spearman": spearman_rank_correlation(score_values, affine),
        "score_vs_rune_pairwise": _pairwise_concordance(score_values, rune),
        "score_vs_complete_word_pairwise": _pairwise_concordance(score_values, words),
        "best_rune_matches": best_rune,
        "best_rune_candidate_score_rank": int(min(math.ceil(ranks[index]) for index, value in enumerate(rune) if value == best_rune)),
        "best_complete_word_matches": best_word,
        "best_complete_word_candidate_score_rank": int(min(math.ceil(ranks[index]) for index, value in enumerate(words) if value == best_word)),
        "top_scored_candidate_terminal": {
            "rune_matches": rune[top_index],
            "complete_word_matches": words[top_index],
            "affine_variable_matches": affine[top_index],
            "exact_plaintext": bool(metrics[top_index]["exact_plaintext"]),
        },
        "exact_plaintext_count": sum(bool(row["exact_plaintext"]) for row in metrics),
        "canonical_key_count": sum(bool(row["canonical_key_equal"]) for row in metrics),
        "combined_shift_count": sum(bool(row["combined_shift_equal"]) for row in metrics),
        "top_k": top_k,
    }


def _ranking_disagreement(rankings: Mapping[str, Sequence[str]]) -> dict[str, Any]:
    ids = sorted(rankings)
    out: dict[str, Any] = {}
    for left_index, left in enumerate(ids):
        left_rank = {candidate_id: index + 1 for index, candidate_id in enumerate(rankings[left])}
        for right in ids[left_index + 1:]:
            right_rank = {candidate_id: index + 1 for index, candidate_id in enumerate(rankings[right])}
            candidates = tuple(rankings[left])
            out[f"{left}__vs__{right}"] = {
                "rank_spearman": spearman_rank_correlation(
                    [left_rank[candidate] for candidate in candidates],
                    [right_rank[candidate] for candidate in candidates],
                    left_higher_is_better=False,
                    right_higher_is_better=False,
                ),
                "top8_overlap": len(set(rankings[left][:8]) & set(rankings[right][:8])),
                "top16_overlap": len(set(rankings[left][:16]) & set(rankings[right][:16])),
            }
    return out


def _score_only_candidate_signals(
    rankings: Mapping[str, Sequence[str]],
) -> dict[str, list[str]]:
    required = (RECORDED_J0, S1, S2, S3, B1, J1)
    missing = [profile.profile_id for profile in required if profile.profile_id not in rankings]
    if missing:
        raise ValueError(f"candidate-signal rankings are missing profiles: {missing}")
    candidate_set = set(rankings[required[0].profile_id])
    if not candidate_set or any(set(rankings[profile.profile_id]) != candidate_set for profile in required[1:]):
        raise ValueError("candidate-signal rankings must cover one identical non-empty candidate set")
    positions = {
        profile.profile_id: {candidate_id: index + 1 for index, candidate_id in enumerate(rankings[profile.profile_id])}
        for profile in required
    }

    def ordered(predicate) -> list[str]:
        return sorted(
            (candidate_id for candidate_id in candidate_set if predicate(candidate_id)),
            key=lambda candidate_id: (
                min(positions[S1.profile_id][candidate_id], positions[S2.profile_id][candidate_id], positions[S3.profile_id][candidate_id]),
                candidate_id,
            ),
        )

    return {
        # Score-only signals are frozen before terminal metrics are opened.
        "low_order_rescued_from_recorded_j0": ordered(
            lambda candidate_id: min(
                positions[S1.profile_id][candidate_id],
                positions[S2.profile_id][candidate_id],
                positions[S3.profile_id][candidate_id],
            ) <= 8
            and positions[RECORDED_J0.profile_id][candidate_id] > 16
        ),
        "bridge_top8_dropped_by_j1": ordered(
            lambda candidate_id: positions[B1.profile_id][candidate_id] <= 8
            and positions[J1.profile_id][candidate_id] > 16
        ),
        "wli12_favoured_over_char12": ordered(
            lambda candidate_id: positions[S2.profile_id][candidate_id] <= 8
            and positions[S1.profile_id][candidate_id] > 16
        ),
        "char12_favoured_over_wli12": ordered(
            lambda candidate_id: positions[S1.profile_id][candidate_id] <= 8
            and positions[S2.profile_id][candidate_id] > 16
        ),
    }


def _aggregate_signal_terminal(
    candidate_ids: Sequence[str],
    terminal_metrics: Sequence[Mapping[str, Any]],
    signals: Mapping[str, Sequence[str]],
) -> dict[str, Any]:
    index = {str(candidate_id): position for position, candidate_id in enumerate(candidate_ids)}
    if len(index) != len(candidate_ids) or len(candidate_ids) != len(terminal_metrics):
        raise ValueError("terminal signal inputs must align to unique candidate IDs")
    out: dict[str, Any] = {}
    for label, selected_ids in signals.items():
        selected = [index[str(candidate_id)] for candidate_id in selected_ids]
        if not selected:
            out[str(label)] = {"candidate_count": 0}
            continue
        rows = [terminal_metrics[position] for position in selected]
        out[str(label)] = {
            "candidate_count": len(rows),
            "rune_match_summary": _numeric_summary([int(row["rune_matches"]) for row in rows]),
            "complete_word_match_summary": _numeric_summary(
                [int(row["complete_word_matches"]) for row in rows]
            ),
            "affine_variable_match_summary": _numeric_summary(
                [int(row["affine_variable_matches"]) for row in rows]
            ),
            "exact_plaintext_count": sum(bool(row["exact_plaintext"]) for row in rows),
        }
    return out


def run_multiscale_static_panel(repo_root: Path) -> Path:
    from cipher_development.shared.experiment import (
        ExperimentDecision,
        ExperimentRun,
        ExperimentSpec,
        FailureMechanism,
        TruthPolicy,
        WliMode,
    )

    repo_root = repo_root.resolve()
    sources = static_surface_sources(repo_root)
    contracts = tuple(profile.scoring_contract() for profile in SCORER_PANEL)
    candidate_total = sum(len(read_candidate_archive(source.archive_path).records) for source in sources)
    replay_budget = candidate_total * len(SCORER_PANEL) * REPLAY_REPEAT_COUNT
    terminal_budget = candidate_total
    evaluation_budget = replay_budget + terminal_budget
    spec = ExperimentSpec(
        campaign_id="two_period_overlay",
        experiment_id="multiscale_static_panel_v1",
        benchmark_id="wp6_saved_d04_d08_d16_surfaces",
        question="Which predeclared character/WLI n-gram profiles best rank the saved d4, d8 and d16 candidate surfaces?",
        hypothesis="At least one low-to-medium order profile improves truth-adjacent enrichment over the recorded high-order baseline on more than one surface.",
        alternative="The panel is no more informative than the recorded baseline, or profile rankings are unstable or surface-specific.",
        decision_rule="Static panels always refine. Freeze no ladder here; report deterministic reranks, aggregate terminal diagnostics, cost and held-surface disagreement for the matched d8 pilot.",
        wli_mode=WliMode.WITH_WLI,
        truth_policy=TruthPolicy.BENCHMARK_ONLY,
        mechanisms=(FailureMechanism.RANKING, FailureMechanism.EVIDENCE_REPRODUCIBILITY),
        budget_evaluations=evaluation_budget,
        lesson_ids=("CSL-004", "CSL-005", "CSL-007"),
    )
    configuration = {
        "surface_ids": list(STATIC_SURFACE_IDS),
        "profiles": [profile.to_json_dict() for profile in SCORER_PANEL],
        "repeat_count": REPLAY_REPEAT_COUNT,
        "replay_evaluation_budget": replay_budget,
        "terminal_evaluation_budget": terminal_budget,
        "evaluation_budget_upper_bound": evaluation_budget,
        "candidate_specific_truth_output": False,
        "weighting_contract_resolution": weighting_contract_note(),
    }

    run_dir: Path | None = None
    result_path: Path | None = None
    try:
        with ExperimentRun(spec=spec, configuration=configuration, repo_root=repo_root) as run:
            assert run.run_dir is not None
            run_dir = run.run_dir
            provenance = build_evaluator_provenance(
                repo_root=repo_root,
                evaluator_source=Path(__file__).with_name("replay.py"),
                scoring_contracts=contracts,
                require_assets=True,
            )
            performance_summary: dict[str, Any] = {}
            aggregate_reference: dict[str, Any] = {}
            all_deterministic = True
            surface_states: dict[str, dict[str, Any]] = {}

            # Pass 1: finish every search-visible rerank and score-only signal on
            # every surface before any benchmark truth is opened.
            for source in sources:
                benchmark = benchmark_for(source.benchmark_id)
                archive = read_candidate_archive(source.archive_path)
                source_context = read_replay_context(source.context_path)
                if source_context.payload.get("benchmark_id") != benchmark.benchmark_id:
                    raise ValueError("source replay context identifies the wrong benchmark")
                surface_root = run_dir / "artifacts/multiscale_static" / benchmark.benchmark_id
                surface_root.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source.archive_path, surface_root / "source_archive.json")
                shutil.copyfile(source.context_path, surface_root / "source_replay_context.json")
                batch = select_candidate_batch(
                    archive,
                    purpose="replay",
                    selection_label=f"all_saved_candidates__{benchmark.benchmark_id}",
                    candidate_ids=tuple(record.candidate_id for record in archive.records),
                )
                batch_rel = f"artifacts/multiscale_static/{benchmark.benchmark_id}/all_candidates_batch.json"
                write_candidate_batch(run_dir / batch_rel, batch)
                surface_rows: dict[str, Any] = {}
                rankings: dict[str, Sequence[str]] = {}
                evidence_by_profile: dict[str, Any] = {}
                for profile in SCORER_PANEL:
                    profile_root = surface_root / profile.profile_id
                    profile_root.mkdir(parents=True, exist_ok=True)
                    payload = dict(source_context.payload)
                    payload["scoring"] = portable_contract(profile.scoring_contract())
                    payload["decision_score"] = profile.score_name
                    payload["evaluator_provenance"] = _portable_json(provenance)
                    context = CandidateReplayContext.create(
                        campaign_id="two_period_overlay",
                        run_id=run_dir.name,
                        configuration_hash=run.configuration_hash,
                        evaluator_id=f"two_period_overlay_{profile.profile_id}_v1",
                        payload=payload,
                    )
                    context_rel = f"artifacts/multiscale_static/{benchmark.benchmark_id}/{profile.profile_id}/replay_context.json"
                    binding_rel = f"artifacts/multiscale_static/{benchmark.benchmark_id}/{profile.profile_id}/binding.json"
                    replay_rel = f"artifacts/multiscale_static/{benchmark.benchmark_id}/{profile.profile_id}/rerank.json"
                    write_replay_context(run_dir / context_rel, context)
                    binding = CandidateReplayBinding.create(
                        campaign_id="two_period_overlay",
                        source_run_id=run_dir.name,
                        configuration_hash=run.configuration_hash,
                        benchmark_id=benchmark.benchmark_id,
                        context=context,
                        batch=batch,
                        context_artifact=context_rel,
                        batch_artifact=batch_rel,
                    )
                    write_replay_binding(run_dir / binding_rel, binding)
                    tracemalloc.start()
                    started = time.perf_counter()
                    evidence = replay_candidate_batch(
                        batch,
                        context,
                        binding,
                        evaluator=build_replay_evaluator(_evaluator_context(context)),
                        mode=ReplayMode.RERANK,
                        decision_score=profile.score_name,
                        higher_is_better=True,
                        evaluator_configuration={
                            "experiment": "multiscale_static_panel_v1",
                            "benchmark_id": benchmark.benchmark_id,
                            "profile": profile.to_json_dict(),
                            "evaluator_provenance": provenance,
                        },
                        repeat_count=REPLAY_REPEAT_COUNT,
                        absolute_tolerance=ABSOLUTE_TOLERANCE,
                        relative_tolerance=RELATIVE_TOLERANCE,
                    )
                    elapsed = time.perf_counter() - started
                    _current, peak = tracemalloc.get_traced_memory()
                    tracemalloc.stop()
                    write_candidate_replay(run_dir / replay_rel, evidence)
                    rankings[profile.profile_id] = evidence.ranking
                    evidence_by_profile[profile.profile_id] = evidence
                    all_deterministic = all_deterministic and evidence.deterministic
                    surface_rows[profile.profile_id] = {
                        "profile": profile.to_json_dict(),
                        "context_id": context.context_id,
                        "binding_id": binding.binding_id,
                        "replay_id": evidence.replay_id,
                        "deterministic": evidence.deterministic,
                        "candidate_count": len(evidence.candidate_ids),
                        "elapsed_s": elapsed,
                        "candidate_evaluations_per_s": (len(evidence.candidate_ids) * REPLAY_REPEAT_COUNT) / elapsed,
                        "python_peak_allocated_bytes": peak,
                        "artifacts": {
                            "context": context_rel,
                            "binding": binding_rel,
                            "rerank": replay_rel,
                        },
                    }

                signals = _score_only_candidate_signals(rankings)
                performance_summary[benchmark.benchmark_id] = {
                    "source_run_id": source.source_run_id,
                    "source_archive_hash": archive_content_hash(archive),
                    "candidate_count": len(batch.candidates),
                    "batch_id": batch.batch_id,
                    "batch_artifact": batch_rel,
                    "profiles": surface_rows,
                    "profile_ranking_disagreement": _ranking_disagreement(rankings),
                    "score_only_candidate_signals": signals,
                    "signal_definitions": {
                        "top_band": 8,
                        "outside_band": 16,
                        "terminal_metrics_used_for_signal_selection": False,
                    },
                }
                surface_states[benchmark.benchmark_id] = {
                    "benchmark": benchmark,
                    "batch": batch,
                    "evidence_by_profile": evidence_by_profile,
                    "signals": signals,
                }

            # Pass 2: all search-visible contexts, bindings, reranks, rankings and
            # candidate signals are now frozen. Terminal truth cannot influence
            # any later search-visible work in this run.
            for benchmark_id in STATIC_SURFACE_IDS:
                state = surface_states[benchmark_id]
                benchmark = state["benchmark"]
                batch = state["batch"]
                evidence_by_profile = state["evidence_by_profile"]
                signals = state["signals"]
                search_case, reference = build_rdp_case(
                    benchmark,
                    scoring_contract=RECORDED_J0.scoring_contract(),
                )
                true_variables = np.asarray(
                    [reference.true_key[index] for index in search_case.free_columns],
                    dtype=np.uint8,
                )
                terminal_rows: list[dict[str, Any]] = []
                for record in batch.candidates:
                    variables = np.asarray(record.payload["variables"], dtype=np.uint8)
                    row = reference_metrics(
                        reference, variables, search_case.particular, search_case.basis
                    )
                    row["affine_variable_matches"] = int(
                        np.count_nonzero(variables == true_variables)
                    )
                    terminal_rows.append(row)
                aggregate_reference[benchmark_id] = {
                    "profiles": {
                        profile.profile_id: aggregate_profile_diagnostic(
                            batch.candidate_ids,
                            [
                                float(observation.observed_scores[profile.score_name])
                                for observation in evidence_by_profile[profile.profile_id].observations
                            ],
                            terminal_rows,
                        )
                        for profile in SCORER_PANEL
                    },
                    "score_only_signal_terminal_diagnostics": _aggregate_signal_terminal(
                        batch.candidate_ids, terminal_rows, signals
                    ),
                }

            summary_artifact = run_dir / "artifacts/static_panel_summary.json"
            _write_json(summary_artifact, {
                "schema": "rdp.two_period_overlay.multiscale_static_panel.v1",
                "surface_ids": list(STATIC_SURFACE_IDS),
                "profile_ids": [profile.profile_id for profile in SCORER_PANEL],
                "all_deterministic": all_deterministic,
                "surfaces": performance_summary,
                "weighting_contract_resolution": weighting_contract_note(),
                "perturbation_shell_status": "explicitly queued for Pack 02 with the matched d8 pilot; not dropped",
            })
            result_path = run.finish(
                decision=ExperimentDecision.REFINE,
                stop_reason="done" if all_deterministic else "non_deterministic",
                result_summary={
                    "surface_count": len(sources),
                    "surface_ids": list(STATIC_SURFACE_IDS),
                    "profile_count": len(SCORER_PANEL),
                    "profile_ids": [profile.profile_id for profile in SCORER_PANEL],
                    "candidate_count": candidate_total,
                    "replay_evaluations": replay_budget,
                    "terminal_evaluations": terminal_budget,
                    "evaluation_budget_upper_bound": evaluation_budget,
                    "all_deterministic": all_deterministic,
                    "static_panel_gate_passed": all_deterministic,
                    "artifact": "artifacts/static_panel_summary.json",
                    "surfaces": performance_summary,
                },
                reference_evaluation={
                    "aggregate_profile_diagnostics": aggregate_reference,
                    "candidate_specific_truth_emitted": False,
                },
            )
    except BaseException as exc:
        if run_dir is not None:
            write_review_pack_after_run(repo_root, run_dir, original_error=exc)
        raise
    assert run_dir is not None and result_path is not None
    write_review_pack_after_run(repo_root, run_dir)
    return result_path


def run_exact_extra_crib_contract_canary(repo_root: Path) -> Path:
    from cipher_development.shared.experiment import (
        ExperimentDecision,
        ExperimentRun,
        ExperimentSpec,
        FailureMechanism,
        TruthPolicy,
        WliMode,
    )

    repo_root = repo_root.resolve()
    spec = ExperimentSpec(
        campaign_id="two_period_overlay",
        experiment_id="exact_extra_crib_contract_canary_v1",
        benchmark_id="alice_308_p13_p17_exact_extra_crib_d08",
        question="Do the offset-206 primary and offset-81 confirmation complete-word cribs each reduce the frozen P13/P17 d16 space to d8?",
        hypothesis="Each declared eight-rune dormouse crib adds rank eight, preserves the gauge and reconstructs the exact benchmark key.",
        alternative="At least one position has a different modular rank, conflicts with the primary crib or fails exact reconstruction.",
        decision_rule="Canaries always refine. Pass only when both independently declared d8 contracts derive dimension eight and reconstruct the exact key.",
        wli_mode=WliMode.WITH_WLI,
        truth_policy=TruthPolicy.BENCHMARK_ONLY,
        mechanisms=(FailureMechanism.CANDIDATE_SUPPLY, FailureMechanism.EVIDENCE_REPRODUCIBILITY),
        budget_evaluations=2,
        lesson_ids=("CSL-004", "CSL-005"),
    )
    configuration = {
        "benchmarks": [benchmark.to_json_dict() for benchmark in EXACT_EXTRA_CRIB_BENCHMARKS],
        "declared_oracle_assistance": True,
        "normal_search_performed": False,
    }

    run_dir: Path | None = None
    result_path: Path | None = None
    try:
        with ExperimentRun(spec=spec, configuration=configuration, repo_root=repo_root) as run:
            assert run.run_dir is not None
            run_dir = run.run_dir
            rows: list[dict[str, Any]] = []
            all_passed = True
            for benchmark in EXACT_EXTRA_CRIB_BENCHMARKS:
                search_case, reference = build_rdp_case(
                    benchmark,
                    scoring_contract=J1.scoring_contract(),
                )
                true_variables = np.asarray(
                    [reference.true_key[index] for index in search_case.free_columns],
                    dtype=np.uint8,
                )
                from cipher_development.two_period_overlay.keyspace import expand
                rebuilt = expand(true_variables, search_case.particular, search_case.basis, benchmark)
                passed = (
                    len(search_case.free_columns) == 8
                    and search_case.basis.shape == (benchmark.key_length, 8)
                    and np.array_equal(rebuilt, reference.true_key)
                    and int(rebuilt[benchmark.gauge_key_index]) == benchmark.gauge_value
                )
                all_passed = all_passed and passed
                rows.append({
                    "benchmark": benchmark.to_json_dict(),
                    "base_dimension": TARGET_BENCHMARK.expected_free_dimension,
                    "added_rank": TARGET_BENCHMARK.expected_free_dimension - len(search_case.free_columns),
                    "resulting_dimension": len(search_case.free_columns),
                    "basis_shape": list(search_case.basis.shape),
                    "gauge_valid": int(rebuilt[benchmark.gauge_key_index]) == benchmark.gauge_value,
                    "exact_key_reconstructed": bool(np.array_equal(rebuilt, reference.true_key)),
                    "passed": passed,
                })
            artifact = run_dir / "artifacts/exact_extra_crib_contracts.json"
            _write_json(artifact, {
                "schema": "rdp.two_period_overlay.exact_extra_crib_contracts.v1",
                "contracts": rows,
                "all_contracts_passed": all_passed,
                "normal_search_performed": False,
            })
            result_path = run.finish(
                decision=ExperimentDecision.REFINE,
                stop_reason="done" if all_passed else "contract_failure",
                result_summary={
                    "benchmark_count": len(rows),
                    "benchmark_ids": [benchmark.benchmark_id for benchmark in EXACT_EXTRA_CRIB_BENCHMARKS],
                    "all_contracts_passed": all_passed,
                    "artifact": "artifacts/exact_extra_crib_contracts.json",
                },
                reference_evaluation={
                    "declared_extra_crib_contracts": rows,
                },
            )
    except BaseException as exc:
        if run_dir is not None:
            write_review_pack_after_run(repo_root, run_dir, original_error=exc)
        raise
    assert run_dir is not None and result_path is not None
    write_review_pack_after_run(repo_root, run_dir)
    return result_path


__all__ = [
    "STATIC_SURFACE_IDS",
    "_aggregate_signal_terminal",
    "_score_only_candidate_signals",
    "aggregate_profile_diagnostic",
    "run_exact_extra_crib_contract_canary",
    "run_multiscale_static_panel",
    "run_scorer_contract_canary",
    "static_surface_sources",
]
