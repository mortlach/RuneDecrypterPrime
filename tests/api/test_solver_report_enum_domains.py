from __future__ import annotations

import pytest
from rdp import api


def test_solver_report_domains_are_distinct_typed_fields() -> None:
    report = api.advanced.SolverReport(
        solver=api.advanced.SolverKind.BEAM_SEARCH,
        parameters=api.advanced.ConfigurationResolution(
            requested={"width": 4}, effective={"width": 4}
        ),
        requested_seed=1,
        effective_seed=1,
        status=api.RunStatus(
            execution_status=api.advanced.ExecutionStatus.COMPLETED,
            stop_category=api.advanced.StopCategory.BUDGET,
            stop_reason=api.advanced.StopReason.MAX_ROUNDS_REACHED,
        ),
    )
    assert report.solver is api.advanced.SolverKind.BEAM_SEARCH
    assert report.status.stop_reason is api.advanced.StopReason.MAX_ROUNDS_REACHED


def test_solver_report_rejects_cross_domain_string_values() -> None:
    with pytest.raises(TypeError, match="solver"):
        api.advanced.SolverReport(
            solver="beam_search",  # type: ignore[arg-type]
            parameters=api.advanced.ConfigurationResolution(),
            requested_seed=1,
            effective_seed=1,
            status=api.RunStatus(
                execution_status=api.advanced.ExecutionStatus.COMPLETED,
                stop_category=api.advanced.StopCategory.BUDGET,
                stop_reason=api.advanced.StopReason.MAX_ROUNDS_REACHED,
            ),
        )
