from __future__ import annotations

import csv
import json

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    build_phaseB_failed_decryption_n3c_strict_320_corrected_consolidated_evidence_v1 as strict320,
)


def test_strict_320_manifest_covers_all_completed_buckets_and_remains_report_only() -> None:
    manifest = json.loads((strict320.OUTPUT_DIR / "run_manifest.json").read_text(encoding="utf-8"))

    assert manifest["status"] == "n3c_strict_320_corrected_consolidated_evidence_ready_for_review_pack"
    assert manifest["cohort_count"] == 4
    assert manifest["bucket_output_count"] == 20
    assert manifest["candidate_count"] == 320
    assert manifest["runtime_chunk_count"] == 3260
    assert manifest["runtime_phrase_rows"] == 1_462_064_928
    assert manifest["verified_hit_count"] == 6_415_767
    assert manifest["global_candidate_n3c_cluster_count"] == 1_115
    assert manifest["exact_containing_cluster_count_invariant_pass"] is True
    assert manifest["query_is_full_734_candidate_fixture"] is False
    assert manifest["production_scoring_change"] is False
    assert manifest["production_ranking_change"] is False
    assert manifest["score_bearing_use_approved"] is False


def test_strict_320_candidate_summaries_obey_exact_subset_invariant() -> None:
    with (strict320.OUTPUT_DIR / "candidate_n3c_summary_rows.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 320
    for row in rows:
        ordinary = int(row["global_candidate_n3c_cluster_count"])
        exact_containing = int(row["global_candidate_n3c_exact_containing_cluster_count"])
        assert 0 <= exact_containing <= ordinary
