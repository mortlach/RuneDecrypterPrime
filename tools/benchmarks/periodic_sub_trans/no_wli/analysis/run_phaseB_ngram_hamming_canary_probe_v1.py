from __future__ import annotations

import csv
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

from rune_decrypter_prime.scoring.ngram_hamming.fast_backend import (  # noqa: E402
    fast_ngram_hamming_available,
    scan_chunk_fast,
)
from rune_decrypter_prime.scoring.ngram_hamming.reference import (  # noqa: E402
    PhraseProfile,
    profile_allows_entry,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (  # noqa: E402
    run_phaseB_ngram_hamming_full_raw_canary_v1 as canary_core,
)


RUN_LABEL = "phaseB_ngram_hamming_canary_probe_v1"
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_canary_probe_v1"
)
ASSET_SUMMARY_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_canary_probe_assets_summary_v1/canary_probe_asset_summary_manifest.json"
)

REQUIRED_ASSET_MODE = "canary_probe"
SCAN_MODE = "whole_phrase_only"
INTERNAL_PHRASE_WINDOWS = False
DIRECTION = "fwd"
DICTIONARY_CUTS = ("normal", "strict")
NGRAM_ORDERS = (2, 3)
SAMPLE_LINE_LIMIT_PER_ORDER = 25_000
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


def validate_canary_probe_summary(manifest: dict[str, Any]) -> list[str]:
    blocked: list[str] = []
    if manifest.get("asset_mode") != REQUIRED_ASSET_MODE:
        blocked.append("required_asset_mode=canary_probe but actual_asset_mode differs")
    if manifest.get("full_asset_available") is not False:
        blocked.append("canary probe must not claim full_asset_available")
    if manifest.get("full_raw_ngram_rebuild_confirmed") is not False:
        blocked.append("canary probe must not claim full_raw_ngram_rebuild_confirmed")
    if manifest.get("sample_line_limit_per_order") != SAMPLE_LINE_LIMIT_PER_ORDER:
        blocked.append("canary probe sample_line_limit_per_order is missing or wrong")
    if manifest.get("scan_mode") != SCAN_MODE:
        blocked.append("scan_mode is not whole_phrase_only")
    if manifest.get("internal_phrase_windows") is not False:
        blocked.append("internal_phrase_windows is not false")
    phrase_index = manifest.get("phrase_index_path", "")
    if not phrase_index or not (REPO_ROOT / phrase_index).exists():
        blocked.append("canary probe phrase index is missing")
    return blocked


def run_canary_probe() -> dict[str, Any]:
    started = time.perf_counter()
    output_dir = REPO_ROOT / OUTPUT_DIR_REL
    ensure_under_repo(output_dir / "canary_probe_manifest.json")
    asset_summary = read_json(ASSET_SUMMARY_REL)
    blocked = validate_canary_probe_summary(asset_summary)
    full_gate_reasons = canary_core.validate_full_asset_summary(asset_summary)
    full_gate_result = "blocked_as_expected_for_probe" if full_gate_reasons else "unexpected_pass"
    if not full_gate_reasons:
        blocked.append("full-run gate unexpectedly accepted canary probe assets")
    if not fast_ngram_hamming_available():
        blocked.append("_ngram_hamming_fast extension is unavailable")
    selected, chunks_by_candidate, missing_selection = canary_core.select_canary_candidates()
    runnable_selected = [row for row in selected if row.get("candidate_id")]
    if missing_selection:
        blocked.extend(f"missing canary stratum {role}: {reason}" for role, reason in missing_selection.items())

    phrase_entries = {} if blocked else canary_core.load_phrase_entries(asset_summary["phrase_index_path"])
    phrase_metadata = {} if blocked else canary_core.load_phrase_metadata(asset_summary["phrase_index_path"])
    selected_tokens = {} if blocked else canary_core.load_tokens(runnable_selected)
    cell_rows: list[dict[str, Any]] = []
    hit_rows: list[dict[str, Any]] = []
    eligible_counts: dict[str, int] = {}
    scan_count = 0

    if not blocked:
        for selected_row in runnable_selected:
            candidate_id = selected_row["candidate_id"]
            role = selected_row["selection_role"]
            token_key = canary_core.base.candidate_hash_from_id(candidate_id)
            tokens = selected_tokens[token_key]
            for chunk_row in chunks_by_candidate[candidate_id][:MAX_CHUNKS_PER_CANDIDATE]:
                start = canary_core.base.parse_int(chunk_row["chunk_start"])
                end = canary_core.base.parse_int(chunk_row["chunk_end"])
                chunk_tokens = tokens[start:end]
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
                                damage_level="canary_probe",
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
                                    canary_core.hit_payload(
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
                                f"eligible={len(eligible)} attempts={attempts} elapsed={elapsed:.3f}s",
                                flush=True,
                            )

    scan_elapsed_seconds = sum(float(row["elapsed_seconds"]) for row in cell_rows)
    attempts = sum(int(row["phrase_verification_attempts"]) for row in cell_rows)
    aggregate_rows = canary_core.aggregate_hit_rows(hit_rows)
    comparison_rows = canary_core.compare_p2_p3(hit_rows)
    candidate_aggregate_rows = canary_core.candidate_chunk_profile_aggregate_rows(cell_rows, hit_rows)
    manifest = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if not blocked and cell_rows else "blocked",
        "blocked_reasons": blocked,
        "asset_summary_manifest": ASSET_SUMMARY_REL,
        "asset_mode": asset_summary.get("asset_mode"),
        "sample_line_limit_per_order": asset_summary.get("sample_line_limit_per_order"),
        "full_asset_available": asset_summary.get("full_asset_available"),
        "full_raw_ngram_rebuild_confirmed": asset_summary.get("full_raw_ngram_rebuild_confirmed"),
        "full_run_gate_on_probe_assets": full_gate_result,
        "full_run_gate_blocked_reasons": full_gate_reasons,
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
        "completed_scan_cells": len(cell_rows),
        "expected_scan_cells": len(runnable_selected) * MAX_CHUNKS_PER_CANDIDATE * len(DICTIONARY_CUTS) * len(NGRAM_ORDERS) * len(PROFILES),
        "phrase_verification_attempts": attempts,
        "scan_elapsed_seconds": scan_elapsed_seconds,
        "elapsed_seconds": time.perf_counter() - started,
        "attempts_per_second": attempts / scan_elapsed_seconds if scan_elapsed_seconds else 0.0,
        "eligible_phrase_counts_by_cut_order_profile": eligible_counts,
        "total_hit_count": len(hit_rows),
        "long_run_runtime_projection_valid": False,
        "long_run_runtime_projection_note": "Canary probe proves workflow/data contract only; do not use capped probe timing as full-run sizing.",
        "length_bias_warning": "P2/P3 len8 is a minimum whole-phrase token-length gate, not fixed-length 8-rune evidence.",
    }
    write_json(output_dir / "canary_probe_manifest.json", manifest)
    write_csv(output_dir / "canary_probe_cell_timing_rows.csv", cell_rows)
    write_jsonl(output_dir / "canary_probe_hit_rows.jsonl", hit_rows)
    write_csv(output_dir / "p2_p3_hit_retention_rows.csv", comparison_rows)
    write_csv(output_dir / "candidate_chunk_profile_aggregate_rows.csv", candidate_aggregate_rows)
    for name, rows in aggregate_rows.items():
        write_csv(output_dir / name, rows)
    readout = [
        "# PhaseB N-Gram Hamming Canary Probe v1",
        "",
        f"Status: `{manifest['status']}`",
        f"Asset mode: `{manifest['asset_mode']}`",
        f"Full-run gate on probe assets: `{full_gate_result}`",
        f"Completed scan cells: `{manifest['completed_scan_cells']}` / `{manifest['expected_scan_cells']}`",
        f"Total hits: `{manifest['total_hit_count']}`",
        "",
        "This canary proves workflow, provenance labels, schema, P2/P3 scan plumbing, and full/sample gate behaviour.",
        "It is not a full raw asset pass and must not be used as long-run runtime sizing.",
        "",
        "P2/P3 are whole-phrase evidence with a minimum length gate, not fixed-length 8-rune evidence.",
    ]
    if blocked:
        readout.extend(["", "## Blocked Reasons", ""])
        readout.extend(f"- `{reason}`" for reason in blocked)
    (output_dir / "readout.md").write_text("\n".join(readout) + "\n", encoding="utf-8")
    print(f"[{RUN_LABEL}] status={manifest['status']}", flush=True)
    print(f"[{RUN_LABEL}] completed_scan_cells={manifest['completed_scan_cells']}", flush=True)
    return manifest


def main() -> None:
    run_canary_probe()


if __name__ == "__main__":
    main()
