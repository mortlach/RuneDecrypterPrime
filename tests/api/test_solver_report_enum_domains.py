from __future__ import annotations

from rune_decrypter_prime.api.solver_report import (
    OracleUse,
    SolverParamKey,
    SolverReportDetailKey,
    SolverStopReason,
    TruthDataPolicy,
    build_solver_report,
)


def test_solver_report_test_key_wire_value_has_separate_domains() -> None:
    assert SolverParamKey.TEST_KEY.value == "test_key"
    assert SolverStopReason.TEST_KEY.value == "test_key"
    assert OracleUse.TEST_KEY.value == "test_key"
    assert SolverParamKey.TEST_KEY is not OracleUse.TEST_KEY
    assert SolverStopReason.TEST_KEY is not OracleUse.TEST_KEY


def test_solver_report_marks_oracle_use_from_solver_param_key() -> None:
    report = build_solver_report(
        solver_name="beam",
        requested_seed=1,
        effective_seed=1,
        normalized_params={SolverParamKey.TEST_KEY.value: [1, 2, 3]},
    )

    details = report.to_json_dict()["details"]
    assert details[SolverReportDetailKey.ORACLE_USE.value] == OracleUse.TEST_KEY.value
    assert (
        details[SolverReportDetailKey.TRUTH_DATA_POLICY.value]
        == TruthDataPolicy.REPORTED_TEST_OR_TUTORIAL_ONLY.value
    )


def test_solver_report_marks_oracle_use_from_solver_stop_reason() -> None:
    report = build_solver_report(
        solver_name="beam",
        requested_seed=1,
        effective_seed=1,
        normalized_params={},
        stop_reason=SolverStopReason.TEST_KEY.value,
    )

    details = report.to_json_dict()["details"]
    assert details[SolverReportDetailKey.ORACLE_USE.value] == OracleUse.TEST_KEY.value
    assert (
        details[SolverReportDetailKey.TRUTH_DATA_POLICY.value]
        == TruthDataPolicy.REPORTED_TEST_OR_TUTORIAL_ONLY.value
    )
