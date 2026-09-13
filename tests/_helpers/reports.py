"""Canonical typed report fixtures for public-API tests."""

from __future__ import annotations

from collections.abc import Mapping

from rdp import api
from rdp.api.stop_reason_contract import stop_category_for_reason


def completed_status(
    stop_reason: api.advanced.StopReason = api.advanced.StopReason.MAX_STEPS_REACHED,
    *,
    runtime_reason: str | None = None,
) -> api.RunStatus:
    """Build a completed status without routing legacy reason strings."""

    return api.RunStatus(
        execution_status=api.advanced.ExecutionStatus.COMPLETED,
        stop_category=stop_category_for_reason(stop_reason),
        stop_reason=stop_reason,
        runtime_reason=runtime_reason,
    )


def make_solver_report(
    *,
    solver: api.advanced.SolverKind = api.advanced.SolverKind.BEAM_SEARCH,
    requested_seed: int | None = 0,
    effective_seed: int = 0,
    parameters: Mapping[str, object] | None = None,
    status: api.RunStatus | None = None,
    best_key: tuple[int, ...] | None = None,
    best_score: float | None = None,
    evaluations: int = 0,
    steps: int = 0,
    tokens_processed: int = 0,
    wall_time_seconds: float = 0.0,
    decrypt_time_seconds: float = 0.0,
    score_time_seconds: float = 0.0,
    details: Mapping[str, object] | None = None,
) -> api.advanced.SolverReport:
    """Construct the immutable public report from its declared typed fields."""

    resolved = dict(parameters or {})
    return api.advanced.SolverReport(
        solver=solver,
        parameters=api.advanced.ConfigurationResolution(
            requested=resolved,
            effective=resolved,
        ),
        requested_seed=requested_seed,
        effective_seed=effective_seed,
        status=status or completed_status(),
        best_key=best_key,
        best_score=best_score,
        evaluations=evaluations,
        steps=steps,
        tokens_processed=tokens_processed,
        wall_time_seconds=wall_time_seconds,
        decrypt_time_seconds=decrypt_time_seconds,
        score_time_seconds=score_time_seconds,
        details=dict(details or {}),
    )
