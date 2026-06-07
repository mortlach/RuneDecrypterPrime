from __future__ import annotations

import csv
import json
import os
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import psutil


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
for path in (REPO_ROOT, REPO_ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.common.phaseB_common_resume_runner_v1 import (  # noqa: E402
    config_hash,
    write_csv,
    write_json_atomic,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.common.phaseB_damage_levels_contract_v1 import (  # noqa: E402
    null_class as null_class_for_model,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.common.phaseB_joint_rule_grid_reference_v1 import (  # noqa: E402
    classify_phrase_confidence,
    rule_flags,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.damage_models_reference_v2 import (  # noqa: E402
    GLOBAL_SEED,
    changed_fraction,
    empirical_probs,
    make_null_or_control_variant,
    make_target_actual_damage_result,
    stable_int_seed,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.phaseB_n3c_query_planning_core_v1 import (  # noqa: E402
    build_sorted_block_index,
    sorted_block_partition_hit_details,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.phaseB_strict_o4_fwd_bridge_reference_v1 import (  # noqa: E402
    hamming_hits_for_group as o4_hamming_hits_for_group,
    load_runtime_npz as load_o4_runtime_npz,
    load_strict_o4_runtime_groups,
    summarise_hits as summarise_o4_hits,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.run_phaseB_failed_decryption_length_aware_order2_informed_n3c_query_planning_v1 import (  # noqa: E402
    RUNTIME_MANIFEST as O3_RUNTIME_MANIFEST,
    RUNTIME_VALIDATION as O3_RUNTIME_VALIDATION,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.run_phaseB_failed_decryption_n3c_full80_query_evidence_v1 import (  # noqa: E402
    N3CRunSpec,
    select_chunks_for_run_spec,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.run_phaseB_strict_o3_anchor_known_damage_calibration_canary_v1 import (  # noqa: E402
    source_word_chunks_for_wli,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.runtime_projection_reference_v2 import (  # noqa: E402
    project_runtime,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.strict_o3_anchor_reference_v1 import (  # noqa: E402
    HitRow,
    group_hits_by_candidate,
    summarise_candidate,
)


RUN_LABEL = "phaseB_strict_o3_o4_fwd_initial_joint_diagnostic_v1"
RUN_MODE = "bounded_8h_8_clean_chunks"  # "smoke_1_clean_chunk" or "bounded_8h_8_clean_chunks"
OUTPUT_DIR = REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis" / RUN_LABEL
TOKENIZED_ROOT = REPO_ROOT / "assets/tokenized_pg"
O4_RUNTIME_MANIFEST = (
    REPO_ROOT
    / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    / "phaseB_ngram_hamming_order4_fwd_nose_fast_runtime_lookup_index_v1/runtime_index_manifest.json"
)

REPORT_ONLY = True
PRODUCTION_SCORER_CHANGE = False
REQUIRE_FWD_ONLY = True
FORCE_RESTART = True
CHUNK_MAX_TOKENS = 500
EXCLUDE_BOOKS = {"1-0.txt", "10004.txt"}
MAX_TOTAL_PHRASE_HD = 2
O3_MIN_PHRASE_LENGTH = 10
O4_MIN_PHRASE_LENGTH = 10

MODE_LIMITS: dict[str, dict[str, Any]] = {
    "smoke_1_clean_chunk": {
        "clean_chunks": 1,
        "damage_levels": (0.30,),
        "damage_repeats_per_chunk": 1,
        "damage_models": (
            "independent_substitution",
            "frequency_matched_global",
            "frequency_matched_book",
            "word_local_substitution",
            "burst_substitution",
            "lane_period_substitution",
        ),
        "null_models": (
            "uniform_random",
            "global_frequency_random",
            "within_chunk_shuffle",
            "block_shuffle_10",
            "block_shuffle_25",
            "block_shuffle_50",
        ),
        "o3_runtime_groups": 8,
        "o4_runtime_groups": 8,
        "o4_max_phrase_rows_per_group": 2_000,
        "intended_wallclock_seconds": 1_800,
    },
    "bounded_8h_8_clean_chunks": {
        "clean_chunks": 8,
        "damage_levels": (0.10, 0.20, 0.30, 0.40, 0.50),
        "damage_repeats_per_chunk": 1,
        "damage_models": (
            "independent_substitution",
            "frequency_matched_global",
            "frequency_matched_book",
            "word_local_substitution",
            "burst_substitution",
            "lane_period_substitution",
        ),
        "null_models": (
            "uniform_random",
            "global_frequency_random",
            "within_chunk_shuffle",
            "block_shuffle_10",
            "block_shuffle_25",
            "block_shuffle_50",
        ),
        "o3_runtime_groups": 774,
        "o4_runtime_groups": 250,
        "o4_max_phrase_rows_per_group": 25_000,
        "intended_wallclock_seconds": 28_800,
    },
}

O3_RUN_SPEC = N3CRunSpec(
    run_family="strict_o3_o4_joint_diagnostic",
    schema_version="n3c_run_spec_v1",
    direction="fwd",
    ngram_order=3,
    dictionary_cut="strict",
    minimum_phrase_length=10,
    length_bucket=None,
    candidate_scope="shared_clean_fwd_chunks",
    query_contract="total_hd_le_2_max_word_hd_le_1_word_structured",
)

O3_LENSES = (
    {"lens_name": "HD0_L10", "max_hd": 0, "min_phrase_length": 10},
    {"lens_name": "HD0_L12", "max_hd": 0, "min_phrase_length": 12},
    {"lens_name": "HDle1_L12", "max_hd": 1, "min_phrase_length": 12},
    {"lens_name": "HDle2_L15", "max_hd": 2, "min_phrase_length": 15},
)

COMMON_FIELDS = (
    "config_hash",
    "direction",
    "order",
    "dictionary_cut",
    "chunk_id",
    "sample_id",
    "source_kind",
    "model_name",
    "damage_level",
    "repeat_index",
    "changed_fraction",
    "null_class",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def repo_rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def append_csv(path: Path, row: Mapping[str, Any], fields: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), extrasaction="ignore")
        if not exists:
            writer.writeheader()
        writer.writerow(dict(row))


def load_clean_chunks(limit: int) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
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
                    "chunk_index": chunk_index,
                    "chunk_start": start,
                    "chunk_end": end,
                    "tokens": tuple(int(x) for x in tokens[start:end]),
                    "wli": tuple((int(a), int(b)) for a, b in wli[start:end]),
                }
            )
            if len(chunks) >= limit:
                return chunks
    return chunks


def control_source_kind(model_name: str) -> str:
    return "hard_local_order_control" if model_name.startswith("block_shuffle_") else "ordinary_null"


def build_samples(chunks: list[dict[str, Any]], limits: Mapping[str, Any], current_hash: str) -> list[dict[str, Any]]:
    all_tokens = [token for chunk in chunks for token in chunk["tokens"]]
    global_probs = empirical_probs(all_tokens)
    rows: list[dict[str, Any]] = []
    for chunk in chunks:
        clean_tokens = tuple(int(x) for x in chunk["tokens"])
        base = {
            "config_hash": current_hash,
            "direction": "fwd",
            "order": "o3_o4",
            "dictionary_cut": "strict",
            "chunk_id": chunk["chunk_id"],
            "book": chunk["book"],
            "token_count": len(clean_tokens),
            "repeat_index": 0,
            "seed": stable_int_seed(GLOBAL_SEED, chunk["chunk_id"], "clean"),
        }
        rows.append(
            {
                **base,
                "sample_id": f"{chunk['chunk_id']}|clean|none||r0",
                "source_kind": "clean",
                "model_name": "none",
                "damage_level": "",
                "changed_fraction": 0.0,
                "null_class": "not_null",
                "tokens": clean_tokens,
            }
        )
        book_probs = empirical_probs(clean_tokens)
        for repeat in range(int(limits["damage_repeats_per_chunk"])):
            for level in limits["damage_levels"]:
                level_text = f"{float(level):.2f}"
                for model in limits["damage_models"]:
                    seed = stable_int_seed(GLOBAL_SEED, chunk["chunk_id"], model, level_text, repeat)
                    result = make_target_actual_damage_result(
                        clean_tokens,
                        model_name=str(model),
                        damage_level=float(level),
                        seed=seed,
                        wli=chunk["wli"],
                        global_probs=global_probs,
                        book_probs=book_probs,
                        tolerance=0.01,
                    )
                    rows.append(
                        {
                            **base,
                            "sample_id": f"{chunk['chunk_id']}|damaged|{model}|{level_text}|r{repeat}",
                            "source_kind": "damaged",
                            "model_name": str(model),
                            "damage_level": level_text,
                            "repeat_index": repeat,
                            "seed": seed,
                            "changed_fraction": result.actual_changed_fraction,
                            "null_class": "not_null",
                            "damage_contract_status": "pass",
                            "damage_shape": str(result.metadata.get("shape", "")),
                            "tokens": result.tokens,
                        }
                    )
            for model in limits["null_models"]:
                seed = stable_int_seed(GLOBAL_SEED, chunk["chunk_id"], model, repeat)
                tokens = make_null_or_control_variant(clean_tokens, model_name=str(model), seed=seed, global_probs=global_probs)
                rows.append(
                    {
                        **base,
                        "sample_id": f"{chunk['chunk_id']}|{control_source_kind(str(model))}|{model}||r{repeat}",
                        "source_kind": control_source_kind(str(model)),
                        "model_name": str(model),
                        "damage_level": "",
                        "repeat_index": repeat,
                        "seed": seed,
                        "changed_fraction": changed_fraction(clean_tokens, tokens),
                        "null_class": null_class_for_model(str(model)),
                        "damage_contract_status": "not_applicable",
                        "damage_shape": "",
                        "tokens": tokens,
                    }
                )
    return rows


def select_o3_groups(limit: int) -> list[dict[str, Any]]:
    validation = json.loads(O3_RUNTIME_VALIDATION.read_text(encoding="utf-8"))
    if validation.get("status") != "pass":
        raise RuntimeError("validated strict O3 runtime asset is required")
    runtime = json.loads(O3_RUNTIME_MANIFEST.read_text(encoding="utf-8"))
    groups = select_chunks_for_run_spec(runtime["files"], O3_RUN_SPEC)
    return groups[: int(limit)]


def run_o3(samples: list[dict[str, Any]], groups: list[dict[str, Any]], current_hash: str, started: float) -> list[dict[str, Any]]:
    hit_rows_by_sample: dict[str, list[HitRow]] = {str(sample["sample_id"]): [] for sample in samples}
    for group_index, group in enumerate(groups, start=1):
        with np.load(REPO_ROOT / str(group["path"]), allow_pickle=False) as data:
            phrase_rows = data["rune_tokens"]
            phrase_ids = data["phrase_id"]
        index = build_sorted_block_index(phrase_rows)
        word_lengths = tuple(int(value) for value in json.loads(str(group["word_token_lengths"])))
        phrase_length = int(group["phrase_token_length"])
        for sample in samples:
            hits, _proposed = sorted_block_partition_hit_details(sample["tokens"], phrase_rows, word_lengths, index)
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
                        word_shape_id=str(group["word_token_lengths"]),
                    )
                )
        if group_index == 1 or group_index % 25 == 0 or group_index == len(groups):
            elapsed = time.perf_counter() - started
            eta = elapsed / float(group_index) * float(len(groups) - group_index)
            print(
                f"[{RUN_LABEL}] stage=o3_scan groups={group_index}/{len(groups)} "
                f"samples={len(samples)} elapsed_seconds={elapsed:.1f} eta_seconds={eta:.1f}",
                flush=True,
            )
    rows: list[dict[str, Any]] = []
    sample_by_id = {str(sample["sample_id"]): sample for sample in samples}
    for sample_id, hits in sorted(hit_rows_by_sample.items()):
        sample = sample_by_id[sample_id]
        grouped = group_hits_by_candidate(hits)
        for lens in O3_LENSES:
            summary, _regions = summarise_candidate(
                grouped.get((str(sample["chunk_id"]), sample_id), []),
                candidate_id=sample_id,
                trial_id=str(sample["chunk_id"]),
                min_phrase_length=int(lens["min_phrase_length"]),
                max_hd=int(lens["max_hd"]),
            )
            row = {
                **{key: sample.get(key, "") for key in COMMON_FIELDS},
                "config_hash": current_hash,
                "order": 3,
                "dictionary_cut": "strict",
                "lens_name": lens["lens_name"],
                **asdict(summary),
            }
            row["selected_nonoverlap_exact_weight"] = row["selected_weight_sum"]
            row["longest_exact_phrase_len"] = row["longest_hd0_phrase_len"]
            rows.append(row)
    return rows


def run_o4(samples: list[dict[str, Any]], groups: list[Any], limits: Mapping[str, Any], current_hash: str, run_started: float) -> list[dict[str, Any]]:
    payloads = [
        (group, load_o4_runtime_npz(REPO_ROOT, group, max_phrase_rows=int(limits["o4_max_phrase_rows_per_group"])))
        for group in groups
    ]
    stage_started = time.perf_counter()
    rows: list[dict[str, Any]] = []
    for sample_index, sample in enumerate(samples, start=1):
        sample_started = time.perf_counter()
        hits = []
        phrase_rows_considered = 0
        windows_considered = 0
        attempts = 0
        for group, payload in payloads:
            group_hits, phrase_count, windows, group_attempts = o4_hamming_hits_for_group(
                sample_id=str(sample["sample_id"]),
                source_kind=str(sample["source_kind"]),
                model_name=str(sample["model_name"]),
                damage_level=str(sample["damage_level"]),
                repeat_index=int(sample["repeat_index"]),
                tokens=sample["tokens"],
                group=group,
                payload=payload,
                max_total_phrase_hd=MAX_TOTAL_PHRASE_HD,
            )
            hits.extend(group_hits)
            phrase_rows_considered += phrase_count
            windows_considered += windows
            attempts += group_attempts
        summary = summarise_o4_hits(
            sample_id=str(sample["sample_id"]),
            source_kind=str(sample["source_kind"]),
            model_name=str(sample["model_name"]),
            damage_level=str(sample["damage_level"]),
            repeat_index=int(sample["repeat_index"]),
            token_count=int(sample["token_count"]),
            changed_fraction=float(sample["changed_fraction"]),
            groups_loaded=len(payloads),
            phrase_rows_considered=phrase_rows_considered,
            windows_considered=windows_considered,
            verification_attempts=attempts,
            hits=hits,
            elapsed_seconds=time.perf_counter() - sample_started,
        )
        rows.append(
            {
                **{key: sample.get(key, "") for key in COMMON_FIELDS},
                "config_hash": current_hash,
                "order": 4,
                "dictionary_cut": "strict",
                **asdict(summary),
            }
        )
        if sample_index == 1 or sample_index % 10 == 0 or sample_index == len(samples):
            stage_elapsed = time.perf_counter() - stage_started
            total_elapsed = time.perf_counter() - run_started
            eta = stage_elapsed / float(sample_index) * float(len(samples) - sample_index)
            print(
                f"[{RUN_LABEL}] stage=o4_scan samples={sample_index}/{len(samples)} "
                f"groups={len(payloads)} elapsed_seconds={total_elapsed:.1f} eta_seconds={eta:.1f}",
                flush=True,
            )
    return rows


def sample_key(row: Mapping[str, Any]) -> str:
    return "|".join(str(row.get(key, "")) for key in ("chunk_id", "source_kind", "model_name", "damage_level", "repeat_index"))


def f(row: Mapping[str, Any], key: str) -> float:
    value = str(row.get(key, "") or "0")
    return float(value) if value else 0.0


def i(row: Mapping[str, Any], key: str) -> int:
    value = str(row.get(key, "") or "0")
    return int(float(value)) if value else 0


def build_joint_rows(samples: list[dict[str, Any]], o3_rows: list[dict[str, Any]], o4_rows: list[dict[str, Any]], current_hash: str) -> list[dict[str, Any]]:
    o3_by_key: dict[str, dict[str, Any]] = {}
    for row in o3_rows:
        key = sample_key(row)
        target = o3_by_key.setdefault(key, {k: row.get(k, "") for k in COMMON_FIELDS})
        lens = str(row.get("lens_name", ""))
        if lens == "HD0_L10":
            target["o3_hd0_l10_weight"] = max(f(target, "o3_hd0_l10_weight"), f(row, "selected_weight_sum"))
        elif lens == "HD0_L12":
            target["o3_hd0_l12_weight"] = max(f(target, "o3_hd0_l12_weight"), f(row, "selected_weight_sum"))
        elif lens == "HDle1_L12":
            target["o3_hdle1_l12_weight"] = max(f(target, "o3_hdle1_l12_weight"), f(row, "selected_weight_sum"))
        elif lens == "HDle2_L15":
            target["o3_hdle2_l15_weight"] = max(f(target, "o3_hdle2_l15_weight"), f(row, "selected_weight_sum"))
        target["o3_longest_exact_phrase_len"] = max(i(target, "o3_longest_exact_phrase_len"), i(row, "longest_hd0_phrase_len"))
    o4_by_key = {sample_key(row): row for row in o4_rows}
    rows: list[dict[str, Any]] = []
    for sample in samples:
        key = sample_key(sample)
        o3 = o3_by_key.get(key, {})
        o4 = o4_by_key.get(key, {})
        row = {
            **{k: sample.get(k, "") for k in COMMON_FIELDS},
            "config_hash": current_hash,
            "sample_key": key,
            "o3_hd0_l10_weight": f(o3, "o3_hd0_l10_weight"),
            "o3_hd0_l12_weight": f(o3, "o3_hd0_l12_weight"),
            "o3_hdle1_l12_weight": f(o3, "o3_hdle1_l12_weight"),
            "o3_hdle2_l15_weight": f(o3, "o3_hdle2_l15_weight"),
            "o3_longest_exact_phrase_len": i(o3, "o3_longest_exact_phrase_len"),
            "o4_exact_hit_count": i(o4, "exact_hit_count"),
            "o4_longest_exact_phrase_len": i(o4, "longest_exact_phrase_len"),
            "o4_selected_nonoverlap_exact_count": i(o4, "selected_nonoverlap_exact_count"),
            "o4_selected_nonoverlap_exact_weight": f(o4, "selected_nonoverlap_exact_weight"),
        }
        row["phrase_confidence_class"] = classify_phrase_confidence(row)
        row.update({name: int(value) for name, value in rule_flags(row).items()})
        rows.append(row)
    return rows


def grouped_counts(rows: list[Mapping[str, Any]], group_field: str) -> list[dict[str, Any]]:
    groups: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        groups.setdefault(str(row.get(group_field, "")), []).append(row)
    out: list[dict[str, Any]] = []
    for key, values in sorted(groups.items()):
        out.append(
            {
                group_field: key,
                "row_count": len(values),
                "o3_nonzero_count": sum(1 for row in values if f(row, "o3_hd0_l10_weight") > 0 or f(row, "o3_hd0_l12_weight") > 0),
                "o4_nonzero_count": sum(1 for row in values if f(row, "o4_selected_nonoverlap_exact_weight") > 0 or i(row, "o4_exact_hit_count") > 0),
                "strong_confirm_count": sum(1 for row in values if str(row.get("phrase_confidence_class")) == "strong_confirm"),
            }
        )
    return out


def run() -> dict[str, Any]:
    if not REPORT_ONLY or PRODUCTION_SCORER_CHANGE:
        raise RuntimeError("joint diagnostic is report-only")
    limits = MODE_LIMITS[RUN_MODE]
    if FORCE_RESTART and OUTPUT_DIR.exists():
        import shutil

        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    effective_config = {
        "run_label": RUN_LABEL,
        "run_mode": RUN_MODE,
        "report_only": REPORT_ONLY,
        "direction": "fwd",
        "o3_order": 3,
        "o4_order": 4,
        "dictionary_cut": "strict",
        "limits": dict(limits),
        "o3_runtime_manifest": repo_rel(O3_RUNTIME_MANIFEST),
        "o4_runtime_manifest": repo_rel(O4_RUNTIME_MANIFEST),
    }
    current_hash = config_hash(effective_config)
    process = psutil.Process(os.getpid())
    started = time.perf_counter()
    write_json_atomic(
        OUTPUT_DIR / "run_manifest.json",
        {
            **effective_config,
            "config_hash": current_hash,
            "status": "running",
            "created_utc": utc_now(),
            "production_scorer_change": False,
            "production_ranking_change": False,
        },
    )
    chunks = load_clean_chunks(int(limits["clean_chunks"]))
    samples = build_samples(chunks, limits, current_hash)
    sample_public = [{k: v for k, v in sample.items() if k != "tokens"} for sample in samples]
    sample_fields = tuple(dict.fromkeys([*COMMON_FIELDS, "book", "token_count", "seed", "damage_contract_status", "damage_shape"]))
    write_csv(OUTPUT_DIR / "sample_rows.csv", sample_public, sample_fields)
    o3_groups = select_o3_groups(int(limits["o3_runtime_groups"]))
    o4_groups = load_strict_o4_runtime_groups(
        O4_RUNTIME_MANIFEST,
        min_phrase_token_length=O4_MIN_PHRASE_LENGTH,
        max_groups=int(limits["o4_runtime_groups"]),
    )
    append_csv(
        OUTPUT_DIR / "progress_rows.csv",
        {
            "created_utc": utc_now(),
            "event": "scanning_started",
            "config_hash": current_hash,
            "samples": len(samples),
            "o3_groups": len(o3_groups),
            "o4_groups": len(o4_groups),
            "elapsed_seconds": 0,
        },
        ("created_utc", "event", "config_hash", "samples", "o3_groups", "o4_groups", "elapsed_seconds"),
    )
    o3_rows = run_o3(samples, o3_groups, current_hash, started)
    write_csv(OUTPUT_DIR / "sample_o3_summary_rows.csv", o3_rows, tuple(dict.fromkeys([*COMMON_FIELDS, "lens_name", *list(o3_rows[0].keys())])))
    o4_rows = run_o4(samples, o4_groups, limits, current_hash, started)
    write_csv(OUTPUT_DIR / "sample_o4_summary_rows.csv", o4_rows, tuple(dict.fromkeys([*COMMON_FIELDS, *list(o4_rows[0].keys())])))
    joint_rows = build_joint_rows(samples, o3_rows, o4_rows, current_hash)
    write_csv(OUTPUT_DIR / "joint_feature_rows.csv", joint_rows, tuple(joint_rows[0].keys()))
    rule_rows = grouped_counts(joint_rows, "phrase_confidence_class")
    write_csv(OUTPUT_DIR / "joint_rule_rows.csv", rule_rows, tuple(rule_rows[0].keys()))
    by_damage = grouped_counts(joint_rows, "damage_level")
    write_csv(OUTPUT_DIR / "joint_rule_by_damage_rows.csv", by_damage, tuple(by_damage[0].keys()))
    by_null = grouped_counts(joint_rows, "null_class")
    write_csv(OUTPUT_DIR / "joint_rule_by_null_class_rows.csv", by_null, tuple(by_null[0].keys()))
    failed_fields = ("created_utc", "sample_id", "config_hash", "error_type", "error_message")
    write_csv(OUTPUT_DIR / "failed_sample_rows.csv", [], failed_fields)
    write_csv(OUTPUT_DIR / "incomplete_sample_rows.csv", [], ("created_utc", "sample_id", "config_hash", "reason", "action"))
    elapsed = time.perf_counter() - started
    projections = [
        project_runtime(
            stage_name="bounded_8h_8_clean_chunks",
            clean_chunks=8,
            samples_per_chunk=(len(samples) // max(1, len(chunks))),
            observed_elapsed_seconds=elapsed,
            observed_samples=len(samples),
        ).row()
    ]
    write_csv(
        OUTPUT_DIR / "known_damage_runtime_projection_rows.csv",
        projections,
        tuple(projections[0].keys()),
    )
    final = {
        **effective_config,
        "config_hash": current_hash,
        "status": "complete",
        "finished_utc": utc_now(),
        "elapsed_seconds": elapsed,
        "sample_count": len(samples),
        "o3_summary_rows": len(o3_rows),
        "o4_summary_rows": len(o4_rows),
        "joint_feature_rows": len(joint_rows),
        "failed_sample_rows": 0,
        "incomplete_sample_rows": 0,
        "fwd_only_confirmed": True,
        "peak_memory_mb": max(getattr(process.memory_info(), "peak_wset", process.memory_info().rss), process.memory_info().rss) / 1_000_000,
    }
    write_json_atomic(OUTPUT_DIR / "final_summary.json", final)
    write_json_atomic(OUTPUT_DIR / "run_state.json", {**final, "updated_utc": utc_now()})
    append_csv(
        OUTPUT_DIR / "progress_rows.csv",
        {
            "created_utc": utc_now(),
            "event": "complete",
            "config_hash": current_hash,
            "samples": len(samples),
            "o3_groups": len(o3_groups),
            "o4_groups": len(o4_groups),
            "elapsed_seconds": f"{elapsed:.6f}",
        },
        ("created_utc", "event", "config_hash", "samples", "o3_groups", "o4_groups", "elapsed_seconds"),
    )
    (OUTPUT_DIR / "readout.md").write_text(
        "\n".join(
            [
                f"# {RUN_LABEL}",
                "",
                f"- status: `{final['status']}`",
                f"- run_mode: `{RUN_MODE}`",
                f"- samples: `{len(samples)}`",
                f"- O3 groups: `{len(o3_groups)}`",
                f"- O4 groups: `{len(o4_groups)}`",
                f"- O3 summary rows: `{len(o3_rows)}`",
                f"- O4 summary rows: `{len(o4_rows)}`",
                f"- joint rows: `{len(joint_rows)}`",
                f"- failed samples: `0`",
                f"- incomplete samples: `0`",
                "- report_only: `true`",
                "- production scorer/ranking change: `false`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    write_json_atomic(OUTPUT_DIR / "run_manifest.json", {**final, "created_utc": effective_config.get("created_utc", utc_now())})
    print(json.dumps(final, indent=2, sort_keys=True))
    return final


def main() -> int:
    run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
