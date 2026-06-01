from __future__ import annotations

import json
from pathlib import Path

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    run_phaseB_ngram_hamming_bridge_lane2_gated_diagnostic_v1 as gated,
)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def test_gated_diagnostic_blocks_when_readiness_is_blocked(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(gated, "REPO_ROOT", tmp_path)
    readiness_path = tmp_path / "readiness.json"
    write_json(
        readiness_path,
        {
            "status": "blocked",
            "bridge_broad_scan_ready": False,
            "completed_shards": 595,
            "total_shards": 1118,
        },
    )

    manifest = gated.run_gated_diagnostic(
        readiness_manifest_path=readiness_path,
        output_dir=tmp_path / "out",
    )

    assert manifest["status"] == "blocked"
    assert manifest["real_candidate_scan_started"] is False
    assert "Lane 2 readiness gate is not pass" in manifest["blocked_reasons"]
    assert "ALLOW_REAL_BRIDGE_SCAN is false" in manifest["blocked_reasons"]


def test_gated_diagnostic_still_blocks_without_hardcoded_scan_approval(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(gated, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(gated, "ALLOW_REAL_BRIDGE_SCAN", False)
    readiness_path = tmp_path / "readiness.json"
    write_json(
        readiness_path,
        {
            "status": "pass",
            "bridge_broad_scan_ready": True,
            "completed_shards": 1118,
            "total_shards": 1118,
        },
    )

    manifest = gated.run_gated_diagnostic(
        readiness_manifest_path=readiness_path,
        output_dir=tmp_path / "out",
    )

    assert manifest["status"] == "blocked"
    assert manifest["readiness_bridge_broad_scan_ready"] is True
    assert manifest["real_candidate_scan_started"] is False
    assert manifest["blocked_reasons"] == ["ALLOW_REAL_BRIDGE_SCAN is false"]


def test_gated_diagnostic_ready_state_is_explicitly_unimplemented(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(gated, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(gated, "ALLOW_REAL_BRIDGE_SCAN", True)
    readiness_path = tmp_path / "readiness.json"
    write_json(
        readiness_path,
        {
            "status": "pass",
            "bridge_broad_scan_ready": True,
            "completed_shards": 1118,
            "total_shards": 1118,
        },
    )

    manifest = gated.run_gated_diagnostic(
        readiness_manifest_path=readiness_path,
        output_dir=tmp_path / "out",
    )

    assert manifest["status"] == "ready_no_scan_implemented"
    assert manifest["real_candidate_scan_started"] is False
    assert manifest["blocked_reasons"] == []
