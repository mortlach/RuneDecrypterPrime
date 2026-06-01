from __future__ import annotations

import json
from pathlib import Path

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    build_phaseB_ngram_hamming_lane1_closure_review_pack_v1 as pack,
)


def write_repo_file(tmp_path: Path, rel_path: str, text: str) -> None:
    path = tmp_path / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_repo_json(tmp_path: Path, rel_path: str, payload: object) -> None:
    write_repo_file(tmp_path, rel_path, json.dumps(payload, indent=2) + "\n")


def prepare_minimal_inputs(tmp_path: Path, *, real_scan: bool = False, production_change: bool = False) -> None:
    for rel_path in pack.CONTEXT_FILES_REL + pack.SOURCE_FILES_REL + pack.TEST_FILES_REL:
        write_repo_file(tmp_path, rel_path, f"# {rel_path}\n")
    for rel_path in pack.COMPONENT_FILES_REL:
        write_repo_file(tmp_path, rel_path, "col\nvalue\n")
    write_repo_json(
        tmp_path,
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_asset_shard_provenance_v1/shard_provenance_manifest.json",
        {
            "status": "pass",
            "completed_shards": 2,
            "total_shards": 2,
            "missing_shards": 0,
            "failed_shards": 0,
            "missing_output_files": 0,
            "missing_required_output_combos": 0,
        },
    )
    write_repo_json(
        tmp_path,
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_provenance_review_pack_v1/review_pack_manifest.json",
        {
            "status": "review_ready",
            "pending_review_checks": [],
            "no_production_scorer_changes": not production_change,
            "no_broad_scan_launched": True,
        },
    )
    write_repo_json(
        tmp_path,
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_full_raw_language_asset_validation_v1/validation_manifest.json",
        {"status": "pass", "no_production_scorer_change": not production_change},
    )
    write_repo_json(
        tmp_path,
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_readiness_v1/readiness_manifest.json",
        {"status": "pass"},
    )
    write_repo_json(
        tmp_path,
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_launch_decision_record_v1/launch_decision_record_manifest.json",
        {
            "status": "blocked",
            "no_production_scorer_changes": not production_change,
            "no_broad_scan_launched": not real_scan,
        },
    )
    write_repo_json(
        tmp_path,
        "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_bridge_lane2_gated_diagnostic_v1/gated_diagnostic_manifest.json",
        {
            "status": "blocked",
            "real_candidate_scan_started": real_scan,
            "no_production_scorer_changes": not production_change,
        },
    )
    write_repo_json(
        tmp_path,
        f"{pack.ASSET_HOME_REL}/asset_manifest.json",
        {
            "asset_status": "review_ready_candidate",
            "no_production_scorer_change": not production_change,
            "lane2_launch_authority": "not_granted_by_this_asset",
        },
    )
    write_repo_file(tmp_path, f"{pack.ASSET_HOME_REL}/README.md", "# asset\n")
    for rel_path in pack.ASSET_INDEX_FILES_REL:
        if not (tmp_path / rel_path).exists():
            write_repo_file(tmp_path, rel_path, "col\nvalue\n")


def test_lane1_closure_pack_mirrors_asset_provenance_under_asset_index(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(pack, "REPO_ROOT", tmp_path)
    prepare_minimal_inputs(tmp_path)

    manifest = pack.build_lane1_closure_review_pack(
        pack_dir=tmp_path / "planning/projects/no_wli/40_review_summaries/review",
        zip_path=tmp_path / "planning/projects/no_wli/40_review_summaries/review.zip",
    )

    assert manifest["status"] == "packed_review_ready"
    assert not manifest["missing_files"]
    assert (
        tmp_path
        / "planning/projects/no_wli/40_review_summaries/review/50_asset_index/assets/ngram_hamming/phaseB_full_raw_v1/provenance/shard_provenance_manifest.json"
    ).exists()


def test_lane1_closure_pack_blocks_on_real_scan_or_production_change(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(pack, "REPO_ROOT", tmp_path)
    prepare_minimal_inputs(tmp_path, real_scan=True, production_change=True)

    manifest = pack.build_lane1_closure_review_pack(
        pack_dir=tmp_path / "planning/projects/no_wli/40_review_summaries/review",
        zip_path=tmp_path / "planning/projects/no_wli/40_review_summaries/review.zip",
    )

    assert manifest["status"] == "packed_with_blocks"
    assert manifest["production_scorer_change"] is True
    assert manifest["no_real_scan_state"] is False
