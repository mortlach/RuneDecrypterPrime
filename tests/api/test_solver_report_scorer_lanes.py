from __future__ import annotations
import rdp.api.pipeline_helpers
import importlib


class _SolutionLike:
    def __init__(self, meta=None, stop_reason=None) -> None:
        self.meta = meta
        self.stop_reason = stop_reason


class _ProblemLike:
    def __init__(self, scorer) -> None:
        self.scorer = scorer


def test_scorer_report_details_carries_scorer_lanes_from_solution_meta() -> None:
    scorer_lanes = {"lanes": [], "components": []}
    solution = _SolutionLike(
        meta={"scorer_lanes": scorer_lanes}, stop_reason="max_rounds_reached"
    )
    run_module = importlib.import_module("rdp.api.run")
    details = run_module._scorer_report_details_from_solution(solution)
    assert details["scorer_lanes"] == scorer_lanes


def test_scorer_report_details_is_empty_when_scorer_lanes_missing() -> None:
    run_module = importlib.import_module("rdp.api.run")
    details = run_module._scorer_report_details_from_solution(
        _SolutionLike(meta={}, stop_reason="patience")
    )
    assert details == {}


def test_solver_report_details_handles_missing_meta() -> None:
    run_module = importlib.import_module("rdp.api.run")
    details = run_module._scorer_report_details_from_solution(object())
    assert details == {}


def test_scorer_lanes_report_failure_cannot_silently_disappear_from_solver_report_details() -> (
    None
):
    class _BrokenScorer:
        def capability_report(self):
            raise RuntimeError("capability report exploded")

    solution = _SolutionLike(meta={}, stop_reason="max_rounds_reached")
    rdp.api.pipeline_helpers._attach_scorer_lanes_to_meta(
        solution, _ProblemLike(_BrokenScorer())
    )
    run_module = importlib.import_module("rdp.api.run")
    details = run_module._scorer_report_details_from_solution(solution)
    scorer_lanes = details["scorer_lanes"]
    assert scorer_lanes["lanes"] == []
    assert scorer_lanes["components"] == []
    assert scorer_lanes["error"]["code"] == "scorer_lanes_unavailable"
    assert scorer_lanes["error"]["exception_type"] == "RuntimeError"


def test_scorer_lanes_serialization_failure_cannot_silently_disappear_from_solver_report_details() -> (
    None
):
    class _BrokenReport:
        def to_json_dict(self):
            raise ValueError("serialization exploded")

    class _BrokenScorer:
        def capability_report(self):
            return _BrokenReport()

    solution = _SolutionLike(meta={}, stop_reason="max_rounds_reached")
    rdp.api.pipeline_helpers._attach_scorer_lanes_to_meta(
        solution, _ProblemLike(_BrokenScorer())
    )
    run_module = importlib.import_module("rdp.api.run")
    details = run_module._scorer_report_details_from_solution(solution)
    scorer_lanes = details["scorer_lanes"]
    assert scorer_lanes["error"]["code"] == "scorer_lanes_unavailable"
    assert scorer_lanes["error"]["exception_type"] == "ValueError"
