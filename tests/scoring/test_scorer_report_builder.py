from __future__ import annotations

import pytest

from rune_decrypter_prime.scoring.scorer_report_builder import build_scorer_report


pytestmark = pytest.mark.tier_a


class _FakeScorer:
    def __init__(self) -> None:
        self.win = 10

    def telemetry(self):
        return {"impl": "numpy", "device": "cpu", "dtype": "float64"}

    def last_stats(self):
        return {"score_mean": 0.12, "score_std": 0.34, "ignored": "x"}


def test_build_scorer_report_normalises_fields() -> None:
    scorer = _FakeScorer()
    report = build_scorer_report(
        scorer=scorer,
        objective_str="pct.logp.win10",
        score=0.123,
        raw_score=0.12,
        cost_ms=5.0,
        extra_metrics={"n_windows": 7},
        extra_details={"stage": "A"},
    )
    payload = report.to_json_dict()

    assert payload["objective_spec"]["family"] == "pct"
    assert payload["objective_spec"]["stat"] == "logp"
    assert payload["objective_spec"]["win"] == 10
    assert payload["metrics"]["score_mean"] == pytest.approx(0.12)
    assert payload["metrics"]["n_windows"] == pytest.approx(7.0)
    assert payload["telemetry"]["impl"] == "numpy"
    assert payload["details"]["stage"] == "A"

