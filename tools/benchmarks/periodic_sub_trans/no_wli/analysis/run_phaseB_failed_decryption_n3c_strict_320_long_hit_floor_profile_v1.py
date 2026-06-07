from __future__ import annotations

"""
PhaseB strict-320 long-hit floor and anchored-region diagnostic v1.

IDE-friendly: edit CONFIG and run. No CLI required.

This is a reference/drop-in script for dev integration. It is deliberately
report-only and must not alter production scorer weights.

Inputs expected:
- strict O3/N3C hit rows with at least candidate_id, trial_id, direction, hd,
  phrase_length, start/end or start+phrase_length.
- optional pair rows with correct_candidate_id and other_candidate_id.

Outputs:
- candidate_anchor_summary_rows.csv
- candidate_anchor_region_rows.csv
- anchor_lens_margin_threshold_rows.csv
- anchor_lens_manifest.json
"""

import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
for path in (REPO_ROOT, REPO_ROOT / "src", SCRIPT_PATH.parent):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from strict_o3_anchor_reference_v1 import (  # noqa: E402
    HitRow,
    group_hits_by_candidate,
    summarise_candidate,
    write_csv,
    hit_from_csv_row,
    wilson_interval,
)

# =============================================================================
# CONFIG: edit here, run from IDE
# =============================================================================

RUN_LABEL = "phaseB_failed_decryption_n3c_strict_320_long_hit_floor_profile_v1"
REPORT_ONLY = True
REQUIRE_FWD_ONLY = True

INPUT_PHASE = "phaseB_failed_decryption_n3c_strict_320_corrected_consolidated_evidence_v1"
ANALYSIS_ROOT = REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis"
INPUT_DIR = ANALYSIS_ROOT / INPUT_PHASE
HIT_MANIFEST_CSV = INPUT_DIR / "hit_file_manifest_rows.csv"
PAIR_ROWS_CSV = INPUT_DIR / "unique_semantic_pairwise_gold_n3c_report_rows.csv"
OUTPUT_DIR = ANALYSIS_ROOT / RUN_LABEL
PROGRESS_EVERY_ROWS = 250_000

# First production sweep should include both variants. Keep the grid deliberately
# small until null calibration and known-correctness fixtures exist.
LENSES = (
    {"lens_name": "HD0_L10_nonoverlap_basic", "max_hd": 0, "min_phrase_length": 10, "min_gap": 0},
    {"lens_name": "HD0_L12_nonoverlap_basic", "max_hd": 0, "min_phrase_length": 12, "min_gap": 0},
    {"lens_name": "HD1_L12_support_probe", "max_hd": 1, "min_phrase_length": 12, "min_gap": 0},
    {"lens_name": "HD2_L15_telemetry_only", "max_hd": 2, "min_phrase_length": 15, "min_gap": 0},
)
MARGIN_THRESHOLDS = (0, 5, 10, 20, 30, 50)
TOTAL_PHRASE_ROWS_FOR_IDF = 1_000_000.0


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def repo_relative(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def resolve_repo_path(path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    import csv

    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return [dict(row) for row in csv.DictReader(fh)]


def load_manifest_hit_rows() -> tuple[list[HitRow], list[dict[str, object]]]:
    import csv
    import time

    manifest_rows = read_csv_rows(HIT_MANIFEST_CSV)
    expected_rows = sum(int(row["csv_data_rows"]) for row in manifest_rows)
    hit_rows: list[HitRow] = []
    input_files: list[dict[str, object]] = []
    started = time.monotonic()
    total_read = 0
    print(f"[{RUN_LABEL}] input_files={len(manifest_rows)} expected_hit_rows={expected_rows}")
    for file_index, manifest_row in enumerate(manifest_rows, start=1):
        hit_path = resolve_repo_path(manifest_row["hit_file"])
        file_rows = 0
        with hit_path.open("r", encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                hit_rows.append(hit_from_csv_row(row))
                file_rows += 1
                total_read += 1
                if total_read % PROGRESS_EVERY_ROWS == 0:
                    elapsed = time.monotonic() - started
                    rate = total_read / elapsed if elapsed else 0.0
                    eta = (expected_rows - total_read) / rate if rate else 0.0
                    print(
                        f"[{RUN_LABEL}] rows={total_read}/{expected_rows} "
                        f"elapsed_seconds={elapsed:.1f} eta_seconds={eta:.1f}"
                    )
        if file_rows != int(manifest_row["csv_data_rows"]):
            raise RuntimeError(
                f"{repo_relative(hit_path)} row mismatch: read {file_rows}, expected {manifest_row['csv_data_rows']}"
            )
        input_files.append(
            {
                "cohort_id": manifest_row.get("cohort_id", ""),
                "length_bucket": manifest_row.get("length_bucket", ""),
                "hit_file": repo_relative(hit_path),
                "rows": file_rows,
                "bytes": int(manifest_row["bytes"]),
                "sha256": manifest_row["sha256"],
            }
        )
        print(
            f"[{RUN_LABEL}] files={file_index}/{len(manifest_rows)} "
            f"rows={total_read}/{expected_rows}"
        )
    return hit_rows, input_files


def validate_hit_contract(hits: list[HitRow]) -> None:
    if not hits:
        raise ValueError("no hit rows loaded")
    if REQUIRE_FWD_ONLY:
        bad = sorted({hit.direction for hit in hits if hit.direction != "fwd"})
        if bad:
            raise ValueError(f"FWD-only contract failed; observed non-fwd directions={bad}")
    for hit in hits:
        if hit.end <= hit.start:
            raise ValueError(f"bad span for candidate={hit.candidate_id}: {hit.start}-{hit.end}")
        if hit.phrase_length <= 0:
            raise ValueError(f"bad phrase_length for candidate={hit.candidate_id}: {hit.phrase_length}")
        if hit.hd < 0:
            raise ValueError(f"bad hd for candidate={hit.candidate_id}: {hit.hd}")


def run_once() -> dict[str, Any]:
    out = OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    print(f"[{RUN_LABEL}] started_utc={utc_now()}")
    hits, input_files = load_manifest_hit_rows()
    validate_hit_contract(hits)
    pairs = read_csv_rows(PAIR_ROWS_CSV)
    grouped = group_hits_by_candidate(hits)

    all_summary_rows: list[dict[str, Any]] = []
    all_region_rows: list[dict[str, Any]] = []
    all_pair_rows: list[dict[str, Any]] = []

    for lens in LENSES:
        lens_name = str(lens["lens_name"])
        scores: dict[str, float] = {}
        for (trial_id, candidate_id), candidate_hits in sorted(grouped.items()):
            summary, regions = summarise_candidate(
                candidate_hits,
                candidate_id=candidate_id,
                trial_id=trial_id,
                min_phrase_length=int(lens["min_phrase_length"]),
                max_hd=int(lens["max_hd"]),
                min_gap=int(lens["min_gap"]),
                total_phrase_rows=TOTAL_PHRASE_ROWS_FOR_IDF,
            )
            scores[candidate_id] = summary.selected_weight_sum
            all_summary_rows.append({"lens_name": lens_name, **asdict(summary)})
            for region_index, region in enumerate(regions):
                all_region_rows.append({"lens_name": lens_name, "region_index": region_index, **asdict(region)})
        for margin in MARGIN_THRESHOLDS:
            covered = agree = break_count = tie = 0
            for pair in pairs:
                candidate_a = pair["candidate_a_id"]
                candidate_b = pair["candidate_b_id"]
                gold = pair["gold_winner_id"]
                if candidate_a not in scores or candidate_b not in scores:
                    continue
                score_a = scores[candidate_a]
                score_b = scores[candidate_b]
                if score_a >= score_b + float(margin):
                    winner = candidate_a
                elif score_b >= score_a + float(margin):
                    winner = candidate_b
                else:
                    winner = "tie"
                covered += 1
                if winner == "tie":
                    tie += 1
                elif winner == gold:
                    agree += 1
                else:
                    break_count += 1
            low, high = wilson_interval(break_count, covered) if covered else (0.0, 1.0)
            all_pair_rows.append(
                {
                    "lens_name": lens_name,
                    "margin": float(margin),
                    "covered": covered,
                    "agree": agree,
                    "break": break_count,
                    "tie": tie,
                    "break_rate": break_count / covered if covered else 0.0,
                    "break_rate_wilson95_low": low,
                    "break_rate_wilson95_high": high,
                }
            )

    write_csv(
        out / "candidate_anchor_summary_rows.csv",
        all_summary_rows,
        [
            "lens_name", "candidate_id", "trial_id", "selected_region_count",
            "selected_weight_sum", "selected_coverage_tokens", "longest_selected_phrase_len",
            "longest_hd0_phrase_len", "longest_hd1_phrase_len", "longest_hd2_phrase_len",
            "min_hd_at_len_ge_10", "min_hd_at_len_ge_12", "min_hd_at_len_ge_15",
            "min_hd_at_len_ge_18", "min_hd_at_len_ge_20",
            "rarest_hd0_count_len_ge_10", "rarest_hd0_count_len_ge_12",
        ],
    )
    write_csv(
        out / "candidate_anchor_region_rows.csv",
        all_region_rows,
        [
            "lens_name", "region_index", "candidate_id", "trial_id", "start", "end", "hd",
            "phrase_length", "weight", "phrase_row_id", "word_shape_id", "o4_confirmed",
        ],
    )
    write_csv(
        out / "anchor_lens_margin_threshold_rows.csv",
        all_pair_rows,
        [
            "lens_name", "margin", "covered", "agree", "break", "tie", "break_rate",
            "break_rate_wilson95_low", "break_rate_wilson95_high",
        ],
    )
    manifest = {
        "run_label": RUN_LABEL,
        "created_utc": utc_now(),
        "report_only": REPORT_ONLY,
        "require_fwd_only": REQUIRE_FWD_ONLY,
        "input_phase": INPUT_PHASE,
        "hit_manifest_csv": repo_relative(HIT_MANIFEST_CSV),
        "pair_rows_csv": repo_relative(PAIR_ROWS_CSV),
        "hit_rows": len(hits),
        "input_files": input_files,
        "candidate_groups": len(grouped),
        "pair_rows": len(pairs),
        "lenses": list(LENSES),
        "margin_thresholds": list(MARGIN_THRESHOLDS),
        "outputs": {
            "candidate_anchor_summary_rows": repo_relative(out / "candidate_anchor_summary_rows.csv"),
            "candidate_anchor_region_rows": repo_relative(out / "candidate_anchor_region_rows.csv"),
            "anchor_lens_margin_threshold_rows": repo_relative(out / "anchor_lens_margin_threshold_rows.csv"),
        },
        "production_scoring_change": False,
        "production_ranking_change": False,
        "score_bearing_use_approved": False,
    }
    (out / "anchor_lens_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print(f"[{RUN_LABEL}] status=complete")
    print(f"[{RUN_LABEL}] output_dir={repo_relative(out)}")
    return manifest


if __name__ == "__main__":
    print(json.dumps(run_once(), indent=2, sort_keys=True))
