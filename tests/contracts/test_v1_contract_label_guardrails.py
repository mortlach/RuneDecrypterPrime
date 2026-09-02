from __future__ import annotations
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_AGREEMENT = ROOT / "src" / "rdp" / "api" / "artifact_agreement.py"
SOLVER_REPORT = ROOT / "src" / "rdp" / "api" / "solver_report.py"
SCORER_REPORT_BUILDER = (
    ROOT / "src" / "rdp" / "scoring" / "scorer_report_builder.py"
)
SCORING_CONFIG = (
    ROOT / "src" / "rdp" / "core" / "config" / "scoring.py"
)
CORE_TYPES = ROOT / "src" / "rdp" / "core" / "types.py"
RUNE_SCORER_IMPL = (
    ROOT / "src" / "rdp" / "scoring" / "rune_scorer_impl.py"
)
TORCH_RUNE_SCORER = (
    ROOT / "src" / "rdp" / "scoring" / "torch_rune_scorer.py"
)
ENGINE_BUILDERS = (
    ROOT / "src" / "rune_decrypter_prime" / "core" / "engine" / "builders.py"
)
UNIFIED_RUNE_SCORER = (
    ROOT / "src" / "rdp" / "scoring" / "unified_rune_scorer.py"
)
RUNE_SCORER_WRAPPER = (
    ROOT / "src" / "rdp" / "scoring" / "rune_scorer.py"
)


def test_artifact_classifications_are_enum_owned_not_literal_or_raw_set() -> None:
    text = ARTIFACT_AGREEMENT.read_text(encoding='utf-8')
    assert 'class ArtifactClassification(StrEnum)' in text
    assert 'Classification = Literal' not in text
    assert 'ALLOWED_CLASSIFICATIONS = {"candidate"' not in text
    assert 'ALLOWED_CLASSIFICATIONS = frozenset(item.value for item in ArtifactClassification)' in text

def test_solver_report_reserved_detail_keys_are_enum_derived() -> None:
    text = SOLVER_REPORT.read_text(encoding="utf-8")
    assert "class SolverReportDetailKey" not in text
    assert "class OracleUse" not in text
    assert "class SolverReport" in text
    assert "status: RunStatus" in text
    assert "class OracleReport" in text


def test_scorer_report_reserved_detail_keys_are_enum_derived() -> None:
    text = SCORER_REPORT_BUILDER.read_text(encoding='utf-8')
    assert 'class ScorerReportDetailKey(StrEnum)' in text
    assert 'class ReportBuilderDiagnosticKey(StrEnum)' in text
    assert 'RESERVED_DETAIL_KEYS = frozenset({"hamming_dictionary"' not in text
    assert 'RESERVED_DETAIL_KEYS = frozenset(key.value for key in ScorerReportDetailKey)' in text
    assert 'CALLER_FORBIDDEN_DETAIL_KEYS' in text

def test_d7_scoring_config_modes_are_enum_owned_not_raw_validation_sets() -> None:
    text = SCORING_CONFIG.read_text(encoding="utf-8")
    type_text = CORE_TYPES.read_text(encoding="utf-8")
    assert "class HammingTextDirectionMode(StrEnum)" in type_text
    assert "class SpanHammingMode(StrEnum)" in type_text
    assert "class SpanHammingBucketPolicy(StrEnum)" in type_text
    assert "class SpanHammingCombineMode(StrEnum)" in type_text
    assert "class SpanHammingGateFailurePolicy(StrEnum)" in type_text
    assert "class SpanHammingLanguageModelProfileSource(StrEnum)" in type_text
    assert "hamming_direction_mode not in" not in text
    assert "span_hamming_mode not in" not in text
    assert "span_hamming_combine_mode not in" not in text
    assert "span_hamming_gate_fail_policy not in" not in text
    assert "span_hamming_lm_profile_source not in" not in text
    assert "span_mode ==" not in text
    assert "SpanHammingMode.CALIBRATED" in text


def test_d7_scorer_report_telemetry_sources_are_enum_owned() -> None:
    text = SCORER_REPORT_BUILDER.read_text(encoding='utf-8')
    assert 'class ScorerTelemetryPrefix(StrEnum)' in text
    assert 'class ScorerTelemetryKey(StrEnum)' in text
    assert '_section_from_prefix(telemetry, "span_hamming_")' not in text
    assert '_section_from_prefix(telemetry, "word_ngram_judge_")' not in text
    assert '_section_from_prefix(telemetry, "span_lm_")' not in text
    assert 'for key in (\n        "hamming_dictionary_policy"' not in text
    assert "for key in ScorerTelemetryKey:" in text


def test_d7_solver_report_does_not_reuse_oracle_use_for_route_or_param_domains() -> (
    None
):
    text = SOLVER_REPORT.read_text(encoding="utf-8")
    assert "class ExecutionRoute" not in text
    assert "class SolverParamKey" not in text
    assert "known_key_fastpath" not in text
    assert "test_key" not in text


def test_d7_runtime_scorers_use_enum_owned_mode_state() -> None:
    for path in (RUNE_SCORER_IMPL, TORCH_RUNE_SCORER):
        text = path.read_text(encoding="utf-8")
        assert "ensure_hamming_text_direction_mode" in text
        assert "ensure_span_hamming_mode" in text
        assert "ensure_span_hamming_bucket_policy" in text
        assert "ensure_span_hamming_combine_mode" in text
        assert "ensure_span_hamming_gate_failure_policy" in text
        assert "ensure_span_hamming_language_model_profile_source" in text
        assert "_span_hamming_mode = str" not in text
        assert "_span_hamming_combine_mode = str" not in text
        assert "_span_hamming_gate_fail_policy = str" not in text
        assert "_span_hamming_lm_profile_source = str" not in text
        assert "span_hamming_mode not in" not in text
        assert "span_hamming_combine_mode not in" not in text
        assert "span_hamming_gate_fail_policy not in" not in text
        assert "_hamming_direction_mode: str" not in text
        assert "SpanHammingMode.CALIBRATED" in text
        assert "SpanHammingCombineMode.WEIGHTED_SUM" in text


def test_d7_capability_report_helpers_normalise_backend_mode_through_contract() -> None:
    for path in (ENGINE_BUILDERS, UNIFIED_RUNE_SCORER, RUNE_SCORER_WRAPPER):
        text = path.read_text(encoding='utf-8')
        assert 'SpanHammingMode' in text
        assert 'ensure_span_hamming_mode' in text
        assert 'span_hamming_mode == "raw_bonus"' not in text
        assert '_span_hamming_mode", "off"' not in text
