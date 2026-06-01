from __future__ import annotations

import json
from pathlib import Path

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    check_phaseB_ngram_hamming_bridge_lane2_readiness_v1 as readiness,
)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def contract_manifest() -> dict[str, object]:
    return {
        "status": "pass",
        "no_broad_scan_launched": True,
        "no_production_scorer_changes": True,
        "gate_status": readiness.REQUIRED_GATE_STATUS,
        "profile_manifest_hash": "abc",
    }


def provenance_manifest(*, status: str, complete: bool) -> dict[str, object]:
    return {
        "status": status,
        "full_raw_ngram_rebuild_confirmed": complete,
        "missing_shards": 0 if complete else 12,
        "failed_shards": 0,
        "missing_output_files": 0,
        "completed_shards": 1118 if complete else 1106,
        "total_shards": 1118,
    }


def test_readiness_blocks_partial_shard_provenance(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(readiness, "REPO_ROOT", tmp_path)
    contract_path = tmp_path / "contract.json"
    provenance_path = tmp_path / "provenance.json"
    write_json(contract_path, contract_manifest())
    write_json(provenance_path, provenance_manifest(status="running_or_interrupted", complete=False))

    manifest = readiness.check_readiness(
        contract_manifest_path=contract_path,
        shard_provenance_manifest_path=provenance_path,
        output_dir=tmp_path / "out",
    )

    assert manifest["status"] == "blocked"
    assert manifest["bridge_broad_scan_ready"] is False
    assert "full raw shard provenance status is not pass" in manifest["blocked_reasons"]
    assert "full raw n-gram rebuild is not confirmed" in manifest["blocked_reasons"]
    assert (tmp_path / "out" / "readiness_manifest.json").exists()


def test_readiness_passes_when_contract_and_full_provenance_pass(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(readiness, "REPO_ROOT", tmp_path)
    contract_path = tmp_path / "contract.json"
    provenance_path = tmp_path / "provenance.json"
    write_json(contract_path, contract_manifest())
    write_json(provenance_path, provenance_manifest(status="pass", complete=True))

    manifest = readiness.check_readiness(
        contract_manifest_path=contract_path,
        shard_provenance_manifest_path=provenance_path,
        output_dir=tmp_path / "out",
    )

    assert manifest["status"] == "pass"
    assert manifest["bridge_broad_scan_ready"] is True
    assert manifest["blocked_reasons"] == []


def test_readiness_blocks_contract_drift(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(readiness, "REPO_ROOT", tmp_path)
    contract = contract_manifest()
    contract["gate_status"] = "unexpected"
    contract_path = tmp_path / "contract.json"
    provenance_path = tmp_path / "provenance.json"
    write_json(contract_path, contract)
    write_json(provenance_path, provenance_manifest(status="pass", complete=True))

    manifest = readiness.check_readiness(
        contract_manifest_path=contract_path,
        shard_provenance_manifest_path=provenance_path,
        output_dir=tmp_path / "out",
    )

    assert manifest["status"] == "blocked"
    assert "contract pack gate status has drifted" in manifest["blocked_reasons"]
