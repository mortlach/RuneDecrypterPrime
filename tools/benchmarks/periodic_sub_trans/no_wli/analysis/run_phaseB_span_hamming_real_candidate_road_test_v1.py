from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
import shutil
import statistics
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (  # noqa: E402
    run_phaseB_runeberg_nose_damage_ladder_v1 as ladder,
)


RUN_LABEL = "phaseB_span_hamming_real_candidate_road_test_v1"
RUN_MODE = RUN_LABEL
OUTPUT_DIR = REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis" / RUN_LABEL
REVIEW_PACK_DIR = (
    REPO_ROOT
    / "planning/projects/no_wli/40_review_summaries"
    / "phaseB_span_hamming_real_candidate_road_test_v1_review_pack_2026-05-13"
)
REVIEW_PACK_ZIP = REVIEW_PACK_DIR.with_suffix(".zip")

CANDIDATE_SOURCE_ROOT = (
    REPO_ROOT
    / "planning/projects/no_wli/40_review_summaries"
    / "no_wli_fixed_panel_v1_external_review_pack_2026-04-14/50_completed_job_runs"
)
HISTORICAL_PAIRWISE_ROWS = (
    REPO_ROOT
    / "planning/projects/no_wli/40_review_summaries"
    / "no_wli_historical_partial_text_and_scorer_review_pack_2026-05-02"
    / "historical_pairwise_rescore/historical_pairwise_rescore_pairs.csv"
)

ACTIVE_CALIBRATION_DIR = (
    REPO_ROOT
    / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/stage3_fwd_full_len5_14_pcb"
)
STAGE1_STAGE2_COMBINED_DIR = (
    REPO_ROOT
    / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/stage1_stage2_fwd_full_len2_14_combined_v1"
)
STAGE4_DIR = REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/stage4_fwd_full_len8_14_pcb"

CANDIDATE_CHUNK_MAX_TOKENS = 500
MIN_FULL_CHUNK_TOKENS = 450
ALLOW_SHORT_CHUNKS = False
MAX_ARTIFACTS = 20
STAGE2_TOPK_LIMIT = 3
STAGE3_TOPK_LIMIT = 3
STAGE35_ARCHIVE_LIMIT = 6
STAGE35_SEED_LIMIT = 0

SPAN_LENGTHS = tuple(range(5, 15))
MAX_HD_BY_LENGTH = {
    5: 1,
    6: 2,
    7: 3,
    8: 3,
    9: 4,
    10: 4,
    11: 5,
    12: 5,
    13: 6,
    14: 6,
}
LADDER_PROFILE = "v0_3_plus_long_relaxed_v2_len5_14"

CALIBRATION_DAMAGE_MODEL = "word_local_substitution"
CALIBRATION_DAMAGE_LEVEL = "0.20"
LOCAL_NULL_MODELS = ("uniform_random", "global_frequency_random", "within_chunk_shuffle")
BLOCK_NULL_MODELS = ("block_shuffle_10", "block_shuffle_25", "block_shuffle_50")
COMPARISON_NULL_MODELS = LOCAL_NULL_MODELS + BLOCK_NULL_MODELS
PANEL_FEATURE_NAMES = ("exact_count_norm", "hd_le_count_norm")
PANEL_POSITIVE_THRESHOLD = 0.5
STRICT_PRECISION_MIN_COHEN_D = 1.0


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def ensure_under_repo(path: Path) -> None:
    resolved = path.resolve()
    if not resolved.is_relative_to(REPO_ROOT):
        raise ValueError(f"path escapes repo root: {resolved}")
    resolved.parent.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    ensure_under_repo(path)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]], fieldnames: list[str]) -> None:
    ensure_under_repo(path)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_csv_gz(path: Path, rows: Iterable[Mapping[str, Any]], fieldnames: list[str]) -> None:
    ensure_under_repo(path)
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def stable_hash_tokens(tokens: Iterable[int]) -> str:
    joined = ",".join(str(int(token)) for token in tokens)
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()[:16]


def stable_id(parts: Iterable[Any]) -> str:
    raw = "|".join(str(part) for part in parts)
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in raw[:80]).strip("_").lower()
    return f"{cleaned}_{digest}" if cleaned else digest


def as_float(value: Any, default: float | None = None) -> float | None:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def label_from_match(match_ratio: float | None, candidate_kind: str) -> tuple[str, float]:
    if candidate_kind == "target_plaintext":
        return "known_good", 1.0
    if match_ratio is None:
        return "unknown", 0.0
    if match_ratio >= 0.90:
        return "known_good", 0.95
    if match_ratio >= 0.50:
        return "likely_good", 0.70
    if match_ratio <= 0.10:
        return "known_bad", 0.90
    if match_ratio <= 0.40:
        return "likely_bad", 0.75
    return "unknown", 0.40


def token_list(value: Any) -> list[int]:
    if not isinstance(value, list):
        return []
    return [int(token) for token in value]


def candidate_from_tokens(
    *,
    artifact: Mapping[str, Any],
    source_file: Path,
    source_run_id: str,
    candidate_kind: str,
    rank: int,
    tokens: list[int],
    current_score: float | None,
    current_score_name: str,
    match_ratio: float | None,
    notes: str,
) -> dict[str, Any]:
    token_hash = stable_hash_tokens(tokens)
    candidate_id = stable_id((source_run_id, candidate_kind, rank, token_hash))
    label, confidence = label_from_match(match_ratio, candidate_kind)
    fixture_seed = artifact.get("fixture_seed", artifact.get("seed", ""))
    search_seed = artifact.get("search_seed", "")
    return {
        "candidate_id": candidate_id,
        "source_run_id": source_run_id,
        "source_file": rel(source_file),
        "candidate_kind": candidate_kind,
        "candidate_rank": rank,
        "current_score": "" if current_score is None else f"{current_score:.12g}",
        "current_score_name": current_score_name,
        "truth_match_ratio": "" if match_ratio is None else f"{match_ratio:.12g}",
        "label": label,
        "label_confidence": f"{confidence:.3f}",
        "direction": "fwd",
        "token_count": len(tokens),
        "candidate_text_or_token_path": f"{rel(source_file)}#{candidate_kind}[{rank}]",
        "notes": notes,
        "fixture_seed": fixture_seed,
        "search_seed": search_seed,
        "token_hash": token_hash,
        "_tokens": tokens,
    }


def load_candidates() -> list[dict[str, Any]]:
    best_files = sorted(CANDIDATE_SOURCE_ROOT.rglob("best_instance.json"))[:MAX_ARTIFACTS]
    candidates: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for source_file in best_files:
        artifact = json.loads(source_file.read_text(encoding="utf-8"))
        source_run_id = source_file.parent.parent.name

        def add(candidate: dict[str, Any]) -> None:
            key = (str(candidate["source_run_id"]), str(candidate["token_hash"]))
            if key in seen:
                return
            seen.add(key)
            candidates.append(candidate)

        final_tokens = token_list(artifact.get("final_best_plaintext_idx"))
        if final_tokens:
            add(
                candidate_from_tokens(
                    artifact=artifact,
                    source_file=source_file,
                    source_run_id=source_run_id,
                    candidate_kind="final_best",
                    rank=1,
                    tokens=final_tokens,
                    current_score=as_float(artifact.get("best_score")),
                    current_score_name="best_score",
                    match_ratio=as_float(artifact.get("best_match_ratio")),
                    notes="solver final_best_plaintext_idx from fixed-panel external pack",
                )
            )

        target_tokens = token_list(artifact.get("target_plaintext_idx"))
        if target_tokens:
            add(
                candidate_from_tokens(
                    artifact=artifact,
                    source_file=source_file,
                    source_run_id=source_run_id,
                    candidate_kind="target_plaintext",
                    rank=0,
                    tokens=target_tokens,
                    current_score=None,
                    current_score_name="control_target_plaintext",
                    match_ratio=1.0,
                    notes="known-good target plaintext control from same fixture",
                )
            )

        for row in artifact.get("stage2_topk", [])[:STAGE2_TOPK_LIMIT]:
            tokens = token_list(row.get("plaintext_idx"))
            if not tokens:
                continue
            add(
                candidate_from_tokens(
                    artifact=artifact,
                    source_file=source_file,
                    source_run_id=source_run_id,
                    candidate_kind="stage2_topk",
                    rank=as_int(row.get("rank"), 0),
                    tokens=tokens,
                    current_score=as_float(row.get("score_judge"), as_float(row.get("score_stage2"))),
                    current_score_name="score_judge",
                    match_ratio=as_float(row.get("match_ratio")),
                    notes="stage2 top-k candidate from fixed-panel external pack",
                )
            )

        for row in artifact.get("stage3_topk", [])[:STAGE3_TOPK_LIMIT]:
            tokens = token_list(row.get("plaintext_idx"))
            if not tokens:
                continue
            add(
                candidate_from_tokens(
                    artifact=artifact,
                    source_file=source_file,
                    source_run_id=source_run_id,
                    candidate_kind="stage3_topk",
                    rank=as_int(row.get("rank"), 0),
                    tokens=tokens,
                    current_score=as_float(row.get("score_judge"), as_float(row.get("score_raw"))),
                    current_score_name="score_judge",
                    match_ratio=as_float(row.get("match_ratio")),
                    notes="stage3 top-k candidate from fixed-panel external pack",
                )
            )

        for row in artifact.get("stage35_archive", [])[:STAGE35_ARCHIVE_LIMIT]:
            tokens = token_list(row.get("plaintext_idx"))
            if not tokens:
                continue
            add(
                candidate_from_tokens(
                    artifact=artifact,
                    source_file=source_file,
                    source_run_id=source_run_id,
                    candidate_kind="stage35_archive",
                    rank=as_int(row.get("archive_rank"), 0),
                    tokens=tokens,
                    current_score=as_float(row.get("score"), as_float(row.get("search_score"))),
                    current_score_name="score",
                    match_ratio=as_float(row.get("checkpoint_final_match")),
                    notes="stage35 archive candidate from fixed-panel external pack",
                )
            )

        for row in artifact.get("stage35_seed_rows", [])[:STAGE35_SEED_LIMIT]:
            tokens = token_list(row.get("plaintext_idx"))
            if not tokens:
                continue
            add(
                candidate_from_tokens(
                    artifact=artifact,
                    source_file=source_file,
                    source_run_id=source_run_id,
                    candidate_kind="stage35_seed_rows",
                    rank=as_int(row.get("rank"), 0),
                    tokens=tokens,
                    current_score=as_float(row.get("score"), as_float(row.get("search_score"))),
                    current_score_name="score",
                    match_ratio=as_float(row.get("checkpoint_final_match")),
                    notes="stage35 seed-row candidate from fixed-panel external pack",
                )
            )

    return candidates


def chunk_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for candidate in candidates:
        tokens = list(candidate["_tokens"])
        if len(tokens) < MIN_FULL_CHUNK_TOKENS and not ALLOW_SHORT_CHUNKS:
            continue
        for chunk_index, start in enumerate(range(0, len(tokens), CANDIDATE_CHUNK_MAX_TOKENS)):
            chunk_tokens = tokens[start : start + CANDIDATE_CHUNK_MAX_TOKENS]
            if len(chunk_tokens) < MIN_FULL_CHUNK_TOKENS and not ALLOW_SHORT_CHUNKS:
                continue
            chunk_status = "short_chunk" if len(chunk_tokens) < MIN_FULL_CHUNK_TOKENS else "full_chunk"
            chunk_id = f"{candidate['candidate_id']}|chunk{chunk_index:03d}|{start}_{start + len(chunk_tokens)}"
            chunks.append(
                {
                    "candidate_chunk_id": chunk_id,
                    "candidate_id": candidate["candidate_id"],
                    "chunk_index": chunk_index,
                    "chunk_start": start,
                    "chunk_end": start + len(chunk_tokens),
                    "token_count": len(chunk_tokens),
                    "chunk_status": chunk_status,
                    "direction": "fwd",
                    "_tokens": chunk_tokens,
                }
            )
    return chunks


def load_calibration_rows() -> dict[tuple[str, int, int, str, str], dict[str, str]]:
    path = ACTIVE_CALIBRATION_DIR / "damaged_vs_null_summary.csv"
    rows = read_csv_rows(path)
    index: dict[tuple[str, int, int, str, str], dict[str, str]] = {}
    for row in rows:
        if row["damage_model"] != CALIBRATION_DAMAGE_MODEL:
            continue
        if row["damage_level"] != CALIBRATION_DAMAGE_LEVEL:
            continue
        if row["null_model"] not in COMPARISON_NULL_MODELS:
            continue
        if row["feature_name"] not in PANEL_FEATURE_NAMES:
            continue
        key = (
            row["dictionary_cut"],
            int(row["span_length"]),
            int(row["hd"]),
            row["feature_name"],
            row["null_model"],
        )
        index[key] = row
    return index


def normal_percentile(value: float, mean: float, stddev: float) -> float:
    if stddev <= 0:
        if value < mean:
            return 0.0
        if value > mean:
            return 1.0
        return 0.5
    z = (value - mean) / stddev
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def panel_id_for(row: Mapping[str, Any]) -> list[str]:
    dictionary_cut = str(row["dictionary_cut"])
    length = int(row["span_length"])
    feature_name = str(row["feature_name"])
    null_model = str(row["comparison_null_model"])
    cohen_d = abs(float(row["calibration_cohen_d"]))
    panels: list[str] = []
    if (
        5 <= length <= 9
        and dictionary_cut == "phaseA14_normal_selected"
        and feature_name in PANEL_FEATURE_NAMES
        and null_model in LOCAL_NULL_MODELS
    ):
        panels.append("A_core_medium_local")
    if 10 <= length <= 14 and feature_name in PANEL_FEATURE_NAMES:
        panels.append("B_longer_span")
    if 2 <= length <= 4 and feature_name in PANEL_FEATURE_NAMES:
        panels.append("C_short_diagnostic")
    if (
        dictionary_cut == "phaseA14_strict_selected"
        and feature_name in PANEL_FEATURE_NAMES
        and null_model in LOCAL_NULL_MODELS
        and cohen_d >= STRICT_PRECISION_MIN_COHEN_D
    ):
        panels.append("D_strict_precision")
    return panels


def configure_ladder_module() -> None:
    ladder.RUN_LABEL = RUN_LABEL
    ladder.RUN_MODE = RUN_MODE
    ladder.LADDER_PROFILE = LADDER_PROFILE
    ladder.SPAN_LENGTHS = SPAN_LENGTHS
    ladder.MAX_HD_BY_LENGTH = dict(MAX_HD_BY_LENGTH)
    ladder.START_VIEW_SHIFTS_BY_MODE[RUN_MODE] = (0,)
    ladder.SCORE_REGIONS_BY_MODE[RUN_MODE] = ("full",)
    ladder.DIRECTIONS_BY_MODE[RUN_MODE] = ("fwd",)


def score_candidate_chunks(
    chunks: list[dict[str, Any]],
    candidates_by_id: Mapping[str, Mapping[str, Any]],
    calibration_index: Mapping[tuple[str, int, int, str, str], Mapping[str, str]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    configure_ladder_module()
    dictionary_specs = [ladder.DictionarySpec(**spec) for spec in ladder.DICTIONARY_SPECS]
    backends = {spec.dictionary_cut: ladder.build_backend(spec) for spec in dictionary_specs}

    feature_rows: list[dict[str, Any]] = []
    score_timing_rows: list[dict[str, Any]] = []

    for ordinal, chunk in enumerate(chunks, start=1):
        candidate = candidates_by_id[chunk["candidate_id"]]
        clean_chunk = ladder.CleanChunk(
            book=str(candidate["candidate_id"]),
            direction="fwd",
            chunk_index=int(chunk["chunk_index"]),
            chunk_start=int(chunk["chunk_start"]),
            chunk_end=int(chunk["chunk_end"]),
            tokens=tuple(int(token) for token in chunk["_tokens"]),
            wli=(),
            source_start_assumption="assumed_word_start",
            corpus_chunk_index=ordinal,
        )
        sample = ladder.Sample(
            sample_id=str(chunk["candidate_chunk_id"]),
            source_kind="candidate",
            damage_model="none",
            damage_level="",
            null_model="",
            repeat_index=0,
            seed=0,
            clean_chunk=clean_chunk,
            tokens=tuple(int(token) for token in chunk["_tokens"]),
        )

        for spec in dictionary_specs:
            raw_rows, elapsed_ms = ladder.fingerprint_rows_for_sample(
                sample=sample,
                spec=spec,
                backend=backends[spec.dictionary_cut],
            )
            score_timing_rows.append(
                {
                    "candidate_chunk_id": chunk["candidate_chunk_id"],
                    "dictionary_cut": spec.dictionary_cut,
                    "elapsed_ms": f"{elapsed_ms:.6f}",
                    "raw_feature_rows": len(raw_rows),
                }
            )
            for raw in raw_rows:
                for feature_name in PANEL_FEATURE_NAMES:
                    value = float(raw[feature_name])
                    for null_model in COMPARISON_NULL_MODELS:
                        key = (
                            str(raw["dictionary_cut"]),
                            int(raw["span_length"]),
                            int(raw["hd"]),
                            feature_name,
                            null_model,
                        )
                        calibration = calibration_index.get(key)
                        if calibration is None:
                            continue
                        damaged_mean = float(calibration["damaged_mean"])
                        damaged_stddev = float(calibration["damaged_stddev"])
                        null_mean = float(calibration["null_mean"])
                        null_stddev = float(calibration["null_stddev"])
                        diff = damaged_mean - null_mean
                        pooled_stddev = math.sqrt(max(0.0, (damaged_stddev * damaged_stddev + null_stddev * null_stddev) / 2.0))
                        if pooled_stddev > 1e-12:
                            signed_effect = ((value - null_mean) * (1.0 if diff >= 0 else -1.0)) / pooled_stddev
                        elif abs(diff) <= 1e-12:
                            signed_effect = 0.0
                        else:
                            signed_effect = ((value - null_mean) * (1.0 if diff >= 0 else -1.0)) / abs(diff)
                        row = {
                            "candidate_id": candidate["candidate_id"],
                            "candidate_chunk_id": chunk["candidate_chunk_id"],
                            "candidate_kind": candidate["candidate_kind"],
                            "candidate_rank": candidate["candidate_rank"],
                            "label": candidate["label"],
                            "label_confidence": candidate["label_confidence"],
                            "source_run_id": candidate["source_run_id"],
                            "source_file": candidate["source_file"],
                            "current_score": candidate["current_score"],
                            "current_score_name": candidate["current_score_name"],
                            "truth_match_ratio": candidate["truth_match_ratio"],
                            "chunk_index": chunk["chunk_index"],
                            "chunk_token_count": chunk["token_count"],
                            "chunk_status": chunk["chunk_status"],
                            "direction": raw["direction"],
                            "score_region": raw["score_region"],
                            "start_shift": raw["start_shift"],
                            "dictionary_cut": raw["dictionary_cut"],
                            "ladder_profile": LADDER_PROFILE,
                            "span_length": raw["span_length"],
                            "hd": raw["hd"],
                            "feature_name": feature_name,
                            "candidate_value": f"{value:.12g}",
                            "comparison_null_model": null_model,
                            "comparison_null_class": "local_null" if null_model in LOCAL_NULL_MODELS else "block_shuffle",
                            "calibration_damage_model": CALIBRATION_DAMAGE_MODEL,
                            "calibration_damage_level": CALIBRATION_DAMAGE_LEVEL,
                            "damaged_mean": calibration["damaged_mean"],
                            "damaged_stddev": calibration["damaged_stddev"],
                            "null_mean": calibration["null_mean"],
                            "null_stddev": calibration["null_stddev"],
                            "damaged_percentile": f"{normal_percentile(value, damaged_mean, damaged_stddev):.12g}",
                            "comparison_null_percentile": f"{normal_percentile(value, null_mean, null_stddev):.12g}",
                            "signed_effect_vs_comparison_null": f"{signed_effect:.12g}",
                            "signed_effect_vs_local_null": f"{signed_effect:.12g}" if null_model in LOCAL_NULL_MODELS else "",
                            "signed_effect_vs_block_shuffle": f"{signed_effect:.12g}" if null_model in BLOCK_NULL_MODELS else "",
                            "calibration_n_chunks": calibration["damaged_count"],
                            "calibration_n_samples": calibration["damaged_count"],
                            "calibration_cohen_d": calibration["cohen_d"],
                        }
                        row["panels"] = ";".join(panel_id_for(row))
                        feature_rows.append(row)

    return feature_rows, score_timing_rows


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int(math.ceil((p / 100.0) * len(ordered))) - 1))
    return ordered[idx]


def summarize_panels(feature_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in feature_rows:
        for panel_id in str(row.get("panels", "")).split(";"):
            if not panel_id:
                continue
            grouped[(row["candidate_id"], row["candidate_chunk_id"], panel_id)].append(row)

    summaries: list[dict[str, Any]] = []
    for (candidate_id, chunk_id, panel_id), rows in sorted(grouped.items()):
        effects = [float(row["signed_effect_vs_comparison_null"]) for row in rows]
        supporting = sorted(rows, key=lambda row: float(row["signed_effect_vs_comparison_null"]), reverse=True)[:5]
        warning = sorted(rows, key=lambda row: float(row["signed_effect_vs_comparison_null"]))[:5]
        first = rows[0]
        summaries.append(
            {
                "candidate_id": candidate_id,
                "candidate_chunk_id": chunk_id,
                "panel_id": panel_id,
                "label": first["label"],
                "candidate_kind": first["candidate_kind"],
                "source_run_id": first["source_run_id"],
                "candidate_rank": first["candidate_rank"],
                "current_score": first["current_score"],
                "truth_match_ratio": first["truth_match_ratio"],
                "panel_feature_count": len(effects),
                "panel_mean_signed_effect": f"{statistics.fmean(effects):.12g}",
                "panel_median_signed_effect": f"{statistics.median(effects):.12g}",
                "panel_p90_signed_effect": f"{percentile(effects, 90):.12g}",
                "panel_fraction_positive": f"{sum(1 for value in effects if value > 0.0) / len(effects):.12g}",
                "panel_fraction_above_threshold": f"{sum(1 for value in effects if value >= PANEL_POSITIVE_THRESHOLD) / len(effects):.12g}",
                "panel_top_supporting_features": ";".join(
                    f"{row['dictionary_cut']}|L{row['span_length']}|HD{row['hd']}|{row['feature_name']}|{row['comparison_null_model']}={row['signed_effect_vs_comparison_null']}"
                    for row in supporting
                ),
                "panel_top_warning_features": ";".join(
                    f"{row['dictionary_cut']}|L{row['span_length']}|HD{row['hd']}|{row['feature_name']}|{row['comparison_null_model']}={row['signed_effect_vs_comparison_null']}"
                    for row in warning
                ),
            }
        )
    return summaries


def summarize_candidates(panel_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in panel_rows:
        grouped[(row["candidate_id"], row["panel_id"])].append(row)

    summaries: list[dict[str, Any]] = []
    for (candidate_id, panel_id), rows in sorted(grouped.items()):
        scores = [float(row["panel_mean_signed_effect"]) for row in rows]
        first = rows[0]
        summaries.append(
            {
                "candidate_id": candidate_id,
                "panel_id": panel_id,
                "label": first["label"],
                "candidate_kind": first["candidate_kind"],
                "source_run_id": first["source_run_id"],
                "candidate_rank": first["candidate_rank"],
                "current_score": first["current_score"],
                "truth_match_ratio": first["truth_match_ratio"],
                "chunk_count": len(rows),
                "best_chunk_score": f"{max(scores):.12g}",
                "mean_chunk_score": f"{statistics.fmean(scores):.12g}",
                "median_chunk_score": f"{statistics.median(scores):.12g}",
                "number_of_positive_chunks": sum(1 for score in scores if score > 0.0),
                "fraction_positive_chunks": f"{sum(1 for score in scores if score > 0.0) / len(scores):.12g}",
            }
        )
    return summaries


def build_pairwise_summary(candidate_level_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    panel_a = {
        row["candidate_id"]: float(row["mean_chunk_score"])
        for row in candidate_level_rows
        if row["panel_id"] == "A_core_medium_local"
    }
    by_source: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for row in candidate_level_rows:
        if row["panel_id"] != "A_core_medium_local":
            continue
        by_source[row["source_run_id"]][row["candidate_kind"]].append(row)

    pairs: list[dict[str, Any]] = []
    for source_run_id, kinds in sorted(by_source.items()):
        targets = kinds.get("target_plaintext", [])
        finals = kinds.get("final_best", [])
        if not targets or not finals:
            continue
        target = targets[0]
        final = finals[0]
        score_target = panel_a.get(target["candidate_id"], 0.0)
        score_final = panel_a.get(final["candidate_id"], 0.0)
        preferred = target["candidate_id"] if score_target >= score_final else final["candidate_id"]
        pairs.append(
            {
                "pair_id": f"{source_run_id}__final_best_vs_target",
                "candidate_a_id": final["candidate_id"],
                "candidate_b_id": target["candidate_id"],
                "current_scorer_preferred": final["candidate_id"],
                "known_better_candidate": target["candidate_id"],
                "current_scorer_correct": "false",
                "span_hamming_panel_preferred": preferred,
                "span_hamming_rescues_current_misrank": "true" if preferred == target["candidate_id"] else "false",
                "span_hamming_breaks_current_correct": "false",
                "panel_scores_a": f"A_core_medium_local={score_final:.12g}",
                "panel_scores_b": f"A_core_medium_local={score_target:.12g}",
                "notes": "constructed target-vs-final_best pair; target is known-good fixture control, not an independently current-scored candidate",
            }
        )
    return pairs


def build_bad_candidate_separation(candidate_level_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in candidate_level_rows:
        grouped[(row["label"], row["panel_id"])].append(float(row["mean_chunk_score"]))
    out: list[dict[str, Any]] = []
    for (label, panel_id), scores in sorted(grouped.items()):
        out.append(
            {
                "label": label,
                "panel_id": panel_id,
                "candidate_count": len(scores),
                "mean_score": f"{statistics.fmean(scores):.12g}",
                "median_score": f"{statistics.median(scores):.12g}",
                "p10_score": f"{percentile(scores, 10):.12g}",
                "p90_score": f"{percentile(scores, 90):.12g}",
                "fraction_above_threshold": f"{sum(1 for score in scores if score >= PANEL_POSITIVE_THRESHOLD) / len(scores):.12g}",
            }
        )
    return out


def top_rows(candidate_level_rows: list[dict[str, Any]], *, warnings_only: bool) -> list[dict[str, Any]]:
    rows = [row for row in candidate_level_rows if row["panel_id"] == "A_core_medium_local"]
    if warnings_only:
        rows = [row for row in rows if row["label"] in {"known_bad", "likely_bad"}]
    rows = sorted(rows, key=lambda row: float(row["mean_chunk_score"]), reverse=True)[:30]
    return rows


def write_readout(
    *,
    candidates: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
    feature_rows: list[dict[str, Any]],
    panel_rows: list[dict[str, Any]],
    candidate_level_rows: list[dict[str, Any]],
    pairwise_rows: list[dict[str, Any]],
    separation_rows: list[dict[str, Any]],
    elapsed_s: float,
) -> None:
    label_counts: dict[str, int] = defaultdict(int)
    for candidate in candidates:
        label_counts[str(candidate["label"])] += 1

    def panel_stats(panel_id: str) -> dict[str, Any]:
        rows = [row for row in candidate_level_rows if row["panel_id"] == panel_id]
        scores = [float(row["mean_chunk_score"]) for row in rows]
        bad_scores = [float(row["mean_chunk_score"]) for row in rows if row["label"] in {"known_bad", "likely_bad"}]
        good_scores = [float(row["mean_chunk_score"]) for row in rows if row["label"] in {"known_good", "likely_good"}]
        return {
            "n": len(rows),
            "mean": statistics.fmean(scores) if scores else 0.0,
            "bad_mean": statistics.fmean(bad_scores) if bad_scores else 0.0,
            "good_mean": statistics.fmean(good_scores) if good_scores else 0.0,
            "bad_pass": (sum(1 for score in bad_scores if score >= PANEL_POSITIVE_THRESHOLD) / len(bad_scores)) if bad_scores else 0.0,
        }

    panel_a = panel_stats("A_core_medium_local")
    panel_b = panel_stats("B_longer_span")
    panel_d = panel_stats("D_strict_precision")
    rescues = sum(1 for row in pairwise_rows if row["span_hamming_rescues_current_misrank"] == "true")

    lines = [
        "# PhaseB Span-Hamming Real Candidate Road Test v1",
        "",
        f"Created UTC: {datetime.now(timezone.utc).isoformat()}",
        f"Elapsed seconds: {elapsed_s:.1f}",
        "",
        "## Scope",
        "",
        f"- Candidate texts scored: {len(candidates)}",
        f"- Candidate chunks scored: {len(chunks)}",
        f"- Candidate feature comparison rows: {len(feature_rows)}",
        f"- Label counts: {dict(sorted(label_counts.items()))}",
        f"- Active calibration: {rel(ACTIVE_CALIBRATION_DIR)}",
        f"- Calibration damage reference: {CALIBRATION_DAMAGE_MODEL} level {CALIBRATION_DAMAGE_LEVEL}",
        "- Percentiles are normal-approximation readouts from the calibration mean/stddev rows.",
        "- Signed effects are oriented in the damaged-human direction and normalized by pooled damaged/null stddev.",
        "- No production scorer weights were changed.",
        "",
        "## Main Questions",
        "",
        f"- High-scoring bad candidates under Panel A: bad/likely-bad pass fraction {panel_a['bad_pass']:.3f}; bad mean {panel_a['bad_mean']:.3f}; good mean {panel_a['good_mean']:.3f}.",
        f"- Panel A medium lengths 5-9 rows scored {panel_a['n']} candidates and is the primary local-word evidence panel.",
        f"- Panel B longer lengths 10-14 rows scored {panel_b['n']} candidates; bad mean {panel_b['bad_mean']:.3f}; good mean {panel_b['good_mean']:.3f}.",
        f"- Panel D strict precision rows scored {panel_d['n']} candidates; bad mean {panel_d['bad_mean']:.3f}; good mean {panel_d['good_mean']:.3f}.",
        "- Panel C short-length diagnostic is intentionally absent in this first run because the active Stage 3 calibration profile is lengths 5-14.",
        f"- Pairwise target-vs-final_best comparisons: {len(pairwise_rows)}; span-Hamming Panel A rescues current final_best misrank in {rescues}.",
        "",
        "## Interpretation Guardrails",
        "",
        "- A high score means the candidate has local span-Hamming evidence similar to damaged human text, not that it is globally ordered or correct.",
        "- Bad candidates that pass Panel A are warning cases: local word-like fragments are present and order/phrase evidence is still needed.",
        "- Target plaintext controls are included only as known-good anchors; candidate-vs-candidate labelled pair data can be added when matching token streams are available.",
        "",
        "## Output Files",
        "",
        "- config.json",
        "- calibration_manifest.json",
        "- candidate_manifest_resolved.csv",
        "- candidate_chunk_manifest.csv",
        "- candidate_feature_rows.csv.gz",
        "- candidate_panel_summary.csv",
        "- candidate_level_summary.csv",
        "- pairwise_road_test_summary.csv",
        "- top_supported_candidates.csv",
        "- top_warning_candidates.csv",
        "- bad_candidate_separation_summary.csv",
        "- readout.md",
        "",
        "## Separation Snapshot",
        "",
    ]
    for row in separation_rows:
        lines.append(
            f"- {row['panel_id']} / {row['label']}: n={row['candidate_count']} mean={row['mean_score']} median={row['median_score']} pass_fraction={row['fraction_above_threshold']}"
        )
    (OUTPUT_DIR / "readout.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def copy_review_pack() -> None:
    if REVIEW_PACK_DIR.exists():
        shutil.rmtree(REVIEW_PACK_DIR)
    REVIEW_PACK_DIR.mkdir(parents=True, exist_ok=True)
    for name in (
        "config.json",
        "calibration_manifest.json",
        "candidate_manifest_resolved.csv",
        "candidate_chunk_manifest.csv",
        "candidate_feature_rows.csv.gz",
        "candidate_panel_summary.csv",
        "candidate_level_summary.csv",
        "pairwise_road_test_summary.csv",
        "top_supported_candidates.csv",
        "top_warning_candidates.csv",
        "bad_candidate_separation_summary.csv",
        "score_timing_rows.csv",
        "readout.md",
    ):
        shutil.copy2(OUTPUT_DIR / name, REVIEW_PACK_DIR / name)
    if REVIEW_PACK_ZIP.exists():
        REVIEW_PACK_ZIP.unlink()
    shutil.make_archive(str(REVIEW_PACK_DIR), "zip", REVIEW_PACK_DIR)


def main() -> None:
    start = time.perf_counter()
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    required = [
        ACTIVE_CALIBRATION_DIR / "damaged_vs_null_summary.csv",
        ACTIVE_CALIBRATION_DIR / "damaged_vs_null_by_view.csv.gz",
        ACTIVE_CALIBRATION_DIR / "feature_histograms.csv.gz",
        ACTIVE_CALIBRATION_DIR / "feature_quantiles.csv.gz",
        ACTIVE_CALIBRATION_DIR / "dictionary_hash_manifest.csv",
        CANDIDATE_SOURCE_ROOT,
    ]
    missing = [rel(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"missing required inputs: {missing}")

    config = {
        "run_label": RUN_LABEL,
        "report_only": True,
        "candidate_source_root": rel(CANDIDATE_SOURCE_ROOT),
        "candidate_chunk_max_tokens": CANDIDATE_CHUNK_MAX_TOKENS,
        "min_full_chunk_tokens": MIN_FULL_CHUNK_TOKENS,
        "allow_short_chunks": ALLOW_SHORT_CHUNKS,
        "max_artifacts": MAX_ARTIFACTS,
        "stage2_topk_limit": STAGE2_TOPK_LIMIT,
        "stage3_topk_limit": STAGE3_TOPK_LIMIT,
        "stage35_archive_limit": STAGE35_ARCHIVE_LIMIT,
        "direction": ["fwd"],
        "score_region": ["full"],
        "start_shift": [0],
        "span_lengths": list(SPAN_LENGTHS),
        "max_hd_by_length": MAX_HD_BY_LENGTH,
        "ladder_profile": LADDER_PROFILE,
        "dictionary_cuts": [spec["dictionary_cut"] for spec in ladder.DICTIONARY_SPECS],
        "panel_feature_names": PANEL_FEATURE_NAMES,
        "calibration_damage_model": CALIBRATION_DAMAGE_MODEL,
        "calibration_damage_level": CALIBRATION_DAMAGE_LEVEL,
        "local_null_models": LOCAL_NULL_MODELS,
        "block_null_models": BLOCK_NULL_MODELS,
        "panel_positive_threshold": PANEL_POSITIVE_THRESHOLD,
        "strict_precision_min_abs_cohen_d": STRICT_PRECISION_MIN_COHEN_D,
    }
    write_json(OUTPUT_DIR / "config.json", config)

    calibration_manifest = {
        "active_calibration": {
            "name": "stage3_fwd_full_len5_14_pcb",
            "path": rel(ACTIVE_CALIBRATION_DIR),
            "role": "active profile comparison for lengths 5-14",
            "required_files_present": {name: (ACTIVE_CALIBRATION_DIR / name).exists() for name in (
                "final_feature_summary.csv",
                "damaged_vs_null_by_view.csv.gz",
                "feature_histograms.csv.gz",
                "feature_quantiles.csv.gz",
                "dictionary_hash_manifest.csv",
                "readout.md",
                "final_summary.json",
            )},
        },
        "available_calibrations": [
            {
                "name": "stage1_stage2_fwd_full_len2_14_combined_v1",
                "path": rel(STAGE1_STAGE2_COMBINED_DIR),
                "exists": STAGE1_STAGE2_COMBINED_DIR.exists(),
                "role": "earlier combined calibration; not active for v1 panel scoring except noted metadata",
            },
            {
                "name": "stage4_fwd_full_len8_14_pcb",
                "path": rel(STAGE4_DIR),
                "exists": STAGE4_DIR.exists(),
                "role": "future longer-span refresh after completion/review",
            },
        ],
        "historical_pairwise_rows": {
            "path": rel(HISTORICAL_PAIRWISE_ROWS),
            "exists": HISTORICAL_PAIRWISE_ROWS.exists(),
            "role": "candidate pair labels discovered but not directly token-resolved in this v1 pack",
        },
    }
    write_json(OUTPUT_DIR / "calibration_manifest.json", calibration_manifest)

    calibration_index = load_calibration_rows()
    candidates = load_candidates()
    chunks = chunk_candidates(candidates)
    candidates_by_id = {str(candidate["candidate_id"]): candidate for candidate in candidates}

    manifest_fieldnames = [
        "candidate_id",
        "source_run_id",
        "source_file",
        "candidate_kind",
        "candidate_rank",
        "current_score",
        "current_score_name",
        "truth_match_ratio",
        "label",
        "label_confidence",
        "direction",
        "token_count",
        "candidate_text_or_token_path",
        "notes",
        "fixture_seed",
        "search_seed",
        "token_hash",
    ]
    write_csv(OUTPUT_DIR / "candidate_manifest_resolved.csv", candidates, manifest_fieldnames)

    chunk_fieldnames = [
        "candidate_chunk_id",
        "candidate_id",
        "chunk_index",
        "chunk_start",
        "chunk_end",
        "token_count",
        "chunk_status",
        "direction",
    ]
    write_csv(OUTPUT_DIR / "candidate_chunk_manifest.csv", chunks, chunk_fieldnames)

    feature_rows, timing_rows = score_candidate_chunks(chunks, candidates_by_id, calibration_index)
    feature_fieldnames = [
        "candidate_id",
        "candidate_chunk_id",
        "candidate_kind",
        "candidate_rank",
        "label",
        "label_confidence",
        "source_run_id",
        "source_file",
        "current_score",
        "current_score_name",
        "truth_match_ratio",
        "chunk_index",
        "chunk_token_count",
        "chunk_status",
        "direction",
        "score_region",
        "start_shift",
        "dictionary_cut",
        "ladder_profile",
        "span_length",
        "hd",
        "feature_name",
        "candidate_value",
        "comparison_null_model",
        "comparison_null_class",
        "calibration_damage_model",
        "calibration_damage_level",
        "damaged_mean",
        "damaged_stddev",
        "null_mean",
        "null_stddev",
        "damaged_percentile",
        "comparison_null_percentile",
        "signed_effect_vs_comparison_null",
        "signed_effect_vs_local_null",
        "signed_effect_vs_block_shuffle",
        "calibration_n_chunks",
        "calibration_n_samples",
        "calibration_cohen_d",
        "panels",
    ]
    write_csv_gz(OUTPUT_DIR / "candidate_feature_rows.csv.gz", feature_rows, feature_fieldnames)
    write_csv(OUTPUT_DIR / "score_timing_rows.csv", timing_rows, ["candidate_chunk_id", "dictionary_cut", "elapsed_ms", "raw_feature_rows"])

    panel_rows = summarize_panels(feature_rows)
    panel_fieldnames = [
        "candidate_id",
        "candidate_chunk_id",
        "panel_id",
        "label",
        "candidate_kind",
        "source_run_id",
        "candidate_rank",
        "current_score",
        "truth_match_ratio",
        "panel_feature_count",
        "panel_mean_signed_effect",
        "panel_median_signed_effect",
        "panel_p90_signed_effect",
        "panel_fraction_positive",
        "panel_fraction_above_threshold",
        "panel_top_supporting_features",
        "panel_top_warning_features",
    ]
    write_csv(OUTPUT_DIR / "candidate_panel_summary.csv", panel_rows, panel_fieldnames)

    candidate_level_rows = summarize_candidates(panel_rows)
    candidate_level_fieldnames = [
        "candidate_id",
        "panel_id",
        "label",
        "candidate_kind",
        "source_run_id",
        "candidate_rank",
        "current_score",
        "truth_match_ratio",
        "chunk_count",
        "best_chunk_score",
        "mean_chunk_score",
        "median_chunk_score",
        "number_of_positive_chunks",
        "fraction_positive_chunks",
    ]
    write_csv(OUTPUT_DIR / "candidate_level_summary.csv", candidate_level_rows, candidate_level_fieldnames)

    pairwise_rows = build_pairwise_summary(candidate_level_rows)
    pairwise_fieldnames = [
        "pair_id",
        "candidate_a_id",
        "candidate_b_id",
        "current_scorer_preferred",
        "known_better_candidate",
        "current_scorer_correct",
        "span_hamming_panel_preferred",
        "span_hamming_rescues_current_misrank",
        "span_hamming_breaks_current_correct",
        "panel_scores_a",
        "panel_scores_b",
        "notes",
    ]
    write_csv(OUTPUT_DIR / "pairwise_road_test_summary.csv", pairwise_rows, pairwise_fieldnames)

    write_csv(OUTPUT_DIR / "top_supported_candidates.csv", top_rows(candidate_level_rows, warnings_only=False), candidate_level_fieldnames)
    write_csv(OUTPUT_DIR / "top_warning_candidates.csv", top_rows(candidate_level_rows, warnings_only=True), candidate_level_fieldnames)

    separation_rows = build_bad_candidate_separation(candidate_level_rows)
    separation_fieldnames = [
        "label",
        "panel_id",
        "candidate_count",
        "mean_score",
        "median_score",
        "p10_score",
        "p90_score",
        "fraction_above_threshold",
    ]
    write_csv(OUTPUT_DIR / "bad_candidate_separation_summary.csv", separation_rows, separation_fieldnames)

    elapsed_s = time.perf_counter() - start
    write_readout(
        candidates=candidates,
        chunks=chunks,
        feature_rows=feature_rows,
        panel_rows=panel_rows,
        candidate_level_rows=candidate_level_rows,
        pairwise_rows=pairwise_rows,
        separation_rows=separation_rows,
        elapsed_s=elapsed_s,
    )
    copy_review_pack()

    print(f"[{RUN_LABEL}] complete candidates={len(candidates)} chunks={len(chunks)} feature_rows={len(feature_rows)} elapsed={elapsed_s:.1f}s")
    print(f"[{RUN_LABEL}] output_dir={rel(OUTPUT_DIR)}")
    print(f"[{RUN_LABEL}] review_pack={rel(REVIEW_PACK_ZIP)}")


if __name__ == "__main__":
    main()
