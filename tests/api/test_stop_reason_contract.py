from __future__ import annotations
from rdp import api
import rdp.api.stop_reason_contract
from types import SimpleNamespace

def test_stop_categories_are_stable_and_enum_backed() -> None:
    assert rdp.api.stop_reason_contract.STOP_CATEGORIES == frozenset((item.value for item in api.advanced.StopCategory))
    assert rdp.api.stop_reason_contract.STOP_CATEGORIES == frozenset({'success', 'budget', 'blocked_before_run', 'error', 'manual', 'not_started'})

def test_stop_reason_category_mapping() -> None:
    assert rdp.api.stop_reason_contract.stop_category_for_reason(None) is api.advanced.StopCategory.NOT_STARTED
    assert rdp.api.stop_reason_contract.stop_category_for_reason(rdp.api.stop_reason_contract.KnownStopReason.DONE.value) is api.advanced.StopCategory.ERROR
    assert rdp.api.stop_reason_contract.stop_category_for_reason(rdp.api.stop_reason_contract.KnownStopReason.PATIENCE.value) is api.advanced.StopCategory.BUDGET
    assert rdp.api.stop_reason_contract.stop_category_for_reason(rdp.api.stop_reason_contract.KnownStopReason.ALL_REJECTED_BY_HARD_CRIB.value) is api.advanced.StopCategory.BLOCKED_BEFORE_RUN
    assert rdp.api.stop_reason_contract.stop_category_for_reason(rdp.api.stop_reason_contract.KnownStopReason.ERROR.value) is api.advanced.StopCategory.ERROR
    assert rdp.api.stop_reason_contract.stop_category_for_reason(rdp.api.stop_reason_contract.KnownStopReason.MANUAL.value) is api.advanced.StopCategory.MANUAL

def test_explicit_positive_stop_reason_aliases_are_success() -> None:
    assert rdp.api.stop_reason_contract.stop_category_for_reason(rdp.api.stop_reason_contract.KnownStopReason.TARGET_SCORE.value) is api.advanced.StopCategory.SUCCESS
    assert rdp.api.stop_reason_contract.stop_category_for_reason(rdp.api.stop_reason_contract.KnownStopReason.STOP_SCORE.value) is api.advanced.StopCategory.SUCCESS
    assert rdp.api.stop_reason_contract.stop_category_for_reason(rdp.api.stop_reason_contract.KnownStopReason.TEST_KEY.value) is api.advanced.StopCategory.SUCCESS

def test_ambiguous_legacy_completion_is_not_promoted_to_success() -> None:
    assert rdp.api.stop_reason_contract.stop_category_for_reason(rdp.api.stop_reason_contract.KnownStopReason.DONE.value) is api.advanced.StopCategory.ERROR
    assert rdp.api.stop_reason_contract.stop_category_for_reason(rdp.api.stop_reason_contract.KnownStopReason.SUCCESS.value) is api.advanced.StopCategory.ERROR

def test_emitted_dynamic_budget_stop_reason_families_are_budget() -> None:
    assert rdp.api.stop_reason_contract.stop_category_for_reason('no_improve_25') is api.advanced.StopCategory.BUDGET
    assert rdp.api.stop_reason_contract.stop_category_for_reason('stall_slip_limit_12') is api.advanced.StopCategory.BUDGET

def test_unknown_stop_reasons_are_errors_not_silent_budget() -> None:
    assert rdp.api.stop_reason_contract.stop_category_for_reason('future_solver_reason_not_in_v1_schema') is api.advanced.StopCategory.ERROR

def test_stop_reason_details_are_json_safe_and_explicit() -> None:
    solution = SimpleNamespace(stop_reason=rdp.api.stop_reason_contract.KnownStopReason.ALL_REJECTED_BY_HARD_CRIB.value, meta={'stop_detail': 'hard crib rejected every candidate'}, extras={})
    assert rdp.api.stop_reason_contract.stop_reason_details_from_solution(solution) == {'stop_category': 'blocked_before_run', 'stop_reason': 'all_rejected_by_hard_crib', 'stop_detail': 'hard crib rejected every candidate', 'blocked_before_run': True, 'error_type': None}

def test_stop_reason_details_preserve_error_type() -> None:
    solution = SimpleNamespace(stop_reason=rdp.api.stop_reason_contract.KnownStopReason.ERROR.value, meta={'error_type': 'RuntimeError'}, extras={})
    details = rdp.api.stop_reason_contract.stop_reason_details_from_solution(solution)
    assert details['stop_category'] == 'error'
    assert details['error_type'] == 'RuntimeError'
