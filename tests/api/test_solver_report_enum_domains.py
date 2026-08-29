from __future__ import annotations
from rdp import api
import rdp.api.solver_report

def test_solver_report_test_key_wire_value_has_separate_domains() -> None:
    assert rdp.api.solver_report.SolverParamKey.TEST_KEY.value == 'test_key'
    assert rdp.api.solver_report.SolverStopReason.TEST_KEY.value == 'test_key'
    assert rdp.api.solver_report.OracleUse.TEST_KEY.value == 'test_key'
    assert rdp.api.solver_report.SolverParamKey.TEST_KEY is not rdp.api.solver_report.OracleUse.TEST_KEY
    assert rdp.api.solver_report.SolverStopReason.TEST_KEY is not rdp.api.solver_report.OracleUse.TEST_KEY

def test_solver_report_marks_oracle_use_from_solver_param_key() -> None:
    report = rdp.api.solver_report.build_solver_report(solver_name='beam', requested_seed=1, effective_seed=1, normalized_params={rdp.api.solver_report.SolverParamKey.TEST_KEY.value: [1, 2, 3]})
    details = report.to_json_dict()['details']
    assert details[rdp.api.solver_report.SolverReportDetailKey.ORACLE_USE.value] == rdp.api.solver_report.OracleUse.TEST_KEY.value
    assert details[rdp.api.solver_report.SolverReportDetailKey.TRUTH_DATA_POLICY.value] == rdp.api.solver_report.TruthDataPolicy.REPORTED_TEST_OR_TUTORIAL_ONLY.value

def test_solver_report_marks_oracle_use_from_solver_stop_reason() -> None:
    report = rdp.api.solver_report.build_solver_report(solver_name='beam', requested_seed=1, effective_seed=1, normalized_params={}, stop_reason=rdp.api.solver_report.SolverStopReason.TEST_KEY.value)
    details = report.to_json_dict()['details']
    assert details[rdp.api.solver_report.SolverReportDetailKey.ORACLE_USE.value] == rdp.api.solver_report.OracleUse.TEST_KEY.value
    assert details[rdp.api.solver_report.SolverReportDetailKey.TRUTH_DATA_POLICY.value] == rdp.api.solver_report.TruthDataPolicy.REPORTED_TEST_OR_TUTORIAL_ONLY.value
