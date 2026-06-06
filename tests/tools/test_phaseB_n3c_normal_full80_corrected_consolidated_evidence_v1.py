from __future__ import annotations

import csv
import json

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    build_phaseB_failed_decryption_n3c_normal_full80_corrected_consolidated_evidence_v1 as corrected,
)


def test_corrected_normal_manifest_locks_scope_and_exact_containing_semantics() -> None:
    manifest = json.loads((corrected.OUTPUT_DIR / "run_manifest.json").read_text(encoding="utf-8"))

    assert manifest["status"] == "n3c_normal_full80_corrected_consolidated_evidence_ready_for_engineering_gate"
    assert manifest["run_spec"]["dictionary_cut"] == "normal"
    assert manifest["run_spec"]["ngram_order"] == 3
    assert manifest["normal_query_rerun"] is False
    assert manifest["reused_existing_hit_files"] is True
    assert manifest["runtime_chunk_count"] == 1028
    assert manifest["logical_group_count"] == 702
    assert manifest["runtime_phrase_rows"] == 613_280_613
    assert manifest["verified_hit_count"] == 1_667_717
    assert manifest["global_candidate_n3c_cluster_count"] == 275
    assert manifest["global_candidate_n3c_exact_containing_cluster_count"] == 225
    assert manifest["exact_containing_cluster_count_invariant_pass"] is True
    assert manifest["production_scoring_change"] is False
    assert manifest["production_ranking_change"] is False
    assert manifest["score_bearing_use_approved"] is False


def test_corrected_normal_pair_counts_use_unique_semantic_pairs() -> None:
    manifest = json.loads((corrected.OUTPUT_DIR / "run_manifest.json").read_text(encoding="utf-8"))

    assert manifest["raw_pair_row_count_with_both_candidates_in_sample"] == 16
    assert manifest["unique_semantic_pair_count_with_both_candidates_in_sample"] == 8
    assert manifest["semantic_pair_duplicate_count"] == 8
    assert manifest["baseline_correct_unique_semantic_pair_count"] == 8
    assert manifest["rescue_capable_unique_semantic_pair_count"] == 0
    assert manifest["break_capable_unique_semantic_pair_count"] == 8
    assert manifest["unique_semantic_pair_result_counts"]["verified_hit_count"]["break"] > 0


def test_corrected_normal_candidate_summaries_obey_exact_subset_invariant() -> None:
    with (corrected.OUTPUT_DIR / "candidate_n3c_summary_rows.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 80
    for row in rows:
        exact_containing = int(row["global_candidate_n3c_exact_containing_cluster_count"])
        ordinary = int(row["global_candidate_n3c_cluster_count"])
        assert 0 <= exact_containing <= ordinary
