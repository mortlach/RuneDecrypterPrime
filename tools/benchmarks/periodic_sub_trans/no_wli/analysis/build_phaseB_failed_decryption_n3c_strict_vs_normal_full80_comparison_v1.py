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


PHASE = "phaseB_failed_decryption_n3c_strict_vs_normal_full80_comparison_v1"
OUTPUT_DIR = REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis" / PHASE
ANALYSIS_ROOT = REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis"
NORMAL_DIR = ANALYSIS_ROOT / "phaseB_failed_decryption_n3c_normal_full80_corrected_consolidated_evidence_v1"
STRICT_DIR = ANALYSIS_ROOT / "phaseB_failed_decryption_n3c_strict_full80_corrected_consolidated_evidence_v1"


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fields: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def ratio(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def aggregate_hit_yields(evidence_dir: Path) -> tuple[dict[str, Counter[str]], dict[tuple[str, str], Counter[str]]]:
    by_length: dict[str, Counter[str]] = defaultdict(Counter)
    by_shape: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    for manifest_row in read_rows(evidence_dir / "hit_file_manifest_rows.csv"):
        hit_path = REPO_ROOT / manifest_row["hit_file"]
        with hit_path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                length = row["phrase_token_length"]
                shape = row["word_token_lengths"]
                by_length[length]["verified_hit_count"] += 1
                by_shape[(length, shape)]["verified_hit_count"] += 1
                if row["exact_flag"] == "True":
                    by_length[length]["exact_hit_count"] += 1
                    by_shape[(length, shape)]["exact_hit_count"] += 1
    return by_length, by_shape


def phrase_rows_by_length_and_shape(evidence_dir: Path) -> tuple[Counter[str], Counter[tuple[str, str]]]:
    by_length: Counter[str] = Counter()
    by_shape: Counter[tuple[str, str]] = Counter()
    for row in read_rows(evidence_dir / "logical_group_summary_rows.csv"):
        phrase_rows = int(row["logical_group_phrase_count"])
        length = row["phrase_token_length"]
        shape = row["word_token_lengths"]
        by_length[length] += phrase_rows
        by_shape[(length, shape)] += phrase_rows
    return by_length, by_shape


def build_bucket_comparison(normal_manifest: dict[str, object], strict_manifest: dict[str, object]) -> list[dict[str, object]]:
    normal_rows = {row["length_bucket"]: row for row in read_rows(NORMAL_DIR / "bucket_summary_rows.csv")}
    strict_rows = {row["length_bucket"]: row for row in read_rows(STRICT_DIR / "bucket_summary_rows.csv")}
    rows: list[dict[str, object]] = []
    for bucket in ("8-9", "10-11", "12-14", "15-17", "18+"):
        normal = normal_rows[bucket]
        strict = strict_rows[bucket]
        normal_phrase_rows = int(normal["runtime_phrase_rows"])
        strict_phrase_rows = int(strict["runtime_phrase_rows"])
        normal_hits = int(normal["verified_hit_count"])
        strict_hits = int(strict["verified_hit_count"])
        normal_runtime = float(normal["runtime_seconds"])
        strict_runtime = float(strict["runtime_seconds"])
        rows.append({
            "length_bucket": bucket,
            "normal_runtime_chunk_count": normal["runtime_chunk_count"],
            "strict_runtime_chunk_count": strict["runtime_chunk_count"],
            "chunk_reduction": int(normal["runtime_chunk_count"]) - int(strict["runtime_chunk_count"]),
            "normal_phrase_rows": normal_phrase_rows,
            "strict_phrase_rows": strict_phrase_rows,
            "phrase_row_reduction": normal_phrase_rows - strict_phrase_rows,
            "phrase_row_retention_fraction": ratio(strict_phrase_rows, normal_phrase_rows),
            "normal_verified_hit_count": normal_hits,
            "strict_verified_hit_count": strict_hits,
            "verified_hit_retention_fraction": ratio(strict_hits, normal_hits),
            "normal_hits_per_million_phrase_rows": ratio(normal_hits * 1_000_000.0, normal_phrase_rows),
            "strict_hits_per_million_phrase_rows": ratio(strict_hits * 1_000_000.0, strict_phrase_rows),
            "normal_runtime_seconds": normal_runtime,
            "strict_runtime_seconds": strict_runtime,
            "runtime_reduction_seconds": normal_runtime - strict_runtime,
            "runtime_retention_fraction": ratio(strict_runtime, normal_runtime),
        })
    return rows


def build_candidate_comparison() -> list[dict[str, object]]:
    normal_rows = {row["candidate_id"]: row for row in read_rows(NORMAL_DIR / "candidate_n3c_summary_rows.csv")}
    strict_rows = {row["candidate_id"]: row for row in read_rows(STRICT_DIR / "candidate_n3c_summary_rows.csv")}
    rows: list[dict[str, object]] = []
    for candidate_id in sorted(normal_rows):
        normal = normal_rows[candidate_id]
        strict = strict_rows[candidate_id]
        normal_hits = int(normal["verified_hit_count"])
        strict_hits = int(strict["verified_hit_count"])
        normal_clusters = int(normal["global_candidate_n3c_cluster_count"])
        strict_clusters = int(strict["global_candidate_n3c_cluster_count"])
        normal_exact_clusters = int(normal["global_candidate_n3c_exact_containing_cluster_count"])
        strict_exact_clusters = int(strict["global_candidate_n3c_exact_containing_cluster_count"])
        rows.append({
            "trial_id": normal["trial_id"],
            "candidate_id": candidate_id,
            "normal_verified_hit_count": normal_hits,
            "strict_verified_hit_count": strict_hits,
            "verified_hit_retention_fraction": ratio(strict_hits, normal_hits),
            "normal_exact_hit_count": normal["exact_hit_count"],
            "strict_exact_hit_count": strict["exact_hit_count"],
            "exact_hit_retention_fraction": ratio(int(strict["exact_hit_count"]), int(normal["exact_hit_count"])),
            "normal_global_cluster_count": normal_clusters,
            "strict_global_cluster_count": strict_clusters,
            "global_cluster_delta": strict_clusters - normal_clusters,
            "normal_exact_containing_global_cluster_count": normal_exact_clusters,
            "strict_exact_containing_global_cluster_count": strict_exact_clusters,
            "exact_containing_global_cluster_delta": strict_exact_clusters - normal_exact_clusters,
            "normal_cluster_coverage_fraction": normal["cluster_coverage_fraction"],
            "strict_cluster_coverage_fraction": strict["cluster_coverage_fraction"],
        })
    return rows


def build_pair_comparison() -> list[dict[str, object]]:
    normal_rows = {
        row["semantic_pair_id"]: row for row in read_rows(NORMAL_DIR / "unique_semantic_pairwise_gold_n3c_report_rows.csv")
    }
    strict_rows = {
        row["semantic_pair_id"]: row for row in read_rows(STRICT_DIR / "unique_semantic_pairwise_gold_n3c_report_rows.csv")
    }
    rows: list[dict[str, object]] = []
    for pair_id in sorted(normal_rows):
        normal = normal_rows[pair_id]
        strict = strict_rows[pair_id]
        rows.append({
            "semantic_pair_id": pair_id,
            "trial_id": normal["trial_id"],
            "candidate_a_id": normal["candidate_a_id"],
            "candidate_b_id": normal["candidate_b_id"],
            "baseline_winner_id": normal["baseline_winner_id"],
            "gold_winner_id": normal["gold_winner_id"],
            "can_observe_break": normal["can_observe_break"],
            "can_observe_rescue": normal["can_observe_rescue"],
            "normal_verified_hit_count_pair_result": normal["n3c_verified_hit_count_pair_result"],
            "strict_verified_hit_count_pair_result": strict["n3c_verified_hit_count_pair_result"],
            "normal_global_cluster_pair_result": normal["n3c_global_cluster_pair_result"],
            "strict_global_cluster_pair_result": strict["n3c_global_cluster_pair_result"],
            "normal_exact_containing_global_cluster_pair_result": normal[
                "n3c_exact_containing_global_cluster_pair_result"
            ],
            "strict_exact_containing_global_cluster_pair_result": strict[
                "n3c_exact_containing_global_cluster_pair_result"
            ],
        })
    return rows


def build_yield_comparison_rows(
    normal_hits: dict[str, Counter[str]],
    strict_hits: dict[str, Counter[str]],
    normal_phrase_rows: Counter[str],
    strict_phrase_rows: Counter[str],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for length in sorted(set(normal_phrase_rows) | set(strict_phrase_rows), key=int):
        normal_rows = normal_phrase_rows[length]
        strict_rows = strict_phrase_rows[length]
        normal_verified = normal_hits[length]["verified_hit_count"]
        strict_verified = strict_hits[length]["verified_hit_count"]
        normal_exact = normal_hits[length]["exact_hit_count"]
        strict_exact = strict_hits[length]["exact_hit_count"]
        rows.append({
            "phrase_token_length": length,
            "normal_phrase_rows": normal_rows,
            "strict_phrase_rows": strict_rows,
            "phrase_row_retention_fraction": ratio(strict_rows, normal_rows),
            "normal_verified_hit_count": normal_verified,
            "strict_verified_hit_count": strict_verified,
            "verified_hit_retention_fraction": ratio(strict_verified, normal_verified),
            "normal_exact_hit_count": normal_exact,
            "strict_exact_hit_count": strict_exact,
            "exact_hit_retention_fraction": ratio(strict_exact, normal_exact),
            "normal_hits_per_million_phrase_rows": ratio(normal_verified * 1_000_000.0, normal_rows),
            "strict_hits_per_million_phrase_rows": ratio(strict_verified * 1_000_000.0, strict_rows),
        })
    return rows


def build_shape_yield_comparison_rows(
    normal_hits: dict[tuple[str, str], Counter[str]],
    strict_hits: dict[tuple[str, str], Counter[str]],
    normal_phrase_rows: Counter[tuple[str, str]],
    strict_phrase_rows: Counter[tuple[str, str]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for length_shape in sorted(set(normal_phrase_rows) | set(strict_phrase_rows), key=lambda item: (int(item[0]), item[1])):
        length, shape = length_shape
        normal_rows = normal_phrase_rows[length_shape]
        strict_rows = strict_phrase_rows[length_shape]
        normal_verified = normal_hits[length_shape]["verified_hit_count"]
        strict_verified = strict_hits[length_shape]["verified_hit_count"]
        normal_exact = normal_hits[length_shape]["exact_hit_count"]
        strict_exact = strict_hits[length_shape]["exact_hit_count"]
        rows.append({
            "phrase_token_length": length,
            "word_token_lengths": shape,
            "normal_phrase_rows": normal_rows,
            "strict_phrase_rows": strict_rows,
            "phrase_row_retention_fraction": ratio(strict_rows, normal_rows),
            "normal_verified_hit_count": normal_verified,
            "strict_verified_hit_count": strict_verified,
            "verified_hit_retention_fraction": ratio(strict_verified, normal_verified),
            "normal_exact_hit_count": normal_exact,
            "strict_exact_hit_count": strict_exact,
            "exact_hit_retention_fraction": ratio(strict_exact, normal_exact),
        })
    return rows


def build_comparison() -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    normal_manifest = read_json(NORMAL_DIR / "run_manifest.json")
    strict_manifest = read_json(STRICT_DIR / "run_manifest.json")
    if normal_manifest["status"] != "n3c_normal_full80_corrected_consolidated_evidence_ready_for_engineering_gate":
        raise RuntimeError("corrected normal evidence is not ready")
    if strict_manifest["status"] != "n3c_strict_full80_corrected_consolidated_evidence_ready_for_comparison":
        raise RuntimeError("corrected strict evidence is not ready")

    bucket_rows = build_bucket_comparison(normal_manifest, strict_manifest)
    candidate_rows = build_candidate_comparison()
    pair_rows = build_pair_comparison()
    normal_hits_by_length, normal_hits_by_shape = aggregate_hit_yields(NORMAL_DIR)
    strict_hits_by_length, strict_hits_by_shape = aggregate_hit_yields(STRICT_DIR)
    normal_phrase_by_length, normal_phrase_by_shape = phrase_rows_by_length_and_shape(NORMAL_DIR)
    strict_phrase_by_length, strict_phrase_by_shape = phrase_rows_by_length_and_shape(STRICT_DIR)
    length_rows = build_yield_comparison_rows(
        normal_hits_by_length, strict_hits_by_length, normal_phrase_by_length, strict_phrase_by_length
    )
    shape_rows = build_shape_yield_comparison_rows(
        normal_hits_by_shape, strict_hits_by_shape, normal_phrase_by_shape, strict_phrase_by_shape
    )

    write_csv(OUTPUT_DIR / "bucket_comparison_rows.csv", bucket_rows, tuple(bucket_rows[0]))
    write_csv(OUTPUT_DIR / "candidate_comparison_rows.csv", candidate_rows, tuple(candidate_rows[0]))
    write_csv(OUTPUT_DIR / "semantic_pair_comparison_rows.csv", pair_rows, tuple(pair_rows[0]))
    write_csv(OUTPUT_DIR / "length_yield_comparison_rows.csv", length_rows, tuple(length_rows[0]))
    write_csv(OUTPUT_DIR / "word_shape_yield_comparison_rows.csv", shape_rows, tuple(shape_rows[0]))

    pair_result_counts = {
        "normal_verified_hit_count": dict(Counter(row["normal_verified_hit_count_pair_result"] for row in pair_rows)),
        "strict_verified_hit_count": dict(Counter(row["strict_verified_hit_count_pair_result"] for row in pair_rows)),
        "normal_global_cluster": dict(Counter(row["normal_global_cluster_pair_result"] for row in pair_rows)),
        "strict_global_cluster": dict(Counter(row["strict_global_cluster_pair_result"] for row in pair_rows)),
        "normal_exact_containing_global_cluster": dict(Counter(
            row["normal_exact_containing_global_cluster_pair_result"] for row in pair_rows
        )),
        "strict_exact_containing_global_cluster": dict(Counter(
            row["strict_exact_containing_global_cluster_pair_result"] for row in pair_rows
        )),
    }
    normal_rows_total = int(normal_manifest["runtime_phrase_rows"])
    strict_rows_total = int(strict_manifest["runtime_phrase_rows"])
    normal_hits_total = int(normal_manifest["verified_hit_count"])
    strict_hits_total = int(strict_manifest["verified_hit_count"])
    normal_runtime = float(normal_manifest["bucket_runtime_seconds_sum"])
    strict_runtime = float(strict_manifest["bucket_runtime_seconds_sum"])
    manifest = {
        "status": "n3c_strict_vs_normal_full80_comparison_ready_for_review_pack",
        "phase": PHASE,
        "normal_evidence_dir": NORMAL_DIR.relative_to(REPO_ROOT).as_posix(),
        "strict_evidence_dir": STRICT_DIR.relative_to(REPO_ROOT).as_posix(),
        "candidate_count": normal_manifest["candidate_count"],
        "unique_semantic_pair_count": normal_manifest["unique_semantic_pair_count_with_both_candidates_in_sample"],
        "rescue_capable_unique_semantic_pair_count": normal_manifest["rescue_capable_unique_semantic_pair_count"],
        "normal_runtime_chunk_count": normal_manifest["runtime_chunk_count"],
        "strict_runtime_chunk_count": strict_manifest["runtime_chunk_count"],
        "chunk_reduction": int(normal_manifest["runtime_chunk_count"]) - int(strict_manifest["runtime_chunk_count"]),
        "normal_phrase_rows": normal_rows_total,
        "strict_phrase_rows": strict_rows_total,
        "phrase_row_reduction": normal_rows_total - strict_rows_total,
        "phrase_row_retention_fraction": ratio(strict_rows_total, normal_rows_total),
        "normal_verified_hit_count": normal_hits_total,
        "strict_verified_hit_count": strict_hits_total,
        "verified_hit_retention_fraction": ratio(strict_hits_total, normal_hits_total),
        "normal_global_candidate_cluster_count": normal_manifest["global_candidate_n3c_cluster_count"],
        "strict_global_candidate_cluster_count": strict_manifest["global_candidate_n3c_cluster_count"],
        "normal_exact_containing_global_candidate_cluster_count": normal_manifest[
            "global_candidate_n3c_exact_containing_cluster_count"
        ],
        "strict_exact_containing_global_candidate_cluster_count": strict_manifest[
            "global_candidate_n3c_exact_containing_cluster_count"
        ],
        "normal_bucket_runtime_seconds_sum": normal_runtime,
        "strict_bucket_runtime_seconds_sum": strict_runtime,
        "runtime_reduction_seconds": normal_runtime - strict_runtime,
        "runtime_retention_fraction": ratio(strict_runtime, normal_runtime),
        "normal_peak_memory_mb_max": normal_manifest["peak_memory_mb_max"],
        "strict_peak_memory_mb_max": strict_manifest["peak_memory_mb_max"],
        "unique_semantic_pair_result_counts": pair_result_counts,
        "phrase_level_strict_subset_identity_proven": False,
        "comparison_scope_note": "aggregate_candidate_cluster_pair_length_shape_only_no_shared_phrase_claim",
        "production_scoring_change": False,
        "production_ranking_change": False,
        "score_bearing_use_approved": False,
        "next_gate": "main_external_review_pack_before_734_or_score_bearing_work",
    }
    (OUTPUT_DIR / "run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (OUTPUT_DIR / "readout.md").write_text(
        "# N3C Strict Versus Normal Full80 Comparison\n\n"
        f"- status: `{manifest['status']}`\n"
        f"- phrase rows normal -> strict: `{normal_rows_total}` -> `{strict_rows_total}` "
        f"({manifest['phrase_row_retention_fraction']:.3f} retained)\n"
        f"- runtime chunks normal -> strict: `{manifest['normal_runtime_chunk_count']}` -> "
        f"`{manifest['strict_runtime_chunk_count']}`\n"
        f"- verified hits normal -> strict: `{normal_hits_total}` -> `{strict_hits_total}` "
        f"({manifest['verified_hit_retention_fraction']:.3f} retained)\n"
        f"- global clusters normal -> strict: `{manifest['normal_global_candidate_cluster_count']}` -> "
        f"`{manifest['strict_global_candidate_cluster_count']}`\n"
        f"- exact-containing clusters normal -> strict: "
        f"`{manifest['normal_exact_containing_global_candidate_cluster_count']}` -> "
        f"`{manifest['strict_exact_containing_global_candidate_cluster_count']}`\n"
        f"- summed bucket runtime seconds normal -> strict: `{normal_runtime:.1f}` -> `{strict_runtime:.1f}`\n"
        f"- unique semantic pairs: `{manifest['unique_semantic_pair_count']}`; "
        f"rescue-capable: `{manifest['rescue_capable_unique_semantic_pair_count']}`\n"
        f"- pair result counts: `{json.dumps(pair_result_counts, sort_keys=True)}`\n\n"
        "Strict and normal phrase-level shared/only classes are not reported because stable phrase identity "
        "across cuts has not been proven. This comparison remains report-only and changes no production "
        "score or ranking.\n",
        encoding="utf-8",
    )
    print(f"[{PHASE}] status={manifest['status']}")
    print(
        f"[{PHASE}] rows_retained={manifest['phrase_row_retention_fraction']:.3f} "
        f"hits_retained={manifest['verified_hit_retention_fraction']:.3f} "
        f"runtime_seconds={strict_runtime:.1f}"
    )
    return manifest


if __name__ == "__main__":
    build_comparison()
