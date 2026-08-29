from __future__ import annotations

"Search, archive, and replay helpers retained solely for Pack 09."
import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
import numpy as np
from cipher_development.shared.archive import (
    ArchivePolicy,
    CandidateArchive,
    CandidateProvenance,
    CandidateRecord,
    archive_content_hash,
    candidate_id_for,
    write_candidate_archive,
)
from cipher_development.shared.replay import (
    CandidateReplayContext,
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
from cipher_development.two_period_overlay.benchmark import reference_metrics
from cipher_development.two_period_overlay.config import BenchmarkSpec, MASTER_SEED
from cipher_development.two_period_overlay.keyspace import coordinate_search, expand
from cipher_development.two_period_overlay.scorer_profiles import ScorerProfile

STAGE_SWEEPS = {"S2": 5}
STAGE_SAFETY_SECONDS = 4.0 * 60.0 * 60.0
REPLAY_REPEAT_COUNT = 2
ABSOLUTE_TOLERANCE = 1e-12
RELATIVE_TOLERANCE = 1e-12


def _numeric_summary(values: Sequence[int | float]) -> dict[str, float]:
    array = np.asarray(tuple((float(value) for value in values)), dtype=np.float64)
    if array.size == 0:
        return {
            "minimum": 0.0,
            "q25": 0.0,
            "median": 0.0,
            "q75": 0.0,
            "maximum": 0.0,
            "mean": 0.0,
        }
    return {
        "minimum": float(np.min(array)),
        "q25": float(np.quantile(array, 0.25)),
        "median": float(np.median(array)),
        "q75": float(np.quantile(array, 0.75)),
        "maximum": float(np.max(array)),
        "mean": float(np.mean(array)),
    }


@dataclass(frozen=True, slots=True)
class StageOutcome:
    stage_id: str
    profile: ScorerProfile
    sweeps_requested: int
    input_count: int
    archive: CandidateArchive
    attempt_rows: tuple[Mapping[str, Any], ...]
    generated_candidates: int
    unique_candidates: int
    duplicate_candidates: int
    evaluations: int
    elapsed_s: float

    def to_search_summary(self) -> dict[str, Any]:
        attempt_elapsed = [float(row["elapsed_s"]) for row in self.attempt_rows]
        attempt_rates = [
            float(row["candidate_evaluations_per_s"]) for row in self.attempt_rows
        ]
        score_gains = [float(row["score_gain"]) for row in self.attempt_rows]
        changed = sum((bool(row["candidate_changed"]) for row in self.attempt_rows))
        return {
            "stage_id": self.stage_id,
            "profile_id": self.profile.profile_id,
            "sweeps_requested": self.sweeps_requested,
            "input_count": self.input_count,
            "attempt_count": len(self.attempt_rows),
            "generated_candidates": self.generated_candidates,
            "unique_candidates": self.unique_candidates,
            "duplicate_candidates": self.duplicate_candidates,
            "duplicate_rate": self.duplicate_candidates / self.generated_candidates
            if self.generated_candidates
            else 0.0,
            "changed_candidate_count": changed,
            "unchanged_candidate_count": len(self.attempt_rows) - changed,
            "evaluations": self.evaluations,
            "elapsed_s": self.elapsed_s,
            "candidate_evaluations_per_s": self.evaluations / self.elapsed_s,
            "attempt_elapsed_s_summary": _numeric_summary(attempt_elapsed),
            "attempt_candidate_evaluations_per_s_summary": _numeric_summary(
                attempt_rates
            ),
            "score_gain_summary": _numeric_summary(score_gains),
            "archive_hash": archive_content_hash(self.archive),
        }


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            dict(payload), ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


def stage_seed(stage_id: str, candidate_token: str) -> int:
    if not stage_id or not candidate_token:
        raise ValueError("stage_id and candidate_token must be non-empty")
    payload = f"{MASTER_SEED}:wp6-pack02b:{stage_id}:{candidate_token}".encode("utf-8")
    return int.from_bytes(
        hashlib.blake2b(payload, digest_size=8, person=b"rdp-wp6-02b").digest(), "big"
    )


def _archive_policy(profile: ScorerProfile, capacity: int) -> ArchivePolicy:
    return ArchivePolicy(
        capacity=capacity,
        decision_score=profile.score_name,
        higher_is_better=True,
        family_limit=None,
    )


def _candidate_record(
    variables: np.ndarray,
    score: float,
    search_case: Any,
    profile: ScorerProfile,
    *,
    stage_id: str,
    evaluation_index: int,
    parent: CandidateRecord | None,
    details: Mapping[str, Any],
    benchmark: BenchmarkSpec,
    provenance_source: str = "staged_d8_handoff",
    provenance_operation: str = "coordinate_descent",
    family_id: str | None = None,
) -> CandidateRecord:
    values = np.asarray(variables, dtype=np.uint8)
    expanded = expand(values, search_case.particular, search_case.basis, benchmark)
    identity = {"expanded_key": expanded.astype(int).tolist()}
    candidate_id = candidate_id_for(identity)
    inherited_scores = {} if parent is None else dict(parent.scores)
    inherited_scores[profile.score_name] = float(score)
    parent_id = None if parent is None else parent.candidate_id
    parent_ids = (
        (parent_id,) if parent_id is not None and parent_id != candidate_id else ()
    )
    provenance_details = {
        "stage_id": stage_id,
        "profile_id": profile.profile_id,
        "parent_candidate_id": parent_id,
        **dict(details),
    }
    return CandidateRecord(
        candidate_id=candidate_id,
        identity=identity,
        payload={
            "variables": values.astype(int).tolist(),
            "expanded_key": expanded.astype(int).tolist(),
            "benchmark_id": benchmark.benchmark_id,
        },
        scores=inherited_scores,
        provenance=CandidateProvenance(
            source=provenance_source,
            operation=provenance_operation,
            parent_ids=parent_ids,
            evaluation_index=evaluation_index,
            details=provenance_details,
        ),
        family_id=parent.family_id if parent is not None else family_id,
    )


def _run_stage(
    *,
    stage_id: str,
    profile: ScorerProfile,
    search_case: Any,
    inputs: Sequence[CandidateRecord | Mapping[str, Any]],
    sweeps: int,
    benchmark: BenchmarkSpec,
    seed_factory: Callable[[str, str], int] = stage_seed,
    archive_capacity: int | None = None,
    stage_safety_seconds: float = STAGE_SAFETY_SECONDS,
    provenance_source: str = "staged_d8_handoff",
    provenance_operation: str = "coordinate_descent",
    family_id: str | None = None,
) -> StageOutcome:
    if not inputs:
        raise ValueError(f"{stage_id} inputs must not be empty")
    if sweeps <= 0:
        raise ValueError("sweeps must be positive")
    capacity = len(inputs) if archive_capacity is None else int(archive_capacity)
    if capacity <= 0:
        raise ValueError("archive_capacity must be positive")
    if stage_safety_seconds <= 0.0:
        raise ValueError("stage_safety_seconds must be positive")
    archive = CandidateArchive(_archive_policy(profile, capacity))
    attempt_rows: list[dict[str, Any]] = []
    generated_ids: set[str] = set()
    evaluations = 0
    stage_started = time.perf_counter()
    deadline = time.monotonic() + stage_safety_seconds
    for input_index, source in enumerate(inputs):
        if isinstance(source, CandidateRecord):
            parent = source
            start_variables = np.asarray(source.payload["variables"], dtype=np.uint8)
            token = source.candidate_id
            source_candidate_id = source.candidate_id
            source_label = "candidate"
        else:
            parent = None
            start_variables = np.asarray(source["variables"], dtype=np.uint8)
            token = f"restart-{int(source['restart_index'])}-seed-{int(source['seed'])}"
            source_candidate_id = None
            source_label = "deterministic_restart"
        seed = seed_factory(stage_id, token)
        rng = np.random.default_rng(seed)
        start_score = float(search_case.evaluate_variables(start_variables)[0])
        attempt_started = time.perf_counter()
        ending, final_score, used = coordinate_search(
            search_case.evaluate_variables,
            rng,
            start_variables,
            sweeps,
            deadline=deadline,
        )
        attempt_elapsed = time.perf_counter() - attempt_started
        attempt_evaluations = 1 + used
        evaluations += attempt_evaluations
        changed = not np.array_equal(start_variables, ending)
        record = _candidate_record(
            ending,
            final_score,
            search_case,
            profile,
            stage_id=stage_id,
            evaluation_index=evaluations,
            parent=parent,
            benchmark=benchmark,
            provenance_source=provenance_source,
            provenance_operation=provenance_operation,
            family_id=family_id,
            details={
                "input_index": input_index,
                "input_kind": source_label,
                "seed": seed,
                "starting_variables": start_variables.astype(int).tolist(),
                "ending_variables": ending.astype(int).tolist(),
                "start_score": start_score,
                "final_score": float(final_score),
                "score_gain": float(final_score - start_score),
                "sweeps_requested": sweeps,
                "evaluations_used": attempt_evaluations,
                "elapsed_s": attempt_elapsed,
                "candidate_evaluations_per_s": attempt_evaluations / attempt_elapsed,
                "candidate_changed": changed,
            },
        )
        generated_ids.add(record.candidate_id)
        offer = archive.offer(record)
        attempt_rows.append(
            {
                "stage_id": stage_id,
                "profile_id": profile.profile_id,
                "input_index": input_index,
                "input_kind": source_label,
                "source_candidate_id": source_candidate_id,
                "seed": seed,
                "starting_variables": start_variables.astype(int).tolist(),
                "ending_variables": ending.astype(int).tolist(),
                "start_score": start_score,
                "final_score": float(final_score),
                "score_gain": float(final_score - start_score),
                "sweeps_requested": sweeps,
                "evaluations_used": attempt_evaluations,
                "elapsed_s": attempt_elapsed,
                "candidate_evaluations_per_s": attempt_evaluations / attempt_elapsed,
                "candidate_changed": changed,
                "candidate_id": record.candidate_id,
                "archive_offer_action": offer.action.value,
                "archive_retained": offer.retained,
            }
        )
    elapsed = time.perf_counter() - stage_started
    return StageOutcome(
        stage_id=stage_id,
        profile=profile,
        sweeps_requested=sweeps,
        input_count=len(inputs),
        archive=archive,
        attempt_rows=tuple(attempt_rows),
        generated_candidates=len(attempt_rows),
        unique_candidates=len(generated_ids),
        duplicate_candidates=len(attempt_rows) - len(generated_ids),
        evaluations=evaluations,
        elapsed_s=elapsed,
    )


def _rescore_final_union(
    records: Sequence[CandidateRecord],
    search_case: Any,
    profile: ScorerProfile,
    first_stage: Mapping[str, str],
    *,
    archive_capacity: int | None = None,
    provenance_source: str = "staged_d8_handoff",
    provenance_operation: str = "final_judge_rescore",
) -> tuple[CandidateArchive, float, int]:
    capacity = len(records) if archive_capacity is None else int(archive_capacity)
    if capacity <= 0:
        raise ValueError("archive_capacity must be positive")
    archive = CandidateArchive(_archive_policy(profile, capacity))
    started = time.perf_counter()
    evaluations = 0
    for index, source in enumerate(records):
        variables = np.asarray(source.payload["variables"], dtype=np.uint8)
        score = float(search_case.evaluate_variables(variables)[0])
        evaluations += 1
        merged_scores = dict(source.scores)
        merged_scores[profile.score_name] = score
        archive.offer(
            CandidateRecord(
                candidate_id=source.candidate_id,
                identity=source.identity,
                payload=source.payload,
                scores=merged_scores,
                provenance=CandidateProvenance(
                    source=provenance_source,
                    operation=provenance_operation,
                    parent_ids=(),
                    evaluation_index=index + 1,
                    details={
                        "profile_id": profile.profile_id,
                        "first_stage": first_stage[source.candidate_id],
                        "source_candidate_id": source.candidate_id,
                    },
                ),
                family_id=source.family_id,
            )
        )
    return (archive, time.perf_counter() - started, evaluations)


def _write_stage_and_replay(
    *,
    run_dir: Path,
    run: Any,
    stage: StageOutcome,
    search_case: Any,
    evaluator_provenance: Mapping[str, Any],
    artifact_root: Path,
    experiment_id: str,
    benchmark: BenchmarkSpec,
    selection_purpose: str = "handoff",
    selection_label: str | None = None,
    evaluator_id: str | None = None,
) -> dict[str, Any]:
    from cipher_development.two_period_overlay.replay import (
        build_replay_evaluator,
        make_replay_context,
    )

    root = artifact_root / stage.stage_id
    archive_rel = root / "candidate_archive.json"
    attempts_rel = root / "attempts.json"
    batch_rel = root / "handoff_batch.json"
    context_rel = root / "replay_context.json"
    binding_rel = root / "replay_binding.json"
    replay_rel = root / "replay_evidence.json"
    write_candidate_archive(run_dir / archive_rel, stage.archive)
    _write_json(
        run_dir / attempts_rel,
        {
            "schema": "rdp.two_period_overlay.staged_attempts.v1",
            "stage_id": stage.stage_id,
            "profile_id": stage.profile.profile_id,
            "rows": list(stage.attempt_rows),
        },
    )
    batch = select_candidate_batch(
        stage.archive,
        purpose=selection_purpose,
        selection_label=selection_label or f"{stage.stage_id}__all",
        candidate_ids=tuple((record.candidate_id for record in stage.archive.records)),
    )
    write_candidate_batch(run_dir / batch_rel, batch)
    context: CandidateReplayContext = make_replay_context(
        search_case,
        run_id=run_dir.name,
        configuration_hash=run.configuration_hash,
        evaluator_provenance=evaluator_provenance,
        scoring_contract=stage.profile.scoring_contract(),
        decision_score=stage.profile.score_name,
        evaluator_id=evaluator_id
        or f"two_period_overlay_{stage.stage_id}_{stage.profile.profile_id}_v1",
    )
    write_replay_context(run_dir / context_rel, context)
    binding = CandidateReplayBinding.create(
        campaign_id="two_period_overlay",
        source_run_id=run_dir.name,
        configuration_hash=run.configuration_hash,
        benchmark_id=benchmark.benchmark_id,
        context=context,
        batch=batch,
        context_artifact=context_rel.as_posix(),
        batch_artifact=batch_rel.as_posix(),
    )
    write_replay_binding(run_dir / binding_rel, binding)
    replay = replay_candidate_batch(
        batch,
        context,
        binding,
        evaluator=build_replay_evaluator(context),
        mode=ReplayMode.VERIFY,
        decision_score=stage.profile.score_name,
        higher_is_better=True,
        evaluator_configuration={
            "experiment": experiment_id,
            "stage_id": stage.stage_id,
            "profile": stage.profile.to_json_dict(),
            "evaluator_provenance": dict(evaluator_provenance),
        },
        repeat_count=REPLAY_REPEAT_COUNT,
        absolute_tolerance=ABSOLUTE_TOLERANCE,
        relative_tolerance=RELATIVE_TOLERANCE,
    )
    write_candidate_replay(run_dir / replay_rel, replay)
    return {
        **stage.to_search_summary(),
        "replay_deterministic": replay.deterministic,
        "replay_stored_scores_verified": replay.stored_scores_verified,
        "artifacts": {
            "archive": archive_rel.as_posix(),
            "attempts": attempts_rel.as_posix(),
            "batch": batch_rel.as_posix(),
            "context": context_rel.as_posix(),
            "binding": binding_rel.as_posix(),
            "replay": replay_rel.as_posix(),
        },
    }


def _write_final_union_and_replay(
    *,
    run_dir: Path,
    run: Any,
    archive: CandidateArchive,
    search_case: Any,
    profile: ScorerProfile,
    evaluator_provenance: Mapping[str, Any],
    artifact_root: Path,
    experiment_id: str,
    benchmark: BenchmarkSpec,
    selection_label: str = "final_union__all",
    evaluator_id: str = "two_period_overlay_final_union_f1_v1",
) -> dict[str, Any]:
    from cipher_development.two_period_overlay.replay import (
        build_replay_evaluator,
        make_replay_context,
    )

    root = artifact_root / "final_union"
    archive_rel = root / "candidate_archive.json"
    batch_rel = root / "replay_batch.json"
    context_rel = root / "replay_context.json"
    binding_rel = root / "replay_binding.json"
    replay_rel = root / "replay_evidence.json"
    write_candidate_archive(run_dir / archive_rel, archive)
    batch = select_candidate_batch(
        archive,
        purpose="replay",
        selection_label=selection_label,
        candidate_ids=tuple((record.candidate_id for record in archive.records)),
    )
    write_candidate_batch(run_dir / batch_rel, batch)
    context = make_replay_context(
        search_case,
        run_id=run_dir.name,
        configuration_hash=run.configuration_hash,
        evaluator_provenance=evaluator_provenance,
        scoring_contract=profile.scoring_contract(),
        decision_score=profile.score_name,
        evaluator_id=evaluator_id,
    )
    write_replay_context(run_dir / context_rel, context)
    binding = CandidateReplayBinding.create(
        campaign_id="two_period_overlay",
        source_run_id=run_dir.name,
        configuration_hash=run.configuration_hash,
        benchmark_id=benchmark.benchmark_id,
        context=context,
        batch=batch,
        context_artifact=context_rel.as_posix(),
        batch_artifact=batch_rel.as_posix(),
    )
    write_replay_binding(run_dir / binding_rel, binding)
    replay = replay_candidate_batch(
        batch,
        context,
        binding,
        evaluator=build_replay_evaluator(context),
        mode=ReplayMode.VERIFY,
        decision_score=profile.score_name,
        higher_is_better=True,
        evaluator_configuration={
            "experiment": experiment_id,
            "stage_id": "final_union",
            "profile": profile.to_json_dict(),
            "evaluator_provenance": dict(evaluator_provenance),
        },
        repeat_count=REPLAY_REPEAT_COUNT,
        absolute_tolerance=ABSOLUTE_TOLERANCE,
        relative_tolerance=RELATIVE_TOLERANCE,
    )
    write_candidate_replay(run_dir / replay_rel, replay)
    return {
        "candidate_count": len(archive.records),
        "archive_hash": archive_content_hash(archive),
        "replay_deterministic": replay.deterministic,
        "replay_stored_scores_verified": replay.stored_scores_verified,
        "artifacts": {
            "archive": archive_rel.as_posix(),
            "batch": batch_rel.as_posix(),
            "context": context_rel.as_posix(),
            "binding": binding_rel.as_posix(),
            "replay": replay_rel.as_posix(),
        },
    }


def _stage_terminal_summary(
    records: Sequence[CandidateRecord],
    profile: ScorerProfile,
    search_case: Any,
    reference: Any,
) -> dict[str, Any]:
    scores = [float(record.scores[profile.score_name]) for record in records]
    if not records:
        raise ValueError("stage terminal summary requires at least one candidate")
    true_variables = np.asarray(
        [reference.true_key[index] for index in search_case.free_columns],
        dtype=np.uint8,
    )
    terminal_rows: list[dict[str, Any]] = []
    for record in records:
        variables = np.asarray(record.payload["variables"], dtype=np.uint8)
        row = reference_metrics(
            reference, variables, search_case.particular, search_case.basis
        )
        row["affine_variable_matches"] = int(
            np.count_nonzero(variables == true_variables)
        )
        terminal_rows.append(row)
    top_index = min(
        range(len(records)),
        key=lambda index: (-scores[index], records[index].candidate_id),
    )
    return {
        "candidate_count": len(records),
        "candidate_specific_truth_emitted": False,
        "score_summary": _numeric_summary(scores),
        "rune_match_summary": _numeric_summary(
            [int(row["rune_matches"]) for row in terminal_rows]
        ),
        "complete_word_match_summary": _numeric_summary(
            [int(row["complete_word_matches"]) for row in terminal_rows]
        ),
        "affine_variable_match_summary": _numeric_summary(
            [int(row["affine_variable_matches"]) for row in terminal_rows]
        ),
        "top_scored_candidate_terminal": {
            "rune_matches": int(terminal_rows[top_index]["rune_matches"]),
            "complete_word_matches": int(
                terminal_rows[top_index]["complete_word_matches"]
            ),
            "affine_variable_matches": int(
                terminal_rows[top_index]["affine_variable_matches"]
            ),
            "exact_plaintext": bool(terminal_rows[top_index]["exact_plaintext"]),
        },
        "exact_plaintext_count": sum(
            (bool(row["exact_plaintext"]) for row in terminal_rows)
        ),
        "canonical_key_count": sum(
            (bool(row["canonical_key_equal"]) for row in terminal_rows)
        ),
        "combined_shift_count": sum(
            (bool(row["combined_shift_equal"]) for row in terminal_rows)
        ),
    }


def _attempt_terminal_movement(
    stage: StageOutcome, search_case: Any, reference: Any
) -> dict[str, Any]:
    true_variables = np.asarray(
        [reference.true_key[index] for index in search_case.free_columns],
        dtype=np.uint8,
    )
    rows: list[dict[str, int]] = []
    for attempt in stage.attempt_rows:
        start = np.asarray(attempt["starting_variables"], dtype=np.uint8)
        final = np.asarray(attempt["ending_variables"], dtype=np.uint8)
        start_metrics = reference_metrics(
            reference, start, search_case.particular, search_case.basis
        )
        final_metrics = reference_metrics(
            reference, final, search_case.particular, search_case.basis
        )
        rows.append(
            {
                "rune_improvement": int(final_metrics["rune_matches"])
                - int(start_metrics["rune_matches"]),
                "complete_word_improvement": int(final_metrics["complete_word_matches"])
                - int(start_metrics["complete_word_matches"]),
                "affine_variable_improvement": int(
                    np.count_nonzero(final == true_variables)
                )
                - int(np.count_nonzero(start == true_variables)),
            }
        )
    return {
        "attempt_count": len(rows),
        "rune_improved_count": sum((row["rune_improvement"] > 0 for row in rows)),
        "rune_worsened_count": sum((row["rune_improvement"] < 0 for row in rows)),
        "rune_improvement_summary": _numeric_summary(
            [row["rune_improvement"] for row in rows]
        ),
        "complete_word_improved_count": sum(
            (row["complete_word_improvement"] > 0 for row in rows)
        ),
        "complete_word_worsened_count": sum(
            (row["complete_word_improvement"] < 0 for row in rows)
        ),
        "complete_word_improvement_summary": _numeric_summary(
            [row["complete_word_improvement"] for row in rows]
        ),
        "affine_variable_improved_count": sum(
            (row["affine_variable_improvement"] > 0 for row in rows)
        ),
        "affine_variable_worsened_count": sum(
            (row["affine_variable_improvement"] < 0 for row in rows)
        ),
        "affine_variable_improvement_summary": _numeric_summary(
            [row["affine_variable_improvement"] for row in rows]
        ),
    }


__all__ = [
    "STAGE_SWEEPS",
    "StageOutcome",
    "_attempt_terminal_movement",
    "_rescore_final_union",
    "_run_stage",
    "_stage_terminal_summary",
    "_write_final_union_and_replay",
    "_write_stage_and_replay",
]
