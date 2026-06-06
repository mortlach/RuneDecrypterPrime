from __future__ import annotations

import csv
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import psutil


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
for path in (REPO_ROOT, REPO_ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.phaseB_n3c_query_planning_core_v1 import (
    build_sorted_block_index,
    cluster_hit_spans,
    length_bucket,
    sorted_block_partition_hits,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.run_phaseB_failed_decryption_length_aware_order2_informed_n3c_query_planning_v1 import (
    FIXTURE_DIR,
    RUNTIME_MANIFEST,
    RUNTIME_VALIDATION,
    select_candidates,
)


PHASE = "phaseB_failed_decryption_n3c_memory_bounded_medium_group_canary_v1"
OUTPUT_DIR = REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis" / PHASE
TARGET_BUCKET = "8-9"
TARGET_FREQUENCY_CLASS = "medium"
MAX_CANDIDATE_COUNT = 40
MAX_RUNTIME_SECONDS = 600.0
MAX_PEAK_MEMORY_MB = 2048.0


def select_medium_group(files: list[dict[str, object]]) -> dict[str, object]:
    eligible = sorted(
        (
            row for row in files
            if row["direction"] == "fwd"
            and int(row["ngram_order"]) == 3
            and row["dictionary_cut"] == "normal"
            and int(row["phrase_token_length"]) >= 8
            and length_bucket(int(row["phrase_token_length"])) == TARGET_BUCKET
        ),
        key=lambda row: (int(row["phrase_count"]), str(row["path"])),
    )
    selected = eligible[len(eligible) // 2]
    return {
        **selected,
        "shape_frequency_rank": len(eligible) // 2 + 1,
        "shape_frequency_class": TARGET_FREQUENCY_CLASS,
        "bucket_group_count": len(eligible),
    }


def run_canary() -> dict[str, object]:
    runtime = json.loads(RUNTIME_MANIFEST.read_text(encoding="utf-8"))
    validation = json.loads(RUNTIME_VALIDATION.read_text(encoding="utf-8"))
    if validation["status"] != "pass":
        raise RuntimeError("validated N3C runtime asset is required")
    candidates = select_candidates(list(csv.DictReader(
        (FIXTURE_DIR / "retained_candidate_rows.csv").open(encoding="utf-8", newline="")
    )))[:MAX_CANDIDATE_COUNT]
    group = select_medium_group(runtime["files"])
    group_path = REPO_ROOT / str(group["path"])
    process = psutil.Process(os.getpid())
    rss_start = process.memory_info().rss
    started = time.monotonic()
    with np.load(group_path, allow_pickle=False) as data:
        phrase_rows = data["rune_tokens"]
        phrase_ids = data["phrase_id"]
    rss_after_load = process.memory_info().rss
    index_started = time.monotonic()
    index = build_sorted_block_index(phrase_rows)
    index_seconds = time.monotonic() - index_started
    rss_after_index = process.memory_info().rss
    peak_rss = max(rss_start, rss_after_load, rss_after_index)
    os_peak_rss = int(getattr(process.memory_info(), "peak_wset", peak_rss))
    word_lengths = tuple(int(value) for value in json.loads(str(group["word_token_lengths"])))
    hit_rows: list[dict[str, object]] = []
    proposed_count = 0
    candidate_window_count = 0
    cluster_count = 0
    for candidate_index, candidate in enumerate(candidates, start=1):
        tokens = json.loads(candidate["candidate_token_ids_json"])
        candidate_window_count += len(tokens) - int(group["phrase_token_length"]) + 1
        hits, proposed = sorted_block_partition_hits(tokens, phrase_rows, word_lengths, index)
        proposed_count += proposed
        cluster_count += len(cluster_hit_spans(
            (start, start + int(group["phrase_token_length"])) for start, _phrase_index in hits
        ))
        for start, phrase_index in sorted(hits):
            hit_rows.append({
                "trial_id": candidate["trial_id"], "candidate_id": candidate["candidate_id"],
                "phrase_id": str(phrase_ids[phrase_index]), "hit_start": start,
                "hit_end": start + int(group["phrase_token_length"]), "full_phrase_verified": True,
            })
        memory_info = process.memory_info()
        peak_rss = max(peak_rss, memory_info.rss)
        os_peak_rss = max(os_peak_rss, int(getattr(memory_info, "peak_wset", peak_rss)))
        elapsed = time.monotonic() - started
        eta = elapsed / candidate_index * (len(candidates) - candidate_index)
        if candidate_index == 1 or candidate_index % 10 == 0 or candidate_index == len(candidates):
            print(
                f"[{PHASE}] candidates={candidate_index}/{len(candidates)} elapsed_seconds={elapsed:.1f} "
                f"eta_seconds={eta:.1f} peak_rss_mb={peak_rss / 1_000_000:.1f}"
            )
    elapsed = time.monotonic() - started
    peak_memory_mb = max(peak_rss, os_peak_rss) / 1_000_000
    status = "pass" if elapsed <= MAX_RUNTIME_SECONDS and peak_memory_mb <= MAX_PEAK_MEMORY_MB else "blocked_budget_exceeded"
    manifest = {
        "status": status, "phase": PHASE, "query_is_full_n3c": False,
        "query_scope": "one_medium_frequency_8_9_group_memory_canary",
        "n3c_runtime_asset_id": runtime["asset_id"], "n3c_runtime_validation_status": validation["status"],
        "group_id": group["path"], "length_bucket": TARGET_BUCKET,
        "shape_frequency_class": TARGET_FREQUENCY_CLASS, "shape_frequency_rank": group["shape_frequency_rank"],
        "bucket_group_count": group["bucket_group_count"], "phrase_token_length": group["phrase_token_length"],
        "word_token_lengths": group["word_token_lengths"], "runtime_phrase_count": group["phrase_count"],
        "candidate_count": len(candidates), "candidate_window_count": candidate_window_count,
        "lookup_match_count": proposed_count, "verified_hit_count": len(hit_rows),
        "verified_cluster_count": cluster_count, "index_build_seconds": index_seconds,
        "total_runtime_seconds": elapsed, "rss_start_mb": rss_start / 1_000_000,
        "rss_after_load_mb": rss_after_load / 1_000_000, "rss_after_index_mb": rss_after_index / 1_000_000,
        "peak_rss_mb": peak_memory_mb, "retained_index_bytes": index.allocated_bytes,
        "os_peak_working_set_mb": os_peak_rss / 1_000_000,
        "max_runtime_seconds": MAX_RUNTIME_SECONDS, "max_peak_memory_mb": MAX_PEAK_MEMORY_MB,
        "projection_or_anchor_used_for_filter_only": True, "full_phrase_verified": True,
        "all_started_groups_completed": True, "production_scoring_change": False,
        "production_ranking_change": False, "order2_score_authority": "diagnostic_only",
        "old_phrase_index_v1_used": False, "sample_asset_used": False,
        "full_raw_shards_used_directly_as_runtime": False, "absence_of_hits_meaningful": False,
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    fields = ("trial_id", "candidate_id", "phrase_id", "hit_start", "hit_end", "full_phrase_verified")
    with (OUTPUT_DIR / "n3c_verified_hit_rows.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(hit_rows)
    (OUTPUT_DIR / "readout.md").write_text(
        "# N3C Memory-Bounded Medium-Group Canary\n\n"
        f"- status: `{status}`\n"
        f"- group: `{group['path']}`\n"
        f"- runtime phrase rows: `{group['phrase_count']}`\n"
        f"- candidates: `{len(candidates)}`\n"
        f"- verified hits: `{len(hit_rows)}`; verified clusters: `{cluster_count}`\n"
        f"- index build seconds: `{index_seconds:.3f}`; total seconds: `{elapsed:.3f}`\n"
        f"- peak RSS MB: `{peak_memory_mb:.1f}`; retained index bytes: `{index.allocated_bytes}`\n"
        "- query is full N3C: `false`\n"
        "- production rank effect: `none`\n",
        encoding="utf-8",
    )
    return manifest


if __name__ == "__main__":
    run_canary()
