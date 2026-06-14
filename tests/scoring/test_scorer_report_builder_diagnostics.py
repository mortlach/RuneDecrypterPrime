from __future__ import annotations

import pytest

from rune_decrypter_prime.scoring.scorer_report_builder import build_scorer_report


class _TelemetryFailureScorer:
    win = 10
    objective = "pct.logp.win10"

    def telemetry(self) -> dict[str, object]:
        raise RuntimeError("telemetry unavailable")

    def last_stats(self) -> dict[str, float]:
        return {"rank_metric": 3.0}


class _StatsFailureScorer:
    win = 10
    objective = "pct.logp.win10"

    def telemetry(self) -> dict[str, object]:
        return {"span_hamming_quality": 0.75}

    def last_stats(self) -> dict[str, float]:
        raise RuntimeError("stats unavailable")


def test_telemetry_failure_is_explicit_without_changing_score_or_metrics() -> None:
    report = build_scorer_report(
        scorer=_TelemetryFailureScorer(),
        objective_str="pct.logp.win10",
        score=10.0,
        raw_score=9.5,
    )

    assert report.score == 10.0
    assert report.raw_score == 9.5
    assert report.telemetry == {}
    assert report.metrics == {"rank_metric": 3.0}
    assert report.details["report_builder_diagnostics"] == {
        "telemetry_error": {
            "type": "RuntimeError",
            "message": "telemetry unavailable",
        }
    }


def test_last_stats_failure_is_explicit_and_extra_metrics_still_survive() -> None:
    report = build_scorer_report(
        scorer=_StatsFailureScorer(),
        objective_str="pct.logp.win10",
        score=10.0,
        raw_score=9.5,
        extra_metrics={"caller_metric": 4.0},
    )

    assert report.score == 10.0
    assert report.raw_score == 9.5
    assert report.telemetry == {"span_hamming_quality": 0.75}
    assert report.metrics == {"caller_metric": 4.0}
    assert report.details["span_hamming"] == {"quality": 0.75}
    assert report.details["report_builder_diagnostics"] == {
        "last_stats_error": {
            "type": "RuntimeError",
            "message": "stats unavailable",
        }
    }


def test_report_builder_diagnostics_cannot_be_masked_by_extra_details() -> None:
    with pytest.raises(ValueError, match="report_builder_diagnostics"):
        build_scorer_report(
            scorer=_TelemetryFailureScorer(),
            objective_str="pct.logp.win10",
            score=10.0,
            extra_details={
                "report_builder_diagnostics": {
                    "telemetry_error": {
                        "type": "RuntimeError",
                        "message": "caller masked diagnostic",
                    }
                }
            },
        )
