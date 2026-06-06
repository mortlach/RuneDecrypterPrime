from __future__ import annotations

import csv
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
for path in (REPO_ROOT, REPO_ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.phaseB_n3c_query_planning_core_v1 import (
    cluster_hit_spans,
    length_bucket,
    partition_filter_hits,
)


PHASE = "phaseB_failed_decryption_length_aware_order2_informed_n3c_query_planning_v1"
ANALYSIS_ROOT = REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis"
OUTPUT_DIR = ANALYSIS_ROOT / PHASE
FIXTURE_DIR = REPO_ROOT / "assets/evaluation_corpora/failed_decryptions/historical_partial_solves_v1/fixture/phaseB_failed_decryption_retained_candidate_fixture_v1"
RUNTIME_MANIFEST = ANALYSIS_ROOT / "phaseB_ngram_hamming_fast_runtime_lookup_index_v1/runtime_index_manifest.json"
RUNTIME_VALIDATION = ANALYSIS_ROOT / "phaseB_ngram_hamming_fast_runtime_lookup_index_validation_v1/validation_manifest.json"

MAX_CANDIDATE_COUNT = 40
MAX_RUNTIME_GROUPS = 5
MAX_RUNTIME_SECONDS_PER_GROUP = 120.0
MAX_PEAK_MEMORY_MB = 2048
QUERY_MODE = "length_shape_unseeded"
FILTER_STRATEGY = "three_exact_blocks_filter_then_full_word_structured_verification"
BUCKET_ORDER = ("8-9", "10-11", "12-14", "15-17", "18+")


def _write_csv(path: Path, rows: list[dict[str, object]], fields: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def select_candidates(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    by_trial: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_trial[row["trial_id"]].append(row)
    selected = []
    for trial_id in sorted(by_trial):
        ordered = sorted(by_trial[trial_id], key=lambda row: (-float(row["baseline_score"]), row["candidate_id"]))
        selected.append({**ordered[0], "candidate_stratum": "trial_highest_baseline_score_rank_unavailable"})
    return selected[:MAX_CANDIDATE_COUNT]


def select_groups(
    files: list[dict[str, object]],
    *,
    order: int = 3,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    eligible = [
        row for row in files
        if row["direction"] == "fwd"
        and int(row["ngram_order"]) == order
        and row["dictionary_cut"] == "normal"
        and int(row["phrase_token_length"]) >= 8
    ]
    selected: list[dict[str, object]] = []
    for bucket in BUCKET_ORDER:
        bucket_rows = sorted(
            (row for row in eligible if length_bucket(int(row["phrase_token_length"])) == bucket),
            key=lambda row: (int(row["phrase_count"]), str(row["path"])),
        )
        selected.append({**bucket_rows[0], "shape_frequency_rank": 1, "shape_frequency_class": "rare"})
    selected_paths = {str(row["path"]) for row in selected}
    skipped = [
        {
            "group_id": str(row["path"]),
            "length_bucket": length_bucket(int(row["phrase_token_length"])),
            "word_token_lengths": row["word_token_lengths"],
            "phrase_count": row["phrase_count"],
            "skip_reason": "not_selected_first_timed_rare_shape_per_length_bucket_canary",
            "would_be_required_for_full_n3c": True,
            "searched": False,
        }
        for row in eligible if str(row["path"]) not in selected_paths
    ]
    return selected[:MAX_RUNTIME_GROUPS], skipped


def run_study() -> dict[str, object]:
    runtime = json.loads(RUNTIME_MANIFEST.read_text(encoding="utf-8"))
    validation = json.loads(RUNTIME_VALIDATION.read_text(encoding="utf-8"))
    if validation["status"] != "pass":
        raise RuntimeError("validated full N3C runtime asset is required")
    candidate_rows = list(
        csv.DictReader((FIXTURE_DIR / "retained_candidate_rows.csv").open(encoding="utf-8", newline=""))
    )
    candidates = select_candidates(candidate_rows)
    groups, skipped_rows = select_groups(runtime["files"])
    query_plan_candidate_rows = [
        {
            "trial_id": row["trial_id"], "candidate_id": row["candidate_id"],
            "candidate_rank": row["candidate_rank"], "baseline_score": row["baseline_score"],
            "candidate_token_count": row["candidate_token_count"], "candidate_stratum": row["candidate_stratum"],
            "selected": True, "selection_reason": "one highest-baseline-score candidate per trial; ranks unavailable",
        }
        for row in candidates
    ]
    query_plan_group_rows: list[dict[str, object]] = []
    hit_rows: list[dict[str, object]] = []
    timing_rows: list[dict[str, object]] = []
    group_results: list[dict[str, object]] = []
    started_all = time.monotonic()
    for group_index, group in enumerate(groups, start=1):
        group_started = time.monotonic()
        group_path = REPO_ROOT / str(group["path"])
        word_lengths = tuple(int(value) for value in json.loads(str(group["word_token_lengths"])))
        with np.load(group_path, allow_pickle=False) as data:
            phrase_rows = data["rune_tokens"]
            phrase_ids = data["phrase_id"]
        query_plan_group_rows.append({
            "group_id": group["path"], "query_mode": QUERY_MODE,
            "filter_strategy": FILTER_STRATEGY, "length_bucket": length_bucket(int(group["phrase_token_length"])),
            "phrase_token_length": group["phrase_token_length"], "word_token_lengths": group["word_token_lengths"],
            "runtime_phrase_count": group["phrase_count"], "shape_frequency_rank": group["shape_frequency_rank"],
            "shape_frequency_class": group["shape_frequency_class"],
            "selected_reason": "smallest complete group in length bucket",
            "searched": True, "full_phrase_verified": True,
        })
        proposed_count = 0
        candidate_window_count = 0
        group_hit_count = 0
        group_candidates_with_hits: set[str] = set()
        group_cluster_count = 0
        for candidate_index, candidate in enumerate(candidates, start=1):
            tokens = json.loads(candidate["candidate_token_ids_json"])
            candidate_window_count += max(0, len(tokens) - int(group["phrase_token_length"]) + 1)
            hits, proposed = partition_filter_hits(tokens, phrase_rows, word_lengths)
            proposed_count += proposed
            spans = [(start, start + int(group["phrase_token_length"])) for start, _phrase_index in hits]
            clusters = cluster_hit_spans(spans)
            group_cluster_count += len(clusters)
            if hits:
                group_candidates_with_hits.add(candidate["candidate_id"])
            for start, phrase_index in sorted(hits):
                phrase = phrase_rows[phrase_index].tolist()
                window = tokens[start:start + len(phrase)]
                offset = 0
                word_hds = []
                for word_length in word_lengths:
                    end = offset + word_length
                    word_hds.append(sum(left != right for left, right in zip(window[offset:end], phrase[offset:end])))
                    offset = end
                hit_rows.append({
                    "trial_id": candidate["trial_id"], "candidate_id": candidate["candidate_id"],
                    "group_id": group["path"], "query_mode": QUERY_MODE,
                    "length_bucket": length_bucket(int(group["phrase_token_length"])),
                    "phrase_token_length": group["phrase_token_length"],
                    "word_token_lengths": group["word_token_lengths"], "phrase_id": str(phrase_ids[phrase_index]),
                    "hit_start": start, "hit_end": start + len(phrase), "word_hds": json.dumps(word_hds),
                    "total_phrase_hd": sum(word_hds), "exact_verification": True, "full_phrase_verified": True,
                })
            group_hit_count += len(hits)
            if candidate_index == 1 or candidate_index % 10 == 0 or candidate_index == len(candidates):
                elapsed = time.monotonic() - group_started
                print(
                    f"[{PHASE}] groups={group_index}/{len(groups)} candidates={candidate_index}/{len(candidates)} "
                    f"elapsed_seconds={elapsed:.1f}"
                )
        elapsed = time.monotonic() - group_started
        group_results.append({
            "query_mode": QUERY_MODE, "length_bucket": length_bucket(int(group["phrase_token_length"])),
            "word_token_lengths": group["word_token_lengths"], "phrase_token_length": group["phrase_token_length"],
            "runtime_group_count": 1, "runtime_phrase_count": group["phrase_count"],
            "candidate_count": len(candidates), "candidate_window_count": candidate_window_count,
            "generated_key_count": proposed_count, "unique_generated_key_count": "",
            "lookup_match_count": proposed_count, "verified_hit_count": group_hit_count,
            "verified_cluster_count": group_cluster_count, "candidate_with_hit_count": len(group_candidates_with_hits),
            "candidate_with_cluster_count": len(group_candidates_with_hits), "runtime_seconds": elapsed,
            "peak_memory_mb": "", "shape_frequency_class": "rare",
            "status": "complete" if elapsed <= MAX_RUNTIME_SECONDS_PER_GROUP else "complete_over_budget",
            "notes": "projection/filter only; every emitted hit fully verified",
        })
        timing_rows.append({
            "group_id": group["path"], "query_mode": QUERY_MODE, "runtime_seconds": elapsed,
            "runtime_phrase_count": group["phrase_count"], "candidate_count": len(candidates),
            "candidate_window_count": candidate_window_count, "status": group_results[-1]["status"],
        })
    total_runtime = time.monotonic() - started_all
    by_bucket: list[dict[str, object]] = []
    for bucket in BUCKET_ORDER:
        bucket_groups = [row for row in group_results if row["length_bucket"] == bucket]
        if not bucket_groups:
            continue
        windows = sum(int(row["candidate_window_count"]) for row in bucket_groups)
        hits = sum(int(row["verified_hit_count"]) for row in bucket_groups)
        clusters = sum(int(row["verified_cluster_count"]) for row in bucket_groups)
        by_bucket.append({
            "query_mode": QUERY_MODE, "length_bucket": bucket, "candidate_count": len(candidates),
            "runtime_group_count": len(bucket_groups), "candidate_window_count": windows,
            "generated_key_count": sum(int(row["generated_key_count"]) for row in bucket_groups),
            "unique_generated_key_count": "", "lookup_match_count": sum(int(row["lookup_match_count"]) for row in bucket_groups),
            "verified_hit_count": hits, "verified_cluster_count": clusters,
            "candidate_with_hit_count": sum(int(row["candidate_with_hit_count"]) for row in bucket_groups),
            "candidate_with_cluster_count": sum(int(row["candidate_with_cluster_count"]) for row in bucket_groups),
            "runtime_seconds": sum(float(row["runtime_seconds"]) for row in bucket_groups), "peak_memory_mb": "",
            "hits_per_million_windows": hits / windows * 1_000_000 if windows else 0,
            "clusters_per_million_windows": clusters / windows * 1_000_000 if windows else 0,
            "status": "complete", "notes": "one rare complete group; absence is not bucket-wide evidence",
        })
    cluster_rows = []
    hits_by_candidate: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in hit_rows:
        hits_by_candidate[(str(row["candidate_id"]), str(row["group_id"]))].append(row)
    for (candidate_id, group_id), rows in sorted(hits_by_candidate.items()):
        spans = cluster_hit_spans((int(row["hit_start"]), int(row["hit_end"])) for row in rows)
        for cluster_index, (start, end) in enumerate(spans):
            cluster_rows.append({
                "candidate_id": candidate_id, "group_id": group_id, "cluster_index": cluster_index,
                "cluster_start": start, "cluster_end": end,
                "verified_hit_count": sum(start <= int(row["hit_start"]) and int(row["hit_end"]) <= end for row in rows),
            })
    order2_groups, _order2_skipped = select_groups(runtime["files"], order=2)
    order2_seed_rows: list[dict[str, object]] = []
    seed_ranges_by_candidate: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for group in order2_groups:
        group_path = REPO_ROOT / str(group["path"])
        word_lengths = tuple(int(value) for value in json.loads(str(group["word_token_lengths"])))
        with np.load(group_path, allow_pickle=False) as data:
            phrase_rows = data["rune_tokens"]
        for candidate in candidates:
            tokens = json.loads(candidate["candidate_token_ids_json"])
            hits, _proposed = partition_filter_hits(
                tokens, phrase_rows, word_lengths, max_total_hd=2, max_word_hd=2,
            )
            clusters = cluster_hit_spans(
                (start, start + int(group["phrase_token_length"])) for start, _phrase_index in hits
            )
            for cluster_index, (start, end) in enumerate(clusters):
                expanded_start = max(0, start - 20)
                expanded_end = min(len(tokens), end + 20)
                seed_ranges_by_candidate[candidate["candidate_id"]].append((expanded_start, expanded_end))
                order2_seed_rows.append({
                    "candidate_id": candidate["candidate_id"], "seed_profile_id": "B2R_bounded_seed_canary",
                    "seed_cluster_start": start, "seed_cluster_end": end,
                    "seed_hit_count": sum(start <= hit_start < end for hit_start, _phrase_index in hits),
                    "seed_cluster_count": len(clusters), "expanded_search_start": expanded_start,
                    "expanded_search_end": expanded_end, "expansion_margin_tokens": 20,
                    "status": "source_backed_diagnostic_seed", "order2_score_authority": "diagnostic_only",
                })
    comparison_rows: list[dict[str, object]] = []
    unseeded_by_candidate_group: dict[tuple[str, str], set[tuple[int, str]]] = defaultdict(set)
    for row in hit_rows:
        unseeded_by_candidate_group[(str(row["candidate_id"]), str(row["group_id"]))].add(
            (int(row["hit_start"]), str(row["phrase_id"]))
        )
    for group in groups:
        group_path = REPO_ROOT / str(group["path"])
        word_lengths = tuple(int(value) for value in json.loads(str(group["word_token_lengths"])))
        with np.load(group_path, allow_pickle=False) as data:
            phrase_rows = data["rune_tokens"]
            phrase_ids = data["phrase_id"]
        for candidate in candidates:
            unseeded = unseeded_by_candidate_group[(candidate["candidate_id"], str(group["path"]))]
            ranges = cluster_hit_spans(seed_ranges_by_candidate.get(candidate["candidate_id"], ()))
            seeded_started = time.monotonic()
            seeded_hits, _proposed = partition_filter_hits(
                json.loads(candidate["candidate_token_ids_json"]), phrase_rows, word_lengths,
                allowed_start_ranges=ranges,
            )
            seeded_seconds = time.monotonic() - seeded_started
            seeded = {(start, str(phrase_ids[phrase_index])) for start, phrase_index in seeded_hits}
            both = unseeded & seeded
            only_unseeded = unseeded - seeded
            only_seeded = seeded - unseeded
            unseeded_clusters = cluster_hit_spans(
                (start, start + int(group["phrase_token_length"])) for start, _phrase_id in unseeded
            )
            seeded_clusters = cluster_hit_spans(
                (start, start + int(group["phrase_token_length"])) for start, _phrase_id in seeded
            )
            both_clusters = set(unseeded_clusters) & set(seeded_clusters)
            comparison_rows.append({
                "trial_id": candidate["trial_id"], "candidate_id": candidate["candidate_id"],
                "length_bucket": length_bucket(int(group["phrase_token_length"])),
                "word_token_lengths": group["word_token_lengths"],
                "unseeded_verified_hit_count": len(unseeded), "seeded_verified_hit_count": len(seeded),
                "hits_found_by_both": len(both), "hits_found_only_unseeded": len(only_unseeded),
                "hits_found_only_seeded": len(only_seeded), "unseeded_cluster_count": len(unseeded_clusters),
                "seeded_cluster_count": len(seeded_clusters), "clusters_found_by_both": len(both_clusters),
                "clusters_found_only_unseeded": len(set(unseeded_clusters) - set(seeded_clusters)),
                "clusters_found_only_seeded": len(set(seeded_clusters) - set(unseeded_clusters)),
                "seeded_missed_hit_fraction": len(only_unseeded) / len(unseeded) if unseeded else 0,
                "seeded_missed_cluster_fraction": (
                    len(set(unseeded_clusters) - set(seeded_clusters)) / len(unseeded_clusters)
                    if unseeded_clusters else 0
                ),
                "unseeded_runtime_seconds": "", "seeded_runtime_seconds": seeded_seconds, "speedup_factor": "",
                "seed_policy_status": "usable_as_priority_not_candidate_filter",
            })
    if not order2_seed_rows:
        order2_seed_rows = [{
            "candidate_id": "", "seed_profile_id": "B2R_bounded_seed_canary", "seed_cluster_start": "",
            "seed_cluster_end": "", "seed_hit_count": 0, "seed_cluster_count": 0, "expanded_search_start": "",
            "expanded_search_end": "", "expansion_margin_tokens": 20, "status": "complete_no_seed_hits",
            "order2_score_authority": "diagnostic_only",
        }]
    budget_rows = [{
        "searched_group_count": len(groups), "skipped_group_count": len(skipped_rows),
        "completed_group_count": len(groups), "incomplete_group_count": 0, "candidate_count": len(candidates),
        "total_runtime_seconds": total_runtime, "peak_memory_mb": "",
        "estimated_full_fixture_runtime_seconds": total_runtime * 734 / len(candidates),
        "estimated_full_n3c_runtime_seconds": "",
        "query_is_full_n3c": False, "search_completeness_label": "partial_budgeted_canary",
    }]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _write_csv(OUTPUT_DIR / "query_plan_group_rows.csv", query_plan_group_rows, tuple(query_plan_group_rows[0]))
    _write_csv(OUTPUT_DIR / "query_plan_candidate_rows.csv", query_plan_candidate_rows, tuple(query_plan_candidate_rows[0]))
    _write_csv(OUTPUT_DIR / "length_bucket_yield_rows.csv", by_bucket, tuple(by_bucket[0]))
    _write_csv(OUTPUT_DIR / "word_shape_yield_rows.csv", group_results, tuple(group_results[0]))
    _write_csv(OUTPUT_DIR / "order2_seed_rows.csv", order2_seed_rows, tuple(order2_seed_rows[0]))
    _write_csv(OUTPUT_DIR / "order2_seeded_vs_unseeded_rows.csv", comparison_rows, tuple(comparison_rows[0]))
    hit_fields = (
        "trial_id", "candidate_id", "group_id", "query_mode", "length_bucket", "phrase_token_length",
        "word_token_lengths", "phrase_id", "hit_start", "hit_end", "word_hds", "total_phrase_hd",
        "exact_verification", "full_phrase_verified",
    )
    _write_csv(OUTPUT_DIR / "n3c_verified_hit_rows.csv", hit_rows, hit_fields)
    cluster_fields = ("candidate_id", "group_id", "cluster_index", "cluster_start", "cluster_end", "verified_hit_count")
    _write_csv(OUTPUT_DIR / "n3c_cluster_summary_rows.csv", cluster_rows, cluster_fields)
    _write_csv(OUTPUT_DIR / "search_budget_summary_rows.csv", budget_rows, tuple(budget_rows[0]))
    _write_csv(OUTPUT_DIR / "skipped_group_rows.csv", skipped_rows, tuple(skipped_rows[0]))
    _write_csv(OUTPUT_DIR / "timing_rows.csv", timing_rows, tuple(timing_rows[0]))
    manifest = {
        "status": "pass_partial_budgeted_canary",
        "phase": PHASE, "fixture_id": "phaseB_failed_decryption_retained_candidate_fixture_v1",
        "fixture_candidate_count": 734, "study_candidate_count": len(candidates),
        "candidate_rank_availability": "unavailable_not_invented",
        "n3c_runtime_asset_id": runtime["asset_id"], "n3c_runtime_validation_status": validation["status"],
        "query_is_full_n3c": False, "query_scope": "length_aware_order2_informed_study",
        "query_modes_completed": [QUERY_MODE, "order2_seeded_regions", "seeded_vs_unseeded_comparison"],
        "query_modes_blocked": [],
        "filter_strategy": FILTER_STRATEGY, "projection_or_anchor_used_for_filter_only": True,
        "full_phrase_verified": True, "searched_group_count": len(groups), "unsearched_group_count": len(skipped_rows),
        "all_started_groups_completed": True, "length_bucket_rules": list(BUCKET_ORDER),
        "production_scoring_change": False, "production_ranking_change": False,
        "order2_used_for_query_planning_only": True, "order2_score_authority": "diagnostic_only",
        "order2_seed_group_count": len(order2_groups), "order2_seed_row_count": len(order2_seed_rows),
        "seeded_missed_n3c_hit_count": sum(int(row["hits_found_only_unseeded"]) for row in comparison_rows),
        "seeded_missed_n3c_cluster_count": sum(int(row["clusters_found_only_unseeded"]) for row in comparison_rows),
        "old_phrase_index_v1_used": False, "sample_asset_used": False,
        "selected_phrase_subset_used": False, "full_raw_shards_used_directly_as_runtime": False,
        "verified_hit_count": len(hit_rows), "verified_cluster_count": len(cluster_rows),
        "total_runtime_seconds": total_runtime, "max_runtime_seconds_per_group": MAX_RUNTIME_SECONDS_PER_GROUP,
        "max_peak_memory_mb": MAX_PEAK_MEMORY_MB,
        "absence_of_hits_meaningful": False,
    }
    (OUTPUT_DIR / "run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    bucket_counts = Counter(row["length_bucket"] for row in query_plan_group_rows)
    (OUTPUT_DIR / "readout.md").write_text(
        "# Length-Aware And Order-2-Informed N3C Query Planning\n\n"
        f"- status: `{manifest['status']}`\n"
        f"- candidates searched: `{len(candidates)}` (one per trial; ranks unavailable)\n"
        f"- groups searched: `{len(groups)}`; groups unsearched: `{len(skipped_rows)}`\n"
        f"- searched buckets: `{json.dumps(dict(bucket_counts), sort_keys=True)}`\n"
        f"- verified hits: `{len(hit_rows)}`; verified clusters: `{len(cluster_rows)}`\n"
        f"- total runtime seconds: `{total_runtime:.3f}`\n"
        f"- order-2 seed rows: `{len(order2_seed_rows)}`; authority: `diagnostic_only`\n"
        f"- N3C hits missed by seeded regions: `{manifest['seeded_missed_n3c_hit_count']}`\n"
        f"- N3C clusters missed by seeded regions: `{manifest['seeded_missed_n3c_cluster_count']}`\n"
        "- query is full N3C: `false`\n"
        "- absence of hits meaningful: `false`\n"
        "- all filters are candidate generation only; every emitted hit is full-phrase word-structured verified\n"
        "- production rank effect: `none`\n",
        encoding="utf-8",
    )
    return manifest


if __name__ == "__main__":
    run_study()
