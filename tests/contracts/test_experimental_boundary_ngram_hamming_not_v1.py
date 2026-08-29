from __future__ import annotations
from rune_decrypter_prime.scoring.ngram_hamming.report_only_telemetry import N3CNormalReportTelemetryConfig, REPORT_INTEGRATION_MODE, build_n3c_normal_report_telemetry

def test_ngram_hamming_default_report_telemetry_is_off_and_no_rank_effect() -> None:
    row = build_n3c_normal_report_telemetry(candidate_id='candidate-a', hits=(), config=N3CNormalReportTelemetryConfig())
    assert row['enabled'] is False
    assert row['production_rank_effect'] == 'none'
    assert row['report_integration_mode'] == 'report_only_no_rank_effect'

def test_ngram_hamming_report_mode_constant_is_not_rank_affecting() -> None:
    assert REPORT_INTEGRATION_MODE == 'report_only_no_rank_effect'
