from __future__ import annotations

import csv
import gzip
import json
import math
import sys
import time
from collections import Counter, defaultdict
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
SRC_DIR = REPO_ROOT / "src"
for path in (REPO_ROOT, SRC_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from rune_decrypter_prime.scoring.ngram_hamming.fast_backend import (  # noqa: E402
    fast_ngram_hamming_available,
    scan_chunk_fast,
)
from rune_decrypter_prime.scoring.ngram_hamming.reference import (  # noqa: E402
    PhraseEntry,
    PhraseProfile,
    profile_allows_entry,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (  # noqa: E402
    run_phaseB_ngram_hamming_balanced_readout_v1 as base,
)


RUN_LABEL = "phaseB_ngram_hamming_full_raw_canary_v1"
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_full_raw_canary_v1"
)
FULL_ASSET_SUMMARY_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_full_raw_assets_summary_v1/full_raw_asset_summary_manifest.json"
)
HARD_PAIR_DIR_REL = base.HARD_PAIR_DIR_REL
TOKEN_SOURCE_REL = (
    "planning/projects/no_wli/40_review_summaries/"
    "no_wli_historical_partial_text_and_scorer_review_pack_2026-05-02/"
    "historical_partial_texts/unique_partial_text_rows.csv"
)

REQUIRED_ASSET_MODE = "full"
SCAN_MODE = "whole_phrase_only"
INTERNAL_PHRASE_WINDOWS = False
DIRECTION = "fwd"
DICTIONARY_CUTS = ("normal", "strict")
NGRAM_ORDERS = (2, 3)
CANARY_STRATUM_TARGETS = {
    "known_better": 1,
    "known_worse": 1,
    "bad_control": 1,
}
MAX_CHUNKS_PER_CANDIDATE = 1
DEBUG_EXAMPLE_LIMIT = 2
PYTHON_FALLBACK_ALLOWED = False
BACKEND_IMPL = "cpp_fast"
NO_PRODUCTION_SCORER_CHANGES = True

PROFILES = (
    PhraseProfile(
        profile_id="P2_conservative_len8_hd2",
        direction=DIRECTION,
        orders=NGRAM_ORDERS,
        dictionary_cuts=DICTIONARY_CUTS,
        min_phrase_token_length=8,
        max_total_phrase_hd=2,
        max_word_hd=1,
    ),
    PhraseProfile(
        profile_id="P3_word_shape_guarded_len8_hd2",
        direction=DIRECTION,
        orders=NGRAM_ORDERS,
        dictionary_cuts=DICTIONARY_CUTS,
        min_phrase_token_length=8,
        max_total_phrase_hd=2,
        max_word_hd=1,
        exact_match_word_lengths=(1, 2),
    ),
)

REQUIRED_PHRASE_INDEX_FIELDS = {
    "phrase_id",
    "direction",
    "dictionary_cut",
    "ngram_order",
    "word_token_ids",
    "rune_token_ids",
    "word_lengths",
    "phrase_token_length",
    "count",
    "sum_count",
    "max_count",
    "log_count",
    "max_log_count",
    "phrase_count",
    "top_latin_ngram_for_max_count",
}


def repo_rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def ensure_under_repo(path: Path) -> None:
    path.resolve().relative_to(REPO_ROOT.resolve())
    path.parent.mkdir(parents=True, exist_ok=True)


def read_json(rel_path: str) -> dict[str, Any]:
    return json.loads((REPO_ROOT / rel_path).read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    ensure_under_repo(path)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    ensure_under_repo(path)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    ensure_under_repo(path)
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + ("\n" if rows else ""), encoding="utf-8")


def validate_full_asset_summary(manifest: dict[str, Any]) -> list[str]:
    blocked: list[str] = []
    if manifest.get("asset_mode") != REQUIRED_ASSET_MODE:
        blocked.append("required_asset_mode=full but actual_asset_mode is not full")
    if manifest.get("full_asset_available") is not True:
        blocked.append("full_asset_available is not true")
    if manifest.get("full_raw_ngram_rebuild_confirmed") is not True:
        blocked.append("full_raw_ngram_rebuild_confirmed is not true")
    if manifest.get("sample_line_limit_per_order") is not None:
        blocked.append("sample_line_limit_per_order is present/non-null")
    if manifest.get("scan_mode") != SCAN_MODE:
        blocked.append("scan_mode is not whole_phrase_only")
    if manifest.get("internal_phrase_windows") is not False:
        blocked.append("internal_phrase_windows is not false")
    phrase_index = manifest.get("phrase_index_path", "")
    blocked.extend(validate_phrase_index_path(str(phrase_index), manifest))
    return blocked


def validate_phrase_index_path(phrase_index: str, manifest: dict[str, Any]) -> list[str]:
    blocked: list[str] = []
    if not phrase_index:
        return ["full raw phrase index is missing"]
    if not phrase_index.endswith(".jsonl.gz"):
        blocked.append("full raw phrase index path must end with .jsonl.gz")
    path = REPO_ROOT / phrase_index
    if not path.exists():
        blocked.append("full raw phrase index is missing")
        return blocked
    first_row: dict[str, Any] | None = None
    rows_checked = 0
    invalid_rows = 0
    invalid_examples: list[str] = []
    try:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                rows_checked += 1
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    invalid_rows += 1
                    if len(invalid_examples) < 5:
                        invalid_examples.append(f"row {rows_checked}: invalid JSON")
                    continue
                if first_row is None:
                    first_row = row
                row_errors = validate_phrase_index_row(row, rows_checked)
                if row_errors:
                    invalid_rows += 1
                    invalid_examples.extend(row_errors[: max(0, 5 - len(invalid_examples))])
    except Exception as exc:
        blocked.append(f"full raw phrase index is not readable gzip JSONL: {type(exc).__name__}")
        return blocked
    if first_row is None:
        blocked.append("full raw phrase index is empty")
        return blocked
    if invalid_rows:
        blocked.append(
            f"full raw phrase index validation failed: rows_checked={rows_checked}, invalid_rows={invalid_rows}, "
            f"examples={'; '.join(invalid_examples)}"
        )
    if int(manifest.get("phrase_entry_count", 0) or 0) <= 0:
        blocked.append("phrase_entry_count must be > 0")
    if int(manifest.get("phrase_index_rows_checked", rows_checked) or 0) <= 0:
        blocked.append("phrase_index_rows_checked must be > 0")
    if int(manifest.get("phrase_index_invalid_row_count", invalid_rows) or 0) != 0:
        blocked.append("phrase_index_invalid_row_count must be 0")
    return blocked


def validate_phrase_index_row(row: dict[str, Any], row_number: int) -> list[str]:
    errors: list[str] = []
    missing_fields = sorted(REQUIRED_PHRASE_INDEX_FIELDS - set(row))
    if missing_fields:
        return [f"row {row_number}: missing required fields: {', '.join(missing_fields)}"]
    word_token_ids = row["word_token_ids"]
    rune_token_ids = row["rune_token_ids"]
    word_lengths = row["word_lengths"]
    if not isinstance(word_token_ids, list) or not word_token_ids:
        return [f"row {row_number}: word_token_ids is empty or not a list"]
    if not isinstance(rune_token_ids, list) or not rune_token_ids:
        return [f"row {row_number}: rune_token_ids is empty or not a list"]
    if not isinstance(word_lengths, list) or not word_lengths:
        return [f"row {row_number}: word_lengths is empty or not a list"]
    token_errors = validate_word_token_ids(word_token_ids, row_number)
    token_errors.extend(validate_flat_token_ids(rune_token_ids, row_number, "rune_token_ids"))
    token_errors.extend(validate_word_lengths(word_lengths, row_number))
    token_errors.extend(validate_int_field(row.get("phrase_token_length"), row_number, "phrase_token_length", positive=True))
    token_errors.extend(validate_int_field(row.get("ngram_order"), row_number, "ngram_order", positive=True))
    token_errors.extend(validate_numeric_field(row.get("count"), row_number, "count", non_negative=True))
    token_errors.extend(validate_numeric_field(row.get("sum_count"), row_number, "sum_count", non_negative=True))
    token_errors.extend(validate_numeric_field(row.get("max_count"), row_number, "max_count", non_negative=True))
    token_errors.extend(validate_numeric_field(row.get("log_count"), row_number, "log_count", non_negative=True))
    token_errors.extend(validate_numeric_field(row.get("max_log_count"), row_number, "max_log_count", non_negative=True))
    token_errors.extend(validate_int_field(row.get("phrase_count"), row_number, "phrase_count", positive=True))
    if token_errors:
        return token_errors
    phrase_token_length = row["phrase_token_length"]
    ngram_order = row["ngram_order"]
    if phrase_token_length != len(rune_token_ids):
        errors.append(f"row {row_number}: phrase_token_length != len(rune_token_ids)")
    if word_lengths != [len(word) for word in word_token_ids]:
        errors.append(f"row {row_number}: word_lengths != lengths of word_token_ids")
    if sum(word_lengths) != phrase_token_length:
        errors.append(f"row {row_number}: sum(word_lengths) != phrase_token_length")
    if [token for word in word_token_ids for token in word] != rune_token_ids:
        errors.append(f"row {row_number}: flatten(word_token_ids) != rune_token_ids")
    if ngram_order != len(word_token_ids):
        errors.append(f"row {row_number}: ngram_order != len(word_token_ids)")
    if row["direction"] not in (DIRECTION,):
        errors.append(f"row {row_number}: direction outside required set")
    if row["dictionary_cut"] not in DICTIONARY_CUTS:
        errors.append(f"row {row_number}: dictionary_cut outside required set")
    if ngram_order not in NGRAM_ORDERS:
        errors.append(f"row {row_number}: ngram_order outside required set")
    return errors


def validate_int_field(value: Any, row_number: int, field_name: str, *, positive: bool) -> list[str]:
    if isinstance(value, bool) or not isinstance(value, int):
        return [f"row {row_number}: {field_name} must be an integer"]
    if positive and value <= 0:
        return [f"row {row_number}: {field_name} must be positive"]
    return []


def validate_numeric_field(value: Any, row_number: int, field_name: str, *, non_negative: bool) -> list[str]:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return [f"row {row_number}: {field_name} must be numeric"]
    if not math.isfinite(float(value)):
        return [f"row {row_number}: {field_name} must be finite"]
    if non_negative and float(value) < 0:
        return [f"row {row_number}: {field_name} must be non-negative"]
    return []


def validate_flat_token_ids(values: Any, row_number: int, field_name: str) -> list[str]:
    if not isinstance(values, list) or not values:
        return [f"row {row_number}: {field_name} is empty or not a list"]
    errors: list[str] = []
    for token in values:
        if isinstance(token, bool) or not isinstance(token, int):
            errors.append(f"row {row_number}: {field_name} contains non-integer token")
            break
        if token < 0 or token > 28:
            errors.append(f"row {row_number}: {field_name} token outside 0..28")
            break
    return errors


def validate_word_token_ids(words: Any, row_number: int) -> list[str]:
    if not isinstance(words, list) or not words:
        return [f"row {row_number}: word_token_ids is empty or not a list"]
    errors: list[str] = []
    for word in words:
        if not isinstance(word, list) or not word:
            errors.append(f"row {row_number}: word_token_ids contains empty/non-list word")
            break
        errors.extend(validate_flat_token_ids(word, row_number, "word_token_ids"))
        if errors:
            break
    return errors


def validate_word_lengths(lengths: Any, row_number: int) -> list[str]:
    if not isinstance(lengths, list) or not lengths:
        return [f"row {row_number}: word_lengths is empty or not a list"]
    errors: list[str] = []
    for length in lengths:
        if isinstance(length, bool) or not isinstance(length, int):
            errors.append(f"row {row_number}: word_lengths contains non-integer value")
            break
        if length <= 0:
            errors.append(f"row {row_number}: word_lengths contains non-positive value")
            break
    return errors


def read_csv_rows(rel_path: str) -> list[dict[str, str]]:
    with (REPO_ROOT / rel_path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def candidate_role(row: dict[str, str]) -> str:
    winner = base.parse_int(row.get("winner_count", ""))
    challenger = base.parse_int(row.get("challenger_count", ""))
    truth = base.parse_float(row.get("truth_match_ratio", ""))
    label = row.get("label", "")
    if winner > 0 and challenger == 0:
        return "known_better"
    if challenger > 0 and winner == 0:
        return "known_worse"
    if truth <= 0.15 or label in {"known_bad", "likely_bad"}:
        return "bad_control"
    return "other"


def select_canary_candidates() -> tuple[list[dict[str, Any]], dict[str, list[dict[str, str]]], dict[str, str]]:
    candidate_rows = read_csv_rows(f"{HARD_PAIR_DIR_REL}/candidate_manifest_resolved.csv")
    chunk_rows = read_csv_rows(f"{HARD_PAIR_DIR_REL}/candidate_chunk_manifest.csv")
    chunks_by_candidate: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in chunk_rows:
        if row.get("chunk_status") == "full_chunk":
            chunks_by_candidate[row["candidate_id"]].append(row)
    for rows in chunks_by_candidate.values():
        rows.sort(key=lambda item: base.parse_int(item.get("chunk_index", "")))
    selected: list[dict[str, Any]] = []
    selected_counts = {key: 0 for key in CANARY_STRATUM_TARGETS}
    for row in sorted(candidate_rows, key=lambda item: item.get("candidate_id", "")):
        if row.get("direction") != DIRECTION:
            continue
        if row.get("candidate_id", "") not in chunks_by_candidate:
            continue
        role = candidate_role(row)
        if role not in CANARY_STRATUM_TARGETS:
            continue
        if selected_counts[role] >= CANARY_STRATUM_TARGETS[role]:
            continue
        selected_counts[role] += 1
        selected.append(
            {
                "candidate_id": row["candidate_id"],
                "selection_role": role,
                "truth_match_ratio": base.parse_float(row.get("truth_match_ratio", "")),
                "current_score": base.parse_float(row.get("current_score", "")),
                "chunk_count_available": len(chunks_by_candidate[row["candidate_id"]]),
                "selection_status": "selected",
            }
        )
    missing = {
        role: f"target {target}, selected {selected_counts[role]}"
        for role, target in CANARY_STRATUM_TARGETS.items()
        if selected_counts[role] < target
    }
    if missing:
        for role, reason in missing.items():
            selected.append(
                {
                    "candidate_id": "",
                    "selection_role": role,
                    "selection_status": "missing",
                    "missing_reason": reason,
                }
            )
    return selected, chunks_by_candidate, missing


def load_tokens(selected: list[dict[str, Any]]) -> dict[str, list[int]]:
    selected_ids = {row["candidate_id"] for row in selected if row.get("candidate_id")}
    hashes = {base.candidate_hash_from_id(candidate_id) for candidate_id in selected_ids}
    return base.load_token_map(hashes, TOKEN_SOURCE_REL)


def phrase_entry_from_index_row(row: dict[str, Any]) -> PhraseEntry:
    return PhraseEntry(
        phrase_id=str(row["phrase_id"]),
        direction=str(row["direction"]),
        dictionary_cut=str(row["dictionary_cut"]),
        ngram_order=int(row["ngram_order"]),
        word_token_ids=tuple(tuple(int(token) for token in word) for word in row["word_token_ids"]),
        rune_token_ids=tuple(int(token) for token in row["rune_token_ids"]),
        count=float(row.get("count", 0.0) or 0.0),
        log_count=float(row.get("log_count", 0.0) or 0.0),
        phrase_count=int(row.get("phrase_count", 1) or 1),
        top_latin_ngram=str(row.get("top_latin_ngram", "")),
    )


def load_phrase_entries(phrase_index_rel: str) -> dict[tuple[str, int], list[PhraseEntry]]:
    entries: dict[tuple[str, int], list[PhraseEntry]] = {(cut, order): [] for cut in DICTIONARY_CUTS for order in NGRAM_ORDERS}
    with gzip.open(REPO_ROOT / phrase_index_rel, "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            key = (str(row.get("dictionary_cut", "")), int(row.get("ngram_order", -1)))
            if row.get("direction") == DIRECTION and key in entries:
                entries[key].append(phrase_entry_from_index_row(row))
    return entries


def load_phrase_metadata(phrase_index_rel: str) -> dict[str, dict[str, Any]]:
    metadata: dict[str, dict[str, Any]] = {}
    with gzip.open(REPO_ROOT / phrase_index_rel, "rt", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            phrase_id = str(row.get("phrase_id", ""))
            if not phrase_id:
                continue
            metadata[phrase_id] = {
                "sum_count": float(row.get("sum_count", row.get("count", 0.0)) or 0.0),
                "max_count": float(row.get("max_count", row.get("count", 0.0)) or 0.0),
                "max_log_count": float(row.get("max_log_count", row.get("log_count", 0.0)) or 0.0),
                "duplicate_row_count": int(row.get("duplicate_row_count", 0) or 0),
                "top_latin_ngram_for_max_count": str(
                    row.get("top_latin_ngram_for_max_count", row.get("top_latin_ngram", "")) or ""
                ),
            }
    return metadata


def length_bin(length: int) -> str:
    if length <= 10:
        return "8-10"
    if length <= 15:
        return "11-15"
    if length <= 20:
        return "16-20"
    return "21+"


def fraction_bin(value: float) -> str:
    if value <= 0.0:
        return "0"
    if value <= 0.25:
        return "0-0.25"
    if value <= 0.50:
        return "0.25-0.50"
    if value <= 0.75:
        return "0.50-0.75"
    return "0.75-1.0"


def token_count_bin(value: int) -> str:
    if value <= 0:
        return "0"
    if value <= 5:
        return "1-5"
    if value <= 10:
        return "6-10"
    if value <= 20:
        return "11-20"
    return "21+"


def normalised_hd_bin(value: float) -> str:
    if value <= 0.0:
        return "0"
    if value <= 0.10:
        return "0-0.10"
    if value <= 0.20:
        return "0.10-0.20"
    if value <= 0.30:
        return "0.20-0.30"
    return "0.30+"


def log_count_bin(value: float) -> str:
    if value < 5.0:
        return "low"
    if value < 10.0:
        return "medium"
    if value < 15.0:
        return "high"
    return "very_high"


def hit_payload(
    hit: dict[str, Any],
    *,
    candidate_role_value: str,
    profile_id: str,
    phrase_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    word_lengths = [int(value) for value in hit["word_lengths"]]
    word_hds = [int(value) for value in hit["word_hds"]]
    short_pairs = [(length, hd) for length, hd in zip(word_lengths, word_hds) if length <= 2]
    non_short_pairs = [(length, hd) for length, hd in zip(word_lengths, word_hds) if length > 2]
    short_word_count = len(short_pairs)
    short_word_token_count = sum(length for length, _ in short_pairs)
    short_word_hd = sum(hd for _, hd in short_pairs)
    non_short_word_count = len(non_short_pairs)
    non_short_word_token_count = sum(length for length, _ in non_short_pairs)
    non_short_word_hd = sum(hd for _, hd in non_short_pairs)
    short_word_mismatch_count = sum(1 for length, hd in zip(word_lengths, word_hds) if length <= 2 and hd > 0)
    phrase_token_length = int(hit["phrase_token_length"])
    phrase_log_count = float(hit["phrase_log_count"])
    metadata = phrase_metadata or {}
    total_phrase_hd = int(hit["total_phrase_hd"])
    normalised_total_hd = total_phrase_hd / phrase_token_length if phrase_token_length else 0.0
    normalised_non_short_hd = (
        non_short_word_hd / non_short_word_token_count if non_short_word_token_count else 0.0
    )
    short_word_fraction = short_word_token_count / phrase_token_length if phrase_token_length else 0.0
    return {
        "candidate_id": hit["candidate_id"],
        "chunk_id": hit["chunk_id"],
        "candidate_role": candidate_role_value,
        "profile_id": profile_id,
        "ngram_order": int(hit["ngram_order"]),
        "cut": hit["dictionary_cut"],
        "direction": DIRECTION,
        "phrase_token_length": phrase_token_length,
        "phrase_token_length_bin": length_bin(phrase_token_length),
        "word_lengths": word_lengths,
        "word_length_pattern": json.dumps(word_lengths, separators=(",", ":")),
        "word_hds": word_hds,
        "total_phrase_hd": total_phrase_hd,
        "total_phrase_hd_bin": str(total_phrase_hd),
        "normalised_total_hd": normalised_total_hd,
        "normalised_total_hd_bin": normalised_hd_bin(normalised_total_hd),
        "max_word_hd": int(hit["max_word_hd"]),
        "short_word_count": short_word_count,
        "short_word_token_count": short_word_token_count,
        "short_word_hd": short_word_hd,
        "short_word_mismatch_count": short_word_mismatch_count,
        "non_short_word_count": non_short_word_count,
        "non_short_word_token_count": non_short_word_token_count,
        "non_short_word_token_count_bin": token_count_bin(non_short_word_token_count),
        "non_short_word_hd": non_short_word_hd,
        "short_word_fraction_of_phrase": short_word_fraction,
        "short_word_fraction_of_phrase_bin": fraction_bin(short_word_fraction),
        "normalised_non_short_hd": normalised_non_short_hd,
        "normalised_non_short_hd_bin": normalised_hd_bin(normalised_non_short_hd),
        "phrase_count": int(hit["phrase_count"]),
        "phrase_log_count": phrase_log_count,
        "sum_count": float(metadata.get("sum_count", hit.get("count", 0.0)) or 0.0),
        "max_count": float(metadata.get("max_count", hit.get("count", 0.0)) or 0.0),
        "max_log_count": float(metadata.get("max_log_count", phrase_log_count) or 0.0),
        "duplicate_row_count": int(metadata.get("duplicate_row_count", 0) or 0),
        "top_latin_ngram_for_max_count": str(metadata.get("top_latin_ngram_for_max_count", "") or ""),
        "phrase_log_count_bin": log_count_bin(phrase_log_count),
        "hit_start": int(hit["hit_start"]),
        "hit_end": int(hit["hit_end"]),
        "phrase_id": hit["phrase_id"],
    }


def aggregate_hit_rows(hit_rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    length_rows: Counter[tuple[str, str, str, int, str, str]] = Counter()
    weighted_by_length: defaultdict[tuple[str, str, str, int, str, str], float] = defaultdict(float)
    pattern_rows: Counter[tuple[str, str, str, int, str, str]] = Counter()
    freq_rows: Counter[tuple[str, str, str, int, str, str]] = Counter()
    total_hd_rows: Counter[tuple[str, str, str, int, str, str]] = Counter()
    normalised_hd_rows: Counter[tuple[str, str, str, int, str, str]] = Counter()
    short_fraction_rows: Counter[tuple[str, str, str, int, str, str]] = Counter()
    non_short_token_rows: Counter[tuple[str, str, str, int, str, str]] = Counter()
    non_short_hd_rows: Counter[tuple[str, str, str, int, str, str]] = Counter()
    for row in hit_rows:
        base_key = (row["profile_id"], row["cut"], row["direction"], int(row["ngram_order"]), row["candidate_role"])
        key = (*base_key, row["phrase_token_length_bin"])
        length_rows[key] += 1
        weighted_by_length[key] += float(row["phrase_log_count"])
        pattern_rows[(*base_key, row["word_length_pattern"])] += 1
        freq_rows[(*base_key, row["phrase_log_count_bin"])] += 1
        total_hd_rows[(*base_key, row["total_phrase_hd_bin"])] += 1
        normalised_hd_rows[(*base_key, row["normalised_total_hd_bin"])] += 1
        short_fraction_rows[(*base_key, row["short_word_fraction_of_phrase_bin"])] += 1
        non_short_token_rows[(*base_key, row["non_short_word_token_count_bin"])] += 1
        non_short_hd_rows[(*base_key, row["normalised_non_short_hd_bin"])] += 1
    length_out = [
        {
            "profile_id": profile,
            "cut": cut,
            "direction": direction,
            "ngram_order": order,
            "candidate_role": role,
            "phrase_token_length_bin": bin_name,
            "hit_count": count,
            "weighted_hit_sum": weighted_by_length[(profile, cut, direction, order, role, bin_name)],
        }
        for (profile, cut, direction, order, role, bin_name), count in sorted(length_rows.items())
    ]
    pattern_out = [
        {
            "profile_id": profile,
            "cut": cut,
            "direction": direction,
            "ngram_order": order,
            "candidate_role": role,
            "word_length_pattern": pattern,
            "hit_count": count,
        }
        for (profile, cut, direction, order, role, pattern), count in sorted(pattern_rows.items())
    ]
    freq_out = [
        {
            "profile_id": profile,
            "cut": cut,
            "direction": direction,
            "ngram_order": order,
            "candidate_role": role,
            "phrase_log_count_bin": bin_name,
            "hit_count": count,
        }
        for (profile, cut, direction, order, role, bin_name), count in sorted(freq_rows.items())
    ]
    def rows_for(counter: Counter[tuple[str, str, str, int, str, str]], field_name: str) -> list[dict[str, Any]]:
        return [
            {
                "profile_id": profile,
                "cut": cut,
                "direction": direction,
                "ngram_order": order,
                "candidate_role": role,
                field_name: bin_name,
                "hit_count": count,
            }
            for (profile, cut, direction, order, role, bin_name), count in sorted(counter.items())
        ]
    return {
        "hit_summary_by_phrase_length_bin.csv": length_out,
        "word_length_pattern_distribution.csv": pattern_out,
        "phrase_log_count_bin_distribution.csv": freq_out,
        "total_hd_distribution.csv": rows_for(total_hd_rows, "total_phrase_hd_bin"),
        "normalised_total_hd_distribution.csv": rows_for(normalised_hd_rows, "normalised_total_hd_bin"),
        "short_word_fraction_distribution.csv": rows_for(short_fraction_rows, "short_word_fraction_of_phrase_bin"),
        "non_short_word_token_count_distribution.csv": rows_for(non_short_token_rows, "non_short_word_token_count_bin"),
        "normalised_non_short_hd_distribution.csv": rows_for(non_short_hd_rows, "normalised_non_short_hd_bin"),
    }


def compare_p2_p3(hit_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: defaultdict[tuple[str, str, str, int, str, str], dict[str, set[tuple[str, int, int]]]] = defaultdict(
        lambda: {"P2": set(), "P3": set()}
    )
    for row in hit_rows:
        key = (
            row["candidate_id"],
            row["chunk_id"],
            row["direction"],
            row["ngram_order"],
            row["cut"],
            row["candidate_role"],
        )
        hit_key = (row["phrase_id"], row["hit_start"], row["hit_end"])
        if row["profile_id"].startswith("P2_"):
            grouped[key]["P2"].add(hit_key)
        elif row["profile_id"].startswith("P3_"):
            grouped[key]["P3"].add(hit_key)
    out: list[dict[str, Any]] = []
    for key, values in sorted(grouped.items()):
        p2 = values["P2"]
        p3 = values["P3"]
        candidate_id, chunk_id, direction, order, cut, role = key
        out.append(
            {
                "candidate_id": candidate_id,
                "chunk_id": chunk_id,
                "direction": direction,
                "ngram_order": order,
                "cut": cut,
                "candidate_role": role,
                "p2_hit_count": len(p2),
                "p3_retained_hit_count": len(p3),
                "p2_only_rejected_by_p3_count": len(p2 - p3),
            }
        )
    return out


def candidate_chunk_profile_aggregate_rows(
    cell_rows: list[dict[str, Any]],
    hit_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: defaultdict[tuple[str, str, str, str, int, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in hit_rows:
        grouped[
            (
                row["candidate_id"],
                row["chunk_id"],
                row["candidate_role"],
                row["cut"],
                int(row["ngram_order"]),
                row["direction"],
                row["profile_id"],
            )
        ].append(row)
    retention_by_cell = {
        (
            row["candidate_id"],
            row["chunk_id"],
            row["candidate_role"],
            row["cut"],
            int(row["ngram_order"]),
            row["direction"],
        ): row
        for row in compare_p2_p3(hit_rows)
    }
    out: list[dict[str, Any]] = []
    cell_keys = [
        (
            row["candidate_id"],
            row["chunk_id"],
            row["candidate_role"],
            row["cut"],
            int(row["ngram_order"]),
            row["direction"],
            row["profile_id"],
        )
        for row in cell_rows
    ]
    for (candidate_id, chunk_id, role, cut, order, direction, profile_id) in sorted(set(cell_keys)):
        rows = grouped.get((candidate_id, chunk_id, role, cut, order, direction, profile_id), [])
        phrase_log_counts = [float(row["phrase_log_count"]) for row in rows]
        unique_phrases = {row["phrase_id"] for row in rows}
        retention = retention_by_cell.get((candidate_id, chunk_id, role, cut, order, direction), {})
        out.append(
            {
                "candidate_id": candidate_id,
                "chunk_id": chunk_id,
                "candidate_role": role,
                "cut": cut,
                "direction": direction,
                "ngram_order": order,
                "profile_id": profile_id,
                "raw_hit_count": len(rows),
                "unique_phrase_hit_count": len(unique_phrases),
                "weighted_hit_sum": sum(phrase_log_counts),
                "max_phrase_log_count": max(phrase_log_counts) if phrase_log_counts else 0.0,
                "mean_phrase_log_count": sum(phrase_log_counts) / len(phrase_log_counts) if phrase_log_counts else 0.0,
                "cell_p2_hit_count": int(retention.get("p2_hit_count", 0) or 0),
                "cell_p3_retained_hit_count": int(retention.get("p3_retained_hit_count", 0) or 0),
                "cell_p2_only_rejected_by_p3_count": int(retention.get("p2_only_rejected_by_p3_count", 0) or 0),
                "phrase_length_bin_breakdown": json.dumps(Counter(row["phrase_token_length_bin"] for row in rows), sort_keys=True),
                "word_length_pattern_breakdown": json.dumps(Counter(row["word_length_pattern"] for row in rows), sort_keys=True),
                "short_word_fraction_breakdown": json.dumps(
                    Counter(row["short_word_fraction_of_phrase_bin"] for row in rows),
                    sort_keys=True,
                ),
                "non_short_word_token_count_breakdown": json.dumps(
                    Counter(row["non_short_word_token_count_bin"] for row in rows),
                    sort_keys=True,
                ),
                "frequency_log_count_breakdown": json.dumps(Counter(row["phrase_log_count_bin"] for row in rows), sort_keys=True),
                "total_hd_breakdown": json.dumps(Counter(row["total_phrase_hd_bin"] for row in rows), sort_keys=True),
                "normalised_hd_breakdown": json.dumps(Counter(row["normalised_total_hd_bin"] for row in rows), sort_keys=True),
                "normalised_non_short_hd_breakdown": json.dumps(
                    Counter(row["normalised_non_short_hd_bin"] for row in rows),
                    sort_keys=True,
                ),
            }
        )
    return out


def run_canary() -> dict[str, Any]:
    started = time.perf_counter()
    output_dir = REPO_ROOT / OUTPUT_DIR_REL
    ensure_under_repo(output_dir / "canary_manifest.json")
    asset_summary = read_json(FULL_ASSET_SUMMARY_REL)
    blocked = validate_full_asset_summary(asset_summary)
    if not fast_ngram_hamming_available():
        blocked.append("_ngram_hamming_fast extension is unavailable")
    selected, chunks_by_candidate, missing_selection = select_canary_candidates()
    runnable_selected = [row for row in selected if row.get("candidate_id")]
    if missing_selection:
        blocked.extend(f"missing canary stratum {role}: {reason}" for role, reason in missing_selection.items())
    phrase_entries = {} if blocked else load_phrase_entries(asset_summary["phrase_index_path"])
    selected_tokens = {} if blocked else load_tokens(runnable_selected)
    phrase_metadata = {} if blocked else load_phrase_metadata(asset_summary["phrase_index_path"])
    cell_rows: list[dict[str, Any]] = []
    hit_rows: list[dict[str, Any]] = []
    eligible_counts: dict[str, int] = {}
    scan_count = 0
    if not blocked:
        for selected_row in runnable_selected:
            candidate_id = selected_row["candidate_id"]
            role = selected_row["selection_role"]
            token_key = base.candidate_hash_from_id(candidate_id)
            tokens = selected_tokens[token_key]
            for chunk_row in chunks_by_candidate[candidate_id][:MAX_CHUNKS_PER_CANDIDATE]:
                chunk_tokens = tokens[base.parse_int(chunk_row["chunk_start"]) : base.parse_int(chunk_row["chunk_end"])]
                for cut in DICTIONARY_CUTS:
                    for order in NGRAM_ORDERS:
                        entries = phrase_entries[(cut, order)]
                        for profile in PROFILES:
                            scoped_profile = replace(profile, dictionary_cuts=(cut,), orders=(order,))
                            eligible = [entry for entry in entries if profile_allows_entry(entry, scoped_profile)]
                            eligible_counts[f"{cut}|{order}|{profile.profile_id}"] = len(eligible)
                            cell_started = time.perf_counter()
                            payload = scan_chunk_fast(
                                chunk_tokens,
                                eligible,
                                scoped_profile,
                                candidate_id=candidate_id,
                                chunk_id=chunk_row["candidate_chunk_id"],
                                damage_level="full_raw_canary",
                                debug_example_limit=DEBUG_EXAMPLE_LIMIT,
                            )
                            elapsed = time.perf_counter() - cell_started
                            attempts = int(payload["phrase_verification_attempts"])
                            cell_rows.append(
                                {
                                    "candidate_id": candidate_id,
                                    "chunk_id": chunk_row["candidate_chunk_id"],
                                    "candidate_role": role,
                                    "cut": cut,
                                    "direction": DIRECTION,
                                    "ngram_order": order,
                                    "profile_id": profile.profile_id,
                                    "eligible_phrase_count": len(eligible),
                                    "candidate_tokens_scanned": int(payload["candidate_tokens_scanned"]),
                                    "candidate_start_offsets_considered": int(payload["candidate_start_offsets_considered"]),
                                    "phrase_verification_attempts": attempts,
                                    "elapsed_seconds": elapsed,
                                    "attempts_per_second": attempts / elapsed if elapsed else 0.0,
                                    "hit_count": len(payload["phrase_hits"]),
                                }
                            )
                            for hit in payload["phrase_hits"]:
                                hit_rows.append(
                                    hit_payload(
                                        hit,
                                        candidate_role_value=role,
                                        profile_id=profile.profile_id,
                                        phrase_metadata=phrase_metadata.get(str(hit.get("phrase_id", "")), {}),
                                    )
                                )
                            scan_count += 1
                            print(
                                f"[{RUN_LABEL}] scan {scan_count} candidate={candidate_id} "
                                f"cut={cut} order={order} profile={profile.profile_id} "
                                f"attempts={attempts} elapsed={elapsed:.2f}s",
                                flush=True,
                            )
    elapsed_total = time.perf_counter() - started
    completed_attempts = sum(int(row["phrase_verification_attempts"]) for row in cell_rows)
    completed_seconds = sum(float(row["elapsed_seconds"]) for row in cell_rows)
    attempts_per_second = completed_attempts / completed_seconds if completed_seconds else 0.0
    canary_candidate_chunks = max(1, len(runnable_selected) * MAX_CHUNKS_PER_CANDIDATE)
    full_candidate_chunks = sum(
        1
        for rows in chunks_by_candidate.values()
        for row in rows[:MAX_CHUNKS_PER_CANDIDATE]
        if row.get("chunk_status") == "full_chunk"
    )
    projection_rows: list[dict[str, Any]] = []
    for scope_name, cuts in (
        ("normal_order2_order3_p2_p3", ("normal",)),
        ("normal_strict_order2_order3_p2_p3", DICTIONARY_CUTS),
    ):
        scoped_attempts = sum(
            int(row["phrase_verification_attempts"])
            for row in cell_rows
            if row["cut"] in cuts
        )
        scaled_attempts = int(scoped_attempts * (full_candidate_chunks / canary_candidate_chunks))
        projection_rows.append(
            {
                "scope": scope_name,
                "canary_attempts": scoped_attempts,
                "projected_full_attempts": scaled_attempts,
                "projected_runtime_seconds": scaled_attempts / attempts_per_second if attempts_per_second else 0.0,
                "projected_runtime_hours": scaled_attempts / attempts_per_second / 3600.0 if attempts_per_second else 0.0,
            }
        )
    aggregate_rows = aggregate_hit_rows(hit_rows)
    comparison_rows = compare_p2_p3(hit_rows)
    candidate_aggregate_rows = candidate_chunk_profile_aggregate_rows(cell_rows, hit_rows)
    manifest = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if not blocked and cell_rows else "blocked",
        "blocked_reasons": blocked,
        "asset_summary_manifest": FULL_ASSET_SUMMARY_REL,
        "required_asset_mode": REQUIRED_ASSET_MODE,
        "actual_asset_mode": asset_summary.get("asset_mode"),
        "full_raw_ngram_rebuild_confirmed": asset_summary.get("full_raw_ngram_rebuild_confirmed"),
        "sample_line_limit_per_order": asset_summary.get("sample_line_limit_per_order"),
        "scan_mode": SCAN_MODE,
        "internal_phrase_windows": INTERNAL_PHRASE_WINDOWS,
        "backend_impl": BACKEND_IMPL,
        "python_fallback_allowed": PYTHON_FALLBACK_ALLOWED,
        "production_scorer_changes": False,
        "profiles": [asdict(profile) for profile in PROFILES],
        "cuts": list(DICTIONARY_CUTS),
        "orders": list(NGRAM_ORDERS),
        "direction": DIRECTION,
        "selected_candidates": selected,
        "canary_candidate_chunk_count": canary_candidate_chunks,
        "full_candidate_chunk_count_for_projection": full_candidate_chunks,
        "completed_scan_cells": len(cell_rows),
        "phrase_verification_attempts": completed_attempts,
        "scan_elapsed_seconds": completed_seconds,
        "elapsed_seconds": elapsed_total,
        "attempts_per_second": attempts_per_second,
        "eligible_phrase_counts_by_cut_order_profile": eligible_counts,
        "projection_rows": projection_rows,
        "total_hit_count": len(hit_rows),
    }
    write_json(output_dir / "canary_manifest.json", manifest)
    write_csv(output_dir / "canary_cell_timing_rows.csv", cell_rows)
    write_jsonl(output_dir / "canary_hit_rows.jsonl", hit_rows)
    write_csv(output_dir / "p2_p3_hit_retention_rows.csv", comparison_rows)
    write_csv(output_dir / "candidate_chunk_profile_aggregate_rows.csv", candidate_aggregate_rows)
    for name, rows in aggregate_rows.items():
        write_csv(output_dir / name, rows)
    write_csv(output_dir / "runtime_projection_rows.csv", projection_rows)
    readout = [
        "# PhaseB N-Gram Hamming Full Raw Canary v1",
        "",
        f"Status: `{manifest['status']}`",
        "",
        f"- asset mode: `{manifest['actual_asset_mode']}`",
        f"- scan mode: `{SCAN_MODE}`",
        f"- internal phrase windows: `{INTERNAL_PHRASE_WINDOWS}`",
        f"- completed scan cells: `{manifest['completed_scan_cells']}`",
        f"- attempts/sec: `{manifest['attempts_per_second']:.3f}`",
        f"- total hits: `{manifest['total_hit_count']}`",
        "",
        "P2/P3 are whole-phrase evidence with a minimum length gate, not fixed-length 8-rune evidence.",
    ]
    if blocked:
        readout.extend(["", "## Blocked Reasons", ""])
        readout.extend(f"- `{reason}`" for reason in blocked)
    (output_dir / "readout.md").write_text("\n".join(readout) + "\n", encoding="utf-8")
    print(f"[{RUN_LABEL}] status={manifest['status']}")
    print(f"[{RUN_LABEL}] completed_scan_cells={manifest['completed_scan_cells']}")
    return manifest


def main() -> None:
    run_canary()


if __name__ == "__main__":
    main()
