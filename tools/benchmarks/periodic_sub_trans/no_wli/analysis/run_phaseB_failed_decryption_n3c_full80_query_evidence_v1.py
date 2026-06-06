from __future__ import annotations

import csv
import json
import os
import sys
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import psutil


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
for path in (REPO_ROOT, REPO_ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.phaseB_n3c_query_planning_core_v1 import (
    annotated_cluster_hit_rows,
    build_sorted_block_index,
    cluster_hit_spans,
    length_bucket,
    sorted_block_partition_hit_details,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.run_phaseB_failed_decryption_length_aware_order2_informed_n3c_query_planning_v1 import (
    FIXTURE_DIR,
    RUNTIME_MANIFEST,
    RUNTIME_VALIDATION,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.run_phaseB_failed_decryption_n3c_medium_shape_diverse_candidate_microbatch_v1 import (
    select_diverse_candidates,
)


PHASE = "phaseB_failed_decryption_n3c_full80_query_evidence_v1"
OUTPUT_DIR = REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis" / PHASE
MAX_CANDIDATE_COUNT = 80
MAX_TOTAL_RUNTIME_SECONDS = 12_600.0
MAX_PEAK_MEMORY_MB = 2048.0
PROGRESS_EVERY_CHUNKS = 5
CANDIDATE_SELECTION_MODE = "initial_diverse_80"
CANDIDATE_REMAINING_OFFSET = 0
CANDIDATE_SELECTION_LABEL = "selected_80_retained_candidates_v1"
BUCKET_SORT_ORDER = {"8-9": 0, "10-11": 1, "12-14": 2, "15-17": 3, "18+": 4}
QUERY_SCOPE_LABEL = "complete_full_runtime_n3c_for_selected_80_candidates"
QUERY_IS_FULL_N3C_FOR_SELECTED_80 = True


@dataclass(frozen=True)
class N3CRunSpec:
    run_family: str
    schema_version: str
    direction: str
    ngram_order: int
    dictionary_cut: str
    minimum_phrase_length: int
    length_bucket: str | None
    candidate_scope: str
    query_contract: str

    @property
    def identity(self) -> str:
        bucket = self.length_bucket or "all"
        return (
            f"{self.run_family}|{self.schema_version}|{self.direction}|"
            f"order={self.ngram_order}|cut={self.dictionary_cut}|min={self.minimum_phrase_length}|"
            f"bucket={bucket}|scope={self.candidate_scope}|contract={self.query_contract}"
        )


RUN_SPEC = N3CRunSpec(
    run_family="n3c_normal_full80",
    schema_version="n3c_run_spec_v1",
    direction="fwd",
    ngram_order=3,
    dictionary_cut="normal",
    minimum_phrase_length=8,
    length_bucket=None,
    candidate_scope="selected_80_retained_candidates_v1",
    query_contract="total_hd_le_2_max_word_hd_le_1_word_structured",
)
HIT_FIELDS = (
    "trial_id", "candidate_id", "candidate_stratum", "runtime_chunk_id",
    "logical_group_id", "length_bucket", "phrase_token_length",
    "word_token_lengths", "phrase_id", "hit_start", "hit_end",
    "total_phrase_hd", "max_word_hd", "word_hds", "exact_flag",
    "full_phrase_verified",
)
CHUNK_FIELDS = (
    "runtime_chunk_id", "logical_group_id", "length_bucket", "phrase_token_length",
    "word_token_lengths", "runtime_phrase_count", "candidate_count",
    "lookup_match_count", "verified_hit_count", "chunk_candidate_cluster_count",
    "runtime_seconds", "peak_memory_mb", "status",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def logical_group_id(row: dict[str, object]) -> str:
    return "|".join((
        str(row["direction"]),
        str(row["dictionary_cut"]),
        str(row["ngram_order"]),
        str(row["phrase_token_length"]),
        str(row["word_token_lengths"]),
    ))


def select_chunks_for_run_spec(files: list[dict[str, object]], run_spec: N3CRunSpec) -> list[dict[str, object]]:
    rows = [
        {**row, "logical_group_id": logical_group_id(row)}
        for row in files
        if row["direction"] == run_spec.direction
        and row["dictionary_cut"] == run_spec.dictionary_cut
        and int(row["ngram_order"]) == run_spec.ngram_order
        and int(row["phrase_token_length"]) >= run_spec.minimum_phrase_length
        and (run_spec.length_bucket is None or length_bucket(int(row["phrase_token_length"])) == run_spec.length_bucket)
    ]
    return sorted(
        rows,
        key=lambda row: (
            BUCKET_SORT_ORDER[length_bucket(int(row["phrase_token_length"]))],
            int(row["phrase_token_length"]),
            str(row["word_token_lengths"]),
            int(row["chunk_index"]),
            str(row["path"]),
        ),
    )


def select_full_n3c_chunks(files: list[dict[str, object]]) -> list[dict[str, object]]:
    return select_chunks_for_run_spec(files, RUN_SPEC)


def select_candidate_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if CANDIDATE_SELECTION_MODE == "initial_diverse_80":
        return select_diverse_candidates(rows)
    if CANDIDATE_SELECTION_MODE != "remaining_by_trial_score_batch":
        raise RuntimeError(f"unknown candidate selection mode: {CANDIDATE_SELECTION_MODE}")
    already_selected = {row["candidate_id"] for row in select_diverse_candidates(rows)}
    remaining = sorted(
        (row for row in rows if row["candidate_id"] not in already_selected),
        key=lambda row: (row["trial_id"], -float(row["baseline_score"]), row["candidate_id"]),
    )
    selected = remaining[CANDIDATE_REMAINING_OFFSET:CANDIDATE_REMAINING_OFFSET + MAX_CANDIDATE_COUNT]
    return [
        {**row, "candidate_stratum": f"remaining_by_trial_score_batch_offset_{CANDIDATE_REMAINING_OFFSET}"}
        for row in selected
    ]


def assert_resume_identity(output_dir: Path, run_spec: N3CRunSpec) -> None:
    identity_path = output_dir / "run_identity.json"
    expected = {"run_spec": asdict(run_spec), "run_spec_identity": run_spec.identity}
    if identity_path.exists():
        actual = json.loads(identity_path.read_text(encoding="utf-8"))
        if actual != expected:
            raise RuntimeError("existing output run identity does not match requested run spec")
    elif any((output_dir / name).exists() for name in ("chunk_timing_rows.csv", "n3c_verified_hit_rows.csv")):
        raise RuntimeError("existing output lacks run identity; refuse ambiguous resume")
    else:
        identity_path.write_text(json.dumps(expected, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, object]], fields: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def append_csv_row(path: Path, row: dict[str, object], fields: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.is_file()
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def completed_chunk_ids(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    return {row["runtime_chunk_id"] for row in csv.DictReader(path.open(encoding="utf-8", newline=""))}


def compare_signal(signal_a: int, signal_b: int, candidate_a: str, candidate_b: str) -> str:
    if signal_a > signal_b:
        return candidate_a
    if signal_b > signal_a:
        return candidate_b
    return "tie"


def classify_pair(signal_winner: str, baseline_winner: str, gold_winner: str) -> str:
    if signal_winner == "tie":
        return "tie"
    if signal_winner == gold_winner and baseline_winner != gold_winner:
        return "rescue"
    if signal_winner != gold_winner and baseline_winner == gold_winner:
        return "break"
    if signal_winner == gold_winner:
        return "agree"
    return "wrong_no_rescue"


def run_full80() -> dict[str, object]:
    runtime = json.loads(RUNTIME_MANIFEST.read_text(encoding="utf-8"))
    validation = json.loads(RUNTIME_VALIDATION.read_text(encoding="utf-8"))
    if validation["status"] != "pass":
        raise RuntimeError("validated N3C runtime asset is required")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    assert_resume_identity(OUTPUT_DIR, RUN_SPEC)
    candidates = select_candidate_rows(list(csv.DictReader(
        (FIXTURE_DIR / "retained_candidate_rows.csv").open(encoding="utf-8", newline="")
    )))
    if len(candidates) != MAX_CANDIDATE_COUNT:
        raise RuntimeError(f"expected {MAX_CANDIDATE_COUNT} candidates, got {len(candidates)}")
    chunks = select_full_n3c_chunks(runtime["files"])
    logical_groups: dict[str, dict[str, object]] = {}
    for chunk in chunks:
        group_id = str(chunk["logical_group_id"])
        if group_id not in logical_groups:
            logical_groups[group_id] = {
                "logical_group_id": group_id,
                "direction": chunk["direction"],
                "dictionary_cut": chunk["dictionary_cut"],
                "ngram_order": chunk["ngram_order"],
                "phrase_token_length": chunk["phrase_token_length"],
                "length_bucket": length_bucket(int(chunk["phrase_token_length"])),
                "word_token_lengths": chunk["word_token_lengths"],
                "chunk_count": 0,
                "logical_group_phrase_count": 0,
            }
        logical_groups[group_id]["chunk_count"] = int(logical_groups[group_id]["chunk_count"]) + 1
        logical_groups[group_id]["logical_group_phrase_count"] = (
            int(logical_groups[group_id]["logical_group_phrase_count"]) + int(chunk["phrase_count"])
        )

    write_csv(OUTPUT_DIR / "candidate_rows.csv", [
        {
            "trial_id": row["trial_id"], "candidate_id": row["candidate_id"],
            "baseline_score": row["baseline_score"], "candidate_rank": row["candidate_rank"],
            "candidate_stratum": row["candidate_stratum"],
        }
        for row in candidates
    ], ("trial_id", "candidate_id", "baseline_score", "candidate_rank", "candidate_stratum"))
    write_csv(OUTPUT_DIR / "logical_group_summary_rows.csv", list(logical_groups.values()), (
        "logical_group_id", "direction", "dictionary_cut", "ngram_order",
        "phrase_token_length", "length_bucket", "word_token_lengths",
        "chunk_count", "logical_group_phrase_count",
    ))

    chunk_path = OUTPUT_DIR / "chunk_timing_rows.csv"
    done = completed_chunk_ids(chunk_path)
    hit_path = OUTPUT_DIR / "n3c_verified_hit_rows.csv"
    if done and not hit_path.is_file():
        raise RuntimeError("chunk timing exists without hit rows; do not resume ambiguous partial output")

    process = psutil.Process(os.getpid())
    peak_rss = int(getattr(process.memory_info(), "peak_wset", process.memory_info().rss))
    candidate_hits: dict[str, list[dict[str, object]]] = defaultdict(list)
    candidate_hit_counts: dict[str, int] = defaultdict(int)
    candidate_exact_hit_counts: dict[str, int] = defaultdict(int)
    started = time.monotonic()
    processed_this_run = 0

    # Reconstruct global spans if resuming from a partial hit file.
    if done:
        for row in csv.DictReader(hit_path.open(encoding="utf-8", newline="")):
            candidate_id = row["candidate_id"]
            span = (int(row["hit_start"]), int(row["hit_end"]))
            candidate_hits[candidate_id].append({
                "start_offset": span[0],
                "end_offset": span[1],
                "is_exact": row["exact_flag"] == "True",
                "length_bucket": row["length_bucket"],
                "logical_group_id": row["logical_group_id"],
            })
            candidate_hit_counts[candidate_id] += 1
            if row["exact_flag"] == "True":
                candidate_exact_hit_counts[candidate_id] += 1

    with hit_path.open("a", encoding="utf-8", newline="") as hit_handle:
        hit_writer = csv.DictWriter(hit_handle, fieldnames=HIT_FIELDS)
        if not done and hit_path.stat().st_size == 0:
            hit_writer.writeheader()
        for chunk_index, chunk in enumerate(chunks, start=1):
            runtime_chunk_id = str(chunk["path"])
            if runtime_chunk_id in done:
                continue
            chunk_started = time.monotonic()
            with np.load(REPO_ROOT / runtime_chunk_id, allow_pickle=False) as data:
                phrase_rows = data["rune_tokens"]
                phrase_ids = data["phrase_id"]
            index = build_sorted_block_index(phrase_rows)
            word_lengths = tuple(int(value) for value in json.loads(str(chunk["word_token_lengths"])))
            phrase_length = int(chunk["phrase_token_length"])
            chunk_hit_count = 0
            chunk_cluster_count = 0
            proposed_count = 0
            for candidate in candidates:
                candidate_id = candidate["candidate_id"]
                tokens = json.loads(candidate["candidate_token_ids_json"])
                hits, proposed = sorted_block_partition_hit_details(tokens, phrase_rows, word_lengths, index)
                proposed_count += proposed
                chunk_hit_count += len(hits)
                chunk_cluster_count += len(cluster_hit_spans(
                    (start, start + phrase_length) for start, _phrase_index, _word_hds in hits
                ))
                for start, phrase_index, word_hds in sorted(hits):
                    total_hd = sum(word_hds)
                    max_word_hd = max(word_hds) if word_hds else 0
                    exact = total_hd == 0
                    span = (start, start + phrase_length)
                    candidate_hits[candidate_id].append({
                        "start_offset": span[0],
                        "end_offset": span[1],
                        "is_exact": exact,
                        "length_bucket": length_bucket(phrase_length),
                        "logical_group_id": chunk["logical_group_id"],
                    })
                    candidate_hit_counts[candidate_id] += 1
                    if exact:
                        candidate_exact_hit_counts[candidate_id] += 1
                    hit_writer.writerow({
                        "trial_id": candidate["trial_id"],
                        "candidate_id": candidate_id,
                        "candidate_stratum": candidate["candidate_stratum"],
                        "runtime_chunk_id": runtime_chunk_id,
                        "logical_group_id": chunk["logical_group_id"],
                        "length_bucket": length_bucket(phrase_length),
                        "phrase_token_length": phrase_length,
                        "word_token_lengths": chunk["word_token_lengths"],
                        "phrase_id": str(phrase_ids[phrase_index]),
                        "hit_start": start,
                        "hit_end": start + phrase_length,
                        "total_phrase_hd": total_hd,
                        "max_word_hd": max_word_hd,
                        "word_hds": json.dumps(word_hds, separators=(",", ":")),
                        "exact_flag": exact,
                        "full_phrase_verified": True,
                    })
            memory = process.memory_info()
            peak_rss = max(peak_rss, int(getattr(memory, "peak_wset", memory.rss)))
            chunk_seconds = time.monotonic() - chunk_started
            append_csv_row(OUTPUT_DIR / "chunk_timing_rows.csv", {
                "runtime_chunk_id": runtime_chunk_id,
                "logical_group_id": chunk["logical_group_id"],
                "length_bucket": length_bucket(phrase_length),
                "phrase_token_length": phrase_length,
                "word_token_lengths": chunk["word_token_lengths"],
                "runtime_phrase_count": chunk["phrase_count"],
                "candidate_count": len(candidates),
                "lookup_match_count": proposed_count,
                "verified_hit_count": chunk_hit_count,
                "chunk_candidate_cluster_count": chunk_cluster_count,
                "runtime_seconds": chunk_seconds,
                "peak_memory_mb": peak_rss / 1_000_000,
                "status": "complete",
            }, CHUNK_FIELDS)
            processed_this_run += 1
            elapsed = time.monotonic() - started
            completed = len(done) + processed_this_run
            eta = elapsed / processed_this_run * (len(chunks) - completed) if processed_this_run else 0.0
            if processed_this_run == 1 or processed_this_run % PROGRESS_EVERY_CHUNKS == 0 or completed == len(chunks):
                print(
                    f"[{PHASE}] chunks={completed}/{len(chunks)} logical_groups={len(logical_groups)} "
                    f"elapsed_seconds={elapsed:.1f} eta_seconds={eta:.1f} "
                    f"hits_so_far={sum(candidate_hit_counts.values())} peak_rss_mb={peak_rss / 1_000_000:.1f}",
                    flush=True,
                )
            (OUTPUT_DIR / "progress_manifest.json").write_text(json.dumps({
                "status": "running",
                "phase": PHASE,
                "updated_utc": utc_now(),
                "completed_chunk_count": completed,
                "total_chunk_count": len(chunks),
                "logical_group_count": len(logical_groups),
                "hit_count_so_far": sum(candidate_hit_counts.values()),
                "peak_memory_mb_so_far": peak_rss / 1_000_000,
                "production_scoring_change": False,
                "production_ranking_change": False,
                "run_spec_identity": RUN_SPEC.identity,
            }, indent=2) + "\n", encoding="utf-8")

    candidate_summary_rows = []
    for candidate in candidates:
        candidate_id = candidate["candidate_id"]
        clusters = annotated_cluster_hit_rows(candidate_hits[candidate_id])
        exact_containing_cluster_count = sum(1 for row in clusters if row["has_exact"])
        candidate_summary_rows.append({
            "trial_id": candidate["trial_id"],
            "candidate_id": candidate_id,
            "candidate_stratum": candidate["candidate_stratum"],
            "baseline_score": candidate["baseline_score"],
            "verified_hit_count": candidate_hit_counts[candidate_id],
            "exact_hit_count": candidate_exact_hit_counts[candidate_id],
            "global_candidate_n3c_cluster_count": len(clusters),
            "global_candidate_n3c_exact_containing_cluster_count": exact_containing_cluster_count,
            "global_candidate_n3c_cluster_spans_json": json.dumps(
                [(row["start_offset"], row["end_offset"]) for row in clusters], separators=(",", ":")
            ),
        })
    write_csv(OUTPUT_DIR / "candidate_n3c_summary_rows.csv", candidate_summary_rows, tuple(candidate_summary_rows[0]))

    by_candidate = {row["candidate_id"]: row for row in candidate_summary_rows}
    selected_ids = set(by_candidate)
    pair_rows = []
    for pair in csv.DictReader((FIXTURE_DIR / "candidate_pair_rows.csv").open(encoding="utf-8", newline="")):
        if pair["candidate_a_id"] not in selected_ids or pair["candidate_b_id"] not in selected_ids:
            continue
        left = by_candidate[pair["candidate_a_id"]]
        right = by_candidate[pair["candidate_b_id"]]
        hit_winner = compare_signal(
            int(left["verified_hit_count"]), int(right["verified_hit_count"]),
            pair["candidate_a_id"], pair["candidate_b_id"]
        )
        cluster_winner = compare_signal(
            int(left["global_candidate_n3c_cluster_count"]),
            int(right["global_candidate_n3c_cluster_count"]),
            pair["candidate_a_id"],
            pair["candidate_b_id"],
        )
        exact_cluster_winner = compare_signal(
            int(left["global_candidate_n3c_exact_containing_cluster_count"]),
            int(right["global_candidate_n3c_exact_containing_cluster_count"]),
            pair["candidate_a_id"],
            pair["candidate_b_id"],
        )
        pair_rows.append({
            "source_pair_id": pair["pair_id"],
            "trial_id": pair["trial_id"],
            "candidate_a_id": pair["candidate_a_id"],
            "candidate_b_id": pair["candidate_b_id"],
            "baseline_winner_id": pair["baseline_winner_id"],
            "gold_winner_id": pair["gold_winner_id"],
            "baseline_correct": pair["baseline_winner_id"] == pair["gold_winner_id"],
            "can_observe_break": pair["baseline_winner_id"] == pair["gold_winner_id"],
            "can_observe_rescue": pair["baseline_winner_id"] != pair["gold_winner_id"],
            "n3c_hit_winner_id": hit_winner,
            "n3c_verified_hit_count_pair_result": classify_pair(
                hit_winner, pair["baseline_winner_id"], pair["gold_winner_id"]
            ),
            "n3c_global_cluster_winner_id": cluster_winner,
            "n3c_global_cluster_pair_result": classify_pair(
                cluster_winner, pair["baseline_winner_id"], pair["gold_winner_id"]
            ),
            "n3c_exact_containing_global_cluster_winner_id": exact_cluster_winner,
            "n3c_exact_containing_global_cluster_pair_result": classify_pair(
                exact_cluster_winner, pair["baseline_winner_id"], pair["gold_winner_id"]
            ),
            "candidate_a_verified_hit_count": left["verified_hit_count"],
            "candidate_b_verified_hit_count": right["verified_hit_count"],
            "candidate_a_global_clusters": left["global_candidate_n3c_cluster_count"],
            "candidate_b_global_clusters": right["global_candidate_n3c_cluster_count"],
            "candidate_a_exact_containing_global_clusters": left[
                "global_candidate_n3c_exact_containing_cluster_count"
            ],
            "candidate_b_exact_containing_global_clusters": right[
                "global_candidate_n3c_exact_containing_cluster_count"
            ],
        })
    if pair_rows:
        write_csv(OUTPUT_DIR / "pairwise_gold_n3c_report_rows.csv", pair_rows, tuple(pair_rows[0]))

    total_seconds = time.monotonic() - started
    peak_memory_mb = peak_rss / 1_000_000
    status = "full80_n3c_query_complete" if QUERY_IS_FULL_N3C_FOR_SELECTED_80 else "bucket_n3c_query_complete"
    manifest = {
        "status": status,
        "phase": PHASE,
        "run_spec": asdict(RUN_SPEC),
        "run_spec_identity": RUN_SPEC.identity,
        "query_is_complete_for_declared_run_spec": len(done) + processed_this_run == len(chunks),
        "query_scope": QUERY_SCOPE_LABEL,
        "query_is_full_n3c_for_selected_80_candidates": QUERY_IS_FULL_N3C_FOR_SELECTED_80,
        "query_is_full_734_candidate_fixture": False,
        "candidate_count": len(candidates),
        "candidate_selection_mode": CANDIDATE_SELECTION_MODE,
        "candidate_remaining_offset": CANDIDATE_REMAINING_OFFSET,
        "candidate_selection_label": CANDIDATE_SELECTION_LABEL,
        "runtime_chunk_count": len(chunks),
        "logical_group_count": len(logical_groups),
        "runtime_phrase_rows": sum(int(row["phrase_count"]) for row in chunks),
        "verified_hit_count": sum(candidate_hit_counts.values()),
        "global_candidate_n3c_cluster_count": sum(
            int(row["global_candidate_n3c_cluster_count"]) for row in candidate_summary_rows
        ),
        "global_candidate_n3c_exact_containing_cluster_count": sum(
            int(row["global_candidate_n3c_exact_containing_cluster_count"]) for row in candidate_summary_rows
        ),
        "raw_pair_row_count_with_both_candidates_in_sample": len(pair_rows),
        "total_runtime_seconds_this_invocation": total_seconds,
        "peak_memory_mb": peak_memory_mb,
        "max_total_runtime_seconds": MAX_TOTAL_RUNTIME_SECONDS,
        "max_peak_memory_mb": MAX_PEAK_MEMORY_MB,
        "runtime_budget_pass": total_seconds <= MAX_TOTAL_RUNTIME_SECONDS,
        "memory_budget_pass": peak_memory_mb <= MAX_PEAK_MEMORY_MB,
        "runtime_asset_id": runtime["asset_id"],
        "runtime_validation_status": validation["status"],
        "runtime_validation_manifest": RUNTIME_VALIDATION.relative_to(REPO_ROOT).as_posix(),
        "runtime_index_manifest": RUNTIME_MANIFEST.relative_to(REPO_ROOT).as_posix(),
        "hit_record_contract": "phrase_length_word_shape_total_hd_max_word_hd_word_hds_exact_flag",
        "global_clusters_are_candidate_level": True,
        "exact_containing_clusters_are_ordinary_clusters_annotated_with_exact_evidence": True,
        "chunk_clusters_are_diagnostic_only": True,
        "production_scoring_change": False,
        "production_ranking_change": False,
        "score_bearing_use_approved": False,
        "order2_query_authority": "priority_only_never_filter",
    }
    (OUTPUT_DIR / "run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (OUTPUT_DIR / "readout.md").write_text(
        "# Full80 N3C Query Evidence\n\n"
        f"- status: `{manifest['status']}`\n"
        f"- query scope: `{QUERY_SCOPE_LABEL}`\n"
        f"- selected candidates: `{len(candidates)}`\n"
        f"- runtime chunks: `{len(chunks)}`\n"
        f"- logical groups: `{len(logical_groups)}`\n"
        f"- verified hits: `{manifest['verified_hit_count']}`\n"
        f"- global candidate clusters: `{manifest['global_candidate_n3c_cluster_count']}`\n"
        f"- exact-containing global candidate clusters: "
        f"`{manifest['global_candidate_n3c_exact_containing_cluster_count']}`\n"
        f"- raw pair rows with both candidates in sample: `{len(pair_rows)}`\n"
        f"- runtime seconds this invocation: `{total_seconds:.3f}`\n"
        f"- peak memory MB: `{peak_memory_mb:.1f}`\n\n"
        "This is report-only N3C query evidence for the selected 80-candidate fixture sample. "
        "It changes no production score or ranking.\n",
        encoding="utf-8",
    )
    (OUTPUT_DIR / "progress_manifest.json").write_text(json.dumps({
        "status": "complete",
        "phase": PHASE,
        "updated_utc": utc_now(),
        "completed_chunk_count": len(chunks),
        "total_chunk_count": len(chunks),
        "hit_count": manifest["verified_hit_count"],
        "peak_memory_mb": peak_memory_mb,
    }, indent=2) + "\n", encoding="utf-8")
    print(f"[{PHASE}] status={manifest['status']}", flush=True)
    print(
        f"[{PHASE}] chunks={len(chunks)} hits={manifest['verified_hit_count']} "
        f"global_clusters={manifest['global_candidate_n3c_cluster_count']} "
        f"elapsed_seconds={total_seconds:.1f}",
        flush=True,
    )
    return manifest


if __name__ == "__main__":
    run_full80()
