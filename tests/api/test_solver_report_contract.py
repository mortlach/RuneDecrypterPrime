from __future__ import annotations
from rdp import api
import pytest


def _status() -> api.RunStatus:
    return api.RunStatus(
        execution_status=api.advanced.ExecutionStatus.COMPLETED,
        stop_category=api.advanced.StopCategory.BUDGET,
        stop_reason=api.advanced.StopReason.MAX_STEPS_REACHED,
        runtime_reason="max_steps",
    )


def test_solver_report_uses_final_typed_fields() -> None:
    report = api.advanced.SolverReport(
        solver=api.advanced.SolverKind.BEAM_SEARCH,
        parameters=api.advanced.ConfigurationResolution(
            requested={"width": 4}, effective={"width": 4}
        ),
        requested_seed=7,
        effective_seed=7,
        status=_status(),
        best_key=(1, 2),
        best_score=0.5,
        evaluations=8,
        steps=3,
        tokens_processed=24,
    )
    assert report.solver is api.advanced.SolverKind.BEAM_SEARCH
    assert report.status.stop_reason is api.advanced.StopReason.MAX_STEPS_REACHED
    assert report.best_key == (1, 2)


def test_solver_report_rejects_invalid_typed_values() -> None:
    with pytest.raises((TypeError, ValueError)):
        api.advanced.SolverReport(
            solver=api.advanced.SolverKind("not-a-solver"),
            parameters=api.advanced.ConfigurationResolution(),
            requested_seed=None,
            effective_seed=0,
            status=_status(),
        )
