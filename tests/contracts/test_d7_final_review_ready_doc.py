from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REVIEW_READY_DOC = (
    ROOT / "docs" / "release_contracts" / "v1" / "D7_FINAL_REVIEW_READY.md"
)


def _text() -> str:
    assert REVIEW_READY_DOC.exists()
    return REVIEW_READY_DOC.read_text(encoding="utf-8")


def test_d7_final_review_ready_doc_records_final_local_proof_policy() -> None:
    text = _text()
    assert "generated `REVIEW_PACK_MANIFEST.json` and sidecar summary JSON" in text
    assert "does not hard-code a target commit SHA" in text
    assert "focused review-pack tests: 3 passed" in text
    assert "focused D7/tutorial framework tests: 34 passed" in text
    assert "compact D7 smoke: 146 passed" in text
    assert "broader focused closure gate: 676 passed" in text
    assert "full pytest: 1220 passed, 19 skipped" in text
    assert "full_v1 tutorial gate: 14 passed, 0 failed" in text
    assert "focused review/tutorial/cipher/API/guardrail checks: 43 passed" in text


def test_d7_final_review_ready_doc_records_final_review_pack_metadata_policy() -> None:
    text = _text()
    assert "git_branch: prelease/v1.0.0_d7" in text
    assert "git_commit_sha: <generated manifest commit>" in text
    assert "git_working_tree_dirty: false" in text
    assert "included_files_count: <generated manifest count>" in text
    assert "excluded_entries_count: <generated manifest count>" in text
    assert "strict_root_allowlist_filtered_by_review_pack_rules" in text


def test_d7_final_review_ready_doc_has_no_stale_prevalidation_or_metadata_language() -> (
    None
):
    text = _text()
    stale_phrases = [
        "5e5372fff386378dde3f8dcd0acd8c880c70667d",
        "b827aba6a9e2515a8c1f7043c56422d4c7c9c9c1",
        "included_files_count: 692",
        "excluded_entries_count: 480",
        "all_direct_root_files_filtered_by_review_pack_rules",
        "current branch head still needs",
        "rerun at minimum",
        "For final closure evidence, rerun",
        "Regenerate the review pack from the final branch head before external review",
        "before the final review-pack metadata hardening commits",
    ]
    for phrase in stale_phrases:
        assert phrase not in text
