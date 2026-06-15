from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_AGREEMENT = ROOT / "src" / "rune_decrypter_prime" / "api" / "artifact_agreement.py"
SOLVER_REPORT = ROOT / "src" / "rune_decrypter_prime" / "api" / "solver_report.py"
SCORER_REPORT_BUILDER = ROOT / "src" / "rune_decrypter_prime" / "scoring" / "scorer_report_builder.py"
SCORING_CONFIG = ROOT / "src" / "rune_decrypter_prime" / "core" / "config" / "scoring.py"
ENGINE_BUILDERS = ROOT / "src" / "rune_decrypter_prime" / "core" / "engine" / "builders.py"
RUNE_SCORER_WRAPPER = ROOT / "src" / "rune_decrypter_prime" / "scoring" / "rune_scorer.py"
UNIFIED_RUNE_SCORER = ROOT / "src" / "rune_decrypter_prime" / "scoring" / "unified_rune_scorer.py"
RUNE_SCORER_IMPL = ROOT / "src" / "rune_decrypter_prime" / "scoring" / "rune_scorer_impl.py"
TORCH_RUNE_SCORER = ROOT / "src" / "rune_decrypter_prime" / "scoring" / "torch_rune_scorer.py"


def test_artifact_classifications_are_enum_owned_not_literal_or_raw_set() -> None:
    text = ARTIFACT_AGREEMENT.read_text(encoding="utf-8")

    assert "class ArtifactClassification(StrEnum)" in text
    assert "Classification = Literal" not in text
    assert 'ALLOWED_CLASSIFICATIONS = {"candidate"' not in text
    assert "ALLOWED_CLASSIFICATIONS = frozenset(item.value for item in ArtifactClassification)" in text


def test_solver_report_reserved_detail_keys_are_enum_derived() -> None:
    text = SOLVER_REPORT.read_text(encoding="utf-8")

    assert "class SolverReportDetailKey(StrEnum)" in text
    assert "class OracleUse(StrEnum)" in text
    assert "class TruthDataPolicy(StrEnum)" in text
    assert 'RESERVED_CONTRACT_DETAIL_KEYS = frozenset({"report_contract"' not in text
    assert "SolverReportDetailKey.REPORT_CONTRACT" in text


def test_scorer_report_reserved_detail_keys_are_enum_derived() -> None:
    text = SCORER_REPORT_BUILDER.read_text(encoding="utf-8")

    assert "class ScorerReportDetailKey(StrEnum)" in text
    assert "class ReportBuilderDiagnosticKey(StrEnum)" in text
    assert 'RESERVED_DETAIL_KEYS = frozenset({"hamming_dictionary"' not in text
    assert "RESERVED_DETAIL_KEYS = frozenset(key.value for key in ScorerReportDetailKey)" in text
    assert "CALLER_FORBIDDEN_DETAIL_KEYS" in text


def test_d7_scoring_config_modes_are_enum_owned_not_raw_validation_sets() -> None:
    text = SCORING_CONFIG.read_text(encoding="utf-8")

    assert "class HammingDirectionMode(StrEnum)" in text
    assert "class SpanHammingMode(StrEnum)" in text
    assert "class SpanHammingBucketPolicy(StrEnum)" in text
    assert "class SpanHammingCombineMode(StrEnum)" in text
    assert "class SpanHammingGateFailPolicy(StrEnum)" in text
    assert "class SpanHammingLmProfileSource(StrEnum)" in text
    assert "def ensure_hamming_direction_mode" in text
    assert "def ensure_span_hamming_mode" in text
    assert "def ensure_span_hamming_bucket_policy" in text
    assert "def ensure_span_hamming_combine_mode" in text
    assert "def ensure_span_hamming_gate_fail_policy" in text
    assert "def ensure_span_hamming_lm_profile_source" in text
    assert "hamming_direction_mode not in" not in text
    assert "span_hamming_mode not in" not in text
    assert "span_hamming_combine_mode not in" not in text
    assert "span_hamming_gate_fail_policy not in" not in text
    assert "span_hamming_lm_profile_source not in" not in text
    assert "span_mode ==" not in text
    assert "SpanHammingMode.CALIBRATED" in text


def test_d7_scorer_report_telemetry_sources_are_enum_owned() -> None:
    text = SCORER_REPORT_BUILDER.read_text(encoding="utf-8")

    assert "class ScorerTelemetryPrefix(StrEnum)" in text
    assert "class ScorerTelemetryKey(StrEnum)" in text
    assert '_section_from_prefix(telemetry, "span_hamming_")' not in text
    assert '_section_from_prefix(telemetry, "word_ngram_judge_")' not in text
    assert '_section_from_prefix(telemetry, "span_lm_")' not in text
    assert 'for key in (\n        "hamming_dictionary_policy"' not in text
    assert "for key in ScorerTelemetryKey:" in text


def test_d7_solver_report_does_not_reuse_oracle_use_for_route_or_param_domains() -> None:
    text = SOLVER_REPORT.read_text(encoding="utf-8")

    assert "class ExecutionRoute(StrEnum)" in text
    assert "class SolverParamKey(StrEnum)" in text
    assert "ExecutionRoute.KNOWN_KEY_FASTPATH.value" in text
    assert "SolverParamKey.TEST_KEY.value in normalized_params" in text
    assert "OracleUse.KNOWN_KEY_FASTPATH.value" not in text
    assert "OracleUse.TEST_KEY.value in normalized_params" not in text


def test_d7_capability_helpers_do_not_drop_enum_backed_runtime_span_mode() -> None:
    for path in (ENGINE_BUILDERS, RUNE_SCORER_WRAPPER, UNIFIED_RUNE_SCORER):
        text = path.read_text(encoding="utf-8")

        assert "SpanHammingMode" in text
        assert "ensure_span_hamming_mode" in text or "def _ensure_runtime_span_hamming_mode" in text
        assert "SpanHammingMode.RAW_BONUS" in text
        assert 'span_hamming_mode == "raw_bonus"' not in text
        assert 'str(getattr(self._backend, "_span_hamming_mode"' not in text
        assert 'str(getattr(target, "_span_hamming_mode"' not in text


def test_d7_large_backend_runtime_enum_overlay_remains_explicit_until_applied() -> None:
    for path in (RUNE_SCORER_IMPL, TORCH_RUNE_SCORER):
        text = path.read_text(encoding="utf-8")

        assert "_span_hamming_mode = str" in text
        assert "_span_hamming_combine_mode = str" in text
        assert "_span_hamming_gate_fail_policy = str" in text
