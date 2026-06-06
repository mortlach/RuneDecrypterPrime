from __future__ import annotations

import csv
import json
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
ANALYSIS_ROOT = REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis"
RUNTIME_MANIFEST = ANALYSIS_ROOT / "phaseB_ngram_hamming_fast_runtime_lookup_index_v1/runtime_index_manifest.json"
RUNTIME_VALIDATION = ANALYSIS_ROOT / "phaseB_ngram_hamming_fast_runtime_lookup_index_validation_v1/validation_manifest.json"
FIXTURE_DIR = REPO_ROOT / "assets/evaluation_corpora/failed_decryptions/historical_partial_solves_v1/fixture/phaseB_failed_decryption_retained_candidate_fixture_v1"
OUTPUT_DIR = ANALYSIS_ROOT / "phaseB_failed_decryption_full_runtime_n3c_query_readiness_v1"

PROFILE_ID = "BR_O3_conservative"
CANONICAL_PROFILE_ID = "N3C"
DIRECTION = "fwd"
ORDER = 3
CUT = "normal"
MIN_PHRASE_TOKEN_LENGTH = 8


def assess_readiness() -> dict[str, object]:
    runtime = json.loads(RUNTIME_MANIFEST.read_text(encoding="utf-8"))
    validation = json.loads(RUNTIME_VALIDATION.read_text(encoding="utf-8"))
    candidates = list(
        csv.DictReader((FIXTURE_DIR / "retained_candidate_rows.csv").open(encoding="utf-8", newline=""))
    )
    eligible = [
        row for row in runtime["files"]
        if row["direction"] == DIRECTION
        and int(row["ngram_order"]) == ORDER
        and row["dictionary_cut"] == CUT
        and int(row["phrase_token_length"]) >= MIN_PHRASE_TOKEN_LENGTH
    ]
    candidate_lengths = [int(row["candidate_token_count"]) for row in candidates]
    raw_phrase_position_checks = sum(
        int(row["phrase_count"]) * sum(max(0, length - int(row["phrase_token_length"]) + 1) for length in candidate_lengths)
        for row in eligible
    )
    manifest = {
        "status": "blocked_requires_candidate_keyed_query",
        "profile_id": PROFILE_ID,
        "canonical_profile_id": CANONICAL_PROFILE_ID,
        "direction": DIRECTION,
        "ngram_order": ORDER,
        "dictionary_cut": CUT,
        "min_phrase_token_length": MIN_PHRASE_TOKEN_LENGTH,
        "runtime_validation_status": validation["status"],
        "eligible_runtime_file_count": len(eligible),
        "eligible_phrase_row_count": sum(int(row["phrase_count"]) for row in eligible),
        "eligible_compressed_bytes": sum(int(row["bytes"]) for row in eligible),
        "fixture_candidate_count": len(candidates),
        "fixture_candidate_token_count_min": min(candidate_lengths),
        "fixture_candidate_token_count_max": max(candidate_lengths),
        "naive_raw_phrase_position_checks": raw_phrase_position_checks,
        "naive_full_scan_approved": False,
        "required_next_implementation": "candidate_keyed_hamming_neighbour_query",
        "required_next_run": "small_timed_full_group_canary",
        "production_scoring_change": False,
        "production_ranking_change": False,
        "broad_candidate_scan_started": False,
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "readiness_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (OUTPUT_DIR / "readout.md").write_text(
        "# Failed-Decryption Full-Runtime N3C Query Readiness\n\n"
        f"- status: `{manifest['status']}`\n"
        f"- eligible runtime files: `{manifest['eligible_runtime_file_count']}`\n"
        f"- eligible phrase rows: `{manifest['eligible_phrase_row_count']}`\n"
        f"- eligible compressed bytes: `{manifest['eligible_compressed_bytes']}`\n"
        f"- fixture candidates: `{manifest['fixture_candidate_count']}`\n"
        f"- naive phrase-position checks: `{manifest['naive_raw_phrase_position_checks']}`\n"
        "- naive full scan approved: `false`\n"
        "- next implementation: `candidate_keyed_hamming_neighbour_query`\n"
        "- next run: `small_timed_full_group_canary`\n"
        "- production rank effect: `none`\n",
        encoding="utf-8",
    )
    return manifest


if __name__ == "__main__":
    assess_readiness()
