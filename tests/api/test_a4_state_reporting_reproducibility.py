from __future__ import annotations

import json

import pytest

import rdp.api.stop_reason_contract as stop_contract
from rdp import api


@pytest.mark.parametrize(
    ("runtime_reason", "reason", "category"),
    (
        (
            "done",
            api.advanced.StopReason.UNEXPECTED_EXCEPTION,
            api.advanced.StopCategory.ERROR,
        ),
        (
            "target_score",
            api.advanced.StopReason.TARGET_SCORE_REACHED,
            api.advanced.StopCategory.SUCCESS,
        ),
        (
            "max_evals",
            api.advanced.StopReason.MAX_EVALUATIONS_REACHED,
            api.advanced.StopCategory.BUDGET,
        ),
        (
            "test_key",
            api.advanced.StopReason.ORACLE_TEST_KEY_USED,
            api.advanced.StopCategory.SUCCESS,
        ),
        (
            "blocked_before_run",
            api.advanced.StopReason.BLOCKED_BEFORE_RUN,
            api.advanced.StopCategory.BLOCKED_BEFORE_RUN,
        ),
    ),
)
def test_runtime_reasons_map_to_typed_status(
    runtime_reason: str,
    reason: api.advanced.StopReason,
    category: api.advanced.StopCategory,
) -> None:
    status = stop_contract.build_run_status(
        runtime_reason=runtime_reason,
        execution_status=stop_contract.execution_status_for_category(category),
    )
    assert status.stop_reason is reason
    assert status.stop_category is category
    assert status.runtime_reason == runtime_reason
    json.dumps(status.to_json_dict())


def test_completed_execution_without_reason_is_explicit_error() -> None:
    status = stop_contract.build_run_status(
        runtime_reason=None,
        execution_status=api.advanced.ExecutionStatus.COMPLETED,
    )
    assert status.stop_reason is api.advanced.StopReason.UNKNOWN_RUNTIME_REASON
    assert status.stop_category is api.advanced.StopCategory.ERROR


def test_manual_and_error_execution_states_remain_distinct() -> None:
    manual = stop_contract.build_run_status(
        runtime_reason="interrupted",
        execution_status=api.advanced.ExecutionStatus.MANUAL_STOP,
    )
    error = stop_contract.build_run_status(
        runtime_reason="exception",
        execution_status=api.advanced.ExecutionStatus.ERROR,
        error_type="RuntimeError",
        stop_detail="boom",
    )
    assert manual.stop_reason is api.advanced.StopReason.MANUAL_STOP
    assert error.stop_reason is api.advanced.StopReason.UNEXPECTED_EXCEPTION
    assert error.error_type == "RuntimeError"


def test_oracle_report_rejects_use_without_available_or_reason() -> None:
    with pytest.raises(ValueError, match="available=True"):
        api.advanced.OracleReport(
            used_for_stop=True,
            stop_reason=api.advanced.StopReason.TARGET_SCORE_REACHED,
            mode=api.advanced.OracleMode.TEST,
        )
    with pytest.raises(ValueError, match="recorded together"):
        api.advanced.OracleReport(
            available=True,
            used_for_stop=True,
            mode=api.advanced.OracleMode.TEST,
        )


def test_solver_report_uses_typed_status_and_configuration() -> None:
    status = stop_contract.build_run_status(
        runtime_reason="max_rounds_reached",
        execution_status=api.advanced.ExecutionStatus.COMPLETED,
    )
    parameters = api.advanced.ConfigurationResolution(
        requested={"width": 4},
        effective={"width": 4, "plateau_rounds": 16},
    )
    report = api.advanced.SolverReport(
        solver=api.advanced.SolverKind.BEAM_SEARCH,
        parameters=parameters,
        requested_seed=None,
        effective_seed=0,
        status=status,
        best_key=(1, 2),
        best_score=0.5,
    )
    payload = report.to_json_dict()
    assert payload["status"]["runtime_reason"] == "max_rounds_reached"
    assert payload["parameters"]["effective"]["plateau_rounds"] == 16
    assert payload["best_key"] == [1, 2]
    json.dumps(payload)


def test_reproducibility_metadata_is_typed_and_json_safe() -> None:
    metadata = api.advanced.ReproducibilityMetadata(
        backend=api.advanced.ScorerBackend.NUMPY,
        compute_device=api.ComputeDevice.CPU,
        compute_dtype=api.advanced.FloatDType.FLOAT64,
        requested_seed=4,
        effective_seed=4,
        stochastic=True,
        objective={"kind": "percentile", "window_size": 10},
        asset_ids=("ci-light",),
        asset_hashes={"ci-light": "abc"},
        stop_category=api.advanced.StopCategory.BUDGET,
        stop_reason=api.advanced.StopReason.MAX_STEPS_REACHED,
    )
    payload = metadata.to_json_dict()
    assert payload["backend"] == "numpy"
    assert payload["compute_device"] == "cpu"
    assert payload["requested_seed"] == 4
    assert payload["effective_seed"] == 4
    json.dumps(payload)
