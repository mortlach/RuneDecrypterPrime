from __future__ import annotations

import pytest

from rune_decrypter_prime.api.solver_report import (
    ExecutionRoute,
    OracleUse,
    SolverParamKey,
    SolverReportDetailKey,
    TruthDataPolicy,
    build_solver_report,
)


def _report(*, normalized_params: dict[str, object] | None = None, details: dict[str, object] | None = None):
    return build_solver_report(
        solver_name="test_solver",
        requested_seed=1,
        effective_seed=1,
        normalized_params=normalized_params or {},
        details=details,
    )


def test_solver_report_defaults_to_no_oracle_or_truth_use() -> None:
    report = _report()

    assert report.details[SolverReportDetailKey.ORACLE_USE.value] == OracleUse.NONE.value
    assert report.details[SolverReportDetailKey.TRUTH_DATA_POLICY.value] == TruthDataPolicy.NONE.value


def test_test_key_parameter_is_reported_as_test_or_tutorial_truth_use() -> None:
    report = _report(normalized_params={SolverParamKey.TEST_KEY.value: [1, 2, 3]})

    assert report.details[SolverReportDetailKey.ORACLE_USE.value] == OracleUse.TEST_KEY.value
    assert (
        report.details[SolverReportDetailKey.TRUTH_DATA_POLICY.value]
        == TruthDataPolicy.REPORTED_TEST_OR_TUTORIAL_ONLY.value
    )


def test_known_key_execution_route_is_reported_without_borrowing_detail_key_domain() -> None:
    report = _report(
        details={SolverReportDetailKey.EXECUTION_ROUTE.value: ExecutionRoute.KNOWN_KEY_FASTPATH.value}
    )

    assert report.details[SolverReportDetailKey.EXECUTION_ROUTE.value] == ExecutionRoute.KNOWN_KEY_FASTPATH.value
    assert report.details[SolverReportDetailKey.ORACLE_USE.value] == OracleUse.KNOWN_KEY_FASTPATH.value
    assert (
        report.details[SolverReportDetailKey.TRUTH_DATA_POLICY.value]
        == TruthDataPolicy.REPORTED_TEST_OR_TUTORIAL_ONLY.value
    )


def test_user_details_cannot_overwrite_generated_truth_contract_fields() -> None:
    with pytest.raises(ValueError, match="oracle_use"):
        _report(details={SolverReportDetailKey.ORACLE_USE.value: OracleUse.NONE.value})

    with pytest.raises(ValueError, match="truth_data_policy"):
        _report(details={SolverReportDetailKey.TRUTH_DATA_POLICY.value: TruthDataPolicy.NONE.value})
