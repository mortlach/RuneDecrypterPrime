from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_DOC = ROOT / "docs" / "release_contracts" / "v1" / "D5_REPORT_AND_ARTIFACT_AGREEMENT.md"
HANDOFF_DOC = ROOT / "docs" / "release_contracts" / "v1" / "D5_SUMMARY_D6_HANDOFF.md"


def test_d5_contract_doc_names_report_and_artifact_contracts() -> None:
    text = CONTRACT_DOC.read_text(encoding="utf-8")

    for phrase in (
        "artifact agreement",
        "run artifact manifest",
        "oracle_use",
        "truth_data_policy",
        "reproducibility",
        "full-proof CI",
    ):
        assert phrase in text


def test_d5_handoff_doc_names_d6_starting_gate() -> None:
    text = HANDOFF_DOC.read_text(encoding="utf-8")

    assert "D5 summary and D6 handoff" in text
    assert "D5 did not add cipher modes" in text
    assert "D6 should start only after full-proof CI is green" in text
