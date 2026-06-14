from __future__ import annotations

from types import SimpleNamespace

from rune_decrypter_prime.api.pipeline_helpers import (
    _SCORER_LANES_ERROR_CODE,
    _attach_scorer_lanes_to_meta,
)
from rune_decrypter_prime.api.run import _solver_report_details_from_solution


class _Report:
    def __init__(self, payload):
        self.payload = payload

    def to_json_dict(self):
        return self.payload


class _ReportWithBrokenJson:
    def to_json_dict(self):
        raise RuntimeError("json broke")


class _Scorer:
    def __init__(self, report):
        self._report = report

    def capability_report(self):
        if isinstance(self._report, BaseException):
            raise self._report
        return self._report


def _error_payload(res):
    payload = res.meta["scorer_lanes"]
    assert payload["lanes"] == []
    assert payload["components"] == []
    assert payload["error"]["code"] == _SCORER_LANES_ERROR_CODE
    return payload["error"]


def test_scorer_lanes_payload_is_attached_when_report_serializes() -> None:
    payload = {"lanes": [{"lane": "hamming"}], "components": []}
    res = SimpleNamespace(meta={})
    problem = SimpleNamespace(scorer=_Scorer(_Report(payload)))

    _attach_scorer_lanes_to_meta(res, problem)

    assert res.meta["scorer_lanes"] == payload


def test_scorer_lanes_capability_report_failure_is_visible() -> None:
    res = SimpleNamespace(meta={})
    problem = SimpleNamespace(scorer=_Scorer(RuntimeError("report broke")))

    _attach_scorer_lanes_to_meta(res, problem)

    error = _error_payload(res)
    assert error["message"] == "scorer capability_report() failed"
    assert error["exception_type"] == "RuntimeError"


def test_scorer_lanes_serialization_failure_is_visible() -> None:
    res = SimpleNamespace(meta={})
    problem = SimpleNamespace(scorer=_Scorer(_ReportWithBrokenJson()))

    _attach_scorer_lanes_to_meta(res, problem)

    error = _error_payload(res)
    assert error["message"] == "scorer capability report serialization failed"
    assert error["exception_type"] == "RuntimeError"


def test_scorer_lanes_non_dict_payload_is_visible_as_contract_error() -> None:
    res = SimpleNamespace(meta={})
    problem = SimpleNamespace(scorer=_Scorer(_Report(["not", "a", "dict"])))

    _attach_scorer_lanes_to_meta(res, problem)

    error = _error_payload(res)
    assert "must be dict" in error["message"]
    assert error.get("exception_type") is None


def test_solver_report_details_preserves_scorer_lanes_payload() -> None:
    scorer_lanes = {
        "lanes": [],
        "components": [],
        "error": {"code": _SCORER_LANES_ERROR_CODE, "message": "visible"},
    }
    solution = SimpleNamespace(stop_reason="done", meta={"scorer_lanes": scorer_lanes})

    details = _solver_report_details_from_solution(solution)

    assert details["scorer_lanes"] == scorer_lanes
