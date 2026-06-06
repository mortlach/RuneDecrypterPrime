from __future__ import annotations

import csv
import json

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    build_phaseB_failed_decryption_n3c_strict_full80_corrected_consolidated_evidence_v1 as strict,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    build_phaseB_failed_decryption_n3c_strict_vs_normal_full80_comparison_v1 as comparison,
)


def test_strict_consolidated_manifest_locks_full80_scope_and_report_only_authority() -> None:
    manifest = json.loads((strict.OUTPUT_DIR / "run_manifest.json").read_text(encoding="utf-8"))

    assert manifest["status"] == "n3c_strict_full80_corrected_consolidated_evidence_ready_for_comparison"
    assert manifest["run_spec"]["dictionary_cut"] == "strict"
    assert manifest["runtime_chunk_count"] == 815
    assert manifest["logical_group_count"] == 702
    assert manifest["runtime_phrase_rows"] == 365_516_232
    assert manifest["candidate_count"] == 80
    assert manifest["verified_hit_count"] == 1_546_511
    assert manifest["global_candidate_n3c_cluster_count"] == 308
    assert manifest["global_candidate_n3c_exact_containing_cluster_count"] == 249
    assert manifest["exact_containing_cluster_count_invariant_pass"] is True
    assert manifest["production_scoring_change"] is False
    assert manifest["production_ranking_change"] is False
    assert manifest["score_bearing_use_approved"] is False


def test_strict_candidate_summaries_obey_exact_subset_invariant() -> None:
    with (strict.OUTPUT_DIR / "candidate_n3c_summary_rows.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 80
    for row in rows:
        exact_containing = int(row["global_candidate_n3c_exact_containing_cluster_count"])
        ordinary = int(row["global_candidate_n3c_cluster_count"])
        assert 0 <= exact_containing <= ordinary


def test_comparison_manifest_reports_matched_scope_and_no_phrase_identity_claim() -> None:
    manifest = json.loads((comparison.OUTPUT_DIR / "run_manifest.json").read_text(encoding="utf-8"))

    assert manifest["status"] == "n3c_strict_vs_normal_full80_comparison_ready_for_review_pack"
    assert manifest["normal_runtime_chunk_count"] == 1028
    assert manifest["strict_runtime_chunk_count"] == 815
    assert manifest["normal_phrase_rows"] == 613_280_613
    assert manifest["strict_phrase_rows"] == 365_516_232
    assert manifest["normal_verified_hit_count"] == 1_667_717
    assert manifest["strict_verified_hit_count"] == 1_546_511
    assert manifest["unique_semantic_pair_count"] == 8
    assert manifest["rescue_capable_unique_semantic_pair_count"] == 0
    assert manifest["phrase_level_strict_subset_identity_proven"] is False
    assert manifest["production_scoring_change"] is False
    assert manifest["production_ranking_change"] is False
    assert manifest["score_bearing_use_approved"] is False
