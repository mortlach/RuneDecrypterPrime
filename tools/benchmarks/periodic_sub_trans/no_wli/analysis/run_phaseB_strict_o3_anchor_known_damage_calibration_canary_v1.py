from __future__ import annotations

import csv
import json
import os
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

import numpy as np
import psutil


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
for path in (REPO_ROOT, REPO_ROOT / "src", SCRIPT_PATH.parent):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.damage_models_reference_v1 import (  # noqa: E402
    GLOBAL_SEED,
    empirical_probs,
    make_variant,
    stable_int_seed,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.damage_models_reference_v2 import (  # noqa: E402
    make_target_actual_damage_result,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.phaseB_n3c_query_planning_core_v1 import (  # noqa: E402
    build_sorted_block_index,
    length_bucket,
    sorted_block_partition_hit_details,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.run_phaseB_failed_decryption_n3c_full80_query_evidence_v1 import (  # noqa: E402
    logical_group_id,
    select_chunks_for_run_spec,
    N3CRunSpec,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.run_phaseB_failed_decryption_length_aware_order2_informed_n3c_query_planning_v1 import (  # noqa: E402
    RUNTIME_MANIFEST,
    RUNTIME_VALIDATION,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.runtime_projection_reference_v2 import (  # noqa: E402
    default_stage_projection_rows,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.strict_o3_anchor_reference_v1 import (  # noqa: E402
    HitRow,
    group_hits_by_candidate,
    summarise_candidate,
    write_csv,
)


PHASE = "phaseB_strict_o3_anchor_known_damage_calibration_canary_v2_fix"
OUTPUT_DIR = REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis" / PHASE
TOKENIZED_ROOT = REPO_ROOT / "assets/tokenized_pg"
MAX_CLEAN_CHUNKS = 2
CHUNK_MAX_TOKENS = 500
REPEATS = 1
DAMAGE_LEVELS = (0.30, 0.50)
DAMAGE_TOLERANCE = 0.01
DAMAGE_MODELS = (
    "independent_substitution",
    "frequency_matched_global",
    "frequency_matched_book",
    "word_local_substitution",
    "burst_substitution",
    "lane_period_substitution",
)
NULL_MODELS = (
    "uniform_random",
    "global_frequency_random",
    "within_chunk_shuffle",
    "block_shuffle_10",
    "block_shuffle_25",
    "block_shuffle_50",
)
RUN_SPEC = N3CRunSpec(
    run_family="strict_o3_anchor_known_damage_calibration_canary",
    schema_version="n3c_run_spec_v1",
    direction="fwd",
    ngram_order=3,
    dictionary_cut="strict",
    minimum_phrase_length=10,
    length_bucket=None,
    candidate_scope="2_runeberg_fwd_chunks_19_samples_each_target_actual_damage",
    query_contract="total_hd_le_2_max_word_hd_le_1_word_structured",
)
LENSES = (
    {"lens_name": "HD0_L10", "max_hd": 0, "min_phrase_length": 10},
    {"lens_name": "HD0_L12", "max_hd": 0, "min_phrase_length": 12},
    {"lens_name": "HDle1_L12", "max_hd": 1, "min_phrase_length": 12},
    {"lens_name": "HDle2_L15", "max_hd": 2, "min_phrase_length": 15},
)
MAX_WALLCLOCK_SECONDS = 10_800.0
PROGRESS_EVERY_RUNTIME_CHUNKS = 10
EXCLUDE_BOOKS = {"1-0.txt", "10004.txt"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def repo_relative(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def source_word_chunks_for_wli(wli: Sequence[Sequence[int]], *, max_tokens: int) -> list[tuple[int, int]]:
    wli_array = np.asarray(wli, dtype=np.int64)
    positions = wli_array[:, 0]
    lengths = wli_array[:, 1]
    starts = np.flatnonzero((positions == 0) & (lengths > 0)).astype(np.int64).tolist()
    chunks: list[tuple[int, int]] = []
    start_idx = 0
    n = int(wli_array.shape[0])
    while start_idx < len(starts):
        start = starts[start_idx]
        best_end = start
        cursor_idx = start_idx
        while cursor_idx < len(starts):
            cursor = starts[cursor_idx]
            if cursor != best_end:
                break
            word_len = int(lengths[cursor])
            end = cursor + word_len
            if word_len <= 0 or end > n or (end - start) > max_tokens:
                break
            best_end = end
            cursor_idx += 1
        if best_end > start:
            chunks.append((start, best_end))
            while start_idx < len(starts) and starts[start_idx] < best_end:
                start_idx += 1
        else:
            start_idx += 1
    return chunks


def load_clean_chunks() -> list[dict[str, object]]:
    chunks: list[dict[str, object]] = []
    for path in sorted(TOKENIZED_ROOT.glob("*_fwd.npz")):
        book = path.name.removesuffix("_fwd.npz")
        if book in EXCLUDE_BOOKS:
            continue
        with np.load(path, allow_pickle=False) as data:
            tokens = np.asarray(data["pt_nose_data"], dtype=np.uint8)
            wli = np.asarray(data["wli_nose_data"], dtype=np.uint8).reshape(-1, 2)
        for chunk_index, (start, end) in enumerate(source_word_chunks_for_wli(wli, max_tokens=CHUNK_MAX_TOKENS)):
            chunks.append(
                {
                    "chunk_id": f"{book}|fwd|chunk_{chunk_index:06d}|{start}_{end}",
                    "book": book,
                    "direction": "fwd",
                    "source_path": repo_relative(path),
                    "chunk_index": chunk_index,
                    "chunk_start": start,
                    "chunk_end": end,
                    "tokens": tuple(int(x) for x in tokens[start:end]),
                    "wli": tuple((int(a), int(b)) for a, b in wli[start:end]),
                }
            )
            if len(chunks) >= MAX_CLEAN_CHUNKS:
                return chunks
    return chunks


def changed_fraction(clean: Sequence[int], variant: Sequence[int]) -> float:
    return sum(1 for left, right in zip(clean, variant) if int(left) != int(right)) / float(len(clean))


def control_source_kind(model_name: str) -> str:
    if model_name.startswith("block_shuffle_"):
        return "hard_local_order_control"
    return "ordinary_null"


def assert_damage_contract(
    *,
    sample_id: str,
    model_name: str,
    requested_damage_level: float,
    actual_changed_fraction: float,
) -> None:
    delta = abs(float(actual_changed_fraction) - float(requested_damage_level))
    if delta > DAMAGE_TOLERANCE:
        raise RuntimeError(
            f"target-actual damage contract failed for {sample_id}: "
            f"model={model_name} requested={requested_damage_level:.4f} "
            f"actual={actual_changed_fraction:.4f} tolerance={DAMAGE_TOLERANCE:.4f}"
        )


def build_samples(clean_chunks: list[dict[str, object]]) -> list[dict[str, object]]:
    all_tokens = [token for chunk in clean_chunks for token in chunk["tokens"]]
    global_probs = empirical_probs(all_tokens)
    samples: list[dict[str, object]] = []
    for clean_index, chunk in enumerate(clean_chunks):
        clean_tokens = tuple(int(x) for x in chunk["tokens"])
        book_probs = empirical_probs(clean_tokens)
        variants: list[dict[str, object]] = [
            {
                "source_kind": "clean",
                "model_name": "none",
                "requested_damage_level": "",
                "repeat_index": 0,
                "tokens": clean_tokens,
                "seed": stable_int_seed(GLOBAL_SEED, chunk["chunk_id"], "clean"),
                "control_family": "",
                "legacy_model": False,
                "damage_shape": "",
                "damage_shape_metadata": "",
            }
        ]
        for repeat in range(REPEATS):
            for level in DAMAGE_LEVELS:
                for model in DAMAGE_MODELS:
                    seed = stable_int_seed(GLOBAL_SEED, chunk["chunk_id"], model, f"{level:.2f}", repeat)
                    damage_result = make_target_actual_damage_result(
                        clean_tokens,
                        model_name=model,
                        damage_level=level,
                        seed=seed,
                        wli=chunk["wli"],
                        global_probs=global_probs,
                        book_probs=book_probs,
                        tolerance=DAMAGE_TOLERANCE,
                    )
                    variants.append(
                        {
                            "source_kind": "damaged",
                            "model_name": model,
                            "requested_damage_level": f"{level:.2f}",
                            "repeat_index": repeat,
                            "tokens": damage_result.tokens,
                            "seed": seed,
                            "control_family": "",
                            "legacy_model": False,
                            "damage_shape": str(damage_result.metadata.get("shape", "")),
                            "damage_shape_metadata": json.dumps(damage_result.metadata, sort_keys=True),
                        }
                    )
            for model in NULL_MODELS:
                seed = stable_int_seed(GLOBAL_SEED, chunk["chunk_id"], model, repeat)
                tokens = make_variant(
                    clean_tokens,
                    model_name=model,
                    damage_level=None,
                    seed=seed,
                    wli=chunk["wli"],
                    global_probs=global_probs,
                    book_probs=book_probs,
                )
                variants.append(
                    {
                        "source_kind": control_source_kind(model),
                        "model_name": model,
                        "requested_damage_level": "",
                        "repeat_index": repeat,
                        "tokens": tokens,
                        "seed": seed,
                        "control_family": control_source_kind(model),
                        "legacy_model": False,
                        "damage_shape": "",
                        "damage_shape_metadata": "",
                    }
                )
        for variant_index, variant in enumerate(variants):
            kind = str(variant["source_kind"])
            model = str(variant["model_name"])
            level = str(variant["requested_damage_level"])
            repeat = int(variant["repeat_index"])
            tokens = tuple(int(x) for x in variant["tokens"])
            actual_changed = changed_fraction(clean_tokens, tokens)
            sample_id = f"canary_c{clean_index:02d}_v{variant_index:02d}_{kind}_{model}_{level or 'na'}_r{repeat}"
            if kind == "damaged":
                assert_damage_contract(
                    sample_id=sample_id,
                    model_name=model,
                    requested_damage_level=float(level),
                    actual_changed_fraction=actual_changed,
                )
            samples.append(
                {
                    "sample_id": sample_id,
                    "chunk_id": chunk["chunk_id"],
                    "book": chunk["book"],
                    "direction": "fwd",
                    "source_kind": kind,
                    "model_name": model,
                    "requested_damage_level": level,
                    "actual_changed_fraction": actual_changed,
                    "damage_contract_status": "pass" if kind == "damaged" else "not_applicable",
                    "control_family": variant["control_family"],
                    "legacy_model": variant["legacy_model"],
                    "damage_shape": variant.get("damage_shape", ""),
                    "damage_shape_metadata": variant.get("damage_shape_metadata", ""),
                    "repeat_index": repeat,
                    "seed": variant["seed"],
                    "token_count": len(tokens),
                    "tokens": tokens,
                }
            )
    return samples


def select_runtime_chunks() -> list[dict[str, object]]:
    runtime = json.loads(RUNTIME_MANIFEST.read_text(encoding="utf-8"))
    validation = json.loads(RUNTIME_VALIDATION.read_text(encoding="utf-8"))
    if validation["status"] != "pass":
        raise RuntimeError("validated strict O3 runtime asset is required")
    return select_chunks_for_run_spec(runtime["files"], RUN_SPEC)


def write_sample_manifest(samples: list[dict[str, object]], clean_chunks: list[dict[str, object]]) -> None:
    sample_fields = (
        "sample_id",
        "chunk_id",
        "book",
        "direction",
        "source_kind",
        "model_name",
        "requested_damage_level",
        "actual_changed_fraction",
        "damage_contract_status",
        "control_family",
        "legacy_model",
        "damage_shape",
        "damage_shape_metadata",
        "repeat_index",
        "seed",
        "token_count",
    )
    write_csv(OUTPUT_DIR / "calibration_sample_rows.csv", samples, sample_fields)
    chunk_fields = (
        "chunk_id",
        "book",
        "direction",
        "source_path",
        "chunk_index",
        "chunk_start",
        "chunk_end",
    )
    write_csv(OUTPUT_DIR / "calibration_clean_chunk_rows.csv", clean_chunks, chunk_fields)


def append_csv_row(path: Path, row: dict[str, object], fields: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def numeric_stats(values: Sequence[float], *, prefix: str) -> dict[str, object]:
    if not values:
        return {
            f"{prefix}_mean": 0.0,
            f"{prefix}_stddev": 0.0,
            f"{prefix}_stderr": 0.0,
            f"{prefix}_ci95": 0.0,
            f"{prefix}_median": 0.0,
            f"{prefix}_p10": 0.0,
            f"{prefix}_p90": 0.0,
            f"{prefix}_min": 0.0,
            f"{prefix}_max": 0.0,
        }
    arr = np.asarray(values, dtype=np.float64)
    stddev = float(np.std(arr, ddof=1)) if arr.size > 1 else 0.0
    stderr = stddev / float(np.sqrt(arr.size)) if arr.size > 1 else 0.0
    return {
        f"{prefix}_mean": float(np.mean(arr)),
        f"{prefix}_stddev": stddev,
        f"{prefix}_stderr": stderr,
        f"{prefix}_ci95": 1.96 * stderr,
        f"{prefix}_median": float(np.median(arr)),
        f"{prefix}_p10": float(np.percentile(arr, 10)),
        f"{prefix}_p90": float(np.percentile(arr, 90)),
        f"{prefix}_min": float(np.min(arr)),
        f"{prefix}_max": float(np.max(arr)),
    }


def summarise_hits(samples: list[dict[str, object]], hit_rows_by_sample: dict[str, list[HitRow]]) -> None:
    summary_rows: list[dict[str, object]] = []
    region_rows: list[dict[str, object]] = []
    sample_by_id = {str(sample["sample_id"]): sample for sample in samples}
    for sample_id, hits in sorted(hit_rows_by_sample.items()):
        sample = sample_by_id[sample_id]
        grouped = group_hits_by_candidate(hits)
        for lens in LENSES:
            candidate_hits = grouped.get((str(sample["chunk_id"]), sample_id), [])
            summary, regions = summarise_candidate(
                candidate_hits,
                candidate_id=sample_id,
                trial_id=str(sample["chunk_id"]),
                min_phrase_length=int(lens["min_phrase_length"]),
                max_hd=int(lens["max_hd"]),
            )
            summary_rows.append(
                {
                    "lens_name": lens["lens_name"],
                    "source_kind": sample["source_kind"],
                    "model_name": sample["model_name"],
                    "requested_damage_level": sample["requested_damage_level"],
                    "actual_changed_fraction": sample["actual_changed_fraction"],
                    "damage_contract_status": sample["damage_contract_status"],
                    "control_family": sample["control_family"],
                    "legacy_model": sample["legacy_model"],
                    **asdict(summary),
                }
            )
            for index, region in enumerate(regions):
                region_rows.append(
                    {
                        "lens_name": lens["lens_name"],
                        "source_kind": sample["source_kind"],
                        "model_name": sample["model_name"],
                        "requested_damage_level": sample["requested_damage_level"],
                        "actual_changed_fraction": sample["actual_changed_fraction"],
                        "control_family": sample["control_family"],
                        "region_index": index,
                        **asdict(region),
                    }
                )
    write_csv(
        OUTPUT_DIR / "known_damage_anchor_summary_rows.csv",
        summary_rows,
        (
            "lens_name",
            "source_kind",
            "model_name",
            "requested_damage_level",
            "actual_changed_fraction",
            "damage_contract_status",
            "control_family",
            "legacy_model",
            "candidate_id",
            "trial_id",
            "selected_region_count",
            "selected_weight_sum",
            "selected_coverage_tokens",
            "longest_selected_phrase_len",
            "longest_hd0_phrase_len",
            "longest_hd1_phrase_len",
            "longest_hd2_phrase_len",
            "min_hd_at_len_ge_10",
            "min_hd_at_len_ge_12",
            "min_hd_at_len_ge_15",
            "min_hd_at_len_ge_18",
            "min_hd_at_len_ge_20",
            "rarest_hd0_count_len_ge_10",
            "rarest_hd0_count_len_ge_12",
        ),
    )
    write_csv(
        OUTPUT_DIR / "known_damage_anchor_region_rows.csv",
        region_rows,
        (
            "lens_name",
            "source_kind",
            "model_name",
            "requested_damage_level",
            "actual_changed_fraction",
            "control_family",
            "region_index",
            "candidate_id",
            "trial_id",
            "start",
            "end",
            "hd",
            "phrase_length",
            "weight",
            "phrase_row_id",
            "word_shape_id",
            "o4_confirmed",
        ),
    )

    group_rows: list[dict[str, object]] = []
    groups: dict[tuple[str, str, str, str, str], list[dict[str, object]]] = {}
    for row in summary_rows:
        groups.setdefault(
            (
                str(row["lens_name"]),
                str(row["source_kind"]),
                str(row["model_name"]),
                str(row["requested_damage_level"]),
                str(row["control_family"]),
            ),
            [],
        ).append(row)
    for (lens_name, source_kind, model_name, requested_damage_level, control_family), rows in sorted(groups.items()):
        scores = [float(row["selected_weight_sum"]) for row in rows]
        changed = [float(row["actual_changed_fraction"]) for row in rows]
        longest = [int(row["longest_selected_phrase_len"]) for row in rows]
        group_rows.append(
            {
                "lens_name": lens_name,
                "source_kind": source_kind,
                "model_name": model_name,
                "requested_damage_level": requested_damage_level,
                "control_family": control_family,
                "row_count": len(rows),
                "nonzero_selected_region_count": sum(1 for row in rows if int(row["selected_region_count"]) > 0),
                **numeric_stats(scores, prefix="selected_weight_sum"),
                **numeric_stats([float(value) for value in longest], prefix="longest_selected_phrase_len"),
                **numeric_stats(changed, prefix="actual_changed_fraction"),
            }
        )
    write_csv(
        OUTPUT_DIR / "known_damage_vs_null_summary_rows.csv",
        group_rows,
        (
            "lens_name",
            "source_kind",
            "model_name",
            "requested_damage_level",
            "control_family",
            "row_count",
            "nonzero_selected_region_count",
            "selected_weight_sum_mean",
            "selected_weight_sum_stddev",
            "selected_weight_sum_stderr",
            "selected_weight_sum_ci95",
            "selected_weight_sum_median",
            "selected_weight_sum_p10",
            "selected_weight_sum_p90",
            "selected_weight_sum_min",
            "selected_weight_sum_max",
            "longest_selected_phrase_len_mean",
            "longest_selected_phrase_len_stddev",
            "longest_selected_phrase_len_stderr",
            "longest_selected_phrase_len_ci95",
            "longest_selected_phrase_len_median",
            "longest_selected_phrase_len_p10",
            "longest_selected_phrase_len_p90",
            "longest_selected_phrase_len_min",
            "longest_selected_phrase_len_max",
            "actual_changed_fraction_mean",
            "actual_changed_fraction_stddev",
            "actual_changed_fraction_stderr",
            "actual_changed_fraction_ci95",
            "actual_changed_fraction_median",
            "actual_changed_fraction_p10",
            "actual_changed_fraction_p90",
            "actual_changed_fraction_min",
            "actual_changed_fraction_max",
        ),
    )


def write_runtime_projection_rows(*, elapsed_seconds: float, sample_count: int) -> list[dict[str, object]]:
    rows = default_stage_projection_rows(
        observed_elapsed_seconds=elapsed_seconds,
        observed_samples=sample_count,
    )
    write_csv(
        OUTPUT_DIR / "known_damage_runtime_projection_rows.csv",
        rows,
        (
            "stage_name",
            "clean_chunks",
            "samples_per_chunk",
            "total_samples",
            "seconds_per_sample",
            "projected_seconds",
            "projected_hours",
            "projected_days",
        ),
    )
    return rows


def run_canary() -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    process = psutil.Process(os.getpid())
    print(f"[{PHASE}] started_utc={utc_now()}", flush=True)
    clean_chunks = load_clean_chunks()
    if len(clean_chunks) != MAX_CLEAN_CHUNKS:
        raise RuntimeError(f"expected {MAX_CLEAN_CHUNKS} clean chunks, got {len(clean_chunks)}")
    samples = build_samples(clean_chunks)
    write_sample_manifest(samples, clean_chunks)
    runtime_chunks = select_runtime_chunks()
    print(
        f"[{PHASE}] clean_chunks={len(clean_chunks)} samples={len(samples)} "
        f"runtime_chunks={len(runtime_chunks)} wallclock_budget_seconds={MAX_WALLCLOCK_SECONDS}",
        flush=True,
    )

    chunk_fields = (
        "runtime_chunk_id",
        "direction",
        "run_spec_direction",
        "logical_group_id",
        "length_bucket",
        "phrase_token_length",
        "word_token_lengths",
        "runtime_phrase_count",
        "sample_count",
        "lookup_match_count",
        "verified_hit_count",
        "runtime_seconds",
        "peak_memory_mb",
        "status",
    )
    hit_rows_by_sample: dict[str, list[HitRow]] = {str(sample["sample_id"]): [] for sample in samples}
    total_hits = 0
    completed_runtime_chunks = 0
    stopped_by_budget = False
    peak_rss = int(getattr(process.memory_info(), "peak_wset", process.memory_info().rss))

    for runtime_index, runtime_chunk in enumerate(runtime_chunks, start=1):
        elapsed = time.monotonic() - started
        if elapsed >= MAX_WALLCLOCK_SECONDS:
            stopped_by_budget = True
            break
        chunk_started = time.monotonic()
        runtime_chunk_id = str(runtime_chunk["path"])
        with np.load(REPO_ROOT / runtime_chunk_id, allow_pickle=False) as data:
            phrase_rows = data["rune_tokens"]
            phrase_ids = data["phrase_id"]
        index = build_sorted_block_index(phrase_rows)
        word_lengths = tuple(int(value) for value in json.loads(str(runtime_chunk["word_token_lengths"])))
        phrase_length = int(runtime_chunk["phrase_token_length"])
        chunk_hits = 0
        proposed_count = 0
        for sample in samples:
            hits, proposed = sorted_block_partition_hit_details(sample["tokens"], phrase_rows, word_lengths, index)
            proposed_count += proposed
            chunk_hits += len(hits)
            total_hits += len(hits)
            sample_id = str(sample["sample_id"])
            for start, phrase_index, word_hds in hits:
                total_hd = sum(word_hds)
                hit_rows_by_sample[sample_id].append(
                    HitRow(
                        candidate_id=sample_id,
                        trial_id=str(sample["chunk_id"]),
                        direction="fwd",
                        hd=total_hd,
                        phrase_length=phrase_length,
                        start=start,
                        end=start + phrase_length,
                        phrase_row_id=str(phrase_ids[phrase_index]),
                        word_shape_id=str(runtime_chunk["word_token_lengths"]),
                    )
                )
        memory = process.memory_info()
        peak_rss = max(peak_rss, int(getattr(memory, "peak_wset", memory.rss)))
        completed_runtime_chunks += 1
        append_csv_row(
            OUTPUT_DIR / "known_damage_runtime_chunk_rows.csv",
            {
                "runtime_chunk_id": runtime_chunk_id,
                "direction": str(runtime_chunk.get("direction", RUN_SPEC.direction)),
                "run_spec_direction": RUN_SPEC.direction,
                "logical_group_id": logical_group_id(runtime_chunk),
                "length_bucket": length_bucket(phrase_length),
                "phrase_token_length": phrase_length,
                "word_token_lengths": runtime_chunk["word_token_lengths"],
                "runtime_phrase_count": runtime_chunk["phrase_count"],
                "sample_count": len(samples),
                "lookup_match_count": proposed_count,
                "verified_hit_count": chunk_hits,
                "runtime_seconds": time.monotonic() - chunk_started,
                "peak_memory_mb": peak_rss / 1_000_000,
                "status": "complete",
            },
            chunk_fields,
        )
        elapsed = time.monotonic() - started
        eta = elapsed / completed_runtime_chunks * (len(runtime_chunks) - completed_runtime_chunks)
        if completed_runtime_chunks == 1 or completed_runtime_chunks % PROGRESS_EVERY_RUNTIME_CHUNKS == 0:
            print(
                f"[{PHASE}] runtime_chunks={completed_runtime_chunks}/{len(runtime_chunks)} "
                f"samples={len(samples)} hits={total_hits} elapsed_seconds={elapsed:.1f} "
                f"eta_seconds={eta:.1f} peak_rss_mb={peak_rss / 1_000_000:.1f}",
                flush=True,
            )
        (OUTPUT_DIR / "progress_manifest.json").write_text(
            json.dumps(
                {
                    "status": "running",
                    "updated_utc": utc_now(),
                    "completed_runtime_chunks": completed_runtime_chunks,
                    "total_runtime_chunks": len(runtime_chunks),
                    "sample_count": len(samples),
                    "hit_count_so_far": total_hits,
                    "elapsed_seconds": elapsed,
                    "eta_seconds": eta,
                    "peak_memory_mb": peak_rss / 1_000_000,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    summarise_hits(samples, hit_rows_by_sample)
    elapsed = time.monotonic() - started
    runtime_projection_rows = write_runtime_projection_rows(elapsed_seconds=elapsed, sample_count=len(samples))
    status = "budget_reached_partial" if stopped_by_budget else "known_damage_canary_complete"
    manifest = {
        "status": status,
        "phase": PHASE,
        "finished_utc": utc_now(),
        "clean_chunk_count": len(clean_chunks),
        "sample_count": len(samples),
        "samples_per_clean_chunk": len(samples) // len(clean_chunks),
        "runtime_chunk_count": len(runtime_chunks),
        "completed_runtime_chunk_count": completed_runtime_chunks,
        "hit_count": total_hits,
        "elapsed_seconds": elapsed,
        "wallclock_budget_seconds": MAX_WALLCLOCK_SECONDS,
        "peak_memory_mb": peak_rss / 1_000_000,
        "run_spec": RUN_SPEC.__dict__,
        "damage_levels": list(DAMAGE_LEVELS),
        "damage_tolerance": DAMAGE_TOLERANCE,
        "damage_generation_contract": "target_actual_changed_fraction",
        "structured_damage_shape_contract": "preserve_model_shape_and_requested_global_changed_fraction",
        "legacy_nominal_damage_models_not_used_for_damaged_samples": True,
        "damage_models": list(DAMAGE_MODELS),
        "null_models": list(NULL_MODELS),
        "ordinary_null_models": [model for model in NULL_MODELS if not model.startswith("block_shuffle_")],
        "hard_local_order_control_models": [model for model in NULL_MODELS if model.startswith("block_shuffle_")],
        "lens_names": [str(lens["lens_name"]) for lens in LENSES],
        "phrase_rarity_weighting_active": False,
        "phrase_count_populated_in_generated_hit_rows": False,
        "rarity_weighting_note": "Generated HitRow records do not populate phrase_count, so rarity defaults to neutral.",
        "runtime_projection_rows": runtime_projection_rows,
        "repeats": REPEATS,
        "report_only": True,
        "require_fwd_only": True,
        "production_scoring_change": False,
        "production_ranking_change": False,
        "score_bearing_use_approved": False,
    }
    (OUTPUT_DIR / "known_damage_calibration_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"[{PHASE}] status={status}", flush=True)
    print(f"[{PHASE}] output_dir={repo_relative(OUTPUT_DIR)}", flush=True)
    print(f"[{PHASE}] elapsed_seconds={elapsed:.1f} hits={total_hits}", flush=True)
    return manifest


def main() -> int:
    run_canary()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
