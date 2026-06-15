from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SUMMARY_DOC = ROOT / "docs" / "release_contracts" / "v1" / "D7_FINAL_SUMMARY.md"


def _summary_text() -> str:
    assert SUMMARY_DOC.exists()
    return SUMMARY_DOC.read_text(encoding="utf-8")


def test_d7_summary_names_branch_and_scope() -> None:
    text = _summary_text()

    assert "prelease/v1.0.0_d7" in text
    assert "not a feature branch" in text
    assert "new solvers" in text
    assert "new ciphers" in text
    assert "new scorer lanes" in text


def test_d7_summary_names_owned_label_domains() -> None:
    text = _summary_text()

    assert "SpanHammingMode" in text
    assert "SpanHammingGateFailPolicy" in text
    assert "ScorerTelemetryPrefix" in text
    assert "ScorerTelemetryKey" in text


def test_d7_summary_names_output_and_report_only_rules() -> None:
    text = _summary_text()

    assert "public strings" in text
    assert "score" in text
    assert "raw_score" in text
    assert "tie-breaks" in text
    assert "solver stopping" in text


def test_d7_summary_names_remaining_local_overlay() -> None:
    text = _summary_text()

    assert "Known local overlay not yet pushed" in text
    assert "tooling limitation" in text
    assert "not a D7 scope reduction" in text
    assert "branch should not close" in text
