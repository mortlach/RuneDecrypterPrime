from __future__ import annotations

from rune_decrypter_prime.api.run import _solver_report_details_from_solution


class _SolutionLike:
    def __init__(self, meta=None) -> None:
        self.meta = meta


def test_solver_report_details_carries_scorer_lanes_from_solution_meta() -> None:
    scorer_lanes = {"lanes": [], "components": []}
    solution = _SolutionLike(meta={"scorer_lanes": scorer_lanes})

    assert _solver_report_details_from_solution(solution) == {
        "scorer_lanes": scorer_lanes,
    }


def test_solver_report_details_omits_missing_scorer_lanes() -> None:
    assert _solver_report_details_from_solution(_SolutionLike(meta={})) == {}
    assert _solver_report_details_from_solution(object()) == {}
