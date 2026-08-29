from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GATES_DOC = (
    ROOT / "docs" / "release_contracts" / "v1" / "V1_RELEASE_ACCEPTANCE_GATES.md"
)


def _doc_text() -> str:
    assert GATES_DOC.exists()
    return GATES_DOC.read_text(encoding="utf-8")


def test_v1_acceptance_gates_doc_names_no_feature_expansion_rule() -> None:
    text = _doc_text()
    for phrase in (
        "new solvers",
        "new ciphers",
        "new scorer lanes",
        "new assets",
        "new ranking behaviour",
        "new scoring behaviour",
        "monkey patches",
    ):
        assert phrase in text


def test_v1_acceptance_gates_doc_names_current_profile_and_workflow_gates() -> None:
    text = _doc_text()
    assert "workflow_dispatch" in text
    assert "prelease/**" in text
    assert "ci_light" in text
    assert "full_v1" in text
    assert "full-proof" in text


def test_v1_acceptance_gates_doc_names_review_pack_and_tutorial_gates() -> None:
    text = _doc_text()
    assert "tutorials/v1/run_tutorials.py" in text
    assert "review pack" in text
    assert "final integration head" in text


def test_v1_acceptance_gates_doc_names_report_only_no_rank_effect() -> None:
    text = _doc_text()
    for phrase in (
        "score",
        "raw_score",
        "ranking order",
        "tie-breaks",
        "candidate selection",
        "solver stopping",
    ):
        assert phrase in text
