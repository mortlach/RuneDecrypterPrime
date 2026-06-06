from __future__ import annotations

import json

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    build_phaseB_failed_decryption_n3c_full80_consolidated_evidence_v1 as consolidated,
)


def test_full80_consolidated_evidence_declares_full_selected_80_scope_and_no_rank_effect() -> None:
    manifest = json.loads((consolidated.OUTPUT_DIR / "run_manifest.json").read_text(encoding="utf-8"))

    assert manifest["status"] == "full80_consolidated_evidence_ready_for_review"
    assert manifest["bucket_count"] == 5
    assert manifest["runtime_chunk_count"] == 1028
    assert manifest["logical_group_count"] == 702
    assert manifest["runtime_phrase_rows"] == 613_280_613
    assert manifest["candidate_count"] == 80
    assert manifest["query_is_full_n3c_for_selected_80_candidates"] is True
    assert manifest["query_is_full_734_candidate_fixture"] is False
    assert manifest["global_clusters_are_candidate_level_across_all_buckets"] is True
    assert manifest["bucket_clusters_are_diagnostic_only"] is True
    assert manifest["production_scoring_change"] is False
    assert manifest["production_ranking_change"] is False
    assert manifest["score_bearing_use_approved"] is False


def test_full80_consolidated_pair_ledger_keeps_simple_signals_report_only() -> None:
    manifest = json.loads((consolidated.OUTPUT_DIR / "run_manifest.json").read_text(encoding="utf-8"))

    assert manifest["pair_count_with_both_candidates_in_sample"] == 16
    assert manifest["pair_result_counts"]["hit_count"]["break"] > 0
    assert manifest["pair_result_counts"]["global_cluster"]["break"] > 0
    assert manifest["pair_result_counts"]["exact_global_cluster"]["break"] > 0
