from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_ROOT = ROOT / "docs" / "release_contracts" / "v1"
AUTHORITY = CONTRACT_ROOT / "V1_AUTHORITY_AND_DECISIONS.md"
DECISIONS = CONTRACT_ROOT / "v1_resolved_decisions.csv"
BASELINE = CONTRACT_ROOT / "v1_final_integration_baseline.json"


def test_v1_authority_hierarchy_is_explicit() -> None:
    text = AUTHORITY.read_text(encoding="utf-8")
    expected_in_order = (
        "June 10 D0-D7 unified hardening handoff",
        "v1_docs/",
        "Explicit approved WP6, WP7 and final-integration additions",
        "Canonical `docs/`",
        "Tests enforce the approved contracts",
    )
    positions = [text.index(fragment) for fragment in expected_in_order]
    assert positions == sorted(positions)
    assert "do not automatically redefine them" in text


def test_v1_resolved_decision_record_is_complete_and_closed() -> None:
    with DECISIONS.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert [row["decision_id"] for row in rows] == [
        f"V1-DEC-{index:03d}" for index in range(1, 11)
    ]
    assert {row["status"] for row in rows} == {"resolved"}
    assert all(row["decision"] and row["implementation_effect"] for row in rows)


def test_v1_final_integration_baseline_matches_reviewed_source() -> None:
    data = json.loads(BASELINE.read_text(encoding="utf-8"))
    assert data["schema"] == "rdp_v1_final_integration_baseline.v1"
    assert data["repository"] == "mortlach/RuneDecrypterPrime"
    assert data["reviewed_source_branch"] == "prelease/v1.0.0_o2p"
    assert data["integration_branch"] == "prelease/v1.0.0._h"
    assert data["reviewed_remote_head"] == (
        "a7a8439c8c3a6bc0b9110577ba93630857e08156"
    )
    assert data["reviewed_source_snapshot"]["sha256"] == (
        "3af42108db33a0e7b20062d1c1f2f06f276e043bb119bdd6576f9681c7eb1309"
    )
    assert len(data["authority_order"]) == 5
    assert data["local_state_policy"] == {
        "record_tracked_untracked_and_relevant_ignored_state": True,
        "reconcile_intentional_local_source": True,
        "backup_local_only_assets_notes_and_results_once": True,
        "repeat_whole_machine_archive_for_every_pack": False,
    }
