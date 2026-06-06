from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
for path in (REPO_ROOT, REPO_ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.phaseB_n3c_query_planning_core_v1 import (
    annotated_cluster_hit_rows,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.build_phaseB_failed_decryption_n3c_strict_full80_corrected_consolidated_evidence_v1 import (
    build_pair_rows,
    count_csv_data_rows,
    file_sha256,
    interval_covered_token_count,
    read_rows,
    write_csv,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.run_phaseB_failed_decryption_n3c_full80_query_evidence_v1 import (
    FIXTURE_DIR,
)


PHASE = "phaseB_failed_decryption_n3c_strict_320_corrected_consolidated_evidence_v1"
OUTPUT_DIR = REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis" / PHASE
BUCKET_PHASES = (
    ("selected80", "8-9", "phaseB_failed_decryption_n3c_strict_full80_bucket_8_9_query_evidence_v1"),
    ("selected80", "10-11", "phaseB_failed_decryption_n3c_strict_full80_bucket_10_11_query_evidence_v1"),
    ("selected80", "12-14", "phaseB_failed_decryption_n3c_strict_full80_bucket_12_14_query_evidence_v1"),
    ("selected80", "15-17", "phaseB_failed_decryption_n3c_strict_full80_bucket_15_17_query_evidence_v1"),
    ("selected80", "18+", "phaseB_failed_decryption_n3c_strict_full80_bucket_18_plus_query_evidence_v1"),
    ("remaining_batch_01", "8-9", "phaseB_failed_decryption_n3c_strict_full80_remaining_batch_01_bucket_8_9_query_evidence_v1"),
    ("remaining_batch_01", "10-11", "phaseB_failed_decryption_n3c_strict_full80_remaining_batch_01_bucket_10_11_query_evidence_v1"),
    ("remaining_batch_01", "12-14", "phaseB_failed_decryption_n3c_strict_full80_remaining_batch_01_bucket_12_14_query_evidence_v1"),
    ("remaining_batch_01", "15-17", "phaseB_failed_decryption_n3c_strict_full80_remaining_batch_01_bucket_15_17_query_evidence_v1"),
    ("remaining_batch_01", "18+", "phaseB_failed_decryption_n3c_strict_full80_remaining_batch_01_bucket_18_plus_query_evidence_v1"),
    ("remaining_batch_02", "8-9", "phaseB_failed_decryption_n3c_strict_full80_remaining_batch_02_bucket_8_9_query_evidence_v1"),
    ("remaining_batch_02", "10-11", "phaseB_failed_decryption_n3c_strict_full80_remaining_batch_02_bucket_10_11_query_evidence_v1"),
    ("remaining_batch_02", "12-14", "phaseB_failed_decryption_n3c_strict_full80_remaining_batch_02_bucket_12_14_query_evidence_v1"),
    ("remaining_batch_02", "15-17", "phaseB_failed_decryption_n3c_strict_full80_remaining_batch_02_bucket_15_17_query_evidence_v1"),
    ("remaining_batch_02", "18+", "phaseB_failed_decryption_n3c_strict_full80_remaining_batch_02_bucket_18_plus_query_evidence_v1"),
    ("remaining_batch_03", "8-9", "phaseB_failed_decryption_n3c_strict_full80_remaining_batch_03_bucket_8_9_query_evidence_v1"),
    ("remaining_batch_03", "10-11", "phaseB_failed_decryption_n3c_strict_full80_remaining_batch_03_bucket_10_11_query_evidence_v1"),
    ("remaining_batch_03", "12-14", "phaseB_failed_decryption_n3c_strict_full80_remaining_batch_03_bucket_12_14_query_evidence_v1"),
    ("remaining_batch_03", "15-17", "phaseB_failed_decryption_n3c_strict_full80_remaining_batch_03_bucket_15_17_query_evidence_v1"),
    ("remaining_batch_03", "18+", "phaseB_failed_decryption_n3c_strict_full80_remaining_batch_03_bucket_18_plus_query_evidence_v1"),
)


def build_strict_320_consolidated_evidence() -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    analysis_root = REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis"
    fixture_candidates = {
        row["candidate_id"]: row
        for row in csv.DictReader((FIXTURE_DIR / "retained_candidate_rows.csv").open(encoding="utf-8", newline=""))
    }
    bucket_summary_rows: list[dict[str, object]] = []
    chunk_rows: list[dict[str, object]] = []
    logical_rows: list[dict[str, object]] = []
    hit_file_manifest_rows: list[dict[str, object]] = []
    candidate_hits: dict[str, list[dict[str, object]]] = defaultdict(list)
    candidate_hit_counts: dict[str, int] = defaultdict(int)
    candidate_exact_hit_counts: dict[str, int] = defaultdict(int)
    candidate_meta: dict[str, dict[str, str]] = {}

    for cohort_id, expected_bucket, phase in BUCKET_PHASES:
        phase_dir = analysis_root / phase
        manifest = json.loads((phase_dir / "run_manifest.json").read_text(encoding="utf-8"))
        if manifest["status"] != "bucket_n3c_query_complete":
            raise RuntimeError(f"{phase} is not complete: {manifest['status']}")
        run_spec = manifest.get("run_spec", {})
        if run_spec.get("dictionary_cut") != "strict" or run_spec.get("length_bucket") != expected_bucket:
            raise RuntimeError(f"{phase} run spec does not match strict bucket {expected_bucket}")
        if manifest["production_scoring_change"] or manifest["production_ranking_change"]:
            raise RuntimeError(f"{phase} unexpectedly changes production scoring/ranking")
        bucket_summary_rows.append({
            "cohort_id": cohort_id,
            "length_bucket": expected_bucket,
            "phase": phase,
            "runtime_chunk_count": manifest["runtime_chunk_count"],
            "logical_group_count": manifest["logical_group_count"],
            "runtime_phrase_rows": manifest["runtime_phrase_rows"],
            "verified_hit_count": manifest["verified_hit_count"],
            "bucket_local_candidate_n3c_cluster_count": manifest["global_candidate_n3c_cluster_count"],
            "bucket_local_candidate_n3c_exact_containing_cluster_count": manifest[
                "global_candidate_n3c_exact_containing_cluster_count"
            ],
            "runtime_seconds": manifest["total_runtime_seconds_this_invocation"],
            "peak_memory_mb": manifest["peak_memory_mb"],
            "runtime_budget_pass": manifest["runtime_budget_pass"],
            "memory_budget_pass": manifest["memory_budget_pass"],
        })
        for row in read_rows(phase_dir / "chunk_timing_rows.csv"):
            chunk_rows.append({"cohort_id": cohort_id, "length_bucket": expected_bucket, **row})
        for row in read_rows(phase_dir / "logical_group_summary_rows.csv"):
            logical_rows.append(row)
        for row in read_rows(phase_dir / "candidate_rows.csv"):
            candidate_meta[row["candidate_id"]] = row
        hit_path = phase_dir / "n3c_verified_hit_rows.csv"
        hit_file_manifest_rows.append({
            "cohort_id": cohort_id,
            "length_bucket": expected_bucket,
            "phase": phase,
            "hit_file": hit_path.relative_to(REPO_ROOT).as_posix(),
            "bytes": hit_path.stat().st_size,
            "csv_data_rows": count_csv_data_rows(hit_path),
            "sha256": file_sha256(hit_path),
        })
        with hit_path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                candidate_id = row["candidate_id"]
                is_exact = row["exact_flag"] == "True"
                candidate_hits[candidate_id].append({
                    "start_offset": int(row["hit_start"]),
                    "end_offset": int(row["hit_end"]),
                    "is_exact": is_exact,
                    "length_bucket": row["length_bucket"],
                    "logical_group_id": row["logical_group_id"],
                })
                candidate_hit_counts[candidate_id] += 1
                if is_exact:
                    candidate_exact_hit_counts[candidate_id] += 1

    candidate_cluster_rows: list[dict[str, object]] = []
    candidate_summary_rows: list[dict[str, object]] = []
    for candidate_id in sorted(candidate_meta):
        clusters = annotated_cluster_hit_rows(candidate_hits[candidate_id])
        meta = candidate_meta[candidate_id]
        fixture_row = fixture_candidates[candidate_id]
        candidate_token_count = len(json.loads(fixture_row["candidate_token_ids_json"]))
        covered_token_count = interval_covered_token_count(clusters)
        for cluster in clusters:
            candidate_cluster_rows.append({
                "trial_id": meta["trial_id"],
                "candidate_id": candidate_id,
                "dictionary_cut": "strict",
                "ngram_order": 3,
                **cluster,
            })
        exact_containing = sum(1 for row in clusters if row["has_exact"])
        candidate_summary_rows.append({
            "trial_id": meta["trial_id"],
            "candidate_id": candidate_id,
            "candidate_stratum": meta["candidate_stratum"],
            "baseline_score": meta["baseline_score"],
            "verified_hit_count": candidate_hit_counts[candidate_id],
            "exact_hit_count": candidate_exact_hit_counts[candidate_id],
            "global_candidate_n3c_cluster_count": len(clusters),
            "global_candidate_n3c_exact_containing_cluster_count": exact_containing,
            "cluster_covered_token_count": covered_token_count,
            "cluster_coverage_fraction": covered_token_count / candidate_token_count,
        })
    by_candidate = {row["candidate_id"]: row for row in candidate_summary_rows}
    raw_pair_rows, unique_pair_rows = build_pair_rows(by_candidate)

    write_csv(OUTPUT_DIR / "bucket_summary_rows.csv", bucket_summary_rows, tuple(bucket_summary_rows[0]))
    write_csv(OUTPUT_DIR / "chunk_timing_rows.csv", chunk_rows, tuple(chunk_rows[0]))
    write_csv(OUTPUT_DIR / "logical_group_summary_rows.csv", logical_rows, tuple(logical_rows[0]))
    write_csv(OUTPUT_DIR / "hit_file_manifest_rows.csv", hit_file_manifest_rows, tuple(hit_file_manifest_rows[0]))
    write_csv(OUTPUT_DIR / "candidate_n3c_cluster_rows.csv", candidate_cluster_rows, tuple(candidate_cluster_rows[0]))
    write_csv(OUTPUT_DIR / "candidate_n3c_summary_rows.csv", candidate_summary_rows, tuple(candidate_summary_rows[0]))
    write_csv(OUTPUT_DIR / "raw_pairwise_gold_n3c_report_rows.csv", raw_pair_rows, tuple(raw_pair_rows[0]))
    write_csv(OUTPUT_DIR / "unique_semantic_pairwise_gold_n3c_report_rows.csv", unique_pair_rows, tuple(unique_pair_rows[0]))

    unique_pair_result_counts = {
        "verified_hit_count": dict(Counter(row["n3c_verified_hit_count_pair_result"] for row in unique_pair_rows)),
        "global_cluster": dict(Counter(row["n3c_global_cluster_pair_result"] for row in unique_pair_rows)),
        "exact_containing_global_cluster": dict(Counter(
            row["n3c_exact_containing_global_cluster_pair_result"] for row in unique_pair_rows
        )),
    }
    exact_containing_count = sum(
        int(row["global_candidate_n3c_exact_containing_cluster_count"]) for row in candidate_summary_rows
    )
    ordinary_cluster_count = sum(int(row["global_candidate_n3c_cluster_count"]) for row in candidate_summary_rows)
    manifest = {
        "status": "n3c_strict_320_corrected_consolidated_evidence_ready_for_review_pack",
        "phase": PHASE,
        "cohort_count": 4,
        "bucket_output_count": len(bucket_summary_rows),
        "runtime_chunk_count": sum(int(row["runtime_chunk_count"]) for row in bucket_summary_rows),
        "logical_group_count_per_cohort": len({row["logical_group_id"] for row in logical_rows}),
        "runtime_phrase_rows": sum(int(row["runtime_phrase_rows"]) for row in bucket_summary_rows),
        "candidate_count": len(candidate_summary_rows),
        "verified_hit_count": sum(int(row["verified_hit_count"]) for row in bucket_summary_rows),
        "global_candidate_n3c_cluster_count": ordinary_cluster_count,
        "global_candidate_n3c_exact_containing_cluster_count": exact_containing_count,
        "exact_containing_cluster_count_invariant_pass": exact_containing_count <= ordinary_cluster_count,
        "raw_pair_row_count_with_both_candidates_in_sample": len(raw_pair_rows),
        "unique_semantic_pair_count_with_both_candidates_in_sample": len(unique_pair_rows),
        "semantic_pair_duplicate_count": len(raw_pair_rows) - len(unique_pair_rows),
        "rescue_capable_unique_semantic_pair_count": sum(row["can_observe_rescue"] is True for row in unique_pair_rows),
        "break_capable_unique_semantic_pair_count": sum(row["can_observe_break"] is True for row in unique_pair_rows),
        "unique_semantic_pair_result_counts": unique_pair_result_counts,
        "bucket_runtime_seconds_sum": sum(float(row["runtime_seconds"]) for row in bucket_summary_rows),
        "peak_memory_mb_max": max(float(row["peak_memory_mb"]) for row in bucket_summary_rows),
        "query_is_full_734_candidate_fixture": False,
        "candidate_scope_note": "strict selected80 plus three remaining 80-candidate batches",
        "hit_rows_are_external_bucket_files": True,
        "production_scoring_change": False,
        "production_ranking_change": False,
        "score_bearing_use_approved": False,
        "next_gate": "external_review_before_734_or_score_bearing_work",
    }
    (OUTPUT_DIR / "run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (OUTPUT_DIR / "readout.md").write_text(
        "# Strict 320 Candidate Corrected Consolidated Evidence\n\n"
        f"- status: `{manifest['status']}`\n"
        f"- candidates: `{manifest['candidate_count']}`\n"
        f"- bucket outputs: `{manifest['bucket_output_count']}`\n"
        f"- phrase rows queried: `{manifest['runtime_phrase_rows']}`\n"
        f"- verified hits: `{manifest['verified_hit_count']}`\n"
        f"- global candidate clusters: `{manifest['global_candidate_n3c_cluster_count']}`\n"
        f"- exact-containing global candidate clusters: "
        f"`{manifest['global_candidate_n3c_exact_containing_cluster_count']}`\n"
        f"- unique semantic pairs: `{manifest['unique_semantic_pair_count_with_both_candidates_in_sample']}`\n"
        f"- rescue-capable unique pairs: `{manifest['rescue_capable_unique_semantic_pair_count']}`\n"
        f"- summed bucket runtime seconds: `{manifest['bucket_runtime_seconds_sum']:.1f}`\n\n"
        "This is strict report-only evidence for 320 candidates. It changes no production score or ranking.\n",
        encoding="utf-8",
    )
    print(f"[{PHASE}] status={manifest['status']}")
    print(
        f"[{PHASE}] candidates={manifest['candidate_count']} hits={manifest['verified_hit_count']} "
        f"clusters={manifest['global_candidate_n3c_cluster_count']} pairs={manifest['unique_semantic_pair_count_with_both_candidates_in_sample']}"
    )
    return manifest


if __name__ == "__main__":
    build_strict_320_consolidated_evidence()
