from __future__ import annotations

import importlib

import pytest


def _build_report(**kwargs):
    module = importlib.import_module("rune_decrypter_prime.api.solver_report")
    return module.build_solver_report(**kwargs)


def test_test_key_stop_reason_reports_truth_data_use() -> None:
    report = _build_report(
        solver_name="beam",
        requested_seed=123,
        effective_seed=123,
        normalized_params={"beam_width": 4, "test_key": [1, 2, 3]},
        stop_reason="test_key",
    )

    assert report.details["report_contract"] == {"version": "api_solver_report_details.v1"}
    assert report.details["oracle_use"] == "test_key"
    assert report.details["truth_data_policy"] == "reported_test_or_tutorial_only"


def test_production_report_defaults_truth_data_use_to_none() -> None:
    report = _build_report(
        solver_name="beam",
        requested_seed=None,
        effective_seed=0,
        normalized_params={"beam_width": 4},
        stop_reason="max_evals",
    )

    assert report.details["oracle_use"] == "none"
    assert report.details["truth_data_policy"] == "none"
    assert report.details["reproducibility"] == {
        "deterministic_seed_policy": "explicit_or_default_zero",
        "requested_seed": None,
        "effective_seed": 0,
        "solver_name": "beam",
    }


def test_known_key_fastpath_is_reported_and_existing_details_survive() -> None:
    report = _build_report(
        solver_name="beam",
        requested_seed=None,
        effective_seed=None,
        normalized_params={"beam_width": 1},
        stop_reason="done",
        details={"execution_route": "known_key_fastpath", "scorer_lanes": {"lanes": []}},
    )

    payload = report.to_json_dict()
    assert payload["details"]["oracle_use"] == "known_key_fastpath"
    assert payload["details"]["truth_data_policy"] == "reported_test_or_tutorial_only"
    assert payload["details"]["scorer_lanes"] == {"lanes": []}


@pytest.mark.parametrize(
    "reserved_key",
    ["report_contract", "oracle_use", "truth_data_policy", "reproducibility"],
)
def test_caller_details_cannot_overwrite_generated_solver_report_contract_sections(
    reserved_key: str,
) -> None:
    with pytest.raises(ValueError, match=reserved_key):
        _build_report(
            solver_name="beam",
            requested_seed=None,
            effective_seed=0,
            normalized_params={"beam_width": 4},
            details={reserved_key: "caller supplied"},
        )
