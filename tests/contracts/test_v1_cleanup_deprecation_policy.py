from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
LEDGER = REPO_ROOT / "docs" / "release_contracts" / "v1" / "v1_cleanup_deprecation_ledger.json"
ALLOWED_STATUSES = {"retain", "deprecate_only", "remove_after_green", "removed"}
REQUIRED_ENTRY_FIELDS = {
    "id",
    "status",
    "target_paths",
    "symbol_or_feature",
    "reason",
    "replacement",
    "tests_required_before_removal",
    "docs_required_before_removal",
    "rollback_note",
    "v1_action",
}


def _load_ledger() -> dict:
    assert LEDGER.is_file(), "missing cleanup ledger"
    return json.loads(LEDGER.read_text(encoding="utf-8"))


def test_cleanup_deprecation_ledger_has_expected_schema_and_unique_ids() -> None:
    data = _load_ledger()

    assert data["schema"] == "rdp_v1_cleanup_deprecation_ledger.v1"
    assert data["policy"] == "no_silent_drift_no_unsupported_removal_no_experimental_promotion"
    assert set(data["allowed_statuses"]) == ALLOWED_STATUSES

    entries = data["entries"]
    ids = [entry["id"] for entry in entries]
    assert entries
    assert len(ids) == len(set(ids))


def test_cleanup_entries_are_complete_and_actionable() -> None:
    data = _load_ledger()

    for entry in data["entries"]:
        missing = REQUIRED_ENTRY_FIELDS - set(entry)
        assert not missing, f"{entry.get('id', '<missing id>')} missing fields: {sorted(missing)}"
        assert entry["status"] in ALLOWED_STATUSES
        assert isinstance(entry["target_paths"], list) and entry["target_paths"]
        assert isinstance(entry["tests_required_before_removal"], list)
        assert isinstance(entry["docs_required_before_removal"], list)
        assert str(entry["reason"]).strip()
        assert str(entry["replacement"]).strip()
        assert str(entry["rollback_note"]).strip()
        assert str(entry["v1_action"]).strip()


def test_known_v1_cleanup_items_are_tracked() -> None:
    data = _load_ledger()
    ids = {entry["id"] for entry in data["entries"]}

    expected = {
        "api.run.solve_alias",
        "scoring.numpy.hamming_warning_skip",
        "scoring.numpy.span_hamming_warning_skip",
        "scoring.torch.hamming_silent_disable",
        "scoring.torch.span_hamming_silent_disable",
        "experimental.ngram_hamming_scoring",
        "experimental.save_restore_solving",
        "cipher.scheduled_stream_lookup_aliases",
        "release.traceability_files",
    }
    assert expected <= ids
