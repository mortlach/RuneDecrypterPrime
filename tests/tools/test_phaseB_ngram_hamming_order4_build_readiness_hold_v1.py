from __future__ import annotations

import csv
import json
from pathlib import Path

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    build_phaseB_ngram_hamming_order4_build_readiness_hold_v1 as readiness,
)


def test_readiness_evidence_is_an_explicit_build_hold(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(readiness, "REPO_ROOT", tmp_path)

    manifest = readiness.build_readiness_hold_evidence()

    assert manifest["status"] == "hold_not_approved"
    assert manifest["full_build_approved"] is False
    assert manifest["production_scoring_change_approved"] is False
    assert manifest["production_ranking_change_approved"] is False
    assert manifest["raw_asset"]["aggregate_rows"] == 1_037_043_475
    assert manifest["compact_canary"]["validation_status"] == "pass"
    assert manifest["partial_full_compact_preparation"]["completed_partitions"] == 50
    assert manifest["partial_full_compact_preparation"]["total_partitions"] == 800


def test_estimates_have_no_launch_authority_and_resume_is_blocked(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(readiness, "REPO_ROOT", tmp_path)
    readiness.build_readiness_hold_evidence()
    output_dir = tmp_path / readiness.OUTPUT_DIR_REL

    with (output_dir / "temporary_space_estimate_rows.csv").open(newline="", encoding="utf-8") as handle:
        estimate_rows = list(csv.DictReader(handle))
    resume_contract = json.loads((output_dir / "abort_and_resume_contract.json").read_text(encoding="utf-8"))

    assert estimate_rows
    assert {row["launch_authority"] for row in estimate_rows} == {"none"}
    assert any(row["evidence_class"] == "planning_estimate_only" for row in estimate_rows)
    assert resume_contract["status"] == "hold_not_approved"
    assert resume_contract["resume_allowed"] is False
    assert resume_contract["asset_isolation"]["mix_with_closed_order2_order3_assets"] is False
