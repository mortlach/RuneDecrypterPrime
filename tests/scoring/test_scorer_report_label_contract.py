from __future__ import annotations
import pytest
from rdp.scoring.scorer_report_builder import DiagnosticField, ReportBuilderDiagnosticKey, ScorerReportDetailKey, ScorerTelemetryKey, ScorerTelemetryPrefix, build_scorer_report

class _HealthyScorer:
    win = 10
    objective = 'pct.logp.win10'

    def telemetry(self) -> dict[str, object]:
        return {}

    def last_stats(self) -> dict[str, float]:
        return {'rank_metric': 3.0}

class _TelemetryFailureScorer:
    win = 10
    objective = 'pct.logp.win10'

    def telemetry(self) -> dict[str, object]:
        raise RuntimeError('telemetry unavailable')

    def last_stats(self) -> dict[str, float]:
        return {'rank_metric': 3.0}

def test_scorer_report_detail_labels_are_enum_backed() -> None:
    assert ScorerReportDetailKey.REPORT_BUILDER_DIAGNOSTICS.value == 'report_builder_diagnostics'
    assert ScorerReportDetailKey.SCORER_LANES.value == 'scorer_lanes'
    assert ScorerReportDetailKey.ORACLE_USE.value == 'oracle_use'
    assert ReportBuilderDiagnosticKey.TELEMETRY_ERROR.value == 'telemetry_error'
    assert ReportBuilderDiagnosticKey.LAST_STATS_ERROR.value == 'last_stats_error'
    assert DiagnosticField.TYPE.value == 'type'
    assert DiagnosticField.MESSAGE.value == 'message'

def test_report_builder_diagnostics_cannot_be_caller_supplied_on_healthy_path() -> None:
    with pytest.raises(ValueError, match='report_builder_diagnostics'):
        build_scorer_report(scorer=_HealthyScorer(), objective_str='pct.logp.win10', score=1.0, extra_details={'report_builder_diagnostics': {'telemetry_error': {'type': 'RuntimeError', 'message': 'caller supplied diagnostic'}}})

def test_generated_diagnostic_keys_emit_stable_json_strings() -> None:
    report = build_scorer_report(scorer=_TelemetryFailureScorer(), objective_str='pct.logp.win10', score=1.0)
    payload = report.to_json_dict()
    assert payload['details']['report_builder_diagnostics'] == {'telemetry_error': {'type': 'RuntimeError', 'message': 'telemetry unavailable'}}

class _TelemetrySourceScorer:
    win = 10
    objective = 'pct.logp.win10'

    def telemetry(self) -> dict[str, object]:
        return {'span_hamming_mode': 'calibrated', 'span_hamming_pct': 0.9, 'span_lm_tail_pct': 0.8, 'word_ngram_judge_active': True, 'hamming_dictionary_policy': 'normal', 'span_hamming_dictionary_policy': 'strict', 'span_hamming_assets_dictionary_policy': 'strict', 'span_hamming_dictionary_policy_match': True, 'span_hamming_dictionary_policy_note': 'matched'}

    def last_stats(self) -> dict[str, float]:
        return {'rank_metric': 3.0}

def test_scorer_telemetry_source_labels_are_enum_backed() -> None:
    assert ScorerTelemetryPrefix.SPAN_HAMMING.value == 'span_hamming_'
    assert ScorerTelemetryPrefix.WORD_NGRAM_JUDGE.value == 'word_ngram_judge_'
    assert ScorerTelemetryPrefix.SPAN_LM.value == 'span_lm_'
    assert ScorerTelemetryKey.HAMMING_DICTIONARY_POLICY.value == 'hamming_dictionary_policy'
    assert ScorerTelemetryKey.SPAN_HAMMING_DICTIONARY_POLICY.value == 'span_hamming_dictionary_policy'
    assert ScorerTelemetryKey.SPAN_HAMMING_ASSETS_DICTIONARY_POLICY.value == 'span_hamming_assets_dictionary_policy'
    assert ScorerTelemetryKey.SPAN_HAMMING_DICTIONARY_POLICY_MATCH.value == 'span_hamming_dictionary_policy_match'
    assert ScorerTelemetryKey.SPAN_HAMMING_DICTIONARY_POLICY_NOTE.value == 'span_hamming_dictionary_policy_note'

def test_telemetry_source_labels_derive_unchanged_public_report_details() -> None:
    report = build_scorer_report(scorer=_TelemetrySourceScorer(), objective_str='pct.logp.win10', score=1.25, raw_score=1.0)
    payload = report.to_json_dict()
    assert payload['details']['span_hamming'] == {'mode': 'calibrated', 'pct': 0.9, 'dictionary_policy': 'strict', 'assets_dictionary_policy': 'strict', 'dictionary_policy_match': True, 'dictionary_policy_note': 'matched'}
    assert payload['details']['span_lm'] == {'tail_pct': 0.8}
    assert payload['details']['word_ngrams'] == {'active': True}
    assert payload['details']['hamming_dictionary'] == {'hamming_dictionary_policy': 'normal', 'span_hamming_dictionary_policy': 'strict', 'span_hamming_assets_dictionary_policy': 'strict', 'span_hamming_dictionary_policy_match': True, 'span_hamming_dictionary_policy_note': 'matched'}

def test_report_only_telemetry_details_do_not_change_score_raw_score_or_metrics() -> None:
    report = build_scorer_report(scorer=_TelemetrySourceScorer(), objective_str='pct.logp.win10', score=1.25, raw_score=1.0, extra_metrics={'rank_metric': 9.0})
    payload = report.to_json_dict()
    assert payload['score'] == pytest.approx(1.25)
    assert payload['raw_score'] == pytest.approx(1.0)
    assert payload['metrics']['rank_metric'] == pytest.approx(9.0)
    assert 'span_hamming' in payload['details']
