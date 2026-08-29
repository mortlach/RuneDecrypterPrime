from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from numbers import Real
from typing import Any


# Existing June V1 contract identity. A4 extends this contract; it does not
# introduce a second run-status schema.
RUN_STATUS_SCHEMA = "rdp.run_status_contract.v1"


class StopCategory(StrEnum):
    SUCCESS = "success"
    BUDGET = "budget"
    BLOCKED_BEFORE_RUN = "blocked_before_run"
    ERROR = "error"
    MANUAL = "manual"
    NOT_STARTED = "not_started"


class ExecutionStatus(StrEnum):
    COMPLETED = "completed"
    BLOCKED_BEFORE_RUN = "blocked_before_run"
    ERROR = "error"
    MANUAL_STOP = "manual_stop"
    NOT_STARTED = "not_started"


class RecoveryStatus(StrEnum):
    NOT_ASSESSED = "not_assessed"
    EXACT = "exact"
    PARTIAL = "partial"
    NOT_RECOVERED = "not_recovered"


class StopReason(StrEnum):
    # Positive termination conditions. These describe execution/termination,
    # never scientific recovery unless the name explicitly says oracle match.
    TARGET_SCORE_REACHED = "target_score_reached"
    ORACLE_EXACT_PLAINTEXT_MATCH = "oracle_exact_plaintext_match"
    ORACLE_EXACT_KEY_MATCH = "oracle_exact_key_match"
    ORACLE_TEST_KEY_USED = "oracle_test_key_used"
    KNOWN_KEY_EXECUTION_COMPLETED = "known_key_execution_completed"
    CONSTRAINT_SPACE_RESOLVED_EXACTLY = "constraint_space_resolved_exactly"

    # Configured work / search limits.
    MAX_EVALUATIONS_REACHED = "max_evaluations_reached"
    MAX_TIME_REACHED = "max_time_reached"
    NO_IMPROVEMENT_BUDGET_REACHED = "no_improvement_budget_reached"
    MAX_ROUNDS_REACHED = "max_rounds_reached"
    MAX_GENERATIONS_REACHED = "max_generations_reached"
    MAX_ITERATIONS_REACHED = "max_iterations_reached"
    MAX_STEPS_REACHED = "max_steps_reached"
    MAX_SWEEPS_REACHED = "max_sweeps_reached"
    CONFIGURED_WORK_LIMIT_REACHED = "configured_work_limit_reached"
    STATIC_RESCORE_COMPLETED = "static_rescore_completed"

    # Blocking/error/manual/not-started conditions.
    MANUAL_STOP = "manual_stop"
    REQUESTED_LANE_UNAVAILABLE = "requested_lane_unavailable"
    BLOCKED_BEFORE_RUN = "blocked_before_run"
    ALL_CANDIDATES_REJECTED_BY_HARD_CRIB = "all_candidates_rejected_by_hard_crib"
    ASSET_MISSING = "asset_missing"
    CONFIG_INVALID = "config_invalid"
    ARTIFACT_AGREEMENT_FAILED = "artifact_agreement_failed"
    UNEXPECTED_EXCEPTION = "unexpected_exception"
    UNKNOWN_RUNTIME_REASON = "unknown_runtime_reason"
    NOT_STARTED = "not_started"


class KnownStopReason(StrEnum):
    """Legacy/internal reason strings retained for compatibility mapping."""

    DONE = "done"
    SUCCESS = "success"
    TARGET = "target"
    TARGET_SCORE = "target_score"
    STOP_SCORE = "stop_score"
    TEST_KEY = "test_key"
    BUDGET = "budget"
    EVAL_BUDGET = "eval_budget"
    MAX_EVALS = "max_evals"
    MAX_EVAL = "max_eval"
    MAX_STEPS = "max_steps"
    MAX_ROUNDS = "max_rounds"
    TIME_BUDGET = "time_budget"
    MAX_TIME = "max_time"
    PATIENCE = "patience"
    PLATEAU = "plateau"
    ALL_REJECTED_BY_HARD_CRIB = "all_rejected_by_hard_crib"
    REQUESTED_SCORER_LANE_UNAVAILABLE = "requested_scorer_lane_unavailable"
    BLOCKED_BEFORE_RUN = "blocked_before_run"
    ERROR = "error"
    EXCEPTION = "exception"
    MANUAL = "manual"
    CANCELLED = "cancelled"
    CANCELED = "canceled"
    INTERRUPTED = "interrupted"


class StopReasonPrefix(StrEnum):
    NO_IMPROVE = "no_improve_"
    STALL = "stall_"


class StopReasonDetailKey(StrEnum):
    STOP_CATEGORY = "stop_category"
    STOP_REASON = "stop_reason"
    STOP_DETAIL = "stop_detail"
    BLOCKED_BEFORE_RUN = "blocked_before_run"
    ERROR_TYPE = "error_type"


# Compatibility exports. Deliberately do not classify legacy "done" or
# "success" as success: without a precise producer reason their meaning is
# ambiguous and A4 must not infer success from completion.
SUCCESS_REASONS = frozenset(
    item.value
    for item in (
        KnownStopReason.TARGET,
        KnownStopReason.TARGET_SCORE,
        KnownStopReason.STOP_SCORE,
        KnownStopReason.TEST_KEY,
    )
)
BUDGET_REASONS = frozenset(
    item.value
    for item in (
        KnownStopReason.BUDGET,
        KnownStopReason.EVAL_BUDGET,
        KnownStopReason.MAX_EVALS,
        KnownStopReason.MAX_EVAL,
        KnownStopReason.MAX_STEPS,
        KnownStopReason.MAX_ROUNDS,
        KnownStopReason.TIME_BUDGET,
        KnownStopReason.MAX_TIME,
        KnownStopReason.PATIENCE,
        KnownStopReason.PLATEAU,
    )
)
BLOCKED_BEFORE_RUN_REASONS = frozenset(
    item.value
    for item in (
        KnownStopReason.ALL_REJECTED_BY_HARD_CRIB,
        KnownStopReason.REQUESTED_SCORER_LANE_UNAVAILABLE,
        KnownStopReason.BLOCKED_BEFORE_RUN,
    )
)
ERROR_REASONS = frozenset(
    item.value for item in (KnownStopReason.ERROR, KnownStopReason.EXCEPTION)
)
MANUAL_REASONS = frozenset(
    item.value
    for item in (
        KnownStopReason.MANUAL,
        KnownStopReason.CANCELLED,
        KnownStopReason.CANCELED,
        KnownStopReason.INTERRUPTED,
    )
)
BUDGET_REASON_PREFIXES = tuple(item.value for item in StopReasonPrefix)
STOP_CATEGORIES = frozenset(item.value for item in StopCategory)


_CANONICAL_CATEGORY: dict[StopReason, StopCategory] = {
    StopReason.TARGET_SCORE_REACHED: StopCategory.SUCCESS,
    StopReason.ORACLE_EXACT_PLAINTEXT_MATCH: StopCategory.SUCCESS,
    StopReason.ORACLE_EXACT_KEY_MATCH: StopCategory.SUCCESS,
    StopReason.ORACLE_TEST_KEY_USED: StopCategory.SUCCESS,
    StopReason.KNOWN_KEY_EXECUTION_COMPLETED: StopCategory.SUCCESS,
    StopReason.CONSTRAINT_SPACE_RESOLVED_EXACTLY: StopCategory.SUCCESS,
    StopReason.MAX_EVALUATIONS_REACHED: StopCategory.BUDGET,
    StopReason.MAX_TIME_REACHED: StopCategory.BUDGET,
    StopReason.NO_IMPROVEMENT_BUDGET_REACHED: StopCategory.BUDGET,
    StopReason.MAX_ROUNDS_REACHED: StopCategory.BUDGET,
    StopReason.MAX_GENERATIONS_REACHED: StopCategory.BUDGET,
    StopReason.MAX_ITERATIONS_REACHED: StopCategory.BUDGET,
    StopReason.MAX_STEPS_REACHED: StopCategory.BUDGET,
    StopReason.MAX_SWEEPS_REACHED: StopCategory.BUDGET,
    StopReason.CONFIGURED_WORK_LIMIT_REACHED: StopCategory.BUDGET,
    StopReason.STATIC_RESCORE_COMPLETED: StopCategory.BUDGET,
    StopReason.REQUESTED_LANE_UNAVAILABLE: StopCategory.BLOCKED_BEFORE_RUN,
    StopReason.BLOCKED_BEFORE_RUN: StopCategory.BLOCKED_BEFORE_RUN,
    StopReason.ALL_CANDIDATES_REJECTED_BY_HARD_CRIB: StopCategory.BLOCKED_BEFORE_RUN,
    StopReason.ASSET_MISSING: StopCategory.BLOCKED_BEFORE_RUN,
    StopReason.CONFIG_INVALID: StopCategory.BLOCKED_BEFORE_RUN,
    StopReason.ARTIFACT_AGREEMENT_FAILED: StopCategory.BLOCKED_BEFORE_RUN,
    StopReason.UNEXPECTED_EXCEPTION: StopCategory.ERROR,
    StopReason.UNKNOWN_RUNTIME_REASON: StopCategory.ERROR,
    StopReason.MANUAL_STOP: StopCategory.MANUAL,
    StopReason.NOT_STARTED: StopCategory.NOT_STARTED,
}
_CANONICAL_VALUES = frozenset(reason.value for reason in StopReason)


@dataclass(frozen=True, slots=True)
class RunStatus:
    """Typed A4 extension of the existing June V1 run-status contract."""

    execution_status: ExecutionStatus
    stop_category: StopCategory
    stop_reason: StopReason
    runtime_reason: str | None = None
    stop_detail: str | None = None
    error_type: str | None = None
    recovery_status: RecoveryStatus = RecoveryStatus.NOT_ASSESSED
    recovery_match_ratio: float | None = None
    recovery_basis: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.execution_status, ExecutionStatus):
            raise TypeError("execution_status must be ExecutionStatus")
        if not isinstance(self.stop_category, StopCategory):
            raise TypeError("stop_category must be StopCategory")
        if not isinstance(self.stop_reason, StopReason):
            raise TypeError("stop_reason must be StopReason")
        if not isinstance(self.recovery_status, RecoveryStatus):
            raise TypeError("recovery_status must be RecoveryStatus")
        for field_name, value in (
            ("runtime_reason", self.runtime_reason),
            ("stop_detail", self.stop_detail),
            ("error_type", self.error_type),
            ("recovery_basis", self.recovery_basis),
        ):
            if value is not None and not isinstance(value, str):
                raise TypeError(f"{field_name} must be str or None")

        ratio: float | None = None
        if self.recovery_match_ratio is not None:
            if isinstance(self.recovery_match_ratio, bool) or not isinstance(
                self.recovery_match_ratio, Real
            ):
                raise TypeError("recovery_match_ratio must be a finite float or None")
            ratio = float(self.recovery_match_ratio)
            if not math.isfinite(ratio) or not 0.0 <= ratio <= 1.0:
                raise ValueError("recovery_match_ratio must be between 0 and 1")
            object.__setattr__(self, "recovery_match_ratio", ratio)

        expected_category = _CANONICAL_CATEGORY[self.stop_reason]
        if self.stop_category is not expected_category:
            raise ValueError(
                f"stop_category {self.stop_category.value!r} does not match "
                f"stop_reason {self.stop_reason.value!r}"
            )
        if (
            self.execution_status is ExecutionStatus.BLOCKED_BEFORE_RUN
            and self.stop_category is not StopCategory.BLOCKED_BEFORE_RUN
        ):
            raise ValueError(
                "blocked_before_run execution requires blocked_before_run stop category"
            )
        if (
            self.execution_status is ExecutionStatus.ERROR
            and self.stop_category is not StopCategory.ERROR
        ):
            raise ValueError("error execution requires error stop category")
        if (
            self.execution_status is ExecutionStatus.MANUAL_STOP
            and self.stop_category is not StopCategory.MANUAL
        ):
            raise ValueError("manual_stop execution requires manual stop category")
        if (
            self.execution_status is ExecutionStatus.NOT_STARTED
            and self.stop_category is not StopCategory.NOT_STARTED
        ):
            raise ValueError("not_started execution requires not_started stop category")

        if self.recovery_status is RecoveryStatus.NOT_ASSESSED:
            if ratio is not None or self.recovery_basis is not None:
                raise ValueError(
                    "not_assessed recovery must not carry match ratio or basis"
                )
        else:
            if not self.recovery_basis:
                raise ValueError("assessed recovery requires recovery_basis")
            if (
                self.recovery_status is RecoveryStatus.EXACT
                and ratio is not None
                and ratio != 1.0
            ):
                raise ValueError("exact recovery match ratio must be 1.0 when supplied")
            if (
                self.recovery_status is RecoveryStatus.PARTIAL
                and ratio is not None
                and not 0.0 < ratio < 1.0
            ):
                raise ValueError("partial recovery match ratio must be between 0 and 1")
            if (
                self.recovery_status is RecoveryStatus.NOT_RECOVERED
                and ratio is not None
                and ratio != 0.0
            ):
                raise ValueError("not_recovered match ratio must be 0.0 when supplied")

    @property
    def recovery_assessed(self) -> bool:
        return self.recovery_status is not RecoveryStatus.NOT_ASSESSED

    def to_json_dict(self) -> dict[str, object]:
        """Return A4 status fields; SolverReport composes the full June schema."""

        return {
            "execution_status": self.execution_status.value,
            "stop_category": self.stop_category.value,
            "stop_reason": self.stop_reason.value,
            "stop_detail": self.stop_detail,
            "blocked_before_run": self.stop_category is StopCategory.BLOCKED_BEFORE_RUN,
            "error_type": self.error_type,
            "runtime_reason": self.runtime_reason,
            "recovery": {
                "status": self.recovery_status.value,
                "assessed": self.recovery_assessed,
                "match_ratio": self.recovery_match_ratio,
                "basis": self.recovery_basis,
            },
        }


def canonical_stop_reason_for_legacy(reason: str | None) -> StopReason:
    if reason is None or str(reason).strip() == "":
        return StopReason.NOT_STARTED
    value = str(reason).strip().lower()
    if value in _CANONICAL_VALUES:
        return StopReason(value)

    # Ambiguous historical completions are deliberately not promoted to
    # success. Producers changed by A4 must emit a precise reason instead.
    if value in {KnownStopReason.DONE.value, KnownStopReason.SUCCESS.value}:
        return StopReason.UNKNOWN_RUNTIME_REASON
    if value in {
        KnownStopReason.TARGET.value,
        KnownStopReason.TARGET_SCORE.value,
        KnownStopReason.STOP_SCORE.value,
    }:
        return StopReason.TARGET_SCORE_REACHED
    if value == KnownStopReason.TEST_KEY.value:
        return StopReason.ORACLE_TEST_KEY_USED
    if value in {
        KnownStopReason.EVAL_BUDGET.value,
        KnownStopReason.MAX_EVALS.value,
        KnownStopReason.MAX_EVAL.value,
    }:
        return StopReason.MAX_EVALUATIONS_REACHED
    if value in {KnownStopReason.TIME_BUDGET.value, KnownStopReason.MAX_TIME.value}:
        return StopReason.MAX_TIME_REACHED
    if value in {KnownStopReason.MAX_ROUNDS.value, "max_rounds_reached"}:
        return StopReason.MAX_ROUNDS_REACHED
    if value == "max_generations_reached":
        return StopReason.MAX_GENERATIONS_REACHED
    if value == "max_iterations_reached":
        return StopReason.MAX_ITERATIONS_REACHED
    if value in {KnownStopReason.MAX_STEPS.value, "max_steps_reached"}:
        return StopReason.MAX_STEPS_REACHED
    if value == "max_sweeps_reached":
        return StopReason.MAX_SWEEPS_REACHED
    if value == KnownStopReason.BUDGET.value:
        return StopReason.CONFIGURED_WORK_LIMIT_REACHED
    if value in {KnownStopReason.PATIENCE.value, KnownStopReason.PLATEAU.value}:
        return StopReason.NO_IMPROVEMENT_BUDGET_REACHED
    if value.startswith(BUDGET_REASON_PREFIXES):
        return StopReason.NO_IMPROVEMENT_BUDGET_REACHED
    if value == KnownStopReason.ALL_REJECTED_BY_HARD_CRIB.value:
        return StopReason.ALL_CANDIDATES_REJECTED_BY_HARD_CRIB
    if value == KnownStopReason.REQUESTED_SCORER_LANE_UNAVAILABLE.value:
        return StopReason.REQUESTED_LANE_UNAVAILABLE
    if value == KnownStopReason.BLOCKED_BEFORE_RUN.value:
        return StopReason.BLOCKED_BEFORE_RUN
    if value in ERROR_REASONS:
        return StopReason.UNEXPECTED_EXCEPTION
    if value in MANUAL_REASONS:
        return StopReason.MANUAL_STOP
    return StopReason.UNKNOWN_RUNTIME_REASON


def stop_category_for_reason(reason: str | None) -> StopCategory:
    return _CANONICAL_CATEGORY[canonical_stop_reason_for_legacy(reason)]


def execution_status_for_category(category: StopCategory) -> ExecutionStatus:
    if not isinstance(category, StopCategory):
        raise TypeError("category must be StopCategory")
    if category in {StopCategory.SUCCESS, StopCategory.BUDGET}:
        return ExecutionStatus.COMPLETED
    if category is StopCategory.BLOCKED_BEFORE_RUN:
        return ExecutionStatus.BLOCKED_BEFORE_RUN
    if category is StopCategory.ERROR:
        return ExecutionStatus.ERROR
    if category is StopCategory.MANUAL:
        return ExecutionStatus.MANUAL_STOP
    return ExecutionStatus.NOT_STARTED


def build_run_status(
    *,
    runtime_reason: str | None,
    execution_status: ExecutionStatus,
    stop_detail: str | None = None,
    error_type: str | None = None,
    recovery_status: RecoveryStatus = RecoveryStatus.NOT_ASSESSED,
    recovery_match_ratio: float | None = None,
    recovery_basis: str | None = None,
) -> RunStatus:
    if not isinstance(execution_status, ExecutionStatus):
        raise TypeError("execution_status must be ExecutionStatus")

    canonical = canonical_stop_reason_for_legacy(runtime_reason)
    if (
        execution_status is ExecutionStatus.COMPLETED
        and canonical is StopReason.NOT_STARTED
    ):
        canonical = StopReason.UNKNOWN_RUNTIME_REASON
    elif (
        execution_status is ExecutionStatus.BLOCKED_BEFORE_RUN
        and _CANONICAL_CATEGORY[canonical] is not StopCategory.BLOCKED_BEFORE_RUN
    ):
        canonical = StopReason.CONFIG_INVALID
    elif execution_status is ExecutionStatus.ERROR:
        canonical = StopReason.UNEXPECTED_EXCEPTION
    elif execution_status is ExecutionStatus.MANUAL_STOP:
        canonical = StopReason.MANUAL_STOP
    elif execution_status is ExecutionStatus.NOT_STARTED:
        canonical = StopReason.NOT_STARTED

    return RunStatus(
        execution_status=execution_status,
        stop_category=_CANONICAL_CATEGORY[canonical],
        stop_reason=canonical,
        runtime_reason=None if runtime_reason is None else str(runtime_reason),
        stop_detail=stop_detail,
        error_type=error_type,
        recovery_status=recovery_status,
        recovery_match_ratio=recovery_match_ratio,
        recovery_basis=recovery_basis,
    )


def run_status_from_solution(
    solution: Any,
    *,
    execution_status: ExecutionStatus = ExecutionStatus.COMPLETED,
    recovery_status: RecoveryStatus = RecoveryStatus.NOT_ASSESSED,
    recovery_match_ratio: float | None = None,
    recovery_basis: str | None = None,
) -> RunStatus:
    reason_raw = getattr(solution, "stop_reason", None)
    meta = getattr(solution, "meta", None)
    extras = getattr(solution, "extras", None)
    detail = reason_raw
    error_type = None
    if isinstance(meta, dict):
        detail = meta.get("stop_detail", meta.get("stop_reason_detail", detail))
        error_type = meta.get("error_type", error_type)
    if isinstance(extras, dict):
        detail = extras.get("stop_detail", extras.get("stop_reason_detail", detail))
        error_type = extras.get("error_type", error_type)
    return build_run_status(
        runtime_reason=None if reason_raw is None else str(reason_raw),
        execution_status=execution_status,
        stop_detail=None if detail is None else str(detail),
        error_type=None if error_type is None else str(error_type),
        recovery_status=recovery_status,
        recovery_match_ratio=recovery_match_ratio,
        recovery_basis=recovery_basis,
    )


def stop_reason_details_from_solution(solution: Any) -> dict[str, Any]:
    """Legacy flat stop details retained for V1 report compatibility."""

    reason_raw = getattr(solution, "stop_reason", None)
    reason = None if reason_raw is None else str(reason_raw)
    category = stop_category_for_reason(reason)
    meta = getattr(solution, "meta", None)
    extras = getattr(solution, "extras", None)
    detail = reason
    error_type = None
    if isinstance(meta, dict):
        detail = meta.get("stop_detail", meta.get("stop_reason_detail", detail))
        error_type = meta.get("error_type", error_type)
    if isinstance(extras, dict):
        detail = extras.get("stop_detail", extras.get("stop_reason_detail", detail))
        error_type = extras.get("error_type", error_type)
    return {
        StopReasonDetailKey.STOP_CATEGORY.value: category.value,
        StopReasonDetailKey.STOP_REASON.value: reason,
        StopReasonDetailKey.STOP_DETAIL.value: None if detail is None else str(detail),
        StopReasonDetailKey.BLOCKED_BEFORE_RUN.value: category
        is StopCategory.BLOCKED_BEFORE_RUN,
        StopReasonDetailKey.ERROR_TYPE.value: None
        if error_type is None
        else str(error_type),
    }


__all__ = [
    "BLOCKED_BEFORE_RUN_REASONS",
    "BUDGET_REASON_PREFIXES",
    "BUDGET_REASONS",
    "StopReason",
    "ERROR_REASONS",
    "ExecutionStatus",
    "KnownStopReason",
    "MANUAL_REASONS",
    "RUN_STATUS_SCHEMA",
    "RecoveryStatus",
    "RunStatus",
    "STOP_CATEGORIES",
    "SUCCESS_REASONS",
    "StopCategory",
    "StopReasonDetailKey",
    "StopReasonPrefix",
    "build_run_status",
    "canonical_stop_reason_for_legacy",
    "execution_status_for_category",
    "run_status_from_solution",
    "stop_category_for_reason",
    "stop_reason_details_from_solution",
]
