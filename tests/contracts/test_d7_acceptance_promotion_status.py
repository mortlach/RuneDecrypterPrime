from __future__ import annotations
import csv
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_ROOT = REPO_ROOT / "docs" / "release_contracts" / "v1"
STATUS_CSV = CONTRACT_ROOT / "d7_acceptance_test_promotion_status.csv"
CLOSURE_CHECKLIST = CONTRACT_ROOT / "D7_CLOSURE_CHECKLIST.md"
IMPLEMENTATION_SUMMARY = CONTRACT_ROOT / "D7_IMPLEMENTATION_SUMMARY.md"
ALLOWED_STATUS = {"implemented", "not_v1_production"}
REQUIRED_RELEASE_CONTRACT_FILES = {
    "final_source_to_wp_decision_target_test_chain.csv",
    "final_missing_or_new_acceptance_tests.csv",
    "v1_scope_lock.json",
    "D7_CLEANUP_DEPRECATION_POLICY.md",
    "v1_cleanup_deprecation_ledger.json",
    "d7_acceptance_test_promotion_status.csv",
    "D7_CLOSURE_CHECKLIST.md",
    "D7_IMPLEMENTATION_SUMMARY.md",
    "D7_TUTORIAL_BENCHMARK_POLICY.md",
    "D7_TUTORIAL_BENCHMARK_MATCH_RATIO_ADDENDUM.md",
    "D7_TUTORIAL_OUTPUT_FRAMEWORK.md",
}


def _rows() -> list[dict[str, str]]:
    assert STATUS_CSV.is_file(), "missing D7 acceptance promotion status CSV"
    with STATUS_CSV.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_d7_release_contract_evidence_files_exist() -> None:
    missing = sorted(
        (
            name
            for name in REQUIRED_RELEASE_CONTRACT_FILES
            if not (CONTRACT_ROOT / name).is_file()
        )
    )
    assert not missing, f"missing D7 release-contract evidence files: {missing}"


def test_d7_acceptance_promotion_status_has_no_silent_pending_rows() -> None:
    rows = _rows()
    assert rows
    for row in rows:
        assert row["status"] in ALLOWED_STATUS, row
        assert row["notes"].strip(), row


def test_d7_implemented_acceptance_paths_exist() -> None:
    for row in _rows():
        if row["status"] != "implemented":
            continue
        path = REPO_ROOT / row["test_path"]
        assert (
            path.is_file()
        ), f"implemented D7 acceptance path missing: {row['test_path']}"


def test_d7_not_v1_production_rows_are_explicitly_outside_tests_tree() -> None:
    for row in _rows():
        if row["status"] != "not_v1_production":
            continue
        assert row["test_path"].startswith("experimental/"), row
        assert "not part of V1" in row["notes"] or "Experimental" in row["notes"]


def test_d7_closure_checklist_exists_and_names_final_gates() -> None:
    assert CLOSURE_CHECKLIST.is_file(), "missing D7 closure checklist"
    text = CLOSURE_CHECKLIST.read_text(encoding="utf-8")
    required_phrases = [
        "D7 is the final V1 contract-closure branch",
        "python -m pytest -q -ra -p no:cacheprovider tests",
        "No final branch changes after green CI unless CI is rerun",
    ]
    for phrase in required_phrases:
        assert phrase in text


def test_d7_implementation_summary_names_api_forgiving_core_strict_split() -> None:
    assert IMPLEMENTATION_SUMMARY.is_file(), "missing D7 implementation summary"
    text = IMPLEMENTATION_SUMMARY.read_text(encoding="utf-8")
    required_phrases = [
        "D7 deliberately keeps the API layer forgiving and the core layer strict",
        "Requested scorer lanes block when unavailable instead of warning and disappearing",
        "Tutorial truth thresholds are explicitly labelled by `TutorialTruthPolicy`",
        "Tutorial helper boundary tests prevent tutorial/session oracle helpers from leaking into strict runtime modules",
        "Full save/restore solving remains roadmap/experimental",
    ]
    for phrase in required_phrases:
        assert phrase in text
