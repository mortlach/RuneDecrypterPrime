from __future__ import annotations

import csv
import gzip
import json
import sys
import time
from collections import defaultdict
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


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
    PhraseHit,
    PhraseProfile,
    ReferenceScanResult,
    profile_allows_entry,
    scan_chunk_reference,
)


RUN_LABEL = "phaseB_ngram_hamming_exact_no_cap_full_pilot_v1"
CLAIM_MODE = "hard_pair_candidate_comparability"
CONTROLLED_DAMAGE_STREAM_REQUIRED = False
BACKEND_IMPL = "cpp_fast"
REFERENCE_BACKEND_IMPL = "python_reference"
PYTHON_FALLBACK_ALLOWED = False
NO_HIT_CAP = True

HARD_PAIR_DIR_REL = "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_span_hamming_hard_pair_road_test_v1"
CANDIDATE_FULL_TEXTS_REL = "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_span_hamming_candidate_manual_inspection_v1/candidate_full_texts.jsonl.gz"
PHRASE_INDEX_REL = "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_phrase_index_v1/phrase_index.jsonl.gz"
OUTPUT_DIR_REL = "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_exact_no_cap_full_pilot_v1"

DIRECTION = "fwd"
DICTIONARY_CUT = "normal"
NGRAM_ORDERS = (2, 3)
MAX_CANDIDATES = 10
MAX_CHUNKS_TOTAL = 20
MAX_CHUNKS_PER_CANDIDATE = 2
FULL_PILOT_TARGET_CANDIDATES = 10
FULL_PILOT_TARGET_CHUNKS_PER_CANDIDATE = 2
CHUNK_TOKEN_LENGTH = 500
DEBUG_EXAMPLE_LIMIT = 3
MAX_WALLCLOCK_SECONDS = 600.0
EARLY_PROJECTION_CHECK_CELLS = 12
EARLY_PROJECTION_STOP_SECONDS = 600.0

CONTROLLED_DAMAGE_FIELDS = (
    "sample_id",
    "chunk_id",
    "damage_model",
    "damage_level",
    "seed",
    "clean_token_hash",
    "damaged_token_hash",
    "candidate_id",
)

BASE_PROFILES = (
    PhraseProfile(
        profile_id="P0_exact_short",
        direction=DIRECTION,
        orders=NGRAM_ORDERS,
        dictionary_cuts=(DICTIONARY_CUT,),
        min_phrase_token_length=1,
        max_total_phrase_hd=0,
        max_word_hd=0,
    ),
    PhraseProfile(
        profile_id="P1_word_analogue_len7_hd2",
        direction=DIRECTION,
        orders=NGRAM_ORDERS,
        dictionary_cuts=(DICTIONARY_CUT,),
        min_phrase_token_length=7,
        max_total_phrase_hd=2,
        max_word_hd=2,
    ),
    PhraseProfile(
        profile_id="P2_conservative_len8_hd2",
        direction=DIRECTION,
        orders=NGRAM_ORDERS,
        dictionary_cuts=(DICTIONARY_CUT,),
        min_phrase_token_length=8,
        max_total_phrase_hd=2,
        max_word_hd=1,
    ),
)

CHUNK_FEATURE_FIELDS = (
    "candidate_id",
    "candidate_chunk_id",
    "chunk_index",
    "chunk_start",
    "chunk_end",
    "profile_id",
    "direction",
    "dictionary_cut",
    "ngram_order",
    "backend_impl",
    "phrase_hit_count",
    "unique_phrase_hit_count",
    "opportunity_count",
    "positive_start_offset_count",
    "phrase_hits_per_opportunity",
    "positive_start_offset_fraction",
    "mean_total_phrase_hd",
    "min_total_phrase_hd",
    "mean_normalised_phrase_hd",
    "best_normalised_phrase_hd",
    "weighted_hit_sum",
    "max_phrase_weight",
    "mean_phrase_weight",
    "candidate_tokens_scanned",
    "candidate_start_offsets_considered",
    "phrase_entries_considered",
    "phrase_verification_attempts",
    "phrase_verification_passes",
)

CELL_TIMING_FIELDS = (
    "candidate_id",
    "chunk_id",
    "profile_id",
    "ngram_order",
    "phrase_entry_count",
    "verification_attempts",
    "elapsed_seconds",
    "attempts_per_second",
    "hit_count",
)


def repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.name


def ensure_under_repo(path: Path) -> None:
    path.resolve().relative_to(REPO_ROOT.resolve())
    path.parent.mkdir(parents=True, exist_ok=True)


def read_csv_rows(rel_path: str) -> list[dict[str, str]]:
    with (REPO_ROOT / rel_path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def parse_bool(value: str) -> bool:
    return str(value).strip().lower() == "true"


def parse_float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def parse_int(value: str) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def parse_token_sequence(value: str) -> list[int]:
    tokens: list[int] = []
    for part in str(value).split():
        token = int(part)
        if token < 0 or token > 28:
            raise ValueError("candidate token outside 0..28")
        tokens.append(token)
    if not tokens:
        raise ValueError("empty candidate token sequence")
    return tokens


def candidate_hash_from_id(candidate_id: str) -> str:
    prefix = "hist_text_"
    return candidate_id[len(prefix) :] if candidate_id.startswith(prefix) else candidate_id


def token_hash_from_path(path_value: str) -> str:
    marker = "#partial_text_hash="
    if marker in path_value:
        return path_value.split(marker, 1)[1]
    return ""


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


def hit_payload(hit: PhraseHit | dict[str, Any]) -> dict[str, Any]:
    row = dict(hit) if isinstance(hit, dict) else asdict(hit)
    return {
        "candidate_id": row["candidate_id"],
        "chunk_id": row["chunk_id"],
        "damage_level": row["damage_level"],
        "profile_id": row["profile_id"],
        "ngram_order": int(row["ngram_order"]),
        "dictionary_cut": row["dictionary_cut"],
        "phrase_id": row["phrase_id"],
        "phrase_count": int(row["phrase_count"]),
        "phrase_log_count": float(row["phrase_log_count"]),
        "phrase_token_length": int(row["phrase_token_length"]),
        "word_lengths": [int(value) for value in row["word_lengths"]],
        "word_hds": [int(value) for value in row["word_hds"]],
        "total_phrase_hd": int(row["total_phrase_hd"]),
        "max_word_hd": int(row["max_word_hd"]),
        "mean_word_hd": float(row["mean_word_hd"]),
        "normalised_phrase_hd": float(row["normalised_phrase_hd"]),
        "hit_start": int(row["hit_start"]),
        "hit_end": int(row["hit_end"]),
    }


def reference_payload(result: ReferenceScanResult) -> dict[str, Any]:
    return {
        "phrase_hits": [hit_payload(hit) for hit in result.phrase_hits],
        "candidate_tokens_scanned": result.candidate_tokens_scanned,
        "candidate_start_offsets_considered": result.candidate_start_offsets_considered,
        "phrase_entries_considered": result.phrase_entries_considered,
        "phrase_verification_attempts": result.phrase_verification_attempts,
        "phrase_verification_passes": result.phrase_verification_passes,
        "opportunity_count": result.opportunity_count,
        "positive_start_offset_count": result.positive_start_offset_count,
        "phrase_hits_per_opportunity": result.phrase_hits_per_opportunity,
        "positive_start_offset_fraction": result.positive_start_offset_fraction,
        "debug_examples": [hit_payload(hit) for hit in result.debug_examples],
    }


def fast_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "phrase_hits": [hit_payload(hit) for hit in payload["phrase_hits"]],
        "candidate_tokens_scanned": int(payload["candidate_tokens_scanned"]),
        "candidate_start_offsets_considered": int(payload["candidate_start_offsets_considered"]),
        "phrase_entries_considered": int(payload["phrase_entries_considered"]),
        "phrase_verification_attempts": int(payload["phrase_verification_attempts"]),
        "phrase_verification_passes": int(payload["phrase_verification_passes"]),
        "opportunity_count": int(payload["opportunity_count"]),
        "positive_start_offset_count": int(payload["positive_start_offset_count"]),
        "phrase_hits_per_opportunity": float(payload["phrase_hits_per_opportunity"]),
        "positive_start_offset_fraction": float(payload["positive_start_offset_fraction"]),
        "debug_examples": [hit_payload(hit) for hit in payload["debug_examples"]],
    }


def scan_fast_payload(
    tokens: list[int],
    entries: list[PhraseEntry],
    profile: PhraseProfile,
    *,
    candidate_id: str,
    chunk_id: str,
    damage_level: str,
) -> dict[str, Any]:
    return fast_payload(
        scan_chunk_fast(
            tokens,
            entries,
            profile,
            candidate_id=candidate_id,
            chunk_id=chunk_id,
            damage_level=damage_level,
            debug_example_limit=DEBUG_EXAMPLE_LIMIT,
        )
    )


def scan_reference_payload(
    tokens: list[int],
    entries: list[PhraseEntry],
    profile: PhraseProfile,
    *,
    candidate_id: str,
    chunk_id: str,
    damage_level: str,
) -> dict[str, Any]:
    return reference_payload(
        scan_chunk_reference(
            tokens,
            entries,
            profile,
            candidate_id=candidate_id,
            chunk_id=chunk_id,
            damage_level=damage_level,
            debug_example_limit=DEBUG_EXAMPLE_LIMIT,
        )
    )


def feature_row_from_scan(
    payload: dict[str, Any],
    *,
    candidate_id: str,
    chunk_row: dict[str, str],
    profile: PhraseProfile,
    order: int,
) -> dict[str, Any]:
    hits = payload["phrase_hits"]
    total_hds = [int(hit["total_phrase_hd"]) for hit in hits]
    normalised_hds = [float(hit["normalised_phrase_hd"]) for hit in hits]
    weights = [float(hit["phrase_log_count"]) for hit in hits]
    return {
        "candidate_id": candidate_id,
        "candidate_chunk_id": chunk_row["candidate_chunk_id"],
        "chunk_index": parse_int(chunk_row["chunk_index"]),
        "chunk_start": parse_int(chunk_row["chunk_start"]),
        "chunk_end": parse_int(chunk_row["chunk_end"]),
        "profile_id": profile.profile_id,
        "direction": profile.direction,
        "dictionary_cut": DICTIONARY_CUT,
        "ngram_order": order,
        "backend_impl": BACKEND_IMPL,
        "phrase_hit_count": len(hits),
        "unique_phrase_hit_count": len({hit["phrase_id"] for hit in hits}),
        "opportunity_count": payload["opportunity_count"],
        "positive_start_offset_count": payload["positive_start_offset_count"],
        "phrase_hits_per_opportunity": payload["phrase_hits_per_opportunity"],
        "positive_start_offset_fraction": payload["positive_start_offset_fraction"],
        "mean_total_phrase_hd": sum(total_hds) / len(total_hds) if total_hds else 0.0,
        "min_total_phrase_hd": min(total_hds) if total_hds else "",
        "mean_normalised_phrase_hd": sum(normalised_hds) / len(normalised_hds) if normalised_hds else 0.0,
        "best_normalised_phrase_hd": min(normalised_hds) if normalised_hds else "",
        "weighted_hit_sum": sum(weights),
        "max_phrase_weight": max(weights) if weights else 0.0,
        "mean_phrase_weight": sum(weights) / len(weights) if weights else 0.0,
        "candidate_tokens_scanned": payload["candidate_tokens_scanned"],
        "candidate_start_offsets_considered": payload["candidate_start_offsets_considered"],
        "phrase_entries_considered": payload["phrase_entries_considered"],
        "phrase_verification_attempts": payload["phrase_verification_attempts"],
        "phrase_verification_passes": payload["phrase_verification_passes"],
    }


def load_phrase_entries() -> tuple[dict[int, list[PhraseEntry]], dict[str, Any]]:
    entries_by_order: dict[int, list[PhraseEntry]] = {order: [] for order in NGRAM_ORDERS}
    source_rows = 0
    with gzip.open(REPO_ROOT / PHRASE_INDEX_REL, "rt", encoding="utf-8") as handle:
        for line in handle:
            source_rows += 1
            row = json.loads(line)
            if row.get("direction") != DIRECTION:
                continue
            if row.get("dictionary_cut") != DICTIONARY_CUT:
                continue
            order = int(row.get("ngram_order", -1))
            if order not in entries_by_order:
                continue
            entries_by_order[order].append(phrase_entry_from_index_row(row))
    counts_by_order = {str(order): len(entries) for order, entries in entries_by_order.items()}
    if any(count == 0 for count in counts_by_order.values()):
        raise RuntimeError("missing phrase entries for at least one configured order")
    counts_by_profile_order: dict[str, int] = {}
    for profile in BASE_PROFILES:
        for order, entries in entries_by_order.items():
            profile_order = replace(profile, orders=(order,))
            counts_by_profile_order[f"{profile.profile_id}|{DICTIONARY_CUT}|{order}"] = sum(
                1 for entry in entries if profile_allows_entry(entry, profile_order)
            )
    return entries_by_order, {
        "phrase_index_path": PHRASE_INDEX_REL,
        "source_rows_read": source_rows,
        "direction": DIRECTION,
        "dictionary_cut": DICTIONARY_CUT,
        "orders": list(NGRAM_ORDERS),
        "entry_counts_by_order": counts_by_order,
        "loaded_phrase_entry_counts_by_profile_cut_order": counts_by_profile_order,
    }


def load_token_map(needed_hashes: set[str], token_source_rel: str) -> dict[str, list[int]]:
    token_map: dict[str, list[int]] = {}
    with (REPO_ROOT / token_source_rel).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            partial_hash = row.get("partial_text_hash", "")
            if partial_hash not in needed_hashes:
                continue
            token_map[partial_hash] = parse_token_sequence(row.get("token_sequence_text", ""))
            if len(token_map) == len(needed_hashes):
                break
    return token_map


def load_candidate_full_texts(selected_ids: set[str]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    path = REPO_ROOT / CANDIDATE_FULL_TEXTS_REL
    if not path.exists():
        return rows
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            candidate_id = str(row.get("candidate_id", ""))
            if candidate_id in selected_ids:
                rows[candidate_id] = row
    return rows


def select_candidates(
    candidate_rows: list[dict[str, str]],
    chunk_rows_by_candidate: dict[str, list[dict[str, str]]],
    summary_rows: list[dict[str, str]],
) -> dict[str, Any]:
    candidates = {row["candidate_id"]: row for row in candidate_rows}
    selected: list[dict[str, Any]] = []
    missing_strata: list[dict[str, str]] = []

    def usable(candidate_id: str) -> bool:
        row = candidates.get(candidate_id)
        chunks = chunk_rows_by_candidate.get(candidate_id, [])
        return bool(row and row.get("direction") == DIRECTION and len(chunks) >= MAX_CHUNKS_PER_CANDIDATE)

    def role_for_pair(row: dict[str, str], candidate_id: str) -> str:
        if candidate_id == row.get("known_better_candidate"):
            return "known_better"
        if candidate_id in (row.get("candidate_a_id"), row.get("candidate_b_id")):
            return "known_worse"
        return ""

    def add_candidate(stratum: str, candidate_id: str, pair_row: dict[str, str] | None) -> bool:
        if len(selected) >= MAX_CANDIDATES:
            return False
        if not candidate_id or not usable(candidate_id):
            return False
        if any(row["candidate_id"] == candidate_id for row in selected):
            return False
        candidate = candidates[candidate_id]
        selected.append(
            {
                "candidate_id": candidate_id,
                "selected_stratum": stratum,
                "source_pair_id": pair_row.get("pair_id", "") if pair_row else "",
                "known_better_or_worse_role": role_for_pair(pair_row, candidate_id) if pair_row else "",
                "current_score": parse_float(candidate.get("current_score", "")),
                "truth_match_ratio": parse_float(candidate.get("truth_match_ratio", "")),
                "pair_occurrence_count": parse_int(candidate.get("pair_occurrence_count", "")),
                "chunk_count_available": len(chunk_rows_by_candidate.get(candidate_id, [])),
                "selection_status": "selected",
            }
        )
        return True

    def mark_missing(stratum: str) -> None:
        missing_strata.append({"selected_stratum": stratum, "selection_status": "missing"})

    sorted_summary = sorted(summary_rows, key=lambda row: (row.get("pair_id", ""), row.get("candidate_a_id", "")))
    strata: list[tuple[str, Iterable[tuple[str, dict[str, str] | None]]]] = [
        (
            "current_scorer_correct_good_candidate",
            (
                (row.get("known_better_candidate", ""), row)
                for row in sorted_summary
                if parse_bool(row.get("current_scorer_correct", ""))
            ),
        ),
        (
            "current_scorer_misrank_rescue_opportunity",
            (
                (row.get("known_better_candidate", ""), row)
                for row in sorted_summary
                if not parse_bool(row.get("current_scorer_correct", ""))
            ),
        ),
        (
            "panel_a_rescue",
            (
                (row.get("known_better_candidate", ""), row)
                for row in sorted_summary
                if parse_bool(row.get("span_hamming_rescues_current_misrank", ""))
            ),
        ),
        (
            "panel_a_break_or_likely_false_positive",
            (
                (
                    row.get("candidate_b_id", "")
                    if row.get("candidate_a_id") == row.get("known_better_candidate")
                    else row.get("candidate_a_id", ""),
                    row,
                )
                for row in sorted_summary
                if parse_bool(row.get("span_hamming_breaks_current_correct", ""))
            ),
        ),
        (
            "high_current_score_bad_candidate",
            (
                (row.get("candidate_id", ""), None)
                for row in sorted(
                    candidate_rows,
                    key=lambda row: (-parse_float(row.get("current_score", "")), row.get("candidate_id", "")),
                )
                if row.get("label", "") in {"known_bad", "likely_bad"}
            ),
        ),
        (
            "repeated_bad_candidate",
            (
                (row.get("candidate_id", ""), None)
                for row in sorted(
                    candidate_rows,
                    key=lambda row: (-parse_int(row.get("pair_occurrence_count", "")), row.get("candidate_id", "")),
                )
                if row.get("label", "") in {"known_bad", "likely_bad"}
            ),
        ),
        (
            "low_score_control_candidate",
            (
                (row.get("candidate_id", ""), None)
                for row in sorted(candidate_rows, key=lambda row: (parse_float(row.get("current_score", "")), row.get("candidate_id", "")))
            ),
        ),
    ]
    for stratum, candidates_for_stratum in strata:
        if len(selected) >= MAX_CANDIDATES:
            missing_strata.append({"selected_stratum": stratum, "selection_status": "deferred_due_to_microbatch_cap"})
            continue
        added = False
        for candidate_id, pair_row in candidates_for_stratum:
            if add_candidate(stratum, candidate_id, pair_row):
                added = True
                break
        if not added:
            mark_missing(stratum)

    for row in sorted(candidate_rows, key=lambda item: item.get("candidate_id", "")):
        if len(selected) >= MAX_CANDIDATES:
            break
        add_candidate("stable_fill", row.get("candidate_id", ""), None)

    return {
        "selected_candidates": selected[:MAX_CANDIDATES],
        "missing_strata": missing_strata,
        "selection_config": {
            "max_candidates": MAX_CANDIDATES,
            "max_chunks_total": MAX_CHUNKS_TOTAL,
            "max_chunks_per_candidate": MAX_CHUNKS_PER_CANDIDATE,
            "chunk_token_length": CHUNK_TOKEN_LENGTH,
            "direction": DIRECTION,
        },
    }


def build_preflight(
    selected: list[dict[str, Any]],
    candidate_rows_by_id: dict[str, dict[str, str]],
    chunk_rows_by_candidate: dict[str, list[dict[str, str]]],
    hard_pair_rows: list[dict[str, str]],
) -> dict[str, Any]:
    selected_ids = {row["candidate_id"] for row in selected}
    full_text_rows = load_candidate_full_texts(selected_ids)
    token_source_paths = {
        candidate_rows_by_id[candidate_id]["candidate_text_or_token_path"].split("#", 1)[0]
        for candidate_id in selected_ids
        if candidate_id in candidate_rows_by_id
    }
    token_source_rel = sorted(token_source_paths)[0] if token_source_paths else ""
    selected_hashes = {
        candidate_rows_by_id[candidate_id].get("token_hash", "")
        for candidate_id in selected_ids
        if candidate_id in candidate_rows_by_id
    }
    token_map = load_token_map(set(selected_hashes), token_source_rel) if token_source_rel else {}
    hard_pair_candidate_ids = set()
    for row in hard_pair_rows:
        hard_pair_candidate_ids.add(row.get("candidate_a_id", ""))
        hard_pair_candidate_ids.add(row.get("candidate_b_id", ""))
    candidate_checks: list[dict[str, Any]] = []
    hard_pair_verified = True
    full_text_mismatches: list[str] = []
    for candidate_id in sorted(selected_ids):
        candidate = candidate_rows_by_id.get(candidate_id, {})
        chunks = chunk_rows_by_candidate.get(candidate_id, [])[:MAX_CHUNKS_PER_CANDIDATE]
        token_hash = candidate.get("token_hash", "")
        path_hash = token_hash_from_path(candidate.get("candidate_text_or_token_path", ""))
        id_hash = candidate_hash_from_id(candidate_id)
        primary_tokens = token_map.get(token_hash, [])
        full_text = full_text_rows.get(candidate_id)
        full_text_verified = False
        if full_text:
            full_tokens = parse_token_sequence(str(full_text.get("token_sequence_text", "")))
            full_text_verified = (
                str(full_text.get("token_hash", "")) == token_hash
                and int(full_text.get("token_count", 0)) == len(primary_tokens)
                and full_tokens == primary_tokens
            )
            if not full_text_verified:
                full_text_mismatches.append(candidate_id)
        chunk_ok = all(
            row.get("candidate_id") == candidate_id
            and row.get("direction") == DIRECTION
            and parse_int(row.get("token_count", "")) == CHUNK_TOKEN_LENGTH
            for row in chunks
        )
        verified = (
            bool(candidate)
            and candidate_id in hard_pair_candidate_ids
            and token_hash == path_hash == id_hash
            and parse_int(candidate.get("token_count", "")) == len(primary_tokens)
            and len(chunks) >= MAX_CHUNKS_PER_CANDIDATE
            and chunk_ok
        )
        hard_pair_verified = hard_pair_verified and verified
        candidate_checks.append(
            {
                "candidate_id": candidate_id,
                "candidate_manifest_present": bool(candidate),
                "hard_pair_manifest_present": candidate_id in hard_pair_candidate_ids,
                "candidate_token_path": candidate.get("candidate_text_or_token_path", ""),
                "token_hash": token_hash,
                "path_partial_text_hash": path_hash,
                "candidate_id_hash": id_hash,
                "token_count_manifest": parse_int(candidate.get("token_count", "")),
                "token_count_primary": len(primary_tokens),
                "direction": candidate.get("direction", ""),
                "chunk_count_available": len(chunk_rows_by_candidate.get(candidate_id, [])),
                "selected_chunk_ids": [row.get("candidate_chunk_id", "") for row in chunks],
                "chunk_manifest_verified": chunk_ok,
                "candidate_full_texts_row_present": bool(full_text),
                "candidate_full_texts_rehashed_match": full_text_verified if full_text else None,
                "verified": verified,
            }
        )
    available_fields = set(candidate_rows_by_id[next(iter(selected_ids))].keys()) if selected_ids else set()
    controlled_missing = [field for field in CONTROLLED_DAMAGE_FIELDS if field not in available_fields]
    controlled_verified = not controlled_missing
    blocked_reasons: list[str] = []
    if not hard_pair_verified:
        blocked_reasons.append("selected candidate stream could not be verified against hard-pair manifests")
    if full_text_mismatches:
        blocked_reasons.append("candidate_full_texts token sequence mismatch for selected candidates")
    if CLAIM_MODE == "controlled_damage_ladder" and not controlled_verified:
        blocked_reasons.append("controlled damage-stream fingerprints are required for controlled damage ladder claim")
    return {
        "claim_mode": CLAIM_MODE,
        "controlled_damage_stream_required": CONTROLLED_DAMAGE_STREAM_REQUIRED,
        "hard_pair_candidate_stream_verified": hard_pair_verified,
        "controlled_damage_stream_verified": controlled_verified,
        "controlled_damage_missing_fields": controlled_missing,
        "candidate_full_texts_used_as_primary_scan_source": False,
        "primary_scan_source": token_source_rel,
        "candidate_full_texts_path": CANDIDATE_FULL_TEXTS_REL,
        "candidate_checks": candidate_checks,
        "blocked": bool(blocked_reasons),
        "blocked_reasons": blocked_reasons,
    }


def load_manifest_context() -> dict[str, Any]:
    hard_pair_dir = HARD_PAIR_DIR_REL
    candidate_rows = read_csv_rows(f"{hard_pair_dir}/candidate_manifest_resolved.csv")
    chunk_rows = read_csv_rows(f"{hard_pair_dir}/candidate_chunk_manifest.csv")
    hard_pair_rows = read_csv_rows(f"{hard_pair_dir}/hard_pair_manifest.csv")
    summary_rows = read_csv_rows(f"{hard_pair_dir}/pairwise_road_test_summary.csv")
    chunk_rows_by_candidate: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in chunk_rows:
        if row.get("chunk_status") == "full_chunk":
            chunk_rows_by_candidate[row["candidate_id"]].append(row)
    for rows in chunk_rows_by_candidate.values():
        rows.sort(key=lambda row: parse_int(row.get("chunk_index", "")))
    selection = select_candidates(candidate_rows, chunk_rows_by_candidate, summary_rows)
    candidate_rows_by_id = {row["candidate_id"]: row for row in candidate_rows}
    preflight = build_preflight(selection["selected_candidates"], candidate_rows_by_id, chunk_rows_by_candidate, hard_pair_rows)
    return {
        "candidate_rows": candidate_rows,
        "chunk_rows_by_candidate": chunk_rows_by_candidate,
        "selection": selection,
        "preflight": preflight,
        "input_manifest": {
            "hard_pair_dir": HARD_PAIR_DIR_REL,
            "candidate_manifest_resolved_rows": len(candidate_rows),
            "candidate_chunk_manifest_rows": len(chunk_rows),
            "hard_pair_manifest_rows": len(hard_pair_rows),
            "pairwise_road_test_summary_rows": len(summary_rows),
            "candidate_manifest_resolved_path": f"{HARD_PAIR_DIR_REL}/candidate_manifest_resolved.csv",
            "candidate_chunk_manifest_path": f"{HARD_PAIR_DIR_REL}/candidate_chunk_manifest.csv",
            "hard_pair_manifest_path": f"{HARD_PAIR_DIR_REL}/hard_pair_manifest.csv",
            "pairwise_road_test_summary_path": f"{HARD_PAIR_DIR_REL}/pairwise_road_test_summary.csv",
        },
    }


def load_selected_tokens(preflight: dict[str, Any]) -> dict[str, list[int]]:
    hashes = {row["token_hash"] for row in preflight["candidate_checks"]}
    return load_token_map(hashes, preflight["primary_scan_source"])


def run_parity_row(
    label: str,
    tokens: list[int],
    entries: list[PhraseEntry],
    profile: PhraseProfile,
    *,
    candidate_id: str,
    chunk_id: str,
) -> dict[str, Any]:
    fast = scan_fast_payload(tokens, entries, profile, candidate_id=candidate_id, chunk_id=chunk_id, damage_level=label)
    reference = scan_reference_payload(tokens, entries, profile, candidate_id=candidate_id, chunk_id=chunk_id, damage_level=label)
    return {
        "parity_case": label,
        "profile_id": profile.profile_id,
        "dictionary_cut": DICTIONARY_CUT,
        "ngram_order": profile.orders[0],
        "phrase_entry_count": len(entries),
        "candidate_token_count": len(tokens),
        "fast_hit_count": len(fast["phrase_hits"]),
        "reference_hit_count": len(reference["phrase_hits"]),
        "parity_match": fast == reference,
    }


def full_pilot_target_cell_count() -> int:
    return FULL_PILOT_TARGET_CANDIDATES * FULL_PILOT_TARGET_CHUNKS_PER_CANDIDATE * len(BASE_PROFILES) * len(NGRAM_ORDERS)


def microbatch_cell_count(selected_count: int) -> int:
    return selected_count * MAX_CHUNKS_PER_CANDIDATE * len(BASE_PROFILES) * len(NGRAM_ORDERS)


def attempt_weighted_projection(cell_timing_rows: list[dict[str, Any]]) -> dict[str, Any]:
    measured_attempts = sum(int(row["verification_attempts"]) for row in cell_timing_rows)
    measured_scan_seconds = sum(float(row["elapsed_seconds"]) for row in cell_timing_rows)
    cells_per_candidate_chunk = len(BASE_PROFILES) * len(NGRAM_ORDERS)
    measured_candidate_chunks = max(1.0, len(cell_timing_rows) / cells_per_candidate_chunk)
    target_candidate_chunks = FULL_PILOT_TARGET_CANDIDATES * FULL_PILOT_TARGET_CHUNKS_PER_CANDIDATE
    target_attempts = int(measured_attempts * (target_candidate_chunks / measured_candidate_chunks))
    attempts_per_second = measured_attempts / measured_scan_seconds if measured_scan_seconds else 0.0
    projected_seconds = target_attempts / attempts_per_second if attempts_per_second else 0.0
    return {
        "measured_attempts": measured_attempts,
        "measured_scan_seconds": measured_scan_seconds,
        "measured_attempts_per_second": attempts_per_second,
        "microbatch_cell_count": len(cell_timing_rows),
        "full_pilot_target_cell_count": full_pilot_target_cell_count(),
        "full_pilot_target_candidate_chunks": target_candidate_chunks,
        "attempt_weighted_full_pilot_attempts": target_attempts,
        "attempt_weighted_full_pilot_projected_seconds": projected_seconds,
    }


def run_required_pre_scan_parity(
    selected: list[dict[str, Any]],
    chunk_rows_by_candidate: dict[str, list[dict[str, str]]],
    selected_tokens: dict[str, list[int]],
    entries_by_order: dict[int, list[PhraseEntry]],
) -> list[dict[str, Any]]:
    parity_rows: list[dict[str, Any]] = []
    first_entry = entries_by_order[NGRAM_ORDERS[0]][0]
    positive_profile = replace(BASE_PROFILES[0], orders=(NGRAM_ORDERS[0],))
    positive_entries = [entry for entry in entries_by_order[NGRAM_ORDERS[0]] if profile_allows_entry(entry, positive_profile)]
    positive = run_parity_row(
        "positive_control_phrase_index_row",
        [0] + list(first_entry.rune_token_ids) + [0],
        positive_entries,
        positive_profile,
        candidate_id="positive_control_from_phrase_index",
        chunk_id="positive_control",
    )
    positive["parity_phase"] = "pre_scan"
    parity_rows.append(positive)

    first_selected = selected[0]["candidate_id"]
    first_chunk = chunk_rows_by_candidate[first_selected][0]
    first_tokens = selected_tokens[candidate_hash_from_id(first_selected)][
        parse_int(first_chunk["chunk_start"]) : parse_int(first_chunk["chunk_end"])
    ]
    real_profile = replace(BASE_PROFILES[1], orders=(NGRAM_ORDERS[0],))
    real_entries = [entry for entry in entries_by_order[NGRAM_ORDERS[0]] if profile_allows_entry(entry, real_profile)]
    real = run_parity_row(
        "selected_real_candidate_chunk",
        first_tokens,
        real_entries,
        real_profile,
        candidate_id=first_selected,
        chunk_id=first_chunk["candidate_chunk_id"],
    )
    real["parity_phase"] = "pre_scan"
    parity_rows.append(real)
    return parity_rows


def run_pilot() -> dict[str, Any]:
    started = time.perf_counter()
    created_utc = datetime.now(timezone.utc).isoformat()
    output_dir = REPO_ROOT / OUTPUT_DIR_REL
    ensure_under_repo(output_dir / "config.json")
    if not fast_ngram_hamming_available():
        return {
            "run_label": RUN_LABEL,
            "created_utc": created_utc,
            "status": "blocked",
            "blocked_reasons": ["_ngram_hamming_fast extension is unavailable"],
            "backend_impl": BACKEND_IMPL,
            "python_fallback_allowed": PYTHON_FALLBACK_ALLOWED,
        }

    context = load_manifest_context()
    entries_by_order, phrase_manifest = load_phrase_entries()
    selected = context["selection"]["selected_candidates"]
    selected_tokens = load_selected_tokens(context["preflight"])
    chunk_rows_by_candidate = context["chunk_rows_by_candidate"]
    blocked_reasons = list(context["preflight"]["blocked_reasons"])
    if blocked_reasons:
        status = "blocked"
    else:
        status = "pass"

    chunk_feature_rows: list[dict[str, Any]] = []
    cell_timing_rows: list[dict[str, Any]] = []
    debug_rows: list[dict[str, Any]] = []
    parity_rows: list[dict[str, Any]] = []
    scan_count = 0
    attempt_projection: dict[str, Any] = {}
    zero_hit_case: tuple[list[int], list[PhraseEntry], PhraseProfile, str, str] | None = None

    if status == "pass":
        parity_rows.extend(run_required_pre_scan_parity(selected, chunk_rows_by_candidate, selected_tokens, entries_by_order))
        if not all(row.get("parity_match") is not False for row in parity_rows):
            status = "blocked"
            blocked_reasons.append("bounded Python parity audit failed before microbatch scan")

    if status == "pass":
        total_planned_scans = microbatch_cell_count(len(selected))
        for selected_row in selected:
            candidate_id = selected_row["candidate_id"]
            token_hash = candidate_hash_from_id(candidate_id)
            tokens = selected_tokens[token_hash]
            for chunk_row in chunk_rows_by_candidate[candidate_id][:MAX_CHUNKS_PER_CANDIDATE]:
                chunk_tokens = tokens[parse_int(chunk_row["chunk_start"]) : parse_int(chunk_row["chunk_end"])]
                for base_profile in BASE_PROFILES:
                    for order in NGRAM_ORDERS:
                        profile = replace(base_profile, orders=(order,))
                        entries = [entry for entry in entries_by_order[order] if profile_allows_entry(entry, profile)]
                        cell_started = time.perf_counter()
                        payload = scan_fast_payload(
                            chunk_tokens,
                            entries,
                            profile,
                            candidate_id=candidate_id,
                            chunk_id=chunk_row["candidate_chunk_id"],
                            damage_level=CLAIM_MODE,
                        )
                        cell_elapsed = time.perf_counter() - cell_started
                        verification_attempts = int(payload["phrase_verification_attempts"])
                        cell_timing_rows.append(
                            {
                                "candidate_id": candidate_id,
                                "chunk_id": chunk_row["candidate_chunk_id"],
                                "profile_id": profile.profile_id,
                                "ngram_order": order,
                                "phrase_entry_count": len(entries),
                                "verification_attempts": verification_attempts,
                                "elapsed_seconds": cell_elapsed,
                                "attempts_per_second": verification_attempts / cell_elapsed if cell_elapsed else 0.0,
                                "hit_count": len(payload["phrase_hits"]),
                            }
                        )
                        chunk_feature_rows.append(
                            feature_row_from_scan(
                                payload,
                                candidate_id=candidate_id,
                                chunk_row=chunk_row,
                                profile=profile,
                                order=order,
                            )
                        )
                        for hit in payload["debug_examples"]:
                            debug_rows.append(
                                {
                                    "candidate_id": candidate_id,
                                    "candidate_chunk_id": chunk_row["candidate_chunk_id"],
                                    "profile_id": profile.profile_id,
                                    "ngram_order": order,
                                    "hit": hit,
                                }
                            )
                        if zero_hit_case is None and len(payload["phrase_hits"]) == 0:
                            zero_hit_case = (chunk_tokens, entries, profile, candidate_id, chunk_row["candidate_chunk_id"])
                        scan_count += 1
                        elapsed = time.perf_counter() - started
                        print(
                            f"[{RUN_LABEL}] scan {scan_count}/{total_planned_scans} "
                            f"cell_elapsed={cell_elapsed:.2f}s elapsed={elapsed:.1f}s"
                        )
                        if elapsed > MAX_WALLCLOCK_SECONDS:
                            status = "blocked"
                            blocked_reasons.append(
                                f"full pilot exceeded {MAX_WALLCLOCK_SECONDS:.1f}s wallclock budget"
                            )
                            break
                        if scan_count == EARLY_PROJECTION_CHECK_CELLS:
                            early_projection = attempt_weighted_projection(cell_timing_rows)
                            early_seconds = early_projection["attempt_weighted_full_pilot_projected_seconds"]
                            print(
                                f"[{RUN_LABEL}] early_projection_after_{EARLY_PROJECTION_CHECK_CELLS}_cells="
                                f"{early_seconds:.1f}s"
                            )
                            if early_seconds > EARLY_PROJECTION_STOP_SECONDS:
                                status = "blocked"
                                blocked_reasons.append(
                                    f"attempt-weighted projection after {EARLY_PROJECTION_CHECK_CELLS} cells "
                                    f"was {early_seconds:.1f}s beyond {EARLY_PROJECTION_STOP_SECONDS:.1f}s guard"
                                )
                                break
                    if status != "pass":
                        break
                if status != "pass":
                    break
            if status != "pass":
                break

    if status == "pass":
        if zero_hit_case is not None:
            z_tokens, z_entries, z_profile, z_candidate_id, z_chunk_id = zero_hit_case
            zero_hit = run_parity_row(
                "natural_zero_hit_or_low_hit_row",
                z_tokens,
                z_entries,
                z_profile,
                candidate_id=z_candidate_id,
                chunk_id=z_chunk_id,
            )
            zero_hit["parity_phase"] = "post_scan"
            parity_rows.append(zero_hit)
        else:
            parity_rows.append(
                {
                    "parity_case": "natural_zero_hit_or_low_hit_row",
                    "selection_status": "missing_no_zero_hit_row_observed",
                    "parity_match": None,
                }
            )
        if not all(row.get("parity_match") is not False for row in parity_rows):
            status = "blocked"
            blocked_reasons.append("bounded Python parity audit failed")
        attempt_projection = attempt_weighted_projection(cell_timing_rows)

    elapsed_total = time.perf_counter() - started
    if elapsed_total > MAX_WALLCLOCK_SECONDS and status == "pass":
        status = "blocked"
        blocked_reasons.append(f"pilot exceeded {MAX_WALLCLOCK_SECONDS:.1f}s wallclock budget")

    candidate_feature_rows = aggregate_candidate_rows(chunk_feature_rows)
    parity_required_rows_ran = any(row.get("parity_match") is not None for row in parity_rows)
    manifest = {
        "run_label": RUN_LABEL,
        "created_utc": created_utc,
        "status": status,
        "blocked_reasons": blocked_reasons,
        "claim_mode": CLAIM_MODE,
        "controlled_damage_stream_required": CONTROLLED_DAMAGE_STREAM_REQUIRED,
        "backend_impl": BACKEND_IMPL,
        "reference_backend_impl": REFERENCE_BACKEND_IMPL,
        "python_fallback_allowed": PYTHON_FALLBACK_ALLOWED,
        "no_hit_cap": NO_HIT_CAP,
        "broad_pilot": False,
        "full_hard_pair_report": False,
        "production_scorer_changes": False,
        "elapsed_seconds": elapsed_total,
        "scan_count_completed": scan_count,
        "cell_timing_row_count": len(cell_timing_rows),
        "attempt_weighted_projection": attempt_projection,
        "config": build_config(),
        "input_manifest": context["input_manifest"],
        "candidate_source_preflight_manifest": context["preflight"],
        "candidate_selection_manifest": context["selection"],
        "backend_manifest": {
            "backend_impl": BACKEND_IMPL,
            "python_fallback_allowed": PYTHON_FALLBACK_ALLOWED,
            "_ngram_hamming_fast_available": fast_ngram_hamming_available(),
            "extension_module_name": "rune_decrypter_prime.scoring.ngram_hamming._ngram_hamming_fast",
            "phrase_index_path": PHRASE_INDEX_REL,
            "loaded_phrase_entry_counts_by_profile_cut_order": phrase_manifest[
                "loaded_phrase_entry_counts_by_profile_cut_order"
            ],
            "no_hit_cap": NO_HIT_CAP,
        },
        "phrase_index_manifest_used": phrase_manifest,
        "profile_manifest": [asdict(profile) for profile in BASE_PROFILES],
        "parity_audit_summary": {
            "parity_row_count": len(parity_rows),
            "parity_not_run_due_to_block": status == "blocked" and not parity_required_rows_ran,
            "all_required_parity_passed": (
                parity_required_rows_ran and all(row.get("parity_match") is not False for row in parity_rows)
            ),
        },
        "output_files": [
            "config.json",
            "input_manifest.json",
            "candidate_source_preflight_manifest.json",
            "candidate_selection_manifest.json",
            "backend_manifest.json",
            "phrase_index_manifest_used.json",
            "profile_manifest.json",
            "chunk_feature_rows.csv",
            "candidate_feature_rows.csv",
            "debug_examples.jsonl",
            "parity_audit_rows.jsonl",
            "cell_timing_rows.csv",
            "pilot_manifest.json",
            "readout.md",
        ],
    }
    write_outputs(manifest, chunk_feature_rows, candidate_feature_rows, debug_rows, parity_rows, cell_timing_rows)
    return manifest


def aggregate_candidate_rows(chunk_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in chunk_rows:
        grouped[(row["candidate_id"], row["profile_id"], int(row["ngram_order"]))].append(row)
    out: list[dict[str, Any]] = []
    for (candidate_id, profile_id, order), rows in sorted(grouped.items()):
        out.append(
            {
                "candidate_id": candidate_id,
                "profile_id": profile_id,
                "dictionary_cut": DICTIONARY_CUT,
                "ngram_order": order,
                "backend_impl": BACKEND_IMPL,
                "chunk_rows": len(rows),
                "total_phrase_hit_count": sum(int(row["phrase_hit_count"]) for row in rows),
                "mean_phrase_hit_count": sum(int(row["phrase_hit_count"]) for row in rows) / len(rows),
                "max_phrase_hit_count": max(int(row["phrase_hit_count"]) for row in rows),
                "total_weighted_hit_sum": sum(float(row["weighted_hit_sum"]) for row in rows),
                "mean_phrase_hits_per_opportunity": sum(float(row["phrase_hits_per_opportunity"]) for row in rows) / len(rows),
                "mean_positive_start_offset_fraction": sum(float(row["positive_start_offset_fraction"]) for row in rows)
                / len(rows),
            }
        )
    return out


def build_config() -> dict[str, Any]:
    return {
        "run_label": RUN_LABEL,
        "run_mode": "full_pilot",
        "claim_mode": CLAIM_MODE,
        "direction": DIRECTION,
        "dictionary_cuts": [DICTIONARY_CUT],
        "orders": list(NGRAM_ORDERS),
        "profiles": [profile.profile_id for profile in BASE_PROFILES],
        "max_candidates": MAX_CANDIDATES,
        "max_chunks_total": MAX_CHUNKS_TOTAL,
        "max_chunks_per_candidate": MAX_CHUNKS_PER_CANDIDATE,
        "full_pilot_target_candidates": FULL_PILOT_TARGET_CANDIDATES,
        "full_pilot_target_chunks_per_candidate": FULL_PILOT_TARGET_CHUNKS_PER_CANDIDATE,
        "full_pilot_target_cell_count": full_pilot_target_cell_count(),
        "chunk_token_length": CHUNK_TOKEN_LENGTH,
        "debug_example_limit": DEBUG_EXAMPLE_LIMIT,
        "max_wallclock_seconds": MAX_WALLCLOCK_SECONDS,
        "early_projection_check_cells": EARLY_PROJECTION_CHECK_CELLS,
        "early_projection_stop_seconds": EARLY_PROJECTION_STOP_SECONDS,
        "backend_impl": BACKEND_IMPL,
        "python_fallback_allowed": PYTHON_FALLBACK_ALLOWED,
        "no_hit_cap": NO_HIT_CAP,
    }


def write_json(path: Path, payload: Any) -> None:
    ensure_under_repo(path)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: Iterable[str] | None = None) -> None:
    ensure_under_repo(path)
    names = list(fieldnames) if fieldnames is not None else sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=names)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    ensure_under_repo(path)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def write_outputs(
    manifest: dict[str, Any],
    chunk_feature_rows: list[dict[str, Any]],
    candidate_feature_rows: list[dict[str, Any]],
    debug_rows: list[dict[str, Any]],
    parity_rows: list[dict[str, Any]],
    cell_timing_rows: list[dict[str, Any]],
) -> None:
    output_dir = REPO_ROOT / OUTPUT_DIR_REL
    write_json(output_dir / "config.json", manifest["config"])
    write_json(output_dir / "input_manifest.json", manifest["input_manifest"])
    write_json(output_dir / "candidate_source_preflight_manifest.json", manifest["candidate_source_preflight_manifest"])
    write_json(output_dir / "candidate_selection_manifest.json", manifest["candidate_selection_manifest"])
    write_json(output_dir / "backend_manifest.json", manifest["backend_manifest"])
    write_json(output_dir / "phrase_index_manifest_used.json", manifest["phrase_index_manifest_used"])
    write_json(output_dir / "profile_manifest.json", manifest["profile_manifest"])
    write_csv(output_dir / "chunk_feature_rows.csv", chunk_feature_rows, CHUNK_FEATURE_FIELDS)
    write_csv(output_dir / "candidate_feature_rows.csv", candidate_feature_rows)
    write_jsonl(output_dir / "debug_examples.jsonl", debug_rows)
    write_jsonl(output_dir / "parity_audit_rows.jsonl", parity_rows)
    write_csv(output_dir / "cell_timing_rows.csv", cell_timing_rows, CELL_TIMING_FIELDS)
    write_json(output_dir / "pilot_manifest.json", manifest)
    readout = [
        "# PhaseB N-Gram Hamming Exact No-Cap Full Pilot v1",
        "",
        f"Status: `{manifest['status']}`",
        "",
        f"- run mode: `{manifest['config']['run_mode']}`",
        f"- claim mode: `{manifest['claim_mode']}`",
        f"- backend: `{manifest['backend_impl']}`",
        f"- Python fallback allowed: `{manifest['python_fallback_allowed']}`",
        f"- hard-pair candidate stream verified: `{manifest['candidate_source_preflight_manifest']['hard_pair_candidate_stream_verified']}`",
        f"- controlled damage stream verified: `{manifest['candidate_source_preflight_manifest']['controlled_damage_stream_verified']}`",
        f"- broad pilot: `{manifest['broad_pilot']}`",
        f"- full hard-pair report: `{manifest['full_hard_pair_report']}`",
        f"- selected candidates: `{len(manifest['candidate_selection_manifest']['selected_candidates'])}`",
        f"- completed scans: `{manifest['scan_count_completed']}`",
        f"- cell timing rows: `{manifest['cell_timing_row_count']}`",
        f"- chunk feature rows: `{len(chunk_feature_rows)}`",
        f"- candidate feature rows: `{len(candidate_feature_rows)}`",
        f"- parity rows: `{manifest['parity_audit_summary']['parity_row_count']}`",
        f"- elapsed seconds: `{manifest['elapsed_seconds']:.3f}`",
        f"- attempt-weighted full-pilot projection seconds: `{manifest['attempt_weighted_projection'].get('attempt_weighted_full_pilot_projected_seconds', 0.0):.3f}`",
        "",
        "This is a hard-pair candidate comparability pilot, not a controlled 20-50% damage ladder claim.",
    ]
    if manifest["blocked_reasons"]:
        readout.extend(["", "## Blocked Reasons", ""])
        readout.extend(f"- `{reason}`" for reason in manifest["blocked_reasons"])
    (output_dir / "readout.md").write_text("\n".join(readout) + "\n", encoding="utf-8")


def main() -> None:
    manifest = run_pilot()
    print(f"[{RUN_LABEL}] status={manifest['status']}")
    print(f"[{RUN_LABEL}] completed_scans={manifest.get('scan_count_completed', 0)}")
    print(f"[{RUN_LABEL}] elapsed_seconds={manifest.get('elapsed_seconds', 0.0):.3f}")


if __name__ == "__main__":
    main()
