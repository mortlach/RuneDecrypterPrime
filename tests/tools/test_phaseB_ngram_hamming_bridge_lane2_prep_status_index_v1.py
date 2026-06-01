from __future__ import annotations

import json
from pathlib import Path

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    build_phaseB_ngram_hamming_bridge_lane2_prep_status_index_v1 as index,
)


def write_repo_json(tmp_path: Path, rel_path: str, payload: object) -> None:
    path = tmp_path / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def test_prep_status_index_collates_existing_components(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(index, "REPO_ROOT", tmp_path)
    write_repo_json(tmp_path, index.CONTRACT_MANIFEST_REL, {"status": "pass", "run_label": "contract", "profile_manifest_hash": "hash"})
    write_repo_json(
        tmp_path,
        index.INPUT_CONTRACT_MANIFEST_REL,
        {"status": "pass", "run_label": "input", "no_real_candidate_scan": True},
    )
    write_repo_json(
        tmp_path,
        index.SYNTHETIC_MANIFEST_REL,
        {"status": "pass", "run_label": "synthetic", "no_real_candidate_scan": True},
    )
    write_repo_json(
        tmp_path,
        index.SHARD_PROVENANCE_MANIFEST_REL,
        {"status": "running_or_interrupted", "run_label": "shards", "completed_shards": 10, "total_shards": 20},
    )
    write_repo_json(
        tmp_path,
        index.READINESS_MANIFEST_REL,
        {"status": "blocked", "run_label": "ready", "bridge_broad_scan_ready": False, "blocked_reasons": ["partial"]},
    )
    write_repo_json(
        tmp_path,
        index.PROVENANCE_REVIEW_PACK_MANIFEST_REL,
        {"status": "blocked", "run_label": "review", "pending_review_checks": ["shard_count_pass"]},
    )
    write_repo_json(
        tmp_path,
        index.LAUNCH_DECISION_RECORD_MANIFEST_REL,
        {"status": "blocked", "run_label": "launch"},
    )

    manifest = index.build_prep_status_index(output_dir=tmp_path / "out")

    assert manifest["status"] == "blocked"
    assert manifest["completed_shards"] == 10
    assert manifest["bridge_broad_scan_ready"] is False
    assert manifest["synthetic_no_real_candidate_scan"] is True
    assert manifest["input_contract_status"] == "pass"
    assert manifest["provenance_review_pack_status"] == "blocked"
    assert manifest["launch_decision_record_status"] == "blocked"
    assert len(manifest["components"]) == 7
    assert (tmp_path / "out" / "prep_status_index_manifest.json").exists()


def test_prep_status_index_reports_missing_components(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(index, "REPO_ROOT", tmp_path)

    manifest = index.build_prep_status_index(output_dir=tmp_path / "out")

    assert manifest["status"] == "blocked"
    assert any(row["exists"] is False for row in manifest["components"])
    assert "one or more Lane 2 prep components are missing" in manifest["blocked_reasons"]
