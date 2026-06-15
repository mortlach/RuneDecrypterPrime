from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_ROOT = REPO_ROOT / "docs" / "release_contracts" / "v1"
SCOPE_LOCK = CONTRACT_ROOT / "v1_scope_lock.json"
CLEANUP_LEDGER = CONTRACT_ROOT / "v1_cleanup_deprecation_ledger.json"
TRACEABILITY_CHAIN = CONTRACT_ROOT / "final_source_to_wp_decision_target_test_chain.csv"


def _load_json(path: Path) -> dict:
    assert path.is_file(), f"missing contract file: {path.relative_to(REPO_ROOT).as_posix()}"
    return json.loads(path.read_text(encoding="utf-8"))


def test_d7_keeps_v1_scope_lock_and_traceability_evidence_present() -> None:
    assert SCOPE_LOCK.is_file(), "D0 scope lock must remain present after cleanup"
    assert CLEANUP_LEDGER.is_file(), "D7 cleanup ledger must remain present after cleanup"
    assert TRACEABILITY_CHAIN.is_file(), "source-to-test traceability chain must not be deleted as cleanup"


def test_d7_cleanup_policy_does_not_promote_experimental_boundaries() -> None:
    scope = _load_json(SCOPE_LOCK)
    ledger = _load_json(CLEANUP_LEDGER)
    entries = {entry["id"]: entry for entry in ledger["entries"]}

    assert scope["v1_included"]["span_hamming"]["status"] == "v1_optional"
    assert scope["v1_included"]["scheduled_stream_lookup"]["status"] == "v1_core"
    assert scope["not_v1_production"]["new_ngram_hamming_scoring"]["status"] == "experimental_report_only"
    assert scope["not_v1_production"]["full_save_restore_solving"]["status"] == "roadmap"

    ngram = entries["experimental.ngram_hamming_scoring"]
    assert ngram["status"] == "retain"
    assert "report-only" in ngram["replacement"] or "no-rank-effect" in ngram["replacement"]

    resume = entries["experimental.save_restore_solving"]
    assert resume["status"] == "retain"
    assert "out-of-scope" in resume["v1_action"] or "Unsupported" in resume["replacement"]


def test_d7_cleanup_policy_preserves_requested_lane_hardening_items_until_green() -> None:
    ledger = _load_json(CLEANUP_LEDGER)
    entries = {entry["id"]: entry for entry in ledger["entries"]}

    for item in (
        "scoring.numpy.hamming_warning_skip",
        "scoring.numpy.span_hamming_warning_skip",
        "scoring.torch.hamming_silent_disable",
        "scoring.torch.span_hamming_silent_disable",
    ):
        entry = entries[item]
        assert entry["status"] == "remove_after_green"
        assert any("test_" in test for test in entry["tests_required_before_removal"])
        assert "RequestedLaneUnavailableError" in entry["replacement"]
