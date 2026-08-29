from __future__ import annotations
import math
from collections.abc import Callable, Mapping
from typing import Any
from cipher_development.shared.archive import (
    CandidateRecord,
    _snapshot_json,
    _thaw_json,
)
from cipher_development.shared.replay import (
    CandidateReplayBatch,
    CandidateReplayContext,
    _non_negative,
    _reject_replay_reference_fields,
    _text,
)
from cipher_development.shared.replay_binding import CandidateReplayBinding
from cipher_development.shared.replay_evidence import (
    EVIDENCE_SCHEMA,
    CandidateReplayEvidence,
    CandidateReplayObservation,
    ReplayEvaluation,
    ReplayMode,
    _replay_id,
)


def _coerce_evaluation(value: Any) -> ReplayEvaluation:
    if isinstance(value, ReplayEvaluation):
        return value
    if isinstance(value, Mapping):
        if "scores" in value:
            return ReplayEvaluation(
                scores=value["scores"], stable_metrics=value.get("stable_metrics", {})
            )
        return ReplayEvaluation(scores=value)
    raise TypeError("evaluator must return ReplayEvaluation or a score mapping")


def _within_tolerance(a: float, b: float, absolute: float, relative: float) -> bool:
    return math.isclose(a, b, abs_tol=absolute, rel_tol=relative)


def replay_candidate_batch(
    batch: CandidateReplayBatch,
    context: CandidateReplayContext,
    binding: CandidateReplayBinding,
    *,
    evaluator: Callable[
        [CandidateRecord, CandidateReplayContext], ReplayEvaluation | Mapping[str, Any]
    ],
    mode: ReplayMode | str,
    decision_score: str,
    higher_is_better: bool,
    evaluator_configuration: Mapping[str, Any],
    repeat_count: int = 2,
    absolute_tolerance: float = 0.0,
    relative_tolerance: float = 0.0,
) -> CandidateReplayEvidence:
    if not isinstance(batch, CandidateReplayBatch):
        raise TypeError("batch must be a CandidateReplayBatch")
    if not isinstance(context, CandidateReplayContext):
        raise TypeError("context must be a CandidateReplayContext")
    if not isinstance(binding, CandidateReplayBinding):
        raise TypeError("binding must be a CandidateReplayBinding")
    binding.validate(batch, context)
    if not callable(evaluator):
        raise TypeError("evaluator must be callable")
    try:
        mode_value = mode if isinstance(mode, ReplayMode) else ReplayMode(str(mode))
    except ValueError as exc:
        raise ValueError("mode must be verify or rerank") from exc
    decision_score = _text(decision_score, "decision_score")
    _reject_replay_reference_fields({decision_score: 0}, "decision_score")
    if type(higher_is_better) is not bool:
        raise TypeError("higher_is_better must be a bool")
    if isinstance(repeat_count, bool) or not isinstance(repeat_count, int):
        raise TypeError("repeat_count must be an integer")
    if repeat_count < 2:
        raise ValueError("repeat_count must be at least 2")
    absolute_tolerance = _non_negative(absolute_tolerance, "absolute_tolerance")
    relative_tolerance = _non_negative(relative_tolerance, "relative_tolerance")
    configuration = _snapshot_json(evaluator_configuration, "evaluator_configuration")
    _reject_replay_reference_fields(configuration, "evaluator_configuration")
    observations: list[CandidateReplayObservation] = []
    deterministic = True
    stored_verified: bool | None = True if mode_value is ReplayMode.VERIFY else None
    for candidate in batch.candidates:
        evaluations = [
            _coerce_evaluation(evaluator(candidate, context))
            for _ in range(repeat_count)
        ]
        score_names = tuple(evaluations[0].scores)
        if decision_score not in evaluations[0].scores:
            raise ValueError(
                f"evaluator did not return decision score {decision_score!r} for candidate {candidate.candidate_id}"
            )
        if any((tuple(item.scores) != score_names for item in evaluations[1:])):
            raise ValueError("evaluator score names changed between repeats")
        first_metrics = _thaw_json(evaluations[0].stable_metrics)
        if any(
            (
                _thaw_json(item.stable_metrics) != first_metrics
                for item in evaluations[1:]
            )
        ):
            raise ValueError("stable metrics changed between replay repeats")
        maximum_delta = 0.0
        for name in score_names:
            base = evaluations[0].scores[name]
            for other in evaluations[1:]:
                delta = abs(other.scores[name] - base)
                maximum_delta = max(maximum_delta, delta)
                if not _within_tolerance(
                    other.scores[name], base, absolute_tolerance, relative_tolerance
                ):
                    deterministic = False
        stored_delta = None
        if mode_value is ReplayMode.VERIFY:
            if decision_score not in candidate.scores:
                raise ValueError(
                    f"stored candidate lacks decision score {decision_score!r}"
                )
            stored_score = candidate.scores[decision_score]
            decision_values = [item.scores[decision_score] for item in evaluations]
            stored_delta = max((abs(value - stored_score) for value in decision_values))
            verified = all(
                (
                    _within_tolerance(
                        value, stored_score, absolute_tolerance, relative_tolerance
                    )
                    for value in decision_values
                )
            )
            stored_verified = bool(stored_verified and verified)
        observations.append(
            CandidateReplayObservation(
                candidate_id=candidate.candidate_id,
                stored_scores=dict(candidate.scores),
                observed_scores=dict(evaluations[0].scores),
                repeat_scores=tuple((dict(item.scores) for item in evaluations)),
                stable_metrics=first_metrics,
                maximum_repeat_delta=maximum_delta,
                stored_score_delta=stored_delta,
            )
        )
    ranking = tuple(
        (
            item.candidate_id
            for item in sorted(
                observations,
                key=lambda item: (
                    -item.observed_scores[decision_score]
                    if higher_is_better
                    else item.observed_scores[decision_score],
                    item.candidate_id,
                ),
            )
        )
    )
    candidate_ids = tuple(batch.candidate_ids)
    content = {
        "schema": EVIDENCE_SCHEMA,
        "mode": mode_value.value,
        "source_binding_id": binding.binding_id,
        "source_batch_id": batch.batch_id,
        "source_archive_hash": batch.source_archive_hash,
        "source_context_id": context.context_id,
        "evaluator_id": context.evaluator_id,
        "configuration_hash": context.configuration_hash,
        "decision_score": decision_score,
        "higher_is_better": higher_is_better,
        "repeat_count": repeat_count,
        "absolute_tolerance": absolute_tolerance,
        "relative_tolerance": relative_tolerance,
        "candidate_ids": list(candidate_ids),
        "observations": [item.to_json_dict() for item in observations],
        "ranking": list(ranking),
        "deterministic": deterministic,
        "stored_scores_verified": stored_verified,
        "evaluator_configuration": _thaw_json(configuration),
    }
    return CandidateReplayEvidence.from_json_dict(
        {"replay_id": _replay_id(content), **content}
    )


__all__ = ["replay_candidate_batch"]
