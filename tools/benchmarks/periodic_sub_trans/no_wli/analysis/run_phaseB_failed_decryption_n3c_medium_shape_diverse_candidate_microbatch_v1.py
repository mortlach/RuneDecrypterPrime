from __future__ import annotations

import csv
import json
import os
import sys
import time
from collections import defaultdict
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
    BUCKET_ORDER,
    FIXTURE_DIR,
    RUNTIME_MANIFEST,
    RUNTIME_VALIDATION,
)


PHASE = "phaseB_failed_decryption_n3c_medium_shape_diverse_candidate_microbatch_v1"
OUTPUT_DIR = REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis" / PHASE
MAX_CANDIDATE_COUNT = 80
MAX_RUNTIME_SECONDS_PER_GROUP = 180.0
MAX_TOTAL_RUNTIME_SECONDS = 600.0
MAX_PEAK_MEMORY_MB = 1024.0
QUERY_SCOPE = "five_medium_frequency_groups_diverse_80_candidate_microbatch"
READOUT_TITLE = "N3C Medium-Shape Diverse-Candidate Microbatch"


def select_diverse_candidates(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    by_trial: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_trial[row["trial_id"]].append(row)
    selected: list[dict[str, str]] = []
    for trial_id in sorted(by_trial):
        ordered = sorted(by_trial[trial_id], key=lambda row: (-float(row["baseline_score"]), row["candidate_id"]))
        selected.append({**ordered[0], "candidate_stratum": "trial_highest_baseline_score_rank_unavailable"})
        middle = ordered[len(ordered) // 2]
        if middle["candidate_id"] != ordered[0]["candidate_id"]:
            selected.append({**middle, "candidate_stratum": "trial_middle_baseline_score_rank_unavailable"})
    return selected[:MAX_CANDIDATE_COUNT]


def select_medium_groups(files: list[dict[str, object]]) -> list[dict[str, object]]:
    selected = []
    for bucket in BUCKET_ORDER:
        rows = sorted(
            (
                row for row in files
                if row["direction"] == "fwd"
                and int(row["ngram_order"]) == 3
                and row["dictionary_cut"] == "normal"
                and int(row["phrase_token_length"]) >= 8
                and length_bucket(int(row["phrase_token_length"])) == bucket
            ),
            key=lambda row: (int(row["phrase_count"]), str(row["path"])),
        )
        selected.append({
            **rows[len(rows) // 2], "shape_frequency_class": "medium",
            "shape_frequency_rank": len(rows) // 2 + 1, "bucket_group_count": len(rows),
        })
    return selected


def _write_csv(path: Path, rows: list[dict[str, object]], fields: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def run_microbatch() -> dict[str, object]:
    runtime = json.loads(RUNTIME_MANIFEST.read_text(encoding="utf-8"))
    validation = json.loads(RUNTIME_VALIDATION.read_text(encoding="utf-8"))
    if validation["status"] != "pass":
        raise RuntimeError("validated N3C runtime asset is required")
    candidates = select_diverse_candidates(list(csv.DictReader(
        (FIXTURE_DIR / "retained_candidate_rows.csv").open(encoding="utf-8", newline="")
    )))
    groups = select_medium_groups(runtime["files"])
    process = psutil.Process(os.getpid())
    peak_rss = int(getattr(process.memory_info(), "peak_wset", process.memory_info().rss))
    timing_rows: list[dict[str, object]] = []
    hit_rows: list[dict[str, object]] = []
    started_all = time.monotonic()
    for group_index, group in enumerate(groups, start=1):
        group_started = time.monotonic()
        with np.load(REPO_ROOT / str(group["path"]), allow_pickle=False) as data:
            phrase_rows = data["rune_tokens"]
            phrase_ids = data["phrase_id"]
        index = build_sorted_block_index(phrase_rows)
        word_lengths = tuple(int(value) for value in json.loads(str(group["word_token_lengths"])))
        group_hit_count = 0
        group_cluster_count = 0
        proposed_count = 0
        for candidate_index, candidate in enumerate(candidates, start=1):
            tokens = json.loads(candidate["candidate_token_ids_json"])
            hits, proposed = sorted_block_partition_hits(tokens, phrase_rows, word_lengths, index)
            proposed_count += proposed
            group_hit_count += len(hits)
            group_cluster_count += len(cluster_hit_spans(
                (start, start + int(group["phrase_token_length"])) for start, _phrase_index in hits
            ))
            for start, phrase_index in sorted(hits):
                hit_rows.append({
                    "trial_id": candidate["trial_id"], "candidate_id": candidate["candidate_id"],
                    "candidate_stratum": candidate["candidate_stratum"], "group_id": group["path"],
                    "length_bucket": length_bucket(int(group["phrase_token_length"])),
                    "phrase_id": str(phrase_ids[phrase_index]), "hit_start": start,
                    "hit_end": start + int(group["phrase_token_length"]), "full_phrase_verified": True,
                })
            memory = process.memory_info()
            peak_rss = max(peak_rss, int(getattr(memory, "peak_wset", memory.rss)))
            if candidate_index == 1 or candidate_index % 10 == 0 or candidate_index == len(candidates):
                elapsed = time.monotonic() - group_started
                eta = elapsed / candidate_index * (len(candidates) - candidate_index)
                print(
                    f"[{PHASE}] groups={group_index}/{len(groups)} candidates={candidate_index}/{len(candidates)} "
                    f"elapsed_seconds={elapsed:.1f} eta_seconds={eta:.1f} peak_rss_mb={peak_rss / 1_000_000:.1f}"
                )
        group_seconds = time.monotonic() - group_started
        timing_rows.append({
            "group_id": group["path"], "length_bucket": length_bucket(int(group["phrase_token_length"])),
            "word_token_lengths": group["word_token_lengths"], "runtime_phrase_count": group["phrase_count"],
            "candidate_count": len(candidates), "lookup_match_count": proposed_count,
            "verified_hit_count": group_hit_count, "verified_cluster_count": group_cluster_count,
            "runtime_seconds": group_seconds, "peak_memory_mb": peak_rss / 1_000_000,
            "status": "complete" if group_seconds <= MAX_RUNTIME_SECONDS_PER_GROUP else "complete_over_budget",
        })
    total_seconds = time.monotonic() - started_all
    peak_memory_mb = peak_rss / 1_000_000
    group_budget_pass = all(float(row["runtime_seconds"]) <= MAX_RUNTIME_SECONDS_PER_GROUP for row in timing_rows)
    status = (
        "pass"
        if group_budget_pass and total_seconds <= MAX_TOTAL_RUNTIME_SECONDS and peak_memory_mb <= MAX_PEAK_MEMORY_MB
        else "blocked_budget_exceeded"
    )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _write_csv(OUTPUT_DIR / "timing_rows.csv", timing_rows, tuple(timing_rows[0]))
    _write_csv(OUTPUT_DIR / "candidate_rows.csv", [
        {
            "trial_id": row["trial_id"], "candidate_id": row["candidate_id"],
            "baseline_score": row["baseline_score"], "candidate_rank": row["candidate_rank"],
            "candidate_stratum": row["candidate_stratum"],
        }
        for row in candidates
    ], ("trial_id", "candidate_id", "baseline_score", "candidate_rank", "candidate_stratum"))
    hit_fields = (
        "trial_id", "candidate_id", "candidate_stratum", "group_id", "length_bucket",
        "phrase_id", "hit_start", "hit_end", "full_phrase_verified",
    )
    _write_csv(OUTPUT_DIR / "n3c_verified_hit_rows.csv", hit_rows, hit_fields)
    manifest = {
        "status": status, "phase": PHASE, "query_is_full_n3c": False,
        "query_scope": QUERY_SCOPE,
        "n3c_runtime_asset_id": runtime["asset_id"], "n3c_runtime_validation_status": validation["status"],
        "searched_group_count": len(groups), "candidate_count": len(candidates),
        "candidate_strata": sorted({row["candidate_stratum"] for row in candidates}),
        "candidate_rank_availability": "unavailable_not_invented",
        "verified_hit_count": len(hit_rows),
        "verified_cluster_count": sum(int(row["verified_cluster_count"]) for row in timing_rows),
        "total_runtime_seconds": total_seconds, "peak_memory_mb": peak_memory_mb,
        "max_runtime_seconds_per_group": MAX_RUNTIME_SECONDS_PER_GROUP,
        "max_total_runtime_seconds": MAX_TOTAL_RUNTIME_SECONDS, "max_peak_memory_mb": MAX_PEAK_MEMORY_MB,
        "group_budget_pass": group_budget_pass,
        "all_started_groups_completed": True, "projection_or_anchor_used_for_filter_only": True,
        "full_phrase_verified": True, "production_scoring_change": False, "production_ranking_change": False,
        "order2_used_for_query_planning_only": False, "order2_score_authority": "diagnostic_only",
        "old_phrase_index_v1_used": False, "sample_asset_used": False,
        "full_raw_shards_used_directly_as_runtime": False, "absence_of_hits_meaningful": False,
    }
    (OUTPUT_DIR / "run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (OUTPUT_DIR / "readout.md").write_text(
        f"# {READOUT_TITLE}\n\n"
        f"- status: `{status}`\n"
        f"- groups: `{len(groups)}`; candidates: `{len(candidates)}`\n"
        f"- verified hits: `{len(hit_rows)}`; verified clusters: `{manifest['verified_cluster_count']}`\n"
        f"- total seconds: `{total_seconds:.3f}`; peak memory MB: `{peak_memory_mb:.1f}`\n"
        "- query is full N3C: `false`\n"
        "- production rank effect: `none`\n",
        encoding="utf-8",
    )
    return manifest


if __name__ == "__main__":
    run_microbatch()
