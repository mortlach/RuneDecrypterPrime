from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAN_DOC = ROOT / "docs" / "release_contracts" / "v1" / "D6_IMPLEMENTATION_PLAN.md"
D5_CONTRACT_DOC = ROOT / "docs" / "release_contracts" / "v1" / "D5_REPORT_AND_ARTIFACT_AGREEMENT.md"


def test_d6_plan_records_verified_branch_and_scope() -> None:
    text = PLAN_DOC.read_text(encoding="utf-8")

    assert "`prelease/v1.0.0_d6`" in text
    assert "`preleasev1.0.0_d5`" in text
    assert "8b549f934748aa15b7cad3b88403c1ba81bf4f18" in text
    assert "not a feature pass" in text
    assert "must not add" in text


def test_d6_plan_names_reserved_solver_report_contract_sections() -> None:
    text = PLAN_DOC.read_text(encoding="utf-8")

    for phrase in (
        "report_contract",
        "oracle_use",
        "truth_data_policy",
        "reproducibility",
        "must not overwrite or pre-seed",
    ):
        assert phrase in text


def test_d5_contract_still_names_report_only_no_rank_effect() -> None:
    text = D5_CONTRACT_DOC.read_text(encoding="utf-8")

    assert "Report-only scorer lanes are diagnostic" in text
    assert "must not affect score, raw score, ordering, or tie-breaks" in text
