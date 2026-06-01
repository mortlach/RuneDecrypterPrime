from __future__ import annotations

import csv
import json
from pathlib import Path

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    run_phaseB_ngram_hamming_bridge_lane2_synthetic_contract_smoke_v1 as smoke,
)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_synthetic_contract_smoke_writes_all_lane2_output_shapes(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(smoke, "REPO_ROOT", tmp_path)
    output_dir = tmp_path / "out"

    manifest = smoke.run_synthetic_contract_smoke(output_dir=output_dir)

    assert manifest["status"] == "pass"
    assert manifest["no_real_candidate_scan"] is True
    assert manifest["no_production_scorer_changes"] is True
    assert manifest["raw_hit_count"] == 3
    assert manifest["pair_ledger_row_count"] == 1
    assert manifest["zero_hit_audit_row_count"] == 1
    for name in (
        "profile_manifest_rows.csv",
        "all_cluster_rows.csv",
        "score_candidate_cluster_rows.csv",
        "all_profile_candidate_summary_rows.csv",
        "score_candidate_candidate_summary_rows.csv",
        "pair_ledger_rows.csv",
        "zero_hit_audit_rows.csv",
        "readout.md",
    ):
        assert (output_dir / name).exists()


def test_synthetic_contract_smoke_keeps_diagnostic_profile_out_of_score_clusters(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(smoke, "REPO_ROOT", tmp_path)
    output_dir = tmp_path / "out"

    smoke.run_synthetic_contract_smoke(output_dir=output_dir)
    all_clusters = read_csv_rows(output_dir / "all_cluster_rows.csv")
    score_clusters = read_csv_rows(output_dir / "score_candidate_cluster_rows.csv")
    all_candidate_rows = read_csv_rows(output_dir / "all_profile_candidate_summary_rows.csv")
    score_candidate_rows = read_csv_rows(output_dir / "score_candidate_candidate_summary_rows.csv")

    assert len(all_clusters) == 2
    assert len(score_clusters) == 2
    assert any("BR_O2_soft" in row["profiles_present"] for row in all_clusters)
    assert all("BR_O2_soft" not in row["profiles_present"] for row in score_clusters)
    diag_row = next(row for row in all_candidate_rows if row["profile_id"] == "BR_O2_soft")
    assert diag_row["score_authority"] == "diagnostic_only"
    assert all(row["score_authority"] != "diagnostic_only" for row in score_candidate_rows)
    assert all(row["profile_id"] != "BR_O2_soft" for row in score_candidate_rows)


def test_synthetic_contract_smoke_pair_and_zero_rows_are_json_stable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(smoke, "REPO_ROOT", tmp_path)
    output_dir = tmp_path / "out"

    smoke.run_synthetic_contract_smoke(output_dir=output_dir)
    pair = read_csv_rows(output_dir / "pair_ledger_rows.csv")[0]
    zero = read_csv_rows(output_dir / "zero_hit_audit_rows.csv")[0]
    manifest = json.loads((output_dir / "synthetic_contract_manifest.json").read_text(encoding="utf-8"))

    assert json.loads(pair["unsafe_interpretation_flags"]) == ["synthetic_fixture"]
    assert json.loads(zero["ngram_hit_count_by_order"]) == {"2": 0, "3": 0}
    assert manifest["profile_manifest_hash"]
