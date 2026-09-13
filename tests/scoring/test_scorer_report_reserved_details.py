from __future__ import annotations
import pytest
from rdp.scoring.scorer_report_builder import build_scorer_report

class _TelemetryScorer:
    win = 10
    objective = 'pct.logp.win10'

    def __init__(self, telemetry: dict[str, object]) -> None:
        self._telemetry = telemetry

    def telemetry(self) -> dict[str, object]:
        return dict(self._telemetry)

    def last_stats(self) -> dict[str, float]:
        return {'baseline': 1.0}

def test_extra_details_cannot_overwrite_generated_reserved_section() -> None:
    scorer = _TelemetryScorer({'span_hamming_quality': 0.75})
    with pytest.raises(ValueError, match='span_hamming'):
        build_scorer_report(scorer=scorer, objective_str='pct.logp.win10', score=1.0, extra_details={'span_hamming': {'quality': 0.0}})

def test_extra_details_can_add_non_reserved_section() -> None:
    scorer = _TelemetryScorer({'span_hamming_quality': 0.75})
    report = build_scorer_report(scorer=scorer, objective_str='pct.logp.win10', score=1.0, extra_details={'review_note': {'status': 'ok'}})
    assert report.details['span_hamming'] == {'quality': 0.75}
    assert report.details['review_note'] == {'status': 'ok'}

def test_extra_details_can_supply_reserved_section_when_builder_did_not_generate_it() -> None:
    scorer = _TelemetryScorer({})
    report = build_scorer_report(scorer=scorer, objective_str='pct.logp.win10', score=1.0, extra_details={'scorer_lanes': {'lanes': []}})
    assert report.details['scorer_lanes'] == {'lanes': []}
