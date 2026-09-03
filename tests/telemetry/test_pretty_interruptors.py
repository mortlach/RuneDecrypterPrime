from __future__ import annotations

from rdp import api
import pytest
from tests._helpers.reports import completed_status, make_solver_report

pytestmark = pytest.mark.tier_a


def _result(*, telemetry: dict[str, object] | None = None) -> api.RunResult:
    report = make_solver_report(
        requested_seed=1,
        effective_seed=1,
        parameters={},
        status=completed_status(api.advanced.StopReason.TARGET_SCORE_REACHED),
        best_score=0.123,
        best_key=(1, 2, 3, 4, 9),
    )
    return api.RunResult(
        plaintext=(0, 1),
        plaintext_text='AB',
        key=(1, 2, 3, 4, 9),
        score=0.123,
        status=report.status,
        solver_report=report,
        scorer_report=api.advanced.ScorerReport(
            objective=api.advanced.ScoringObjective.percentile_log_probability(
                window_size=10
            ),
            score=0.123,
        ),
        configuration=api.advanced.RunConfigurationReport(
            solver=report.parameters,
            scoring=api.advanced.ConfigurationResolution(),
            cipher=api.advanced.ConfigurationResolution(),
        ),
        reproducibility=api.advanced.ReproducibilityMetadata(),
        oracle=api.advanced.OracleReport(),
        telemetry=telemetry or {},
    )


def test_print_run_report_includes_interruptors_when_solved() -> None:
    summary = api.display.build_summary(
        _result(telemetry={'interruptors': {'found': [4, 9], 'core_length': 3}})
    )
    assert summary.telemetry['interruptors']['found'] == (4, 9)
    assert summary.key['recovered_key']['preview'] == (1, 2, 3, 4, 9)


def test_print_run_report_omits_interruptors_without_meta() -> None:
    summary = api.display.build_summary(_result())
    assert 'interruptors' not in summary.telemetry


def test_print_run_report_prefers_interruptors_ref() -> None:
    summary = api.display.build_summary(
        _result(
            telemetry={
                'interruptors': {
                    'found': [4, 9],
                    'expected': [1, 2],
                    'core_length': 3,
                }
            }
        )
    )
    assert summary.telemetry['interruptors']['expected'] == (1, 2)
