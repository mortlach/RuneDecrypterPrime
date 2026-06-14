from __future__ import annotations

from types import SimpleNamespace

from rune_decrypter_prime.api.stop_reason_contract import (
    STOP_CATEGORIES,
    stop_category_for_reason,
    stop_reason_details_from_solution,
)


def test_stop_categories_are_stable() -> None:
    assert STOP_CATEGORIES == frozenset({
        "success",
        "budget",
        "blocked_before_run",
        "error",
        "manual",
        "not_started",
    })


def test_stop_reason_category_mapping() -> None:
    assert stop_category_for_reason(None) == "not_started"
    assert stop_category_for_reason("done") == "success"
    assert stop_category_for_reason("patience") == "budget"
    assert stop_category_for_reason("all_rejected_by_hard_crib") == "blocked_before_run"
    assert stop_category_for_reason("error") == "error"
    assert stop_category_for_reason("manual") == "manual"


def test_stop_reason_details_are_json_safe_and_explicit() -> None:
    solution = SimpleNamespace(
        stop_reason="all_rejected_by_hard_crib",
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
        stop_reason="error",
        meta={"error_type": "RuntimeError"},
        extras={},
    )

    details = stop_reason_details_from_solution(solution)
    assert details["stop_category"] == "error"
    assert details["error_type"] == "RuntimeError"
