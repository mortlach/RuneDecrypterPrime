from __future__ import annotations

import pytest

from rune_decrypter_prime.api.solver_report import (
    OracleUse,
    SolverReportDetailKey,
    SolverReportDetailsVersion,
    TruthDataPolicy,
    build_solver_report,
)


def test_solver_report_contract_labels_are_enum_backed() -> None:
    assert SolverReportDetailKey.REPORT_CONTRACT.value == "report_contract"
    assert SolverReportDetailKey.ORACLE_USE.value == "oracle_use"
    assert SolverReportDetailKey.TRUTH_DATA_POLICY.value == "truth_data_policy"
    assert SolverReportDetailKey.REPRODUCIBILITY.value == "reproducibility"
    assert OracleUse.NONE.value == "none"
    assert OracleUse.TEST_KEY.value == "test_key"
    assert OracleUse.KNOWN_KEY_FASTPATH.value == "known_key_fastpath"
    assert TruthDataPolicy.NONE.value == "none"
    assert TruthDataPolicy.REPORTED_TEST_OR_TUTORIAL_ONLY.value == "reported_test_or_tutorial_only"
    assert SolverReportDetailsVersion.V1.value == "api_solver_report_details.v1"


def test_solver_report_json_detail_strings_remain_stable() -> None:
    report = build_solver_report(
        solver_name="beam",
        requested_seed=None,
        effective_seed=0,
        normalized_params={"beam_width": 4},
    )

    details = report.to_json_dict()["details"]
    assert details["report_contract"] == {"version": "api_solver_report_details.v1"}
    assert details["oracle_use"] == "none"
    assert details["truth_data_policy"] == "none"
    assert details["reproducibility"]["deterministic_seed_policy"] == "explicit_or_default_zero"


@pytest.mark.parametrize(
    "reserved_key",
    [
        SolverReportDetailKey.REPORT_CONTRACT.value,
        SolverReportDetailKey.ORACLE_USE.value,
        SolverReportDetailKey.TRUTH_DATA_POLICY.value,
        SolverReportDetailKey.REPRODUCIBILITY.value,
    ],
)
def test_solver_report_enum_owned_sections_cannot_be_caller_supplied(reserved_key: str) -> None:
    with pytest.raises(ValueError, match=reserved_key):
        build_solver_report(
            solver_name="beam",
            requested_seed=None,
            effective_seed=0,
            normalized_params={"beam_width": 4},
            details={reserved_key: "caller supplied"},
        )
