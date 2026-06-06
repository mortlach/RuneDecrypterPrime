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

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.phaseB_n3c_query_planning_core_v1 import (
    annotated_cluster_hit_rows,
    semantic_pair_id,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.run_phaseB_failed_decryption_n3c_full80_query_evidence_v1 import (
    FIXTURE_DIR,
    N3CRunSpec,
    compare_signal,
    classify_pair,
)


PHASE = "phaseB_failed_decryption_n3c_strict_full80_corrected_consolidated_evidence_v1"
OUTPUT_DIR = REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis" / PHASE
BUCKET_PHASES = (
    ("8-9", "phaseB_failed_decryption_n3c_strict_full80_bucket_8_9_query_evidence_v1"),
    ("10-11", "phaseB_failed_decryption_n3c_strict_full80_bucket_10_11_query_evidence_v1"),
    ("12-14", "phaseB_failed_decryption_n3c_strict_full80_bucket_12_14_query_evidence_v1"),
    ("15-17", "phaseB_failed_decryption_n3c_strict_full80_bucket_15_17_query_evidence_v1"),
    ("18+", "phaseB_failed_decryption_n3c_strict_full80_bucket_18_plus_query_evidence_v1"),
)
STRICT_RUN_SPEC = N3CRunSpec(
    run_family="n3c_strict_full80",
    schema_version="n3c_run_spec_v1",
    direction="fwd",
    ngram_order=3,
    dictionary_cut="strict",
    minimum_phrase_length=8,
    length_bucket=None,
    candidate_scope="selected_80_retained_candidates_v1",
    query_contract="total_hd_le_2_max_word_hd_le_1_word_structured",
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


def interval_covered_token_count(clusters: list[dict[str, object]]) -> int:
    return sum(int(row["end_offset"]) - int(row["start_offset"]) for row in clusters)


def compare_candidate_signal(
    by_candidate: dict[str, dict[str, object]],
    pair: dict[str, str],
    field: str,
) -> str:
    left = by_candidate[pair["candidate_a_id"]]
    right = by_candidate[pair["candidate_b_id"]]
    return compare_signal(int(left[field]), int(right[field]), pair["candidate_a_id"], pair["candidate_b_id"])


def build_pair_rows(
    by_candidate: dict[str, dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    selected_ids = set(by_candidate)
    raw_rows: list[dict[str, object]] = []
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for pair in csv.DictReader((FIXTURE_DIR / "candidate_pair_rows.csv").open(encoding="utf-8", newline="")):
        if pair["candidate_a_id"] not in selected_ids or pair["candidate_b_id"] not in selected_ids:
            continue
        semantic_id = semantic_pair_id(pair["trial_id"], pair["candidate_a_id"], pair["candidate_b_id"])
        baseline_correct = pair["baseline_winner_id"] == pair["gold_winner_id"]
        raw_row = {
            "source_pair_id": pair["pair_id"],
            "semantic_pair_id": semantic_id,
            "trial_id": pair["trial_id"],
            "candidate_a_id": pair["candidate_a_id"],
            "candidate_b_id": pair["candidate_b_id"],
            "baseline_winner_id": pair["baseline_winner_id"],
            "gold_winner_id": pair["gold_winner_id"],
            "baseline_correct": baseline_correct,
            "can_observe_break": baseline_correct,
            "can_observe_rescue": not baseline_correct,
        }
        raw_rows.append(raw_row)
        grouped[semantic_id].append(raw_row)

    unique_rows: list[dict[str, object]] = []
    for semantic_id in sorted(grouped):
        sources = grouped[semantic_id]
        first = sources[0]
        pair = {
            "candidate_a_id": str(first["candidate_a_id"]),
            "candidate_b_id": str(first["candidate_b_id"]),
        }
        hit_winner = compare_candidate_signal(by_candidate, pair, "verified_hit_count")
        cluster_winner = compare_candidate_signal(by_candidate, pair, "global_candidate_n3c_cluster_count")
        exact_cluster_winner = compare_candidate_signal(
            by_candidate, pair, "global_candidate_n3c_exact_containing_cluster_count"
        )
        baseline_winner = str(first["baseline_winner_id"])
        gold_winner = str(first["gold_winner_id"])
        unique_rows.append({
            "semantic_pair_id": semantic_id,
            "source_pair_ids": json.dumps([row["source_pair_id"] for row in sources], separators=(",", ":")),
            "duplicate_source_row_count": len(sources),
            "trial_id": first["trial_id"],
            "candidate_a_id": first["candidate_a_id"],
            "candidate_b_id": first["candidate_b_id"],
            "baseline_winner_id": baseline_winner,
            "gold_winner_id": gold_winner,
            "baseline_correct": first["baseline_correct"],
            "can_observe_break": first["can_observe_break"],
            "can_observe_rescue": first["can_observe_rescue"],
            "n3c_verified_hit_count_winner_id": hit_winner,
            "n3c_verified_hit_count_pair_result": classify_pair(hit_winner, baseline_winner, gold_winner),
            "n3c_global_cluster_winner_id": cluster_winner,
            "n3c_global_cluster_pair_result": classify_pair(cluster_winner, baseline_winner, gold_winner),
            "n3c_exact_containing_global_cluster_winner_id": exact_cluster_winner,
            "n3c_exact_containing_global_cluster_pair_result": classify_pair(
                exact_cluster_winner, baseline_winner, gold_winner
            ),
            "candidate_a_verified_hit_count": by_candidate[str(first["candidate_a_id"])]["verified_hit_count"],
            "candidate_b_verified_hit_count": by_candidate[str(first["candidate_b_id"])]["verified_hit_count"],
            "candidate_a_global_clusters": by_candidate[str(first["candidate_a_id"])][
                "global_candidate_n3c_cluster_count"
            ],
            "candidate_b_global_clusters": by_candidate[str(first["candidate_b_id"])][
                "global_candidate_n3c_cluster_count"
            ],
            "candidate_a_exact_containing_global_clusters": by_candidate[str(first["candidate_a_id"])][
                "global_candidate_n3c_exact_containing_cluster_count"
            ],
            "candidate_b_exact_containing_global_clusters": by_candidate[str(first["candidate_b_id"])][
                "global_candidate_n3c_exact_containing_cluster_count"
            ],
        })
    return raw_rows, unique_rows


def build_strict_consolidated_evidence() -> dict[str, object]:
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

    for expected_bucket, phase in BUCKET_PHASES:
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
            chunk_rows.append({"length_bucket": expected_bucket, **row})
        for row in read_rows(phase_dir / "logical_group_summary_rows.csv"):
            if row["direction"] != "fwd" or row["dictionary_cut"] != "strict" or int(row["ngram_order"]) != 3:
                raise RuntimeError(f"{phase} has a logical group outside the strict run spec")
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
                "dictionary_cut": STRICT_RUN_SPEC.dictionary_cut,
                "ngram_order": STRICT_RUN_SPEC.ngram_order,
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
        "status": "n3c_strict_full80_corrected_consolidated_evidence_ready_for_comparison",
        "phase": PHASE,
        "run_spec": {
            "run_family": STRICT_RUN_SPEC.run_family,
            "schema_version": STRICT_RUN_SPEC.schema_version,
            "direction": STRICT_RUN_SPEC.direction,
            "ngram_order": STRICT_RUN_SPEC.ngram_order,
            "dictionary_cut": STRICT_RUN_SPEC.dictionary_cut,
            "minimum_phrase_length": STRICT_RUN_SPEC.minimum_phrase_length,
            "length_bucket": STRICT_RUN_SPEC.length_bucket,
            "candidate_scope": STRICT_RUN_SPEC.candidate_scope,
            "query_contract": STRICT_RUN_SPEC.query_contract,
        },
        "bucket_count": len(bucket_summary_rows),
        "runtime_chunk_count": sum(int(row["runtime_chunk_count"]) for row in bucket_summary_rows),
        "logical_group_count": len({row["logical_group_id"] for row in logical_rows}),
        "runtime_phrase_rows": sum(int(row["runtime_phrase_rows"]) for row in bucket_summary_rows),
        "candidate_count": len(candidate_summary_rows),
        "verified_hit_count": sum(int(row["verified_hit_count"]) for row in bucket_summary_rows),
        "global_candidate_n3c_cluster_count": ordinary_cluster_count,
        "global_candidate_n3c_exact_containing_cluster_count": exact_containing_count,
        "exact_containing_cluster_count_invariant_pass": exact_containing_count <= ordinary_cluster_count,
        "raw_pair_row_count_with_both_candidates_in_sample": len(raw_pair_rows),
        "unique_semantic_pair_count_with_both_candidates_in_sample": len(unique_pair_rows),
        "semantic_pair_duplicate_count": len(raw_pair_rows) - len(unique_pair_rows),
        "baseline_correct_unique_semantic_pair_count": sum(row["baseline_correct"] is True for row in unique_pair_rows),
        "rescue_capable_unique_semantic_pair_count": sum(row["can_observe_rescue"] is True for row in unique_pair_rows),
        "break_capable_unique_semantic_pair_count": sum(row["can_observe_break"] is True for row in unique_pair_rows),
        "unique_semantic_pair_result_counts": unique_pair_result_counts,
        "bucket_runtime_seconds_sum": sum(float(row["runtime_seconds"]) for row in bucket_summary_rows),
        "peak_memory_mb_max": max(float(row["peak_memory_mb"]) for row in bucket_summary_rows),
        "query_is_complete_for_declared_run_spec": True,
        "query_is_full_734_candidate_fixture": False,
        "hit_rows_are_external_bucket_files": True,
        "global_clusters_are_candidate_level_across_all_buckets": True,
        "bucket_clusters_are_diagnostic_only": True,
        "production_scoring_change": False,
        "production_ranking_change": False,
        "score_bearing_use_approved": False,
        "order2_query_authority": "priority_only_never_filter",
        "next_gate": "matched_strict_versus_normal_comparison_then_main_external_review_pack",
    }
    (OUTPUT_DIR / "run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (OUTPUT_DIR / "readout.md").write_text(
        "# Corrected Strict Full80 N3C Consolidated Evidence\n\n"
        f"- status: `{manifest['status']}`\n"
        f"- dictionary cut: `{STRICT_RUN_SPEC.dictionary_cut}`\n"
        f"- chunks: `{manifest['runtime_chunk_count']}`; logical groups: `{manifest['logical_group_count']}`\n"
        f"- phrase rows: `{manifest['runtime_phrase_rows']}`\n"
        f"- candidates: `{manifest['candidate_count']}`\n"
        f"- verified hits: `{manifest['verified_hit_count']}`\n"
        f"- global candidate clusters: `{manifest['global_candidate_n3c_cluster_count']}`\n"
        f"- exact-containing global candidate clusters: "
        f"`{manifest['global_candidate_n3c_exact_containing_cluster_count']}`\n"
        f"- raw pair rows: `{manifest['raw_pair_row_count_with_both_candidates_in_sample']}`\n"
        f"- unique semantic pairs: `{manifest['unique_semantic_pair_count_with_both_candidates_in_sample']}`\n"
        f"- unique pair result counts: `{json.dumps(unique_pair_result_counts, sort_keys=True)}`\n\n"
        "This strict reference remains report-only diagnostic evidence and changes no production score or ranking.\n",
        encoding="utf-8",
    )
    print(f"[{PHASE}] status={manifest['status']}")
    print(
        f"[{PHASE}] hits={manifest['verified_hit_count']} "
        f"clusters={manifest['global_candidate_n3c_cluster_count']} "
        f"exact_containing={manifest['global_candidate_n3c_exact_containing_cluster_count']} "
        f"unique_pairs={manifest['unique_semantic_pair_count_with_both_candidates_in_sample']}"
    )
    return manifest


if __name__ == "__main__":
    build_strict_consolidated_evidence()
