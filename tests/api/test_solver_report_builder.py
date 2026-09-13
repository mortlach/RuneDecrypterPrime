from __future__ import annotations

import math
from pathlib import Path

import pytest
from rdp import api


def _report(**overrides: object) -> api.advanced.SolverReport:
    values: dict[str, object] = {
        "solver": api.advanced.SolverKind.BEAM_SEARCH,
        "parameters": api.advanced.ConfigurationResolution(
            requested={"width": 4}, effective={"width": 4}
        ),
        "requested_seed": 123,
        "effective_seed": 123,
        "status": api.RunStatus(
            execution_status=api.advanced.ExecutionStatus.COMPLETED,
            stop_category=api.advanced.StopCategory.BUDGET,
            stop_reason=api.advanced.StopReason.MAX_STEPS_REACHED,
        ),
        "best_score": 10.5,
        "best_key": (1, 2, 3),
        "steps": 7,
        "evaluations": 8,
        "tokens_processed": 9,
        "wall_time_seconds": 0.5,
        "decrypt_time_seconds": 0.2,
        "score_time_seconds": 0.3,
        "details": {"route": "ordinary"},
    }
    values.update(overrides)
    return api.advanced.SolverReport(**values)  # type: ignore[arg-type]


def test_solver_report_serializes_its_declared_contract() -> None:
    payload = _report().to_json_dict()
    assert payload["solver"] == "beam_search"
    assert payload["parameters"] == {
        "requested": {"width": 4},
        "effective": {"width": 4},
    }
    assert payload["requested_seed"] == 123
    assert payload["effective_seed"] == 123
    assert payload["status"]["stop_reason"] == "max_steps_reached"
    assert payload["best_key"] == [1, 2, 3]
    assert payload["details"] == {"route": "ordinary"}


def test_solver_report_preserves_requested_and_effective_seeds() -> None:
    report = _report(requested_seed=None, effective_seed=0)
    assert report.requested_seed is None
    assert report.effective_seed == 0


def test_configuration_resolution_copies_and_validates_nested_values() -> None:
    params = {"width": 4, "nested": {"weights": [1, 2]}}
    resolution = api.advanced.ConfigurationResolution(
        requested=params, effective=params
    )
    params["nested"]["weights"].append(3)  # type: ignore[index, union-attr]
    assert resolution.to_json_dict()["requested"] == {
        "width": 4,
        "nested": {"weights": [1, 2]},
    }


@pytest.mark.parametrize(
    "bad",
    [
        {"artifact": Path.cwd().resolve() / "absolute" / "report.json"},
        {"bad": math.inf},
        {"bad": object()},
    ],
)
def test_configuration_resolution_rejects_nonportable_values(
    bad: dict[str, object],
) -> None:
    with pytest.raises((TypeError, ValueError)):
        api.advanced.ConfigurationResolution(requested=bad)


def test_solver_report_rejects_invalid_concrete_key() -> None:
    with pytest.raises(TypeError):
        _report(best_key=(1, True))


def test_solver_report_requires_typed_solver_and_status() -> None:
    with pytest.raises(TypeError):
        _report(solver="beam")
    with pytest.raises(TypeError):
        _report(status="max_steps")


def test_run_does_not_offer_conditional_report_return() -> None:
    assert "return_solver_report" not in api.run.__annotations__
