from __future__ import annotations

from rune_decrypter_prime.api.run import _solver_report_details_from_solution


class _SolutionLike:
    def __init__(self, meta=None, stop_reason=None) -> None:
        self.meta = meta
        self.stop_reason = stop_reason


def test_solver_report_details_carries_scorer_lanes_from_solution_meta() -> None:
    scorer_lanes = {"lanes": [], "components": []}
    solution = _SolutionLike(meta={"scorer_lanes": scorer_lanes}, stop_reason="done")

    details = _solver_report_details_from_solution(solution)

    assert details["scorer_lanes"] == scorer_lanes
    assert details["stop_category"] == "success"
    assert details["stop_reason"] == "done"


def test_solver_report_details_includes_stop_schema_when_scorer_lanes_missing() -> None:
    details = _solver_report_details_from_solution(_SolutionLike(meta={}, stop_reason="patience"))

    assert details["stop_category"] == "budget"
    assert details["stop_reason"] == "patience"
    assert details["blocked_before_run"] is False


def test_solver_report_details_handles_missing_meta() -> None:
    details = _solver_report_details_from_solution(object())

    assert details["stop_category"] == "not_started"
    assert details["stop_reason"] is None
