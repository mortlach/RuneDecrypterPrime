from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_AGREEMENT = ROOT / "src" / "rune_decrypter_prime" / "api" / "artifact_agreement.py"
SOLVER_REPORT = ROOT / "src" / "rune_decrypter_prime" / "api" / "solver_report.py"
SCORER_REPORT_BUILDER = ROOT / "src" / "rune_decrypter_prime" / "scoring" / "scorer_report_builder.py"


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
