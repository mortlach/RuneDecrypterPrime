from __future__ import annotations

import pytest

from rune_decrypter_prime.scoring.scorer_report_builder import (
    DiagnosticField,
    ReportBuilderDiagnosticKey,
    ScorerReportDetailKey,
    build_scorer_report,
)


class _HealthyScorer:
    win = 10
    objective = "pct.logp.win10"

    def telemetry(self) -> dict[str, object]:
        return {}

    def last_stats(self) -> dict[str, float]:
        return {"rank_metric": 3.0}


class _TelemetryFailureScorer:
    win = 10
    objective = "pct.logp.win10"

    def telemetry(self) -> dict[str, object]:
        raise RuntimeError("telemetry unavailable")

    def last_stats(self) -> dict[str, float]:
        return {"rank_metric": 3.0}


def test_scorer_report_detail_labels_are_enum_backed() -> None:
    assert ScorerReportDetailKey.REPORT_BUILDER_DIAGNOSTICS.value == "report_builder_diagnostics"
    assert ScorerReportDetailKey.SCORER_LANES.value == "scorer_lanes"
    assert ScorerReportDetailKey.ORACLE_USE.value == "oracle_use"
    assert ReportBuilderDiagnosticKey.TELEMETRY_ERROR.value == "telemetry_error"
    assert ReportBuilderDiagnosticKey.LAST_STATS_ERROR.value == "last_stats_error"
    assert DiagnosticField.TYPE.value == "type"
    assert DiagnosticField.MESSAGE.value == "message"


def test_report_builder_diagnostics_cannot_be_caller_supplied_on_healthy_path() -> None:
    with pytest.raises(ValueError, match="report_builder_diagnostics"):
        build_scorer_report(
            scorer=_HealthyScorer(),
            objective_str="pct.logp.win10",
            score=1.0,
            extra_details={
                "report_builder_diagnostics": {
                    "telemetry_error": {
                        "type": "RuntimeError",
                        "message": "caller supplied fake diagnostic",
                    }
                }
            },
        )


def test_generated_diagnostic_keys_emit_stable_json_strings() -> None:
    report = build_scorer_report(
        scorer=_TelemetryFailureScorer(),
        objective_str="pct.logp.win10",
        score=1.0,
    )

    payload = report.to_json_dict()
    assert payload["details"]["report_builder_diagnostics"] == {
        "telemetry_error": {
            "type": "RuntimeError",
            "message": "telemetry unavailable",
        }
    }
