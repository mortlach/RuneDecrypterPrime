from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
for path in (REPO_ROOT, REPO_ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    run_phaseB_failed_decryption_n3c_vectorized_8_9_stratified_shape_microbatch_v1 as bucket_8_9,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    run_phaseB_failed_decryption_n3c_vectorized_10_11_stratified_shape_microbatch_v1 as bucket_10_11,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    run_phaseB_failed_decryption_n3c_vectorized_12_plus_stratified_shape_microbatch_v1 as bucket_12_plus,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.run_phaseB_failed_decryption_length_aware_order2_informed_n3c_query_planning_v1 import (
    RUNTIME_MANIFEST,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.phaseB_n3c_query_planning_core_v1 import length_bucket


PHASE = "phaseB_failed_decryption_n3c_stratified_query_study_summary_v1"
OUTPUT_DIR = REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis" / PHASE
RUNS = (
    (
        "8-9",
        REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis"
        / "phaseB_failed_decryption_n3c_vectorized_8_9_stratified_shape_microbatch_v1",
        bucket_8_9.select_stratified_8_9_groups,
    ),
    (
        "10-11",
        REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis"
        / "phaseB_failed_decryption_n3c_vectorized_10_11_stratified_shape_microbatch_v1",
        bucket_10_11.select_stratified_10_11_groups,
    ),
    (
        "12+",
        REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis"
        / "phaseB_failed_decryption_n3c_vectorized_12_plus_stratified_shape_microbatch_v1",
        bucket_12_plus.select_stratified_12_plus_groups,
    ),
)
EXPECTED_GROUP_COUNTS = {"8-9": 8, "10-11": 8, "12-14": 8, "15-17": 8, "18+": 8}
EXPECTED_FREQUENCY_COUNTS = {"rare": 2, "medium": 3, "common": 3}


def _write_csv(path: Path, rows: list[dict[str, object]], fields: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def build_summary() -> dict[str, object]:
    runtime = json.loads(RUNTIME_MANIFEST.read_text(encoding="utf-8"))
    selected_rows: list[dict[str, object]] = []
    timing_by_group: dict[str, dict[str, str]] = {}
    run_manifests: list[dict[str, object]] = []

    for run_label, run_dir, selector in RUNS:
        manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
        if manifest["status"] != "pass":
            raise RuntimeError(f"{run_label} stratified run is not pass: {manifest['status']}")
        run_manifests.append(manifest)
        timing_rows = list(csv.DictReader((run_dir / "timing_rows.csv").open(encoding="utf-8", newline="")))
        for row in timing_rows:
            if row["group_id"] in timing_by_group:
                raise RuntimeError(f"duplicate searched group: {row['group_id']}")
            timing_by_group[row["group_id"]] = row

        expected = selector(runtime["files"])
        expected_ids = {str(row["path"]) for row in expected}
        actual_ids = {row["group_id"] for row in timing_rows}
        if actual_ids != expected_ids:
            raise RuntimeError(f"{run_label} recorded groups do not match deterministic selector")
        selected_rows.extend(expected)

    group_counts = Counter(str(row["length_bucket"]) for row in timing_by_group.values())
    if dict(group_counts) != EXPECTED_GROUP_COUNTS:
        raise RuntimeError(f"unexpected bucket group counts: {dict(group_counts)}")

    frequency_counts_by_bucket: dict[str, Counter[str]] = {}
    for row in selected_rows:
        bucket = length_bucket(int(row["phrase_token_length"]))
        frequency_counts_by_bucket.setdefault(bucket, Counter())[str(row["shape_frequency_class"])] += 1
    for bucket, counts in frequency_counts_by_bucket.items():
        if dict(counts) != EXPECTED_FREQUENCY_COUNTS:
            raise RuntimeError(f"unexpected frequency counts for {bucket}: {dict(counts)}")

    selected_group_rows = []
    for selected in sorted(
        selected_rows,
        key=lambda row: (length_bucket(int(row["phrase_token_length"])), int(row["shape_frequency_rank"])),
    ):
        timing = timing_by_group[str(selected["path"])]
        selected_group_rows.append({
            "length_bucket": timing["length_bucket"],
            "shape_frequency_class": selected["shape_frequency_class"],
            "shape_frequency_rank": selected["shape_frequency_rank"],
            "bucket_group_count": selected["bucket_group_count"],
            "group_id": timing["group_id"],
            "word_token_lengths": timing["word_token_lengths"],
            "runtime_phrase_count": timing["runtime_phrase_count"],
            "candidate_count": timing["candidate_count"],
            "verified_hit_count": timing["verified_hit_count"],
            "verified_cluster_count": timing["verified_cluster_count"],
            "runtime_seconds": timing["runtime_seconds"],
            "peak_memory_mb": timing["peak_memory_mb"],
            "status": timing["status"],
        })

    bucket_rows = []
    for bucket in EXPECTED_GROUP_COUNTS:
        rows = [row for row in selected_group_rows if row["length_bucket"] == bucket]
        bucket_rows.append({
            "length_bucket": bucket,
            "searched_group_count": len(rows),
            "rare_group_count": sum(row["shape_frequency_class"] == "rare" for row in rows),
            "medium_group_count": sum(row["shape_frequency_class"] == "medium" for row in rows),
            "common_group_count": sum(row["shape_frequency_class"] == "common" for row in rows),
            "candidate_count": max(int(row["candidate_count"]) for row in rows),
            "verified_hit_count": sum(int(row["verified_hit_count"]) for row in rows),
            "verified_cluster_count": sum(int(row["verified_cluster_count"]) for row in rows),
            "runtime_seconds": sum(float(row["runtime_seconds"]) for row in rows),
            "peak_memory_mb": max(float(row["peak_memory_mb"]) for row in rows),
        })

    manifest = {
        "status": "review_gate_ready",
        "phase": PHASE,
        "searched_group_count": len(selected_group_rows),
        "length_bucket_count": len(bucket_rows),
        "candidate_count": max(int(row["candidate_count"]) for row in selected_group_rows),
        "frequency_groups_per_bucket": EXPECTED_FREQUENCY_COUNTS,
        "verified_hit_count": sum(int(row["verified_hit_count"]) for row in selected_group_rows),
        "verified_cluster_count": sum(int(row["verified_cluster_count"]) for row in selected_group_rows),
        "total_runtime_seconds": sum(float(row["runtime_seconds"]) for row in selected_group_rows),
        "peak_memory_mb": max(float(row["peak_memory_mb"]) for row in selected_group_rows),
        "source_run_statuses": [manifest["status"] for manifest in run_manifests],
        "query_is_full_n3c": False,
        "absence_of_hits_meaningful": False,
        "full_phrase_verified": True,
        "candidate_rank_availability": "unavailable_not_invented",
        "order2_query_authority": "priority_only_never_filter",
        "production_scoring_change": False,
        "production_ranking_change": False,
        "next_gate": "external_review_before_wider_or_score_bearing_work",
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _write_csv(OUTPUT_DIR / "selected_group_rows.csv", selected_group_rows, tuple(selected_group_rows[0]))
    _write_csv(OUTPUT_DIR / "bucket_summary_rows.csv", bucket_rows, tuple(bucket_rows[0]))
    (OUTPUT_DIR / "run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# N3C Stratified Query Study Summary",
        "",
        f"- status: `{manifest['status']}`",
        f"- searched complete groups: `{manifest['searched_group_count']}`",
        f"- candidates per group: `{manifest['candidate_count']}`",
        f"- verified hits: `{manifest['verified_hit_count']}`",
        f"- verified clusters: `{manifest['verified_cluster_count']}`",
        f"- summed group runtime seconds: `{manifest['total_runtime_seconds']:.3f}`",
        f"- peak memory MB: `{manifest['peak_memory_mb']:.1f}`",
        "",
        "| length bucket | groups | rare | medium | common | hits | clusters |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in bucket_rows:
        lines.append(
            f"| {row['length_bucket']} | {row['searched_group_count']} | {row['rare_group_count']} | "
            f"{row['medium_group_count']} | {row['common_group_count']} | "
            f"{row['verified_hit_count']} | {row['verified_cluster_count']} |"
        )
    lines.extend([
        "",
        "Every returned hit was verified against the full phrase and N3C word-shape rule.",
        "This is a stratified partial query study, not full N3C. Zero hits do not prove absence.",
        "Order 2 may prioritize work but may not filter candidate regions.",
        "Production scores and ranking remain unchanged.",
    ])
    (OUTPUT_DIR / "readout.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[{PHASE}] status={manifest['status']}")
    print(
        f"[{PHASE}] groups={manifest['searched_group_count']} hits={manifest['verified_hit_count']} "
        f"clusters={manifest['verified_cluster_count']} peak_memory_mb={manifest['peak_memory_mb']:.1f}"
    )
    return manifest


if __name__ == "__main__":
    build_summary()
