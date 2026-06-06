from __future__ import annotations

import bisect
import csv
import json
import math
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
for path in (REPO_ROOT, REPO_ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


PHASE = "phaseB_failed_decryption_n3c_strict_320_anchor_lens_quickcheck_v1"
INPUT_PHASE = "phaseB_failed_decryption_n3c_strict_320_corrected_consolidated_evidence_v1"
ANALYSIS_ROOT = REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis"
INPUT_DIR = ANALYSIS_ROOT / INPUT_PHASE
OUTPUT_DIR = ANALYSIS_ROOT / PHASE
FIXTURE_DIR = (
    REPO_ROOT
    / "assets/evaluation_corpora/failed_decryptions/historical_partial_solves_v1/fixture"
    / "phaseB_failed_decryption_retained_candidate_fixture_v1"
)

HIT_MANIFEST_CSV = INPUT_DIR / "hit_file_manifest_rows.csv"
PAIRWISE_CSV = INPUT_DIR / "unique_semantic_pairwise_gold_n3c_report_rows.csv"
RETAINED_CANDIDATES_CSV = FIXTURE_DIR / "retained_candidate_rows.csv"

MIN_GAP = 0
PROGRESS_EVERY_FILES = 1
PROGRESS_EVERY_ROWS = 250_000

REQUIRED_HIT_COLUMNS = {
    "trial_id",
    "candidate_id",
    "phrase_token_length",
    "phrase_id",
    "hit_start",
    "hit_end",
    "total_phrase_hd",
    "exact_flag",
}

REQUIRED_PAIR_COLUMNS = {
    "semantic_pair_id",
    "trial_id",
    "candidate_a_id",
    "candidate_b_id",
    "gold_winner_id",
    "baseline_winner_id",
    "baseline_correct",
    "can_observe_break",
    "can_observe_rescue",
}


@dataclass(frozen=True)
class Lens:
    name: str
    min_phrase_len: int
    max_hd: int | None = None
    exact_hd: int | None = None
    description: str = ""

    def accepts(self, phrase_len: int, total_hd: int) -> bool:
        if phrase_len < self.min_phrase_len:
            return False
        if self.exact_hd is not None and total_hd != self.exact_hd:
            return False
        if self.max_hd is not None and total_hd > self.max_hd:
            return False
        return True


DEFAULT_LENSES = (
    Lens("hd0_len8", min_phrase_len=8, exact_hd=0, description="Exact-only strict O3, length >= 8."),
    Lens("hd0_len10", min_phrase_len=10, exact_hd=0, description="Exact-only strict O3, length >= 10."),
    Lens("hd0_len12", min_phrase_len=12, exact_hd=0, description="Exact-only strict O3, length >= 12."),
    Lens("hd0_len15", min_phrase_len=15, exact_hd=0, description="Exact-only strict O3, length >= 15."),
    Lens("hd_le1_len12", min_phrase_len=12, max_hd=1, description="HD<=1 strict O3 support, length >= 12."),
    Lens("hd_le1_len15", min_phrase_len=15, max_hd=1, description="HD<=1 strict O3 support, length >= 15."),
    Lens("hd_le2_len12", min_phrase_len=12, max_hd=2, description="HD<=2 strict O3 support, length >= 12."),
    Lens("hd_le2_len15", min_phrase_len=15, max_hd=2, description="HD<=2 strict O3 support, length >= 15."),
)

MARGIN_THRESHOLDS = (0.0, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0, 100.0)


@dataclass
class SpanEvidence:
    trial_id: str
    candidate_id: str
    start: int
    end: int
    best_phrase_id: str
    best_phrase_len: int
    best_total_hd: int
    weight: float
    raw_hit_count_at_span: int = 0
    exact_hit_count_at_span: int = 0


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def hit_weight(phrase_len: int, total_hd: int) -> float:
    return max(0.0, float(phrase_len - 2 * total_hd))


def repo_relative(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def resolve_repo_path(path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_manifest(path: Path) -> list[dict[str, str]]:
    rows = read_rows(path)
    if not rows:
        raise RuntimeError(f"empty manifest: {repo_relative(path)}")
    if "hit_file" not in rows[0]:
        raise RuntimeError(f"hit manifest missing hit_file column: {repo_relative(path)}")
    return rows


def load_pairs(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_PAIR_COLUMNS - set(reader.fieldnames or ())
        if missing:
            raise RuntimeError(f"pairwise CSV missing columns: {sorted(missing)}")
        return list(reader)


def load_candidate_lengths(path: Path) -> dict[str, int]:
    lengths: dict[str, int] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            lengths[row["candidate_id"]] = int(row["candidate_token_count"])
    return lengths


def weighted_interval_schedule(intervals: list[SpanEvidence], min_gap: int) -> list[SpanEvidence]:
    if not intervals:
        return []

    ordered = sorted(intervals, key=lambda x: (x.end, x.start, -x.weight, -x.best_phrase_len, x.best_phrase_id))
    ends = [interval.end for interval in ordered]
    p = [bisect.bisect_right(ends, interval.start - min_gap) - 1 for interval in ordered]

    dp = [0.0] * len(ordered)
    take = [False] * len(ordered)
    for i, interval in enumerate(ordered):
        include = interval.weight + (dp[p[i]] if p[i] >= 0 else 0.0)
        exclude = dp[i - 1] if i else 0.0
        if include > exclude:
            dp[i] = include
            take[i] = True
        else:
            dp[i] = exclude

    selected: list[SpanEvidence] = []
    i = len(ordered) - 1
    while i >= 0:
        include = ordered[i].weight + (dp[p[i]] if p[i] >= 0 else 0.0)
        exclude = dp[i - 1] if i else 0.0
        if take[i] and include >= exclude:
            selected.append(ordered[i])
            i = p[i]
        else:
            i -= 1
    selected.reverse()
    return selected


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def update_span(
    span_map: dict[tuple[int, int], SpanEvidence],
    *,
    trial_id: str,
    candidate_id: str,
    start: int,
    end: int,
    phrase_id: str,
    phrase_len: int,
    total_hd: int,
    exact: bool,
    weight: float,
) -> None:
    key = (start, end)
    existing = span_map.get(key)
    if existing is None:
        span_map[key] = SpanEvidence(
            trial_id=trial_id,
            candidate_id=candidate_id,
            start=start,
            end=end,
            best_phrase_id=phrase_id,
            best_phrase_len=phrase_len,
            best_total_hd=total_hd,
            weight=weight,
            raw_hit_count_at_span=1,
            exact_hit_count_at_span=1 if total_hd == 0 or exact else 0,
        )
        return

    existing.raw_hit_count_at_span += 1
    if total_hd == 0 or exact:
        existing.exact_hit_count_at_span += 1
    replacement_key = (weight, phrase_len, -total_hd, phrase_id)
    current_key = (existing.weight, existing.best_phrase_len, -existing.best_total_hd, existing.best_phrase_id)
    if replacement_key > current_key:
        existing.best_phrase_id = phrase_id
        existing.best_phrase_len = phrase_len
        existing.best_total_hd = total_hd
        existing.weight = weight


def build_quickcheck() -> dict[str, object]:
    started = time.monotonic()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    manifest_rows = load_manifest(HIT_MANIFEST_CSV)
    pair_rows = load_pairs(PAIRWISE_CSV)
    candidate_lengths = load_candidate_lengths(RETAINED_CANDIDATES_CSV)

    expected_hit_rows = sum(int(row["csv_data_rows"]) for row in manifest_rows)
    print(f"[{PHASE}] started_utc={utc_now()}")
    print(f"[{PHASE}] input_files={len(manifest_rows)} expected_hit_rows={expected_hit_rows}")

    span_maps: dict[str, dict[str, dict[tuple[int, int], SpanEvidence]]] = {
        lens.name: {} for lens in DEFAULT_LENSES
    }
    filtered_hit_counts: dict[tuple[str, str], int] = {}
    input_files: list[dict[str, object]] = []
    total_rows_read = 0

    for file_index, manifest_row in enumerate(manifest_rows, start=1):
        hit_path = resolve_repo_path(manifest_row["hit_file"])
        if not hit_path.exists():
            raise FileNotFoundError(repo_relative(hit_path))
        file_rows = 0
        input_files.append({
            "cohort_id": manifest_row.get("cohort_id", ""),
            "length_bucket": manifest_row.get("length_bucket", ""),
            "hit_file": repo_relative(hit_path),
            "manifest_rows": int(manifest_row["csv_data_rows"]),
            "manifest_bytes": int(manifest_row["bytes"]),
            "manifest_sha256": manifest_row["sha256"],
        })
        with hit_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            missing = REQUIRED_HIT_COLUMNS - set(reader.fieldnames or ())
            if missing:
                raise RuntimeError(f"{repo_relative(hit_path)} missing hit columns: {sorted(missing)}")
            for row in reader:
                file_rows += 1
                total_rows_read += 1
                phrase_len = int(row["phrase_token_length"])
                total_hd = int(row["total_phrase_hd"])
                start = int(row["hit_start"])
                end = int(row["hit_end"])
                exact = parse_bool(row["exact_flag"])
                candidate_id = row["candidate_id"]
                weight = hit_weight(phrase_len, total_hd)

                for lens in DEFAULT_LENSES:
                    if not lens.accepts(phrase_len, total_hd):
                        continue
                    filtered_hit_counts[(lens.name, candidate_id)] = (
                        filtered_hit_counts.get((lens.name, candidate_id), 0) + 1
                    )
                    candidate_map = span_maps[lens.name].setdefault(candidate_id, {})
                    update_span(
                        candidate_map,
                        trial_id=row["trial_id"],
                        candidate_id=candidate_id,
                        start=start,
                        end=end,
                        phrase_id=row["phrase_id"],
                        phrase_len=phrase_len,
                        total_hd=total_hd,
                        exact=exact,
                        weight=weight,
                    )
                if total_rows_read % PROGRESS_EVERY_ROWS == 0:
                    elapsed = time.monotonic() - started
                    rate = total_rows_read / elapsed if elapsed else 0.0
                    remaining = max(0, expected_hit_rows - total_rows_read)
                    eta = remaining / rate if rate else 0.0
                    print(
                        f"[{PHASE}] rows={total_rows_read}/{expected_hit_rows} "
                        f"elapsed_seconds={elapsed:.1f} eta_seconds={eta:.1f}"
                    )
        expected_file_rows = int(manifest_row["csv_data_rows"])
        if file_rows != expected_file_rows:
            raise RuntimeError(
                f"{repo_relative(hit_path)} row mismatch: read {file_rows}, expected {expected_file_rows}"
            )
        if file_index % PROGRESS_EVERY_FILES == 0:
            elapsed = time.monotonic() - started
            print(
                f"[{PHASE}] files={file_index}/{len(manifest_rows)} "
                f"rows={total_rows_read}/{expected_hit_rows} elapsed_seconds={elapsed:.1f}"
            )

    candidate_summary_rows: list[dict[str, object]] = []
    region_rows: list[dict[str, object]] = []
    score_by_lens_candidate: dict[tuple[str, str], dict[str, object]] = {}
    print(f"[{PHASE}] selecting_intervals started elapsed_seconds={time.monotonic() - started:.1f}")

    for lens in DEFAULT_LENSES:
        for candidate_id, span_map in sorted(span_maps[lens.name].items()):
            intervals = list(span_map.values())
            selected = weighted_interval_schedule(intervals, min_gap=MIN_GAP)
            selected_weight = sum(interval.weight for interval in selected)
            selected_tokens = sum(max(0, interval.end - interval.start) for interval in selected)
            candidate_length = candidate_lengths[candidate_id]
            trial_ids = sorted({interval.trial_id for interval in intervals})
            trial_id = trial_ids[0] if trial_ids else ""

            summary = {
                "lens_name": lens.name,
                "trial_id": trial_id,
                "candidate_id": candidate_id,
                "filtered_hit_count": filtered_hit_counts.get((lens.name, candidate_id), 0),
                "dedup_span_count": len(intervals),
                "selected_region_count": len(selected),
                "selected_region_score": f"{selected_weight:.6f}",
                "selected_covered_token_count": selected_tokens,
                "selected_coverage_fraction": f"{selected_tokens / candidate_length:.6f}",
                "candidate_length": candidate_length,
                "min_gap": MIN_GAP,
            }
            candidate_summary_rows.append(summary)
            score_by_lens_candidate[(lens.name, candidate_id)] = summary

            for region_rank, interval in enumerate(selected, start=1):
                region_rows.append({
                    "lens_name": lens.name,
                    "trial_id": interval.trial_id,
                    "candidate_id": interval.candidate_id,
                    "region_rank": region_rank,
                    "start_offset": interval.start,
                    "end_offset": interval.end,
                    "region_length": interval.end - interval.start,
                    "region_weight": f"{interval.weight:.6f}",
                    "best_phrase_id": interval.best_phrase_id,
                    "best_phrase_len": interval.best_phrase_len,
                    "best_total_hd": interval.best_total_hd,
                    "raw_hit_count_at_span": interval.raw_hit_count_at_span,
                    "exact_hit_count_at_span": interval.exact_hit_count_at_span,
                })
        print(
            f"[{PHASE}] lens_selected={lens.name} "
            f"candidate_summaries={len([r for r in candidate_summary_rows if r['lens_name'] == lens.name])} "
            f"elapsed_seconds={time.monotonic() - started:.1f}"
        )

    pairwise_rows: list[dict[str, object]] = []
    threshold_rows: list[dict[str, object]] = []

    for lens in DEFAULT_LENSES:
        per_threshold = {
            threshold: {"covered": 0, "agree": 0, "break": 0, "tie": 0}
            for threshold in MARGIN_THRESHOLDS
        }
        for pair in pair_rows:
            candidate_a_id = pair["candidate_a_id"]
            candidate_b_id = pair["candidate_b_id"]
            gold_winner_id = pair["gold_winner_id"]
            candidate_a_summary = score_by_lens_candidate.get((lens.name, candidate_a_id))
            candidate_b_summary = score_by_lens_candidate.get((lens.name, candidate_b_id))
            if candidate_a_summary is None or candidate_b_summary is None:
                continue

            candidate_a_score = float(candidate_a_summary["selected_region_score"])
            candidate_b_score = float(candidate_b_summary["selected_region_score"])
            abs_margin = abs(candidate_a_score - candidate_b_score)

            if math.isclose(candidate_a_score, candidate_b_score):
                winner_id = "tie"
                result = "tie"
            elif candidate_a_score > candidate_b_score:
                winner_id = candidate_a_id
                result = "agree" if winner_id == gold_winner_id else "break"
            else:
                winner_id = candidate_b_id
                result = "agree" if winner_id == gold_winner_id else "break"

            pairwise_rows.append({
                "lens_name": lens.name,
                "semantic_pair_id": pair["semantic_pair_id"],
                "trial_id": pair["trial_id"],
                "candidate_a_id": candidate_a_id,
                "candidate_b_id": candidate_b_id,
                "gold_winner_id": gold_winner_id,
                "baseline_winner_id": pair["baseline_winner_id"],
                "baseline_correct": pair["baseline_correct"],
                "can_observe_break": pair["can_observe_break"],
                "can_observe_rescue": pair["can_observe_rescue"],
                "candidate_a_anchor_score": f"{candidate_a_score:.6f}",
                "candidate_b_anchor_score": f"{candidate_b_score:.6f}",
                "anchor_winner_id": winner_id,
                "anchor_pair_result": result,
                "absolute_score_margin": f"{abs_margin:.6f}",
                "candidate_a_selected_region_count": candidate_a_summary["selected_region_count"],
                "candidate_b_selected_region_count": candidate_b_summary["selected_region_count"],
                "candidate_a_selected_coverage_fraction": candidate_a_summary["selected_coverage_fraction"],
                "candidate_b_selected_coverage_fraction": candidate_b_summary["selected_coverage_fraction"],
            })
            for threshold in MARGIN_THRESHOLDS:
                if abs_margin >= threshold:
                    per_threshold[threshold]["covered"] += 1
                    per_threshold[threshold][result] += 1

        for threshold, counts in per_threshold.items():
            covered = counts["covered"]
            threshold_rows.append({
                "lens_name": lens.name,
                "min_absolute_score_margin": f"{threshold:.6f}",
                "covered_pair_count": covered,
                "agree_count": counts["agree"],
                "break_count": counts["break"],
                "tie_count": counts["tie"],
                "break_rate": f"{(counts['break'] / covered) if covered else 0.0:.6f}",
                "agree_rate": f"{(counts['agree'] / covered) if covered else 0.0:.6f}",
                "tie_rate": f"{(counts['tie'] / covered) if covered else 0.0:.6f}",
            })

    write_csv(OUTPUT_DIR / "candidate_anchor_summary_rows.csv", candidate_summary_rows)
    write_csv(OUTPUT_DIR / "candidate_anchor_region_rows.csv", region_rows)
    write_csv(OUTPUT_DIR / "candidate_anchor_pairwise_rows.csv", pairwise_rows)
    write_csv(OUTPUT_DIR / "anchor_lens_margin_threshold_rows.csv", threshold_rows)

    elapsed = time.monotonic() - started
    manifest = {
        "status": "anchor_lens_quickcheck_complete",
        "phase": PHASE,
        "input_phase": INPUT_PHASE,
        "started_utc": "see console/log",
        "finished_utc": utc_now(),
        "elapsed_seconds": elapsed,
        "purpose": "Report-only strict O3 anchored-region lens quickcheck over existing strict-320 hit rows.",
        "hit_manifest": repo_relative(HIT_MANIFEST_CSV),
        "pairwise": repo_relative(PAIRWISE_CSV),
        "retained_candidates": repo_relative(RETAINED_CANDIDATES_CSV),
        "input_file_count": len(input_files),
        "input_hit_rows_read": total_rows_read,
        "expected_hit_rows": expected_hit_rows,
        "lenses": [asdict(lens) for lens in DEFAULT_LENSES],
        "weight_formula": "max(0, phrase_token_length - 2 * total_phrase_hd)",
        "selection_method": (
            "deduplicate by candidate/lens/start/end; keep best phrase per span; "
            "select max-weight non-overlapping intervals with deterministic tie-breaks"
        ),
        "min_gap": MIN_GAP,
        "margin_thresholds": list(MARGIN_THRESHOLDS),
        "candidate_summary_rows": len(candidate_summary_rows),
        "candidate_anchor_region_rows": len(region_rows),
        "candidate_anchor_pairwise_rows": len(pairwise_rows),
        "anchor_lens_margin_threshold_rows": len(threshold_rows),
        "input_files": input_files,
        "production_scoring_change": False,
        "production_ranking_change": False,
        "score_bearing_use_approved": False,
        "report_only": True,
    }
    (OUTPUT_DIR / "anchor_lens_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"[{PHASE}] status=anchor_lens_quickcheck_complete")
    print(f"[{PHASE}] output_dir={repo_relative(OUTPUT_DIR)}")
    print(f"[{PHASE}] elapsed_seconds={elapsed:.1f}")
    print(f"[{PHASE}] candidate_summary_rows={len(candidate_summary_rows)}")
    print(f"[{PHASE}] selected_region_rows={len(region_rows)}")
    print(f"[{PHASE}] pairwise_rows={len(pairwise_rows)}")
    return manifest


def main() -> int:
    build_quickcheck()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
