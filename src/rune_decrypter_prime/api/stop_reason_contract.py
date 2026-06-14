from __future__ import annotations

from enum import StrEnum
from typing import Any


class StopCategory(StrEnum):
    SUCCESS = "success"
    BUDGET = "budget"
    BLOCKED_BEFORE_RUN = "blocked_before_run"
    ERROR = "error"
    MANUAL = "manual"
    NOT_STARTED = "not_started"


class KnownStopReason(StrEnum):
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


SUCCESS_REASONS = frozenset(
    item.value
    for item in (
        KnownStopReason.DONE,
        KnownStopReason.SUCCESS,
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
ERROR_REASONS = frozenset(item.value for item in (KnownStopReason.ERROR, KnownStopReason.EXCEPTION))
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


def stop_category_for_reason(reason: str | None) -> StopCategory:
    if reason is None or str(reason).strip() == "":
        return StopCategory.NOT_STARTED
    value = str(reason).strip().lower()
    if value in SUCCESS_REASONS:
        return StopCategory.SUCCESS
    if value in BUDGET_REASONS:
        return StopCategory.BUDGET
    if value in BLOCKED_BEFORE_RUN_REASONS:
        return StopCategory.BLOCKED_BEFORE_RUN
    if value in ERROR_REASONS:
        return StopCategory.ERROR
    if value in MANUAL_REASONS:
        return StopCategory.MANUAL
    if value.startswith(BUDGET_REASON_PREFIXES):
        return StopCategory.BUDGET
    return StopCategory.ERROR if KnownStopReason.ERROR.value in value else StopCategory.BUDGET


def stop_reason_details_from_solution(solution: Any) -> dict[str, Any]:
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
        StopReasonDetailKey.BLOCKED_BEFORE_RUN.value: category is StopCategory.BLOCKED_BEFORE_RUN,
        StopReasonDetailKey.ERROR_TYPE.value: None if error_type is None else str(error_type),
    }


__all__ = [
    "BLOCKED_BEFORE_RUN_REASONS",
    "BUDGET_REASON_PREFIXES",
    "BUDGET_REASONS",
    "ERROR_REASONS",
    "KnownStopReason",
    "MANUAL_REASONS",
    "STOP_CATEGORIES",
    "SUCCESS_REASONS",
    "StopCategory",
    "StopReasonDetailKey",
    "StopReasonPrefix",
    "stop_category_for_reason",
    "stop_reason_details_from_solution",
]
