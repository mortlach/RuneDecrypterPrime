from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
for path in (REPO_ROOT, REPO_ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.phaseB_n3c_query_planning_core_v1 import cluster_hit_spans
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.run_phaseB_failed_decryption_n3c_full80_query_evidence_v1 import (
    FIXTURE_DIR,
    compare_signal,
    classify_pair,
)


PHASE = "phaseB_failed_decryption_n3c_full80_consolidated_evidence_v1"
OUTPUT_DIR = REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis" / PHASE
BUCKET_PHASES = (
    ("8-9", "phaseB_failed_decryption_n3c_full80_bucket_8_9_query_evidence_v1"),
    ("10-11", "phaseB_failed_decryption_n3c_full80_bucket_10_11_query_evidence_v1"),
    ("12-14", "phaseB_failed_decryption_n3c_full80_bucket_12_14_query_evidence_v1"),
    ("15-17", "phaseB_failed_decryption_n3c_full80_bucket_15_17_query_evidence_v1"),
    ("18+", "phaseB_failed_decryption_n3c_full80_bucket_18_plus_query_evidence_v1"),
)


def file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def write_csv(path: Path, rows: list[dict[str, object]], fields: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def count_csv_data_rows(path: Path) -> int:
    with path.open(encoding="utf-8", newline="") as handle:
        return max(sum(1 for _line in handle) - 1, 0)


def build_consolidated_evidence() -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    analysis_root = REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis"
    bucket_summary_rows: list[dict[str, object]] = []
    chunk_rows: list[dict[str, object]] = []
    logical_rows: list[dict[str, object]] = []
    hit_file_manifest_rows: list[dict[str, object]] = []
    candidate_spans: dict[str, list[tuple[int, int]]] = defaultdict(list)
    candidate_exact_spans: dict[str, list[tuple[int, int]]] = defaultdict(list)
    candidate_hit_counts: dict[str, int] = defaultdict(int)
    candidate_exact_hit_counts: dict[str, int] = defaultdict(int)
    candidate_meta: dict[str, dict[str, str]] = {}

    for expected_bucket, phase in BUCKET_PHASES:
        phase_dir = analysis_root / phase
        manifest_path = phase_dir / "run_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest["status"] != "bucket_n3c_query_complete":
            raise RuntimeError(f"{phase} is not complete: {manifest['status']}")
        if manifest["production_scoring_change"] or manifest["production_ranking_change"]:
            raise RuntimeError(f"{phase} unexpectedly changes production scoring/ranking")
        bucket_summary_rows.append({
            "length_bucket": expected_bucket,
            "phase": phase,
            "runtime_chunk_count": manifest["runtime_chunk_count"],
            "logical_group_count": manifest["logical_group_count"],
            "runtime_phrase_rows": manifest["runtime_phrase_rows"],
            "verified_hit_count": manifest["verified_hit_count"],
            "bucket_candidate_cluster_count": manifest["global_candidate_n3c_cluster_count"],
            "bucket_candidate_exact_cluster_count": manifest["global_candidate_n3c_exact_cluster_count"],
            "pair_count_with_both_candidates_in_sample": manifest["pair_count_with_both_candidates_in_sample"],
            "runtime_seconds": manifest["total_runtime_seconds_this_invocation"],
            "peak_memory_mb": manifest["peak_memory_mb"],
            "runtime_budget_pass": manifest["runtime_budget_pass"],
            "memory_budget_pass": manifest["memory_budget_pass"],
        })
        for row in read_rows(phase_dir / "chunk_timing_rows.csv"):
            chunk_rows.append({"length_bucket": expected_bucket, **row})
        for row in read_rows(phase_dir / "logical_group_summary_rows.csv"):
            logical_rows.append(row)
        for row in read_rows(phase_dir / "candidate_rows.csv"):
            candidate_meta[row["candidate_id"]] = row

        hit_path = phase_dir / "n3c_verified_hit_rows.csv"
        hit_file_manifest_rows.append({
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
                span = (int(row["hit_start"]), int(row["hit_end"]))
                candidate_spans[candidate_id].append(span)
                candidate_hit_counts[candidate_id] += 1
                if row["exact_flag"] == "True":
                    candidate_exact_spans[candidate_id].append(span)
                    candidate_exact_hit_counts[candidate_id] += 1

    candidate_summary_rows = []
    for candidate_id in sorted(candidate_meta):
        clusters = cluster_hit_spans(candidate_spans[candidate_id])
        exact_clusters = cluster_hit_spans(candidate_exact_spans[candidate_id])
        meta = candidate_meta[candidate_id]
        candidate_summary_rows.append({
            "trial_id": meta["trial_id"],
            "candidate_id": candidate_id,
            "candidate_stratum": meta["candidate_stratum"],
            "baseline_score": meta["baseline_score"],
            "hit_count": candidate_hit_counts[candidate_id],
            "exact_hit_count": candidate_exact_hit_counts[candidate_id],
            "global_candidate_n3c_cluster_count": len(clusters),
            "global_candidate_n3c_exact_cluster_count": len(exact_clusters),
            "global_candidate_n3c_cluster_span_rows": json.dumps(clusters, separators=(",", ":")),
        })
    by_candidate = {row["candidate_id"]: row for row in candidate_summary_rows}
    selected_ids = set(by_candidate)
    pair_rows = []
    for pair in csv.DictReader((FIXTURE_DIR / "candidate_pair_rows.csv").open(encoding="utf-8", newline="")):
        if pair["candidate_a_id"] not in selected_ids or pair["candidate_b_id"] not in selected_ids:
            continue
        left = by_candidate[pair["candidate_a_id"]]
        right = by_candidate[pair["candidate_b_id"]]
        hit_winner = compare_signal(
            int(left["hit_count"]), int(right["hit_count"]), pair["candidate_a_id"], pair["candidate_b_id"]
        )
        cluster_winner = compare_signal(
            int(left["global_candidate_n3c_cluster_count"]),
            int(right["global_candidate_n3c_cluster_count"]),
            pair["candidate_a_id"],
            pair["candidate_b_id"],
        )
        exact_cluster_winner = compare_signal(
            int(left["global_candidate_n3c_exact_cluster_count"]),
            int(right["global_candidate_n3c_exact_cluster_count"]),
            pair["candidate_a_id"],
            pair["candidate_b_id"],
        )
        pair_rows.append({
            "pair_id": pair["pair_id"],
            "trial_id": pair["trial_id"],
            "candidate_a_id": pair["candidate_a_id"],
            "candidate_b_id": pair["candidate_b_id"],
            "baseline_winner_id": pair["baseline_winner_id"],
            "gold_winner_id": pair["gold_winner_id"],
            "baseline_correct": pair["baseline_winner_id"] == pair["gold_winner_id"],
            "n3c_hit_winner_id": hit_winner,
            "n3c_hit_pair_result": classify_pair(hit_winner, pair["baseline_winner_id"], pair["gold_winner_id"]),
            "n3c_global_cluster_winner_id": cluster_winner,
            "n3c_global_cluster_pair_result": classify_pair(
                cluster_winner, pair["baseline_winner_id"], pair["gold_winner_id"]
            ),
            "n3c_exact_global_cluster_winner_id": exact_cluster_winner,
            "n3c_exact_global_cluster_pair_result": classify_pair(
                exact_cluster_winner, pair["baseline_winner_id"], pair["gold_winner_id"]
            ),
            "candidate_a_hit_count": left["hit_count"],
            "candidate_b_hit_count": right["hit_count"],
            "candidate_a_global_clusters": left["global_candidate_n3c_cluster_count"],
            "candidate_b_global_clusters": right["global_candidate_n3c_cluster_count"],
            "candidate_a_exact_global_clusters": left["global_candidate_n3c_exact_cluster_count"],
            "candidate_b_exact_global_clusters": right["global_candidate_n3c_exact_cluster_count"],
        })

    write_csv(OUTPUT_DIR / "bucket_summary_rows.csv", bucket_summary_rows, tuple(bucket_summary_rows[0]))
    write_csv(OUTPUT_DIR / "chunk_timing_rows.csv", chunk_rows, tuple(chunk_rows[0]))
    write_csv(OUTPUT_DIR / "logical_group_summary_rows.csv", logical_rows, tuple(logical_rows[0]))
    write_csv(OUTPUT_DIR / "hit_file_manifest_rows.csv", hit_file_manifest_rows, tuple(hit_file_manifest_rows[0]))
    write_csv(OUTPUT_DIR / "candidate_n3c_summary_rows.csv", candidate_summary_rows, tuple(candidate_summary_rows[0]))
    write_csv(OUTPUT_DIR / "pairwise_gold_n3c_report_rows.csv", pair_rows, tuple(pair_rows[0]))

    pair_result_counts = {
        "hit_count": dict(Counter(row["n3c_hit_pair_result"] for row in pair_rows)),
        "global_cluster": dict(Counter(row["n3c_global_cluster_pair_result"] for row in pair_rows)),
        "exact_global_cluster": dict(Counter(row["n3c_exact_global_cluster_pair_result"] for row in pair_rows)),
    }
    manifest = {
        "status": "full80_consolidated_evidence_ready_for_review",
        "phase": PHASE,
        "bucket_count": len(bucket_summary_rows),
        "runtime_chunk_count": sum(int(row["runtime_chunk_count"]) for row in bucket_summary_rows),
        "logical_group_count": len({row["logical_group_id"] for row in logical_rows}),
        "runtime_phrase_rows": sum(int(row["runtime_phrase_rows"]) for row in bucket_summary_rows),
        "candidate_count": len(candidate_summary_rows),
        "verified_hit_count": sum(int(row["verified_hit_count"]) for row in bucket_summary_rows),
        "global_candidate_n3c_cluster_count": sum(
            int(row["global_candidate_n3c_cluster_count"]) for row in candidate_summary_rows
        ),
        "global_candidate_n3c_exact_cluster_count": sum(
            int(row["global_candidate_n3c_exact_cluster_count"]) for row in candidate_summary_rows
        ),
        "pair_count_with_both_candidates_in_sample": len(pair_rows),
        "pair_result_counts": pair_result_counts,
        "bucket_runtime_seconds_sum": sum(float(row["runtime_seconds"]) for row in bucket_summary_rows),
        "peak_memory_mb_max": max(float(row["peak_memory_mb"]) for row in bucket_summary_rows),
        "query_is_full_n3c_for_selected_80_candidates": True,
        "query_is_full_734_candidate_fixture": False,
        "hit_rows_are_external_bucket_files": True,
        "global_clusters_are_candidate_level_across_all_buckets": True,
        "bucket_clusters_are_diagnostic_only": True,
        "production_scoring_change": False,
        "production_ranking_change": False,
        "score_bearing_use_approved": False,
        "order2_query_authority": "priority_only_never_filter",
        "next_gate": "external_review_before_734_candidate_fixture_or_score_bearing_work",
    }
    (OUTPUT_DIR / "run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (OUTPUT_DIR / "readout.md").write_text(
        "# Full80 N3C Consolidated Evidence\n\n"
        f"- status: `{manifest['status']}`\n"
        f"- chunks: `{manifest['runtime_chunk_count']}`; logical groups: `{manifest['logical_group_count']}`\n"
        f"- phrase rows: `{manifest['runtime_phrase_rows']}`\n"
        f"- candidates: `{manifest['candidate_count']}`\n"
        f"- verified hits: `{manifest['verified_hit_count']}`\n"
        f"- global candidate clusters: `{manifest['global_candidate_n3c_cluster_count']}`\n"
        f"- exact global candidate clusters: `{manifest['global_candidate_n3c_exact_cluster_count']}`\n"
        f"- pair rows: `{manifest['pair_count_with_both_candidates_in_sample']}`\n"
        f"- pair result counts: `{json.dumps(pair_result_counts, sort_keys=True)}`\n"
        f"- bucket runtime seconds sum: `{manifest['bucket_runtime_seconds_sum']:.1f}`\n"
        f"- peak memory MB max: `{manifest['peak_memory_mb_max']:.1f}`\n\n"
        "This is full N3C over the selected 80-candidate sample only. It remains "
        "report-only diagnostic evidence and changes no production score or ranking.\n",
        encoding="utf-8",
    )
    print(f"[{PHASE}] status={manifest['status']}")
    print(
        f"[{PHASE}] hits={manifest['verified_hit_count']} "
        f"global_clusters={manifest['global_candidate_n3c_cluster_count']} "
        f"pairs={manifest['pair_count_with_both_candidates_in_sample']}"
    )
    return manifest


if __name__ == "__main__":
    build_consolidated_evidence()
