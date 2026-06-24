from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from numbers import Integral, Real
from pathlib import Path
from typing import Any


class TutorialRunKind(StrEnum):
    SEEDED_PIPELINE_SMOKE = "seeded_pipeline_smoke"
    REAL_KEY_RECOVERY_BENCHMARK = "real_key_recovery_benchmark"


class TutorialTruthPolicy(StrEnum):
    NONE = "none"
    KNOWN_PLAINTEXT_REFERENCE = "known_plaintext_reference"
    KNOWN_KEY_AND_PLAINTEXT = "known_key_and_plaintext"


class TutorialBenchmarkOutcome(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    INCOMPLETE = "incomplete"


class TutorialAcceptanceKind(StrEnum):
    """Release-runner acceptance policies for tutorial evidence."""

    PROCESS_SUCCESS = "process_success"
    EXACT = "exact"
    NEAR_EXACT = "near_exact"
    HUMAN_READABLE = "human_readable"
    SHOWCASE_NEAR_SOLVE = "showcase_near_solve"
    REQUIRES_ASSET_PROFILE = "requires_asset_profile"
    BLOCKED_KNOWN_ISSUE = "blocked_known_issue"


class TutorialStopReason(StrEnum):
    TARGET_MATCH_RATIO = "target_match_ratio"
    READABLE_MATCH_RATIO = "readable_match_ratio"
    SCORE_THRESHOLD = "score_threshold"
    WORK_BUDGET = "work_budget"
    TIME_BUDGET = "time_budget"
    SOLVER_STOP = "solver_stop"
    NOT_REACHED = "not_reached"


@dataclass(frozen=True, slots=True)
class TutorialStopPolicy:
    """Tutorial/benchmark stop policy.

    Match-ratio thresholds are tutorial/benchmark instrumentation. When
    reference data is available, the summary reports match/readability/target
    fields. Missing reference data is allowed at the tutorial/session layer so
    reference data can be attached progressively without making the run API
    brittle. Score/work/time thresholds are normal benchmark controls and can be
    reported for every run.
    """

    readable_match_ratio: float = 0.85
    target_match_ratio: float = 0.99
    stop_score: float | None = None
    max_evals: int | None = None
    max_tokens: int | None = None
    max_seconds: float | None = None

    def __post_init__(self) -> None:
        _require_ratio(self.readable_match_ratio, "readable_match_ratio")
        _require_ratio(self.target_match_ratio, "target_match_ratio")
        if self.target_match_ratio < self.readable_match_ratio:
            raise ValueError("target_match_ratio must be >= readable_match_ratio")
        _require_optional_finite_float(self.stop_score, "stop_score")
        _require_optional_positive_int(self.max_evals, "max_evals")
        _require_optional_positive_int(self.max_tokens, "max_tokens")
        _require_optional_nonnegative_float(self.max_seconds, "max_seconds")

    def to_json_dict(self) -> dict[str, object]:
        return {
            "readable_match_ratio": float(self.readable_match_ratio),
            "target_match_ratio": float(self.target_match_ratio),
            "stop_score": self.stop_score,
            "max_evals": self.max_evals,
            "max_tokens": self.max_tokens,
            "max_seconds": self.max_seconds,
        }


@dataclass(frozen=True, slots=True)
class TutorialBenchmarkSummary:
    schema: str
    run_kind: TutorialRunKind | str
    truth_policy: TutorialTruthPolicy | str
    stop_policy: TutorialStopPolicy
    outcome: TutorialBenchmarkOutcome | str
    stop_reason: TutorialStopReason | str
    readable_reached: bool | None
    target_reached: bool | None
    match_ratio: float | None
    score: float | None
    evals: int | None
    tokens: int | None
    wall_time_s: float | None

    def __post_init__(self) -> None:
        if self.schema != "rdp_tutorial_benchmark_summary.v1":
            raise ValueError("unsupported tutorial benchmark summary schema")
        object.__setattr__(self, "run_kind", _coerce_enum(self.run_kind, TutorialRunKind, "run_kind"))
        object.__setattr__(self, "truth_policy", _coerce_enum(self.truth_policy, TutorialTruthPolicy, "truth_policy"))
        object.__setattr__(self, "outcome", _coerce_enum(self.outcome, TutorialBenchmarkOutcome, "outcome"))
        object.__setattr__(self, "stop_reason", _coerce_enum(self.stop_reason, TutorialStopReason, "stop_reason"))
        if not isinstance(self.stop_policy, TutorialStopPolicy):
            raise TypeError("stop_policy must be TutorialStopPolicy")
        _require_optional_bool(self.readable_reached, "readable_reached")
        _require_optional_bool(self.target_reached, "target_reached")
        _require_optional_ratio(self.match_ratio, "match_ratio")
        _require_optional_finite_float(self.score, "score")
        _require_optional_nonnegative_int(self.evals, "evals")
        _require_optional_nonnegative_int(self.tokens, "tokens")
        _require_optional_nonnegative_float(self.wall_time_s, "wall_time_s")
        _validate_truth_policy_fields(
            truth_policy=self.truth_policy,
            match_ratio=self.match_ratio,
            readable_reached=self.readable_reached,
            target_reached=self.target_reached,
        )

    def to_json_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "run_kind": self.run_kind.value,
            "truth_policy": self.truth_policy.value,
            "stop_policy": self.stop_policy.to_json_dict(),
            "outcome": self.outcome.value,
            "stop_reason": self.stop_reason.value,
            "readable_reached": self.readable_reached,
            "target_reached": self.target_reached,
            "match_ratio": self.match_ratio,
            "score": self.score,
            "evals": self.evals,
            "tokens": self.tokens,
            "wall_time_s": self.wall_time_s,
        }


def build_tutorial_benchmark_summary(
    *,
    run_kind: TutorialRunKind | str,
    truth_policy: TutorialTruthPolicy | str,
    stop_policy: TutorialStopPolicy,
    plaintext_idx: Sequence[int] | None = None,
    reference_idx: Sequence[int] | None = None,
    score: float | None = None,
    evals: int | None = None,
    tokens: int | None = None,
    wall_time_s: float | None = None,
    solver_stop_reason: str | None = None,
) -> TutorialBenchmarkSummary:
    """Build a compact benchmark summary for tutorial/release evidence."""
    run_kind_value = _coerce_enum(run_kind, TutorialRunKind, "run_kind")
    truth_policy_value = _coerce_enum(truth_policy, TutorialTruthPolicy, "truth_policy")
    if not isinstance(stop_policy, TutorialStopPolicy):
        raise TypeError("stop_policy must be TutorialStopPolicy")

    match_ratio = _match_ratio(plaintext_idx, reference_idx)
    _validate_truth_policy_match_ratio(truth_policy=truth_policy_value, match_ratio=match_ratio)

    readable = None if match_ratio is None else match_ratio >= stop_policy.readable_match_ratio
    target = None if match_ratio is None else match_ratio >= stop_policy.target_match_ratio
    score_value = _optional_float(score)
    evals_value = _optional_int(evals)
    tokens_value = _optional_int(tokens)
    wall_value = _optional_float(wall_time_s)

    stop_reason = _choose_stop_reason(
        stop_policy=stop_policy,
        target=target,
        readable=readable,
        score=score_value,
        evals=evals_value,
        tokens=tokens_value,
        wall_time_s=wall_value,
        solver_stop_reason=solver_stop_reason,
    )
    outcome = _choose_outcome(target=target, readable=readable, stop_reason=stop_reason)

    return TutorialBenchmarkSummary(
        schema="rdp_tutorial_benchmark_summary.v1",
        run_kind=run_kind_value,
        truth_policy=truth_policy_value,
        stop_policy=stop_policy,
        outcome=outcome,
        stop_reason=stop_reason,
        readable_reached=readable,
        target_reached=target,
        match_ratio=match_ratio,
        score=score_value,
        evals=evals_value,
        tokens=tokens_value,
        wall_time_s=wall_value,
    )


def _choose_stop_reason(
    *,
    stop_policy: TutorialStopPolicy,
    target: bool | None,
    readable: bool | None,
    score: float | None,
    evals: int | None,
    tokens: int | None,
    wall_time_s: float | None,
    solver_stop_reason: str | None,
) -> TutorialStopReason:
    if target is True:
        return TutorialStopReason.TARGET_MATCH_RATIO
    if readable is True:
        return TutorialStopReason.READABLE_MATCH_RATIO
    if stop_policy.stop_score is not None and score is not None and score >= stop_policy.stop_score:
        return TutorialStopReason.SCORE_THRESHOLD
    if stop_policy.max_evals is not None and evals is not None and evals >= stop_policy.max_evals:
        return TutorialStopReason.WORK_BUDGET
    if stop_policy.max_tokens is not None and tokens is not None and tokens >= stop_policy.max_tokens:
        return TutorialStopReason.WORK_BUDGET
    if stop_policy.max_seconds is not None and wall_time_s is not None and wall_time_s >= stop_policy.max_seconds:
        return TutorialStopReason.TIME_BUDGET
    if solver_stop_reason:
        return TutorialStopReason.SOLVER_STOP
    return TutorialStopReason.NOT_REACHED


def _choose_outcome(
    *,
    target: bool | None,
    readable: bool | None,
    stop_reason: TutorialStopReason,
) -> TutorialBenchmarkOutcome:
    if target is True:
        return TutorialBenchmarkOutcome.PASS
    if readable is True:
        return TutorialBenchmarkOutcome.PASS
    if stop_reason in {TutorialStopReason.WORK_BUDGET, TutorialStopReason.TIME_BUDGET}:
        return TutorialBenchmarkOutcome.FAIL
    return TutorialBenchmarkOutcome.INCOMPLETE


def _match_ratio(found: Sequence[int] | None, reference: Sequence[int] | None) -> float | None:
    found_values = _int_list(found)
    reference_values = _int_list(reference)
    if found_values is None or reference_values is None:
        return None
    denom = max(len(found_values), len(reference_values))
    if denom == 0:
        return None
    limit = min(len(found_values), len(reference_values))
    return sum(1 for idx in range(limit) if found_values[idx] == reference_values[idx]) / float(denom)


def _int_list(value: Sequence[int] | None) -> list[int] | None:
    if value is None or isinstance(value, (str, bytes, Path, Mapping)):
        return None
    try:
        out = [int(item) for item in value]
    except Exception:
        return None
    return out if out else None


def _validate_truth_policy_match_ratio(
    *,
    truth_policy: TutorialTruthPolicy,
    match_ratio: float | None,
) -> None:
    if truth_policy is TutorialTruthPolicy.NONE and match_ratio is not None:
        raise ValueError("match_ratio requires a tutorial truth policy")


def _validate_truth_policy_fields(
    *,
    truth_policy: TutorialTruthPolicy,
    match_ratio: float | None,
    readable_reached: bool | None,
    target_reached: bool | None,
) -> None:
    _validate_truth_policy_match_ratio(truth_policy=truth_policy, match_ratio=match_ratio)
    if match_ratio is None:
        return
    if readable_reached is None:
        raise ValueError("match_ratio requires readable_reached")
    if target_reached is None:
        raise ValueError("match_ratio requires target_reached")


def _coerce_enum(value: object, enum_type: type[StrEnum], field_name: str) -> StrEnum:
    if isinstance(value, enum_type):
        return value
    try:
        return enum_type(str(value))
    except ValueError as exc:
        allowed = ", ".join(item.value for item in enum_type)
        raise ValueError(f"unknown {field_name} {value!r}; expected one of: {allowed}") from exc


def _require_ratio(value: object, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{field_name} must be a float ratio")
    item = float(value)
    if not math.isfinite(item):
        raise ValueError(f"{field_name} must be finite")
    if not 0.0 <= item <= 1.0:
        raise ValueError(f"{field_name} must be between 0 and 1")


def _require_optional_ratio(value: object, field_name: str) -> None:
    if value is not None:
        _require_ratio(value, field_name)


def _require_optional_bool(value: object, field_name: str) -> None:
    if value is not None and type(value) is not bool:
        raise TypeError(f"{field_name} must be bool or None")


def _optional_float(value: float | None) -> float | None:
    if value is None:
        return None
    _require_optional_finite_float(value, "value")
    return float(value)


def _optional_int(value: int | None) -> int | None:
    if value is None:
        return None
    _require_optional_nonnegative_int(value, "value")
    return int(value)


def _require_optional_finite_float(value: object, field_name: str) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{field_name} must be a finite float or None")
    if not math.isfinite(float(value)):
        raise ValueError(f"{field_name} must be finite")


def _require_optional_nonnegative_float(value: object, field_name: str) -> None:
    _require_optional_finite_float(value, field_name)
    if value is not None and float(value) < 0.0:
        raise ValueError(f"{field_name} must be >= 0")


def _require_optional_positive_int(value: object, field_name: str) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise TypeError(f"{field_name} must be a positive integer or None")
    if int(value) <= 0:
        raise ValueError(f"{field_name} must be > 0")


def _require_optional_nonnegative_int(value: object, field_name: str) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise TypeError(f"{field_name} must be a non-negative integer or None")
    if int(value) < 0:
        raise ValueError(f"{field_name} must be >= 0")


__all__ = [
    "TutorialAcceptanceKind",
    "TutorialBenchmarkOutcome",
    "TutorialBenchmarkSummary",
    "TutorialRunKind",
    "TutorialStopPolicy",
    "TutorialStopReason",
    "TutorialTruthPolicy",
    "build_tutorial_benchmark_summary",
]
