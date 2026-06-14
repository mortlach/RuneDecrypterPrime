from __future__ import annotations

from typing import Any

SUCCESS_REASONS = frozenset({"done", "success", "target", "target_score", "stop_score", "test_key"})
BUDGET_REASONS = frozenset({
    "budget",
    "eval_budget",
    "max_evals",
    "max_eval",
    "max_steps",
    "max_rounds",
    "time_budget",
    "max_time",
    "patience",
    "plateau",
})
BLOCKED_BEFORE_RUN_REASONS = frozenset({
    "all_rejected_by_hard_crib",
    "requested_scorer_lane_unavailable",
    "blocked_before_run",
})
ERROR_REASONS = frozenset({"error", "exception"})
MANUAL_REASONS = frozenset({"manual", "cancelled", "canceled", "interrupted"})
BUDGET_REASON_PREFIXES = ("no_improve_", "stall_")

STOP_CATEGORIES = frozenset({
    "success",
    "budget",
    "blocked_before_run",
    "error",
    "manual",
    "not_started",
})


def stop_category_for_reason(reason: str | None) -> str:
    if reason is None or str(reason).strip() == "":
        return "not_started"
    value = str(reason).strip().lower()
    if value in SUCCESS_REASONS:
        return "success"
    if value in BUDGET_REASONS:
        return "budget"
    if value in BLOCKED_BEFORE_RUN_REASONS:
        return "blocked_before_run"
    if value in ERROR_REASONS:
        return "error"
    if value in MANUAL_REASONS:
        return "manual"
    if value.startswith(BUDGET_REASON_PREFIXES):
        return "budget"
    return "error" if "error" in value else "budget"


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
        "stop_category": category,
        "stop_reason": reason,
        "stop_detail": None if detail is None else str(detail),
        "blocked_before_run": category == "blocked_before_run",
        "error_type": None if error_type is None else str(error_type),
    }
