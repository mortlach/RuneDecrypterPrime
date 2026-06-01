from __future__ import annotations

import gzip
import json
import sys
import time
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

from rune_decrypter_prime.scoring.ngram_hamming.reference import PhraseProfile  # noqa: E402
from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (  # noqa: E402
    run_phaseB_ngram_hamming_balanced_readout_v1 as base,
)


RUN_LABEL = "phaseB_ngram_hamming_sample_index_all_candidate_matrix_v1"
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_sample_index_all_candidate_matrix_v1"
)
DATASET_STATUS = "sample_index_confirmed"
ASSET_PROVENANCE_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_asset_provenance_inventory_v1/provenance_manifest.json"
)

DIRECTION = "fwd"
DICTIONARY_CUT = "normal"
NGRAM_ORDERS = (2,)
MAX_CANDIDATES = 604
MAX_CHUNKS_TOTAL = 1208
MAX_CHUNKS_PER_CANDIDATE = 2
FULL_PILOT_TARGET_CANDIDATES = 604
FULL_PILOT_TARGET_CHUNKS_PER_CANDIDATE = 2
MAX_WALLCLOCK_SECONDS = 1200.0
EARLY_PROJECTION_CHECK_CELLS = 60
EARLY_PROJECTION_STOP_SECONDS = 1200.0
EXPECTED_CELL_COUNT = MAX_CANDIDATES * MAX_CHUNKS_PER_CANDIDATE * 3 * len(NGRAM_ORDERS)

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


def role_from_candidate_row(row: dict[str, str]) -> str:
    winner_count = base.parse_int(row.get("winner_count", ""))
    challenger_count = base.parse_int(row.get("challenger_count", ""))
    if winner_count > 0 and challenger_count > 0:
        return "mixed_pair_role"
    if winner_count > 0:
        return "known_better"
    if challenger_count > 0:
        return "known_worse"
    return ""


def stratum_from_candidate_row(row: dict[str, str], role: str) -> str:
    truth = base.parse_float(row.get("truth_match_ratio", ""))
    label = row.get("label", "")
    if role == "mixed_pair_role":
        return "mixed_pair_role_candidate"
    if role == "known_better":
        return "known_better_pair_candidate"
    if role == "known_worse":
        return "known_worse_pair_candidate"
    if truth >= 0.75 or label in {"known_good", "likely_good"}:
        return "high_truth_stable_fill"
    if truth <= 0.15 or label in {"known_bad", "likely_bad"}:
        return "bad_control_candidate"
    return "mid_truth_candidate"


def select_all_candidates(
    candidate_rows: list[dict[str, str]],
    chunk_rows_by_candidate: dict[str, list[dict[str, str]]],
    summary_rows: list[dict[str, str]],
) -> dict[str, Any]:
    del summary_rows
    selected: list[dict[str, Any]] = []
    for row in sorted(candidate_rows, key=lambda item: item.get("candidate_id", "")):
        candidate_id = row.get("candidate_id", "")
        chunks = chunk_rows_by_candidate.get(candidate_id, [])
        if row.get("direction") != DIRECTION:
            continue
        if len(chunks) < MAX_CHUNKS_PER_CANDIDATE:
            continue
        role = role_from_candidate_row(row)
        selected.append(
            {
                "candidate_id": candidate_id,
                "selected_stratum": stratum_from_candidate_row(row, role),
                "source_pair_id": "",
                "known_better_or_worse_role": role,
                "current_score": base.parse_float(row.get("current_score", "")),
                "truth_match_ratio": base.parse_float(row.get("truth_match_ratio", "")),
                "pair_occurrence_count": base.parse_int(row.get("pair_occurrence_count", "")),
                "chunk_count_available": len(chunks),
                "selection_status": "selected",
            }
        )
        if len(selected) == MAX_CANDIDATES:
            break
    stratum_counts: dict[str, int] = {}
    for row in selected:
        stratum_counts[row["selected_stratum"]] = stratum_counts.get(row["selected_stratum"], 0) + 1
    return {
        "selection_config": {
            "selection_mode": "all_hard_pair_candidates_sample_index_matrix",
            "dataset_status": DATASET_STATUS,
            "max_candidates": MAX_CANDIDATES,
            "max_chunks_per_candidate": MAX_CHUNKS_PER_CANDIDATE,
            "expected_cell_count": EXPECTED_CELL_COUNT,
            "asset_provenance_manifest": ASSET_PROVENANCE_REL,
        },
        "selected_candidates": selected,
        "missing_strata": [],
        "stratum_status_rows": [
            {
                "selected_stratum": stratum,
                "selected_count": count,
                "selection_status": "selected",
            }
            for stratum, count in sorted(stratum_counts.items())
        ],
    }


def build_matrix_config() -> dict[str, Any]:
    return {
        "run_label": RUN_LABEL,
        "run_mode": "sample_index_all_candidate_matrix",
        "claim_mode": base.CLAIM_MODE,
        "direction": DIRECTION,
        "dictionary_cuts": [DICTIONARY_CUT],
        "orders": list(NGRAM_ORDERS),
        "profiles": [profile.profile_id for profile in BASE_PROFILES],
        "max_candidates": MAX_CANDIDATES,
        "max_chunks_total": MAX_CHUNKS_TOTAL,
        "max_chunks_per_candidate": MAX_CHUNKS_PER_CANDIDATE,
        "full_pilot_target_candidates": FULL_PILOT_TARGET_CANDIDATES,
        "full_pilot_target_chunks_per_candidate": FULL_PILOT_TARGET_CHUNKS_PER_CANDIDATE,
        "full_pilot_target_cell_count": EXPECTED_CELL_COUNT,
        "chunk_token_length": base.CHUNK_TOKEN_LENGTH,
        "debug_example_limit": base.DEBUG_EXAMPLE_LIMIT,
        "max_wallclock_seconds": MAX_WALLCLOCK_SECONDS,
        "early_projection_check_cells": EARLY_PROJECTION_CHECK_CELLS,
        "early_projection_stop_seconds": EARLY_PROJECTION_STOP_SECONDS,
        "backend_impl": base.BACKEND_IMPL,
        "python_fallback_allowed": base.PYTHON_FALLBACK_ALLOWED,
        "no_hit_cap": base.NO_HIT_CAP,
        "dataset_status": DATASET_STATUS,
        "asset_provenance_manifest": ASSET_PROVENANCE_REL,
        "expected_cell_count": EXPECTED_CELL_COUNT,
    }


def load_phrase_entries() -> tuple[dict[int, list[base.PhraseEntry]], dict[str, Any]]:
    entries_by_order: dict[int, list[base.PhraseEntry]] = {order: [] for order in NGRAM_ORDERS}
    source_rows = 0
    with gzip.open(REPO_ROOT / base.PHRASE_INDEX_REL, "rt", encoding="utf-8") as handle:
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
            entries_by_order[order].append(base.phrase_entry_from_index_row(row))
    counts_by_order = {str(order): len(entries) for order, entries in entries_by_order.items()}
    if any(count == 0 for count in counts_by_order.values()):
        raise RuntimeError("missing phrase entries for at least one configured order")
    counts_by_profile_order: dict[str, int] = {}
    for profile in BASE_PROFILES:
        for order, entries in entries_by_order.items():
            profile_order = replace(profile, orders=(order,))
            counts_by_profile_order[f"{profile.profile_id}|{DICTIONARY_CUT}|{order}"] = sum(
                1 for entry in entries if base.profile_allows_entry(entry, profile_order)
            )
    return entries_by_order, {
        "phrase_index_path": base.PHRASE_INDEX_REL,
        "source_rows_read": source_rows,
        "direction": DIRECTION,
        "dictionary_cut": DICTIONARY_CUT,
        "orders": list(NGRAM_ORDERS),
        "entry_counts_by_order": counts_by_order,
        "loaded_phrase_entry_counts_by_profile_cut_order": counts_by_profile_order,
    }


def build_preflight(
    selected: list[dict[str, Any]],
    candidate_rows_by_id: dict[str, dict[str, str]],
    chunk_rows_by_candidate: dict[str, list[dict[str, str]]],
    hard_pair_rows: list[dict[str, str]],
) -> dict[str, Any]:
    selected_ids = {row["candidate_id"] for row in selected}
    hard_pair_candidate_ids = {
        candidate_id
        for row in hard_pair_rows
        for candidate_id in (row.get("candidate_a_id", ""), row.get("candidate_b_id", ""))
        if candidate_id
    }
    token_source_rel = (
        "planning/projects/no_wli/40_review_summaries/"
        "no_wli_historical_partial_text_and_scorer_review_pack_2026-05-02/"
        "historical_partial_texts/unique_partial_text_rows.csv"
    )
    needed_hashes = {base.candidate_hash_from_id(candidate_id) for candidate_id in selected_ids}
    token_map = base.load_token_map(needed_hashes, token_source_rel)
    full_texts = base.load_candidate_full_texts(selected_ids)
    candidate_checks: list[dict[str, Any]] = []
    full_text_mismatches: list[str] = []
    hard_pair_verified = True
    for candidate_id in sorted(selected_ids):
        candidate = candidate_rows_by_id.get(candidate_id, {})
        chunks = chunk_rows_by_candidate.get(candidate_id, [])[:MAX_CHUNKS_PER_CANDIDATE]
        id_hash = base.candidate_hash_from_id(candidate_id)
        path_hash = base.token_hash_from_path(candidate.get("candidate_text_or_token_path", ""))
        token_hash = candidate.get("token_hash", "")
        primary_tokens = token_map.get(id_hash, [])
        full_text = full_texts.get(candidate_id, {})
        full_text_verified = None
        if full_text:
            try:
                full_tokens = base.parse_token_sequence(full_text.get("token_sequence_text", ""))
                full_text_verified = full_tokens == primary_tokens
            except Exception:
                full_text_verified = False
            if not full_text_verified:
                full_text_mismatches.append(candidate_id)
        chunk_ok = all(
            row.get("direction") == DIRECTION
            and base.parse_int(row.get("token_count", "")) == base.parse_int(row.get("chunk_end", ""))
            - base.parse_int(row.get("chunk_start", ""))
            for row in chunks
        )
        verified = (
            bool(candidate)
            and candidate_id in hard_pair_candidate_ids
            and token_hash == path_hash == id_hash
            and base.parse_int(candidate.get("token_count", "")) == len(primary_tokens)
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
                "token_count_manifest": base.parse_int(candidate.get("token_count", "")),
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
    controlled_missing = [field for field in base.CONTROLLED_DAMAGE_FIELDS if field not in available_fields]
    controlled_verified = not controlled_missing
    blocked_reasons: list[str] = []
    if not hard_pair_verified:
        blocked_reasons.append("selected candidate stream could not be verified against hard-pair manifests")
    if full_text_mismatches:
        blocked_reasons.append("candidate_full_texts token sequence mismatch for selected candidates")
    return {
        "claim_mode": base.CLAIM_MODE,
        "controlled_damage_stream_required": base.CONTROLLED_DAMAGE_STREAM_REQUIRED,
        "hard_pair_candidate_stream_verified": hard_pair_verified,
        "controlled_damage_stream_verified": controlled_verified,
        "controlled_damage_missing_fields": controlled_missing,
        "candidate_full_texts_used_as_primary_scan_source": False,
        "primary_scan_source": token_source_rel,
        "candidate_full_texts_path": base.CANDIDATE_FULL_TEXTS_REL,
        "candidate_checks": candidate_checks,
        "blocked": bool(blocked_reasons),
        "blocked_reasons": blocked_reasons,
    }


def load_manifest_context() -> dict[str, Any]:
    hard_pair_dir = base.HARD_PAIR_DIR_REL
    candidate_rows = base.read_csv_rows(f"{hard_pair_dir}/candidate_manifest_resolved.csv")
    chunk_rows = base.read_csv_rows(f"{hard_pair_dir}/candidate_chunk_manifest.csv")
    hard_pair_rows = base.read_csv_rows(f"{hard_pair_dir}/hard_pair_manifest.csv")
    summary_rows = base.read_csv_rows(f"{hard_pair_dir}/pairwise_road_test_summary.csv")
    chunk_rows_by_candidate: dict[str, list[dict[str, str]]] = {}
    for row in chunk_rows:
        if row.get("chunk_status") == "full_chunk":
            chunk_rows_by_candidate.setdefault(row["candidate_id"], []).append(row)
    for rows in chunk_rows_by_candidate.values():
        rows.sort(key=lambda row: base.parse_int(row.get("chunk_index", "")))
    selection = select_all_candidates(candidate_rows, chunk_rows_by_candidate, summary_rows)
    candidate_rows_by_id = {row["candidate_id"]: row for row in candidate_rows}
    preflight = build_preflight(selection["selected_candidates"], candidate_rows_by_id, chunk_rows_by_candidate, hard_pair_rows)
    return {
        "candidate_rows": candidate_rows,
        "chunk_rows_by_candidate": chunk_rows_by_candidate,
        "selection": selection,
        "preflight": preflight,
        "input_manifest": {
            "hard_pair_dir": base.HARD_PAIR_DIR_REL,
            "candidate_manifest_resolved_rows": len(candidate_rows),
            "candidate_chunk_manifest_rows": len(chunk_rows),
            "hard_pair_manifest_rows": len(hard_pair_rows),
            "pairwise_road_test_summary_rows": len(summary_rows),
            "candidate_manifest_resolved_path": f"{base.HARD_PAIR_DIR_REL}/candidate_manifest_resolved.csv",
            "candidate_chunk_manifest_path": f"{base.HARD_PAIR_DIR_REL}/candidate_chunk_manifest.csv",
            "hard_pair_manifest_path": f"{base.HARD_PAIR_DIR_REL}/hard_pair_manifest.csv",
            "pairwise_road_test_summary_path": f"{base.HARD_PAIR_DIR_REL}/pairwise_road_test_summary.csv",
        },
    }


def load_selected_tokens(preflight: dict[str, Any]) -> dict[str, list[int]]:
    hashes = {row["token_hash"] for row in preflight["candidate_checks"]}
    return base.load_token_map(hashes, preflight["primary_scan_source"])


def full_pilot_target_cell_count() -> int:
    return EXPECTED_CELL_COUNT


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
    entries_by_order: dict[int, list[base.PhraseEntry]],
) -> list[dict[str, Any]]:
    parity_rows: list[dict[str, Any]] = []
    first_entry = entries_by_order[NGRAM_ORDERS[0]][0]
    positive_profile = replace(BASE_PROFILES[0], orders=(NGRAM_ORDERS[0],))
    positive_entries = [entry for entry in entries_by_order[NGRAM_ORDERS[0]] if base.profile_allows_entry(entry, positive_profile)]
    positive = base.run_parity_row(
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
    first_tokens = selected_tokens[base.candidate_hash_from_id(first_selected)][
        base.parse_int(first_chunk["chunk_start"]) : base.parse_int(first_chunk["chunk_end"])
    ]
    real_profile = replace(BASE_PROFILES[1], orders=(NGRAM_ORDERS[0],))
    real_entries = [entry for entry in entries_by_order[NGRAM_ORDERS[0]] if base.profile_allows_entry(entry, real_profile)]
    real = base.run_parity_row(
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


def write_outputs(
    manifest: dict[str, Any],
    chunk_feature_rows: list[dict[str, Any]],
    candidate_feature_rows: list[dict[str, Any]],
    debug_rows: list[dict[str, Any]],
    parity_rows: list[dict[str, Any]],
    cell_timing_rows: list[dict[str, Any]],
    expansion_summaries: dict[str, list[dict[str, Any]]],
) -> None:
    output_dir = REPO_ROOT / OUTPUT_DIR_REL
    base.write_json(output_dir / "config.json", manifest["config"])
    base.write_json(output_dir / "input_manifest.json", manifest["input_manifest"])
    base.write_json(output_dir / "candidate_source_preflight_manifest.json", manifest["candidate_source_preflight_manifest"])
    base.write_json(output_dir / "candidate_selection_manifest.json", manifest["candidate_selection_manifest"])
    base.write_json(output_dir / "backend_manifest.json", manifest["backend_manifest"])
    base.write_json(output_dir / "phrase_index_manifest_used.json", manifest["phrase_index_manifest_used"])
    base.write_json(output_dir / "profile_manifest.json", manifest["profile_manifest"])
    base.write_csv(output_dir / "chunk_feature_rows.csv", chunk_feature_rows, base.CHUNK_FEATURE_FIELDS)
    base.write_csv(output_dir / "candidate_feature_rows.csv", candidate_feature_rows)
    base.write_jsonl(output_dir / "debug_examples.jsonl", debug_rows)
    base.write_jsonl(output_dir / "parity_audit_rows.jsonl", parity_rows)
    base.write_csv(output_dir / "cell_timing_rows.csv", cell_timing_rows, base.CELL_TIMING_FIELDS)
    base.write_csv(output_dir / "hit_summary_by_candidate.csv", expansion_summaries["summary_by_candidate"])
    base.write_csv(output_dir / "hit_summary_by_stratum.csv", expansion_summaries["summary_by_stratum"])
    base.write_csv(output_dir / "hit_summary_by_role.csv", expansion_summaries["summary_by_role"])
    base.write_csv(output_dir / "hit_summary_by_profile.csv", expansion_summaries["summary_by_profile"])
    base.write_csv(output_dir / "hit_summary_by_candidate_profile.csv", expansion_summaries["summary_by_candidate_profile"])
    base.write_csv(output_dir / "positive_chunk_rows.csv", expansion_summaries["positive_chunk_rows"])
    base.write_json(output_dir / "pilot_manifest.json", manifest)
    readout = [
        "# PhaseB N-Gram Hamming Sample-Index All-Candidate Matrix v1",
        "",
        f"Status: `{manifest['status']}`",
        "",
        f"- run mode: `{manifest['config']['run_mode']}`",
        f"- dataset status: `{manifest['config']['dataset_status']}`",
        f"- claim mode: `{manifest['claim_mode']}`",
        f"- backend: `{manifest['backend_impl']}`",
        f"- Python fallback allowed: `{manifest['python_fallback_allowed']}`",
        f"- selected candidates: `{len(manifest['candidate_selection_manifest']['selected_candidates'])}`",
        f"- completed scans: `{manifest['scan_count_completed']}`",
        f"- total hits: `{manifest['total_hit_count']}`",
        f"- candidates with hits: `{manifest['candidates_with_hits']}`",
        f"- candidates with zero hits: `{manifest['candidates_with_zero_hits']}`",
        f"- elapsed seconds: `{manifest['elapsed_seconds']:.3f}`",
        "",
        "This is sample-index based. It is not a full raw n-gram rebuild result.",
    ]
    if manifest["blocked_reasons"]:
        readout.extend(["", "## Blocked Reasons", ""])
        readout.extend(f"- `{reason}`" for reason in manifest["blocked_reasons"])
    (output_dir / "readout.md").write_text("\n".join(readout) + "\n", encoding="utf-8")


def run_matrix() -> dict[str, Any]:
    started = time.perf_counter()
    created_utc = datetime.now(timezone.utc).isoformat()
    output_dir = REPO_ROOT / OUTPUT_DIR_REL
    base.ensure_under_repo(output_dir / "config.json")
    if not base.fast_ngram_hamming_available():
        return {
            "run_label": RUN_LABEL,
            "created_utc": created_utc,
            "status": "blocked",
            "blocked_reasons": ["_ngram_hamming_fast extension is unavailable"],
            "backend_impl": base.BACKEND_IMPL,
            "python_fallback_allowed": base.PYTHON_FALLBACK_ALLOWED,
        }
    context = load_manifest_context()
    entries_by_order, phrase_manifest = load_phrase_entries()
    selected = context["selection"]["selected_candidates"]
    selected_tokens = load_selected_tokens(context["preflight"])
    chunk_rows_by_candidate = context["chunk_rows_by_candidate"]
    blocked_reasons = list(context["preflight"]["blocked_reasons"])
    status = "blocked" if blocked_reasons else "pass"
    chunk_feature_rows: list[dict[str, Any]] = []
    debug_rows: list[dict[str, Any]] = []
    parity_rows = run_required_pre_scan_parity(selected, chunk_rows_by_candidate, selected_tokens, entries_by_order)
    if not all(row.get("parity_match") is not False for row in parity_rows):
        status = "blocked"
        blocked_reasons.append("pre-scan bounded Python parity audit failed")
    cell_timing_rows: list[dict[str, Any]] = []
    scan_count = 0
    attempt_projection: dict[str, Any] = {}
    total_planned_scans = len(selected) * MAX_CHUNKS_PER_CANDIDATE * len(BASE_PROFILES) * len(NGRAM_ORDERS)
    if status == "pass":
        for selected_row in selected:
            candidate_id = selected_row["candidate_id"]
            tokens = selected_tokens[base.candidate_hash_from_id(candidate_id)]
            for chunk_row in chunk_rows_by_candidate[candidate_id][:MAX_CHUNKS_PER_CANDIDATE]:
                chunk_tokens = tokens[base.parse_int(chunk_row["chunk_start"]) : base.parse_int(chunk_row["chunk_end"])]
                for order in NGRAM_ORDERS:
                    entries = entries_by_order[order]
                    for profile in BASE_PROFILES:
                        profile_order = replace(profile, orders=(order,))
                        eligible_entries = [entry for entry in entries if base.profile_allows_entry(entry, profile_order)]
                        cell_started = time.perf_counter()
                        payload = base.scan_fast_payload(
                            chunk_tokens,
                            eligible_entries,
                            profile_order,
                            candidate_id=candidate_id,
                            chunk_id=chunk_row["candidate_chunk_id"],
                            damage_level=base.CLAIM_MODE,
                        )
                        cell_elapsed = time.perf_counter() - cell_started
                        verification_attempts = int(payload["phrase_verification_attempts"])
                        cell_timing_rows.append(
                            {
                                "candidate_id": candidate_id,
                                "chunk_id": chunk_row["candidate_chunk_id"],
                                "profile_id": profile.profile_id,
                                "ngram_order": order,
                                "phrase_entry_count": len(eligible_entries),
                                "verification_attempts": verification_attempts,
                                "elapsed_seconds": cell_elapsed,
                                "attempts_per_second": verification_attempts / cell_elapsed if cell_elapsed else 0.0,
                                "hit_count": len(payload["phrase_hits"]),
                            }
                        )
                        chunk_feature_rows.append(
                            base.feature_row_from_scan(
                                payload,
                                candidate_id=candidate_id,
                                chunk_row=chunk_row,
                                profile=profile_order,
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
                        scan_count += 1
                        elapsed = time.perf_counter() - started
                        print(
                            f"[{RUN_LABEL}] scan {scan_count}/{total_planned_scans} "
                            f"cell_elapsed={cell_elapsed:.2f}s elapsed={elapsed:.1f}s"
                        )
                        if elapsed > MAX_WALLCLOCK_SECONDS:
                            status = "blocked"
                            blocked_reasons.append(
                                f"matrix exceeded {MAX_WALLCLOCK_SECONDS:.1f}s wallclock budget"
                            )
                            break
                        if scan_count == EARLY_PROJECTION_CHECK_CELLS:
                            early_projection = attempt_weighted_projection(cell_timing_rows)
                            early_seconds = early_projection["attempt_weighted_full_pilot_projected_seconds"]
                            print(f"[{RUN_LABEL}] early_projection_after_{EARLY_PROJECTION_CHECK_CELLS}_cells={early_seconds:.1f}s")
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
        attempt_projection = attempt_weighted_projection(cell_timing_rows)
    elapsed_total = time.perf_counter() - started
    if elapsed_total > MAX_WALLCLOCK_SECONDS and status == "pass":
        status = "blocked"
        blocked_reasons.append(f"matrix exceeded {MAX_WALLCLOCK_SECONDS:.1f}s wallclock budget")
    candidate_feature_rows = base.aggregate_candidate_rows(chunk_feature_rows)
    expansion_summaries = base.summarise_expansion(chunk_feature_rows, selected)
    total_hits = sum(int(row["phrase_hit_count"]) for row in chunk_feature_rows)
    candidates_with_hits = sum(1 for row in expansion_summaries["summary_by_candidate"] if int(row["hit_count"]) > 0)
    parity_required_rows_ran = any(row.get("parity_match") is not None for row in parity_rows)
    manifest = {
        "run_label": RUN_LABEL,
        "created_utc": created_utc,
        "status": status,
        "blocked_reasons": blocked_reasons,
        "claim_mode": base.CLAIM_MODE,
        "controlled_damage_stream_required": base.CONTROLLED_DAMAGE_STREAM_REQUIRED,
        "backend_impl": base.BACKEND_IMPL,
        "reference_backend_impl": base.REFERENCE_BACKEND_IMPL,
        "python_fallback_allowed": base.PYTHON_FALLBACK_ALLOWED,
        "no_hit_cap": base.NO_HIT_CAP,
        "broad_pilot": False,
        "full_hard_pair_report": False,
        "production_scorer_changes": False,
        "elapsed_seconds": elapsed_total,
        "scan_count_completed": scan_count,
        "cell_timing_row_count": len(cell_timing_rows),
        "total_hit_count": total_hits,
        "candidates_with_hits": candidates_with_hits,
        "candidates_with_zero_hits": len(selected) - candidates_with_hits,
        "attempt_weighted_projection": attempt_projection,
        "config": build_matrix_config(),
        "input_manifest": context["input_manifest"],
        "candidate_source_preflight_manifest": context["preflight"],
        "candidate_selection_manifest": context["selection"],
        "backend_manifest": {
            "backend_impl": base.BACKEND_IMPL,
            "python_fallback_allowed": base.PYTHON_FALLBACK_ALLOWED,
            "_ngram_hamming_fast_available": base.fast_ngram_hamming_available(),
            "extension_module_name": "rune_decrypter_prime.scoring.ngram_hamming._ngram_hamming_fast",
            "phrase_index_path": base.PHRASE_INDEX_REL,
            "loaded_phrase_entry_counts_by_profile_cut_order": phrase_manifest[
                "loaded_phrase_entry_counts_by_profile_cut_order"
            ],
            "no_hit_cap": base.NO_HIT_CAP,
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
    }
    write_outputs(
        manifest,
        chunk_feature_rows,
        candidate_feature_rows,
        debug_rows,
        parity_rows,
        cell_timing_rows,
        expansion_summaries,
    )
    output_dir = REPO_ROOT / OUTPUT_DIR_REL
    scope_manifest = {
        "run_label": RUN_LABEL,
        "dataset_status": DATASET_STATUS,
        "asset_provenance_manifest": ASSET_PROVENANCE_REL,
        "expected_cell_count": EXPECTED_CELL_COUNT,
        "profiles": [asdict(profile) for profile in BASE_PROFILES],
        "status": manifest.get("status"),
        "scan_count_completed": manifest.get("scan_count_completed"),
        "total_hit_count": manifest.get("total_hit_count"),
    }
    base.write_json(output_dir / "sample_index_matrix_scope_manifest.json", scope_manifest)
    return manifest


def main() -> None:
    manifest = run_matrix()
    print(f"[{RUN_LABEL}] status={manifest['status']}")
    print(f"[{RUN_LABEL}] completed_scans={manifest.get('scan_count_completed', 0)}")
    print(f"[{RUN_LABEL}] elapsed_seconds={manifest.get('elapsed_seconds', 0.0):.3f}")


if __name__ == "__main__":
    main()
