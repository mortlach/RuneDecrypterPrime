from __future__ import annotations
from rdp import api
import rdp.api.solver_report
import pytest

def _report(*, normalized_params: dict[str, object] | None=None, details: dict[str, object] | None=None):
    return rdp.api.solver_report.build_solver_report(solver_name='test_solver', requested_seed=1, effective_seed=1, normalized_params=normalized_params or {}, details=details)

def test_solver_report_defaults_to_no_oracle_or_truth_use() -> None:
    report = _report()
    assert report.details[rdp.api.solver_report.SolverReportDetailKey.ORACLE_USE.value] == rdp.api.solver_report.OracleUse.NONE.value
    assert report.details[rdp.api.solver_report.SolverReportDetailKey.TRUTH_DATA_POLICY.value] == rdp.api.solver_report.TruthDataPolicy.NONE.value

def test_test_key_parameter_is_reported_as_test_or_tutorial_truth_use() -> None:
    report = _report(normalized_params={rdp.api.solver_report.SolverParamKey.TEST_KEY.value: [1, 2, 3]})
    assert report.details[rdp.api.solver_report.SolverReportDetailKey.ORACLE_USE.value] == rdp.api.solver_report.OracleUse.TEST_KEY.value
    assert report.details[rdp.api.solver_report.SolverReportDetailKey.TRUTH_DATA_POLICY.value] == rdp.api.solver_report.TruthDataPolicy.REPORTED_TEST_OR_TUTORIAL_ONLY.value

def test_known_key_execution_route_is_reported_without_borrowing_detail_key_domain() -> None:
    report = _report(details={rdp.api.solver_report.SolverReportDetailKey.EXECUTION_ROUTE.value: rdp.api.solver_report.ExecutionRoute.KNOWN_KEY_FASTPATH.value})
    assert report.details[rdp.api.solver_report.SolverReportDetailKey.EXECUTION_ROUTE.value] == rdp.api.solver_report.ExecutionRoute.KNOWN_KEY_FASTPATH.value
    assert report.details[rdp.api.solver_report.SolverReportDetailKey.ORACLE_USE.value] == rdp.api.solver_report.OracleUse.KNOWN_KEY_FASTPATH.value
    assert report.details[rdp.api.solver_report.SolverReportDetailKey.TRUTH_DATA_POLICY.value] == rdp.api.solver_report.TruthDataPolicy.REPORTED_TEST_OR_TUTORIAL_ONLY.value
    assert report.details[rdp.api.solver_report.SolverReportDetailKey.ORACLE.value] == {'available': True, 'used_for_scoring': False, 'used_for_ranking': False, 'used_for_stop': True, 'stop_reason': 'known_key_execution_completed', 'mode': 'unknown'}

def test_user_details_cannot_overwrite_generated_truth_contract_fields() -> None:
    with pytest.raises(ValueError, match='oracle_use'):
        _report(details={rdp.api.solver_report.SolverReportDetailKey.ORACLE_USE.value: rdp.api.solver_report.OracleUse.NONE.value})
    with pytest.raises(ValueError, match='truth_data_policy'):
        _report(details={rdp.api.solver_report.SolverReportDetailKey.TRUTH_DATA_POLICY.value: rdp.api.solver_report.TruthDataPolicy.NONE.value})
