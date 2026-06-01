from __future__ import annotations

import json
from pathlib import Path

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    build_phaseB_ngram_hamming_bridge_lane2_launch_decision_record_v1 as decision,
)


def write_repo_json(tmp_path: Path, rel_path: str, payload: object) -> None:
    path = tmp_path / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_dependencies(tmp_path: Path, *, readiness_ready: bool, review_ready: bool) -> None:
    write_repo_json(
        tmp_path,
        decision.READINESS_MANIFEST_REL,
        {
            "status": "pass" if readiness_ready else "blocked",
            "run_label": "readiness",
            "bridge_broad_scan_ready": readiness_ready,
            "completed_shards": 2,
            "total_shards": 2,
        },
    )
    write_repo_json(
        tmp_path,
        decision.PREP_STATUS_INDEX_MANIFEST_REL,
        {"status": "pass" if readiness_ready else "blocked", "run_label": "prep"},
    )
    write_repo_json(
        tmp_path,
        decision.PROVENANCE_REVIEW_PACK_MANIFEST_REL,
        {
            "status": "review_ready" if review_ready else "blocked",
            "run_label": "review",
            "pending_review_checks": [] if review_ready else ["phrase_length_distributions"],
        },
    )
    write_repo_json(
        tmp_path,
        decision.GATED_DIAGNOSTIC_MANIFEST_REL,
        {
            "status": "blocked",
            "run_label": "gated",
            "real_candidate_scan_started": False,
            "no_production_scorer_changes": True,
        },
    )


def test_launch_decision_record_blocks_current_partial_state(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(decision, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(decision, "ALLOW_REAL_BRIDGE_SCAN_AFTER_REVIEW", False)
    write_dependencies(tmp_path, readiness_ready=False, review_ready=False)

    manifest = decision.build_launch_decision_record(output_dir=tmp_path / "out")

    assert manifest["status"] == "blocked"
    assert "Lane 2 readiness gate is not pass" in manifest["blocked_reasons"]
    assert "full raw provenance review pack is not review_ready" in manifest["blocked_reasons"]
    assert "full raw provenance review pack still has pending review checks" in manifest["blocked_reasons"]
    assert "hardcoded real bridge scan approval switch is false" in manifest["blocked_reasons"]
    assert manifest["no_broad_scan_launched"] is True
    assert (tmp_path / "out" / "launch_decision_record_manifest.json").exists()


def test_launch_decision_record_can_become_launchable_after_review_and_approval(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(decision, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(decision, "ALLOW_REAL_BRIDGE_SCAN_AFTER_REVIEW", True)
    write_dependencies(tmp_path, readiness_ready=True, review_ready=True)

    manifest = decision.build_launch_decision_record(output_dir=tmp_path / "out")

    assert manifest["status"] == "launchable_after_review"
    assert not manifest["blocked_reasons"]
    assert manifest["bridge_broad_scan_ready"] is True
