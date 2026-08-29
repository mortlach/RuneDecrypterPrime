from __future__ import annotations
import pytest
from rune_decrypter_prime.scoring.scorer_report_builder import build_scorer_report

pytestmark = pytest.mark.tier_a


class _FakeScorer:
    def __init__(self) -> None:
        self.win = 10

    def telemetry(self):
        return {
            "impl": "numpy",
            "device": "cpu",
            "dtype": "float64",
            "span_hamming_mode": "calibrated",
            "span_hamming_pct": 0.9,
            "word_ngram_judge_active": True,
            "word_ngram_judge_report_xent": 1.23,
            "hamming_dictionary_policy": "normal",
        }

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
    assert payload["objective"] == {
        "kind": "percentile",
        "statistic": "log_probability",
        "window_size": 10,
    }
    assert payload["metrics"]["score_mean"] == pytest.approx(0.12)
    assert payload["metrics"]["n_windows"] == pytest.approx(7.0)
    assert payload["telemetry"]["impl"] == "numpy"
    assert payload["details"]["stage"] == "A"
    assert payload["details"]["span_hamming"]["mode"] == "calibrated"
    assert payload["details"]["span_hamming"]["pct"] == pytest.approx(0.9)
    assert payload["details"]["word_ngrams"]["active"] is True
    assert payload["details"]["word_ngrams"]["report_xent"] == pytest.approx(1.23)
    assert (
        payload["details"]["hamming_dictionary"]["hamming_dictionary_policy"]
        == "normal"
    )
