from __future__ import annotations

import json
from pathlib import Path

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    build_phaseB_ngram_hamming_bridge_lane2_contract_pack_v1 as pack,
)


def test_contract_pack_writes_profile_and_schema_manifests(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(pack, "REPO_ROOT", tmp_path)
    output_dir = tmp_path / "out"

    manifest = pack.build_contract_pack(output_dir=output_dir)

    assert manifest["status"] == "pass"
    assert manifest["no_broad_scan_launched"] is True
    assert manifest["no_production_scorer_changes"] is True
    assert manifest["canonical_profile_count"] == 7
    assert manifest["bridge_profile_count"] == 5
    assert "BR_O3_conservative" in manifest["score_candidate_profile_ids"]
    assert "BR_O2_soft" not in manifest["score_candidate_profile_ids"]
    assert (output_dir / "profile_manifest_rows.csv").exists()
    assert (output_dir / "profile_manifest.json").exists()
    assert (output_dir / "schema_manifest.json").exists()
    assert (output_dir / "readout.md").exists()


def test_contract_pack_schema_manifest_contains_all_required_groups(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(pack, "REPO_ROOT", tmp_path)
    output_dir = tmp_path / "out"

    pack.build_contract_pack(output_dir=output_dir)
    schema = json.loads((output_dir / "schema_manifest.json").read_text(encoding="utf-8"))

    assert "profile_manifest_required_fields" in schema
    assert "cluster_row_required_fields" in schema
    assert "candidate_summary_required_fields" in schema
    assert "pair_ledger_required_fields" in schema
    assert "zero_hit_audit_required_fields" in schema
    assert "score_authority" in schema["profile_manifest_required_fields"]
    assert "best_hit_signature" in schema["candidate_summary_required_fields"]
