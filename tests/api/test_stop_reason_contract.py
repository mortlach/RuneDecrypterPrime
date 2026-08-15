from __future__ import annotations

from types import SimpleNamespace

from rune_decrypter_prime.api.stop_reason_contract import (
    STOP_CATEGORIES,
    KnownStopReason,
    StopCategory,
    stop_category_for_reason,
    stop_reason_details_from_solution,
)


def test_stop_categories_are_stable_and_enum_backed() -> None:
    assert STOP_CATEGORIES == frozenset(item.value for item in StopCategory)
    assert STOP_CATEGORIES == frozenset({
        "success",
        "budget",
        "blocked_before_run",
        "error",
        "manual",
        "not_started",
    })


def test_stop_reason_category_mapping() -> None:
    assert stop_category_for_reason(None) is StopCategory.NOT_STARTED
    assert stop_category_for_reason(KnownStopReason.DONE.value) is StopCategory.ERROR
    assert stop_category_for_reason(KnownStopReason.PATIENCE.value) is StopCategory.BUDGET
    assert stop_category_for_reason(KnownStopReason.ALL_REJECTED_BY_HARD_CRIB.value) is StopCategory.BLOCKED_BEFORE_RUN
    assert stop_category_for_reason(KnownStopReason.ERROR.value) is StopCategory.ERROR
    assert stop_category_for_reason(KnownStopReason.MANUAL.value) is StopCategory.MANUAL


def test_explicit_positive_stop_reason_aliases_are_success() -> None:
    assert stop_category_for_reason(KnownStopReason.TARGET_SCORE.value) is StopCategory.SUCCESS
    assert stop_category_for_reason(KnownStopReason.STOP_SCORE.value) is StopCategory.SUCCESS
    assert stop_category_for_reason(KnownStopReason.TEST_KEY.value) is StopCategory.SUCCESS


def test_ambiguous_legacy_completion_is_not_promoted_to_success() -> None:
    assert stop_category_for_reason(KnownStopReason.DONE.value) is StopCategory.ERROR
    assert stop_category_for_reason(KnownStopReason.SUCCESS.value) is StopCategory.ERROR


def test_emitted_dynamic_budget_stop_reason_families_are_budget() -> None:
    assert stop_category_for_reason("no_improve_25") is StopCategory.BUDGET
    assert stop_category_for_reason("stall_slip_limit_12") is StopCategory.BUDGET


def test_unknown_stop_reasons_are_errors_not_silent_budget() -> None:
    assert stop_category_for_reason("future_solver_reason_not_in_v1_schema") is StopCategory.ERROR


def test_stop_reason_details_are_json_safe_and_explicit() -> None:
    solution = SimpleNamespace(
        stop_reason=KnownStopReason.ALL_REJECTED_BY_HARD_CRIB.value,
        meta={"stop_detail": "hard crib rejected every candidate"},
        extras={},
    )

    assert stop_reason_details_from_solution(solution) == {
        "stop_category": "blocked_before_run",
        "stop_reason": "all_rejected_by_hard_crib",
        "stop_detail": "hard crib rejected every candidate",
        "blocked_before_run": True,
        "error_type": None,
    }


def test_stop_reason_details_preserve_error_type() -> None:
    solution = SimpleNamespace(
        stop_reason=KnownStopReason.ERROR.value,
        meta={"error_type": "RuntimeError"},
        extras={},
    )

    details = stop_reason_details_from_solution(solution)
    assert details["stop_category"] == "error"
    assert details["error_type"] == "RuntimeError"
