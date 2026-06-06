from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
for path in (REPO_ROOT, REPO_ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from rune_decrypter_prime.scoring.ngram_hamming.reference import (
    phrase_entry_from_asset_row,
    scan_chunk_reference,
)
from rune_decrypter_prime.scoring.ngram_hamming.report_only_telemetry import (
    N3CNormalReportTelemetryConfig,
    REPORT_DETAILS_KEY,
    build_n3c_normal_report_telemetry,
    n3c_normal_report_profile,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.run_phaseB_ngram_hamming_lane2_gated_diagnostic_evidence_v1 import (
    phrase_profile_from_spec,
)


ANALYSIS_ROOT = REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis"
FIXTURE_DIR = REPO_ROOT / "assets/evaluation_corpora/failed_decryptions/historical_partial_solves_v1/fixture/phaseB_failed_decryption_retained_candidate_fixture_v1"
VALIDATION_MANIFEST = ANALYSIS_ROOT / "phaseB_failed_decryption_retained_candidate_fixture_validation_v1/validation_manifest.json"
RUNTIME_VALIDATION = ANALYSIS_ROOT / "phaseB_ngram_hamming_fast_runtime_lookup_index_validation_v1/validation_manifest.json"
SELECTED_ENTRIES = ANALYSIS_ROOT / "phaseB_ngram_hamming_lane2b_length_shape_stratified_diagnostic_evidence_v1/selected_phrase_entries.jsonl"
OUTPUT_DIR = ANALYSIS_ROOT / "phaseB_failed_decryption_fixture_n3c_report_telemetry_v1"


def _write_csv(path: Path, rows: list[dict[str, object]], fields: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def run_telemetry() -> dict[str, object]:
    fixture_validation = json.loads(VALIDATION_MANIFEST.read_text(encoding="utf-8"))
    runtime_validation = json.loads(RUNTIME_VALIDATION.read_text(encoding="utf-8"))
    if fixture_validation["status"] != "pass":
        raise RuntimeError("fixture validation is not pass")
    if runtime_validation["status"] != "pass":
        raise RuntimeError("runtime validation is not pass")
    spec = n3c_normal_report_profile()
    profile = phrase_profile_from_spec(spec)
    entries = []
    for line in SELECTED_ENTRIES.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row["ngram_order"] == 3 and row["dictionary_cut"] == "normal":
            row["rune_lengths"] = row["word_lengths"]
            row["encoding_direction"] = row["direction"]
            row["n"] = row["ngram_order"]
            entries.append(phrase_entry_from_asset_row(row))
    config = N3CNormalReportTelemetryConfig(
        enabled=True,
        runtime_index_asset_id=runtime_validation["asset_id"],
        compact_asset_id=runtime_validation["source_compact_asset_id"],
        runtime_validation_status="pass",
    )
    candidates = list(csv.DictReader((FIXTURE_DIR / "retained_candidate_rows.csv").open(encoding="utf-8", newline="")))
    summary_rows: list[dict[str, object]] = []
    report_rows: list[dict[str, object]] = []
    started = time.monotonic()
    for index, row in enumerate(candidates, start=1):
        tokens = json.loads(row["candidate_token_ids_json"])
        result = scan_chunk_reference(
            tokens, entries, profile, candidate_id=row["candidate_id"],
            chunk_id=f"{row['candidate_id']}:0", damage_level="historical_failed_decryption",
        )
        telemetry = build_n3c_normal_report_telemetry(
            candidate_id=row["candidate_id"], hits=result.phrase_hits, config=config,
        )
        summary = {
            "trial_id": row["trial_id"], "candidate_id": row["candidate_id"],
            "candidate_rank": row["candidate_rank"], "baseline_score": row["baseline_score"],
            "cluster_count": telemetry["cluster_count"], "exact_cluster_count": telemetry["exact_cluster_count"],
            "hit_count": telemetry["hit_count"], "best_hit_signature": telemetry["best_hit_signature"],
            "dominant_cluster_hit_fraction": telemetry["dominant_cluster_hit_fraction"],
            "dominant_phrase_hit_fraction": telemetry["dominant_phrase_hit_fraction"],
            "warning_flags": json.dumps(telemetry["warning_flags"], separators=(",", ":")),
            "telemetry_present": True, "production_rank_effect": telemetry["production_rank_effect"],
        }
        summary_rows.append(summary)
        report_rows.append({
            "trial_id": row["trial_id"], "candidate_id": row["candidate_id"],
            "score": float(row["baseline_score"]), "details": {REPORT_DETAILS_KEY: telemetry},
        })
        if index == 1 or index % 25 == 0 or index == len(candidates):
            elapsed = time.monotonic() - started
            eta = elapsed / index * (len(candidates) - index)
            print(
                f"[phaseB_failed_decryption_fixture_n3c_report_telemetry_v1] "
                f"candidates={index}/{len(candidates)} elapsed_seconds={elapsed:.1f} eta_seconds={eta:.1f}"
            )
    summary_by_key = {(row["trial_id"], row["candidate_id"]): row for row in summary_rows}
    pair_rows: list[dict[str, object]] = []
    for row in csv.DictReader((FIXTURE_DIR / "candidate_pair_rows.csv").open(encoding="utf-8", newline="")):
        a = summary_by_key[(row["trial_id"], row["candidate_a_id"])]
        b = summary_by_key[(row["trial_id"], row["candidate_b_id"])]
        a_tuple = (int(a["exact_cluster_count"]), int(a["cluster_count"]), int(a["hit_count"]))
        b_tuple = (int(b["exact_cluster_count"]), int(b["cluster_count"]), int(b["hit_count"]))
        phrase_winner = row["candidate_a_id"] if a_tuple > b_tuple else row["candidate_b_id"] if b_tuple > a_tuple else ""
        pair_rows.append({
            "pair_id": row["pair_id"], "trial_id": row["trial_id"],
            "candidate_a_id": row["candidate_a_id"], "candidate_b_id": row["candidate_b_id"],
            "baseline_winner_id": row["baseline_winner_id"], "phrase_report_only_winner_id": phrase_winner,
            "phrase_cmp": (a_tuple > b_tuple) - (a_tuple < b_tuple),
            "candidate_a_tuple": json.dumps(a_tuple), "candidate_b_tuple": json.dumps(b_tuple),
            "candidate_a_best_hit_signature": a["best_hit_signature"],
            "candidate_b_best_hit_signature": b["best_hit_signature"],
            "agrees_with_baseline": phrase_winner == row["baseline_winner_id"] if phrase_winner else "",
            "gold_winner_id": row["gold_winner_id"],
            "outcome_class_if_gold_available": "offline_unapproved_comparison",
            "notes": "report_only; no score or rank effect",
        })
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with (OUTPUT_DIR / "candidate_report_rows.jsonl").open("w", encoding="utf-8") as handle:
        for row in report_rows:
            handle.write(json.dumps(row, separators=(",", ":")) + "\n")
    _write_csv(OUTPUT_DIR / "candidate_telemetry_summary_rows.csv", summary_rows, tuple(summary_rows[0]))
    _write_csv(OUTPUT_DIR / "pair_report_only_rows.csv", pair_rows, tuple(pair_rows[0]))
    warnings = [row for row in summary_rows if row["warning_flags"] != "[]"]
    candidates_with_hits = sum(int(row["hit_count"]) > 0 for row in summary_rows)
    candidates_with_clusters = sum(int(row["cluster_count"]) > 0 for row in summary_rows)
    phrase_pair_preferences = sum(bool(row["phrase_report_only_winner_id"]) for row in pair_rows)
    _write_csv(OUTPUT_DIR / "concentration_warning_rows.csv", warnings, tuple(summary_rows[0]))
    manifest = {
        "status": "pass", "fixture_id": "phaseB_failed_decryption_retained_candidate_fixture_v1",
        "fixture_validation_status": "pass", "candidate_count": len(summary_rows), "pair_count": len(pair_rows),
        "telemetry_profile_id": "BR_O3_conservative", "canonical_profile_id": "N3C",
        "phrase_entry_scope": "lane2b_selected_bounded_subset",
        "selected_phrase_entry_count": len(entries),
        "full_runtime_index_queried": False,
        "coverage_interpretation": "bounded_canary_only_not_full_runtime_coverage",
        "candidates_with_hits": candidates_with_hits,
        "candidates_with_clusters": candidates_with_clusters,
        "phrase_pair_preference_count": phrase_pair_preferences,
        "phrase_pair_tie_count": len(pair_rows) - phrase_pair_preferences,
        "report_authority": "report_only_telemetry", "production_rank_effect": "none",
        "production_scoring_change": False, "production_ranking_change": False,
        "baseline_scores_preserved": True, "baseline_order_preserved": True,
        "runtime_asset_id": runtime_validation["asset_id"], "runtime_validation_status": "pass",
        "old_phrase_index_v1_used": False, "sample_asset_used": False,
        "full_raw_shards_used_directly_as_runtime": False,
    }
    (OUTPUT_DIR / "run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (OUTPUT_DIR / "readout.md").write_text(
        f"# Failed-Decryption Fixture N3C Report Telemetry\n\n- status: `pass`\n"
        f"- candidates: `{len(summary_rows)}`\n- pairs: `{len(pair_rows)}`\n"
        f"- phrase entry scope: `lane2b_selected_bounded_subset` (`{len(entries)}` entries)\n"
        "- full runtime index queried: `false`\n"
        f"- candidates with hits: `{candidates_with_hits}`\n"
        f"- phrase pair preferences: `{phrase_pair_preferences}`\n"
        "- interpretation: this is a bounded wiring canary, not full-runtime N3C coverage; "
        "zero hits must not be treated as evidence against N3C\n"
        "- production rank effect: `none`\n", encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    run_telemetry()
