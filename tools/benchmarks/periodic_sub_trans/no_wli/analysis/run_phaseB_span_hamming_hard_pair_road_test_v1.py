from __future__ import annotations

import csv
import gzip
import json
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
    run_phaseB_span_hamming_real_candidate_road_test_v1 as base,
)


RUN_LABEL = "phaseB_span_hamming_hard_pair_road_test_v1"
OUTPUT_DIR = REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis" / RUN_LABEL
REVIEW_PACK_DIR = (
    REPO_ROOT
    / "planning/projects/no_wli/40_review_summaries"
    / "phaseB_span_hamming_hard_pair_road_test_v1_review_pack_2026-05-13"
)
REVIEW_PACK_ZIP = REVIEW_PACK_DIR.with_suffix(".zip")

HISTORICAL_PACK = (
    REPO_ROOT
    / "planning/projects/no_wli/40_review_summaries"
    / "no_wli_historical_partial_text_and_scorer_review_pack_2026-05-02"
)
PAIR_ROWS_PATH = HISTORICAL_PACK / "historical_pairwise_rescore/historical_pairwise_rescore_pairs.csv"
UNIQUE_TEXT_ROWS_PATH = HISTORICAL_PACK / "historical_partial_texts/unique_partial_text_rows.csv"

CANDIDATE_CHUNK_MAX_TOKENS = 500
MIN_FULL_CHUNK_TOKENS = 450
PRIMARY_PANEL = "A_core_medium_local"
MAX_PAIRS = 0
MARGIN_SWEEP_THRESHOLDS = (0.0, 0.025, 0.05, 0.075, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.75, 1.0)


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def ensure_under_repo(path: Path) -> None:
    resolved = path.resolve()
    if not resolved.is_relative_to(REPO_ROOT):
        raise ValueError(f"path escapes repo root: {resolved}")
    resolved.parent.mkdir(parents=True, exist_ok=True)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


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


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def candidate_id_for_hash(token_hash: str) -> str:
    return f"hist_text_{token_hash}"


def parse_token_sequence(text: str) -> list[int]:
    return [int(part) for part in text.split() if part.strip()]


def load_pair_rows() -> list[dict[str, str]]:
    rows = read_csv_rows(PAIR_ROWS_PATH)
    if MAX_PAIRS > 0:
        rows = rows[:MAX_PAIRS]
    return rows


def load_token_sequences(needed_hashes: set[str]) -> dict[str, list[int]]:
    found: dict[str, list[int]] = {}
    with UNIQUE_TEXT_ROWS_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            partial_hash = row["partial_text_hash"]
            if partial_hash not in needed_hashes:
                continue
            found[partial_hash] = parse_token_sequence(row["token_sequence_text"])
            if len(found) == len(needed_hashes):
                break
    return found


def label_from_truth(value: float) -> tuple[str, float]:
    if value >= 0.90:
        return "known_good", 0.95
    if value >= 0.50:
        return "likely_good", 0.70
    if value <= 0.10:
        return "known_bad", 0.90
    if value <= 0.40:
        return "likely_bad", 0.75
    return "unknown", 0.40


def build_candidates(pair_rows: list[dict[str, str]], token_sequences: Mapping[str, list[int]]) -> list[dict[str, Any]]:
    stats: dict[str, dict[str, Any]] = defaultdict(lambda: {"truth_values": [], "winner_count": 0, "challenger_count": 0, "current_score_values": []})
    for row in pair_rows:
        winner_hash = row["winner_token_hash"]
        challenger_hash = row["challenger_token_hash"]
        stats[winner_hash]["truth_values"].append(as_float(row["winner_truth_match"]))
        stats[winner_hash]["winner_count"] += 1
        stats[winner_hash]["current_score_values"].append(as_float(row["winner_current_score"]))
        stats[challenger_hash]["truth_values"].append(as_float(row["challenger_truth_match"]))
        stats[challenger_hash]["challenger_count"] += 1
        stats[challenger_hash]["current_score_values"].append(as_float(row["challenger_current_score"]))

    candidates: list[dict[str, Any]] = []
    for token_hash, tokens in sorted(token_sequences.items()):
        truth_values = [float(value) for value in stats[token_hash]["truth_values"]]
        current_values = [float(value) for value in stats[token_hash]["current_score_values"]]
        max_truth = max(truth_values) if truth_values else 0.0
        label, confidence = label_from_truth(max_truth)
        candidates.append(
            {
                "candidate_id": candidate_id_for_hash(token_hash),
                "source_run_id": "historical_pairwise_rescore",
                "source_file": rel(UNIQUE_TEXT_ROWS_PATH),
                "candidate_kind": "historical_pair_token_stream",
                "candidate_rank": "",
                "current_score": f"{statistics.fmean(current_values):.12g}" if current_values else "",
                "current_score_name": "mean_current_score_across_pair_rows",
                "truth_match_ratio": f"{max_truth:.12g}",
                "label": label,
                "label_confidence": f"{confidence:.3f}",
                "direction": "fwd",
                "token_count": len(tokens),
                "candidate_text_or_token_path": f"{rel(UNIQUE_TEXT_ROWS_PATH)}#partial_text_hash={token_hash}",
                "notes": "historical pair token stream resolved from unique_partial_text_rows.csv",
                "fixture_seed": "",
                "search_seed": "",
                "token_hash": token_hash,
                "pair_occurrence_count": len(truth_values),
                "winner_count": stats[token_hash]["winner_count"],
                "challenger_count": stats[token_hash]["challenger_count"],
                "_tokens": tokens,
            }
        )
    return candidates


def chunk_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for candidate in candidates:
        tokens = list(candidate["_tokens"])
        for chunk_index, start in enumerate(range(0, len(tokens), CANDIDATE_CHUNK_MAX_TOKENS)):
            chunk_tokens = tokens[start : start + CANDIDATE_CHUNK_MAX_TOKENS]
            if len(chunk_tokens) < MIN_FULL_CHUNK_TOKENS:
                continue
            chunks.append(
                {
                    "candidate_chunk_id": f"{candidate['candidate_id']}|chunk{chunk_index:03d}|{start}_{start + len(chunk_tokens)}",
                    "candidate_id": candidate["candidate_id"],
                    "chunk_index": chunk_index,
                    "chunk_start": start,
                    "chunk_end": start + len(chunk_tokens),
                    "token_count": len(chunk_tokens),
                    "chunk_status": "full_chunk",
                    "direction": "fwd",
                    "_tokens": chunk_tokens,
                }
            )
    return chunks


def panel_score_map(candidate_level_rows: list[dict[str, Any]]) -> dict[tuple[str, str], float]:
    return {
        (row["candidate_id"], row["panel_id"]): as_float(row["mean_chunk_score"])
        for row in candidate_level_rows
    }


def score_string(candidate_id: str, scores: Mapping[tuple[str, str], float]) -> str:
    panels = ("A_core_medium_local", "B_longer_span", "D_strict_precision")
    return ";".join(f"{panel}={scores.get((candidate_id, panel), 0.0):.12g}" for panel in panels)


def build_hard_pair_manifest(pair_rows: list[dict[str, str]], resolved_hashes: set[str]) -> list[dict[str, Any]]:
    manifest: list[dict[str, Any]] = []
    for row in pair_rows:
        winner_hash = row["winner_token_hash"]
        challenger_hash = row["challenger_token_hash"]
        resolved = winner_hash in resolved_hashes and challenger_hash in resolved_hashes
        current_prefers_winner = row["current_score_correct"] == "1"
        manifest.append(
            {
                "pair_id": row["pair_id"],
                "candidate_a_id": candidate_id_for_hash(winner_hash),
                "candidate_b_id": candidate_id_for_hash(challenger_hash),
                "current_scorer_preferred": candidate_id_for_hash(winner_hash if current_prefers_winner else challenger_hash),
                "known_better_candidate": candidate_id_for_hash(winner_hash),
                "candidate_a_token_path": f"{rel(UNIQUE_TEXT_ROWS_PATH)}#partial_text_hash={winner_hash}" if winner_hash in resolved_hashes else "",
                "candidate_b_token_path": f"{rel(UNIQUE_TEXT_ROWS_PATH)}#partial_text_hash={challenger_hash}" if challenger_hash in resolved_hashes else "",
                "current_score_a": row["winner_current_score"],
                "current_score_b": row["challenger_current_score"],
                "truth_or_label_metadata": f"winner_truth={row['winner_truth_match']};challenger_truth={row['challenger_truth_match']};truth_gap={row['truth_gap']}",
                "source_artifact_path": row["artifact_path"],
                "token_streams_resolved": "true" if resolved else "false",
            }
        )
    return manifest


def build_pairwise_summary(
    pair_rows: list[dict[str, str]],
    scores: Mapping[tuple[str, str], float],
    resolved_hashes: set[str],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in pair_rows:
        winner_hash = row["winner_token_hash"]
        challenger_hash = row["challenger_token_hash"]
        if winner_hash not in resolved_hashes or challenger_hash not in resolved_hashes:
            continue
        winner_id = candidate_id_for_hash(winner_hash)
        challenger_id = candidate_id_for_hash(challenger_hash)
        winner_score = scores.get((winner_id, PRIMARY_PANEL), 0.0)
        challenger_score = scores.get((challenger_id, PRIMARY_PANEL), 0.0)
        if winner_score > challenger_score:
            span_preferred = winner_id
        elif challenger_score > winner_score:
            span_preferred = challenger_id
        else:
            span_preferred = "tie"
        current_correct = row["current_score_correct"] == "1"
        span_prefers_known_better = span_preferred == winner_id
        out.append(
            {
                "pair_id": row["pair_id"],
                "candidate_a_id": winner_id,
                "candidate_b_id": challenger_id,
                "current_scorer_correct": "true" if current_correct else "false",
                "span_hamming_panel_preferred": span_preferred,
                "span_hamming_rescues_current_misrank": "true" if (not current_correct and span_prefers_known_better) else "false",
                "span_hamming_breaks_current_correct": "true" if (current_correct and span_preferred not in {winner_id, "tie"}) else "false",
                "panel_scores_a": score_string(winner_id, scores),
                "panel_scores_b": score_string(challenger_id, scores),
                "current_scorer_preferred": winner_id if current_correct else challenger_id,
                "known_better_candidate": winner_id,
                "winner_truth_match": row["winner_truth_match"],
                "challenger_truth_match": row["challenger_truth_match"],
                "truth_gap": row["truth_gap"],
                "winner_current_score": row["winner_current_score"],
                "challenger_current_score": row["challenger_current_score"],
                "current_score_margin": row["current_score_margin"],
            }
        )
    return out


def build_pairwise_rollup(pair_rows: list[dict[str, Any]], scores: Mapping[tuple[str, str], float]) -> list[dict[str, Any]]:
    rollup: list[dict[str, Any]] = []
    for panel in ("A_core_medium_local", "B_longer_span", "D_strict_precision"):
        total = 0
        current_correct = 0
        current_misrank = 0
        span_prefers_truth = 0
        rescues = 0
        breaks = 0
        score_gap_when_rescued: list[float] = []
        for row in pair_rows:
            winner_id = row["candidate_a_id"]
            challenger_id = row["candidate_b_id"]
            winner_score = scores.get((winner_id, panel), 0.0)
            challenger_score = scores.get((challenger_id, panel), 0.0)
            if winner_score == challenger_score:
                span_prefers = "tie"
            else:
                span_prefers = winner_id if winner_score > challenger_score else challenger_id
            is_current_correct = row["current_scorer_correct"] == "true"
            total += 1
            current_correct += 1 if is_current_correct else 0
            current_misrank += 0 if is_current_correct else 1
            span_prefers_truth += 1 if span_prefers == winner_id else 0
            if (not is_current_correct) and span_prefers == winner_id:
                rescues += 1
                score_gap_when_rescued.append(winner_score - challenger_score)
            if is_current_correct and span_prefers == challenger_id:
                breaks += 1
        rollup.append(
            {
                "panel_id": panel,
                "pair_count": total,
                "current_scorer_correct": current_correct,
                "current_scorer_misranked": current_misrank,
                "span_hamming_prefers_truth_better": span_prefers_truth,
                "span_hamming_truth_preference_rate": f"{span_prefers_truth / total:.12g}" if total else "0",
                "span_hamming_rescues_current_misrank": rescues,
                "span_hamming_breaks_current_correct": breaks,
                "net_rescue_minus_break": rescues - breaks,
                "mean_rescue_panel_gap": f"{statistics.fmean(score_gap_when_rescued):.12g}" if score_gap_when_rescued else "",
            }
        )
    return rollup


def build_margin_policy_sweep(pair_rows: list[dict[str, Any]], scores: Mapping[tuple[str, str], float]) -> list[dict[str, Any]]:
    sweep: list[dict[str, Any]] = []
    for panel in ("A_core_medium_local", "B_longer_span", "D_strict_precision"):
        for threshold in MARGIN_SWEEP_THRESHOLDS:
            overrides = 0
            rescues = 0
            breaks = 0
            truth_preferences = 0
            abstentions = 0
            for row in pair_rows:
                winner_id = row["candidate_a_id"]
                challenger_id = row["candidate_b_id"]
                winner_score = scores.get((winner_id, panel), 0.0)
                challenger_score = scores.get((challenger_id, panel), 0.0)
                gap = winner_score - challenger_score
                if gap > 0.0:
                    truth_preferences += 1
                if gap == 0.0 or abs(gap) < threshold:
                    abstentions += 1
                    continue
                overrides += 1
                is_current_correct = row["current_scorer_correct"] == "true"
                span_prefers_truth = gap > 0.0
                if (not is_current_correct) and span_prefers_truth:
                    rescues += 1
                if is_current_correct and not span_prefers_truth:
                    breaks += 1
            sweep.append(
                {
                    "panel_id": panel,
                    "margin_threshold_abs": f"{threshold:.12g}",
                    "pair_count": len(pair_rows),
                    "abstentions": abstentions,
                    "override_count": overrides,
                    "truth_preference_count": truth_preferences,
                    "truth_preference_rate": f"{truth_preferences / len(pair_rows):.12g}" if pair_rows else "0",
                    "rescues_current_misrank": rescues,
                    "breaks_current_correct": breaks,
                    "net_rescue_minus_break": rescues - breaks,
                    "rescue_per_override": f"{rescues / overrides:.12g}" if overrides else "0",
                }
            )
    return sweep


def write_readout(
    *,
    pair_rows: list[dict[str, str]],
    resolved_hashes: set[str],
    candidates: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
    feature_rows: list[dict[str, Any]],
    pairwise_rows: list[dict[str, Any]],
    rollup_rows: list[dict[str, Any]],
    margin_sweep_rows: list[dict[str, Any]],
    elapsed_s: float,
) -> None:
    current_misrank = sum(1 for row in pair_rows if row["current_score_correct"] == "0")
    lines = [
        "# PhaseB Span-Hamming Hard-Pair Road Test v1",
        "",
        f"Created UTC: {datetime.now(timezone.utc).isoformat()}",
        f"Elapsed seconds: {elapsed_s:.1f}",
        "",
        "## Scope",
        "",
        f"- Historical pair rows: {len(pair_rows)}",
        f"- Current-scorer misrank rows: {current_misrank}",
        f"- Resolved token hashes: {len(resolved_hashes)}",
        f"- Candidates scored once: {len(candidates)}",
        f"- Candidate chunks scored: {len(chunks)}",
        f"- Feature comparison rows: {len(feature_rows)}",
        f"- Active calibration: {rel(base.ACTIVE_CALIBRATION_DIR)}",
        "- No production scorer weights were changed.",
        "",
        "## Pairwise Rescue/Break Rollup",
        "",
    ]
    for row in rollup_rows:
        lines.append(
            f"- {row['panel_id']}: truth preference {row['span_hamming_prefers_truth_better']}/{row['pair_count']} "
            f"({row['span_hamming_truth_preference_rate']}), rescues {row['span_hamming_rescues_current_misrank']}, "
            f"breaks {row['span_hamming_breaks_current_correct']}, net {row['net_rescue_minus_break']}"
        )
    lines.extend(["", "## Margin Sweep", ""])
    for panel in ("A_core_medium_local", "B_longer_span", "D_strict_precision"):
        rows = [row for row in margin_sweep_rows if row["panel_id"] == panel]
        best_net = max(rows, key=lambda row: int(row["net_rescue_minus_break"]))
        lines.append(
            f"- {panel}: best net in sweep {best_net['net_rescue_minus_break']} at margin {best_net['margin_threshold_abs']} "
            f"(rescues {best_net['rescues_current_misrank']}, breaks {best_net['breaks_current_correct']}, overrides {best_net['override_count']})"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- This is the hard-pair test over token-resolved historical pair rows.",
            "- Candidate A is the truth-better candidate from the historical pair row.",
            "- Candidate B is the truth-worse candidate.",
            "- Primary `span_hamming_panel_preferred` uses Panel A, lengths 5-9.",
            "- Panel B and Panel D rollups are included for comparison.",
            "- Margin-sweep rows model report-only override/abstain policies; they are not production thresholds.",
            "- This remains report-only.",
        ]
    )
    (OUTPUT_DIR / "readout.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def copy_review_pack() -> None:
    if REVIEW_PACK_DIR.exists():
        shutil.rmtree(REVIEW_PACK_DIR)
    REVIEW_PACK_DIR.mkdir(parents=True, exist_ok=True)
    for name in (
        "config.json",
        "calibration_manifest.json",
        "hard_pair_manifest.csv",
        "candidate_manifest_resolved.csv",
        "candidate_chunk_manifest.csv",
        "candidate_feature_rows.csv.gz",
        "candidate_panel_summary.csv",
        "candidate_level_summary.csv",
        "pairwise_road_test_summary.csv",
        "pairwise_rescue_break_rollup.csv",
        "pairwise_margin_policy_sweep.csv",
        "bad_candidate_separation_summary.csv",
        "top_supported_candidates.csv",
        "top_warning_candidates.csv",
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

    for path in (PAIR_ROWS_PATH, UNIQUE_TEXT_ROWS_PATH, base.ACTIVE_CALIBRATION_DIR / "damaged_vs_null_summary.csv"):
        if not path.exists():
            raise FileNotFoundError(rel(path))

    pair_rows = load_pair_rows()
    needed_hashes = {row["winner_token_hash"] for row in pair_rows} | {row["challenger_token_hash"] for row in pair_rows}
    token_sequences = load_token_sequences(needed_hashes)
    missing_hashes = sorted(needed_hashes - set(token_sequences))
    if missing_hashes:
        raise RuntimeError(f"missing {len(missing_hashes)} token sequences, first={missing_hashes[:5]}")

    base.RUN_LABEL = RUN_LABEL
    base.RUN_MODE = RUN_LABEL
    config = {
        "run_label": RUN_LABEL,
        "report_only": True,
        "pair_rows_path": rel(PAIR_ROWS_PATH),
        "unique_text_rows_path": rel(UNIQUE_TEXT_ROWS_PATH),
        "max_pairs": MAX_PAIRS,
        "pair_rows_loaded": len(pair_rows),
        "unique_token_hashes_scored": len(token_sequences),
        "candidate_chunk_max_tokens": CANDIDATE_CHUNK_MAX_TOKENS,
        "min_full_chunk_tokens": MIN_FULL_CHUNK_TOKENS,
        "primary_panel": PRIMARY_PANEL,
        "margin_sweep_thresholds": MARGIN_SWEEP_THRESHOLDS,
        "active_calibration": rel(base.ACTIVE_CALIBRATION_DIR),
        "ladder_profile": base.LADDER_PROFILE,
        "span_lengths": list(base.SPAN_LENGTHS),
        "max_hd_by_length": base.MAX_HD_BY_LENGTH,
        "dictionary_cuts": [spec["dictionary_cut"] for spec in base.ladder.DICTIONARY_SPECS],
        "scorer_policy": "report-only; no production weights/defaults/ranking changes",
    }
    write_json(OUTPUT_DIR / "config.json", config)
    write_json(
        OUTPUT_DIR / "calibration_manifest.json",
        {
            "active_calibration": rel(base.ACTIVE_CALIBRATION_DIR),
            "calibration_damage_model": base.CALIBRATION_DAMAGE_MODEL,
            "calibration_damage_level": base.CALIBRATION_DAMAGE_LEVEL,
            "stage4_status": "not included; Stage 4 still running/review pending",
            "calibration_files_present": {
                name: (base.ACTIVE_CALIBRATION_DIR / name).exists()
                for name in (
                    "final_feature_summary.csv",
                    "damaged_vs_null_by_view.csv.gz",
                    "feature_histograms.csv.gz",
                    "feature_quantiles.csv.gz",
                    "dictionary_hash_manifest.csv",
                    "damaged_vs_null_summary.csv",
                )
            },
        },
    )

    candidates = build_candidates(pair_rows, token_sequences)
    chunks = chunk_candidates(candidates)
    candidates_by_id = {candidate["candidate_id"]: candidate for candidate in candidates}
    hard_pair_manifest = build_hard_pair_manifest(pair_rows, set(token_sequences))

    candidate_fields = [
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
        "pair_occurrence_count",
        "winner_count",
        "challenger_count",
    ]
    write_csv(OUTPUT_DIR / "candidate_manifest_resolved.csv", candidates, candidate_fields)
    write_csv(
        OUTPUT_DIR / "candidate_chunk_manifest.csv",
        chunks,
        ["candidate_chunk_id", "candidate_id", "chunk_index", "chunk_start", "chunk_end", "token_count", "chunk_status", "direction"],
    )
    hard_pair_fields = [
        "pair_id",
        "candidate_a_id",
        "candidate_b_id",
        "current_scorer_preferred",
        "known_better_candidate",
        "candidate_a_token_path",
        "candidate_b_token_path",
        "current_score_a",
        "current_score_b",
        "truth_or_label_metadata",
        "source_artifact_path",
        "token_streams_resolved",
    ]
    write_csv(OUTPUT_DIR / "hard_pair_manifest.csv", hard_pair_manifest, hard_pair_fields)

    calibration_index = base.load_calibration_rows()
    feature_rows, timing_rows = base.score_candidate_chunks(chunks, candidates_by_id, calibration_index)
    feature_fields = [
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
    write_csv_gz(OUTPUT_DIR / "candidate_feature_rows.csv.gz", feature_rows, feature_fields)
    write_csv(OUTPUT_DIR / "score_timing_rows.csv", timing_rows, ["candidate_chunk_id", "dictionary_cut", "elapsed_ms", "raw_feature_rows"])

    panel_rows = base.summarize_panels(feature_rows)
    panel_fields = [
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
    write_csv(OUTPUT_DIR / "candidate_panel_summary.csv", panel_rows, panel_fields)

    candidate_level_rows = base.summarize_candidates(panel_rows)
    candidate_level_fields = [
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
    write_csv(OUTPUT_DIR / "candidate_level_summary.csv", candidate_level_rows, candidate_level_fields)

    scores = panel_score_map(candidate_level_rows)
    pairwise_rows = build_pairwise_summary(pair_rows, scores, set(token_sequences))
    pairwise_fields = [
        "pair_id",
        "candidate_a_id",
        "candidate_b_id",
        "current_scorer_correct",
        "span_hamming_panel_preferred",
        "span_hamming_rescues_current_misrank",
        "span_hamming_breaks_current_correct",
        "panel_scores_a",
        "panel_scores_b",
        "current_scorer_preferred",
        "known_better_candidate",
        "winner_truth_match",
        "challenger_truth_match",
        "truth_gap",
        "winner_current_score",
        "challenger_current_score",
        "current_score_margin",
    ]
    write_csv(OUTPUT_DIR / "pairwise_road_test_summary.csv", pairwise_rows, pairwise_fields)

    rollup_rows = build_pairwise_rollup(pairwise_rows, scores)
    rollup_fields = [
        "panel_id",
        "pair_count",
        "current_scorer_correct",
        "current_scorer_misranked",
        "span_hamming_prefers_truth_better",
        "span_hamming_truth_preference_rate",
        "span_hamming_rescues_current_misrank",
        "span_hamming_breaks_current_correct",
        "net_rescue_minus_break",
        "mean_rescue_panel_gap",
    ]
    write_csv(OUTPUT_DIR / "pairwise_rescue_break_rollup.csv", rollup_rows, rollup_fields)

    margin_sweep_rows = build_margin_policy_sweep(pairwise_rows, scores)
    margin_sweep_fields = [
        "panel_id",
        "margin_threshold_abs",
        "pair_count",
        "abstentions",
        "override_count",
        "truth_preference_count",
        "truth_preference_rate",
        "rescues_current_misrank",
        "breaks_current_correct",
        "net_rescue_minus_break",
        "rescue_per_override",
    ]
    write_csv(OUTPUT_DIR / "pairwise_margin_policy_sweep.csv", margin_sweep_rows, margin_sweep_fields)

    separation_rows = base.build_bad_candidate_separation(candidate_level_rows)
    write_csv(
        OUTPUT_DIR / "bad_candidate_separation_summary.csv",
        separation_rows,
        ["label", "panel_id", "candidate_count", "mean_score", "median_score", "p10_score", "p90_score", "fraction_above_threshold"],
    )
    write_csv(OUTPUT_DIR / "top_supported_candidates.csv", base.top_rows(candidate_level_rows, warnings_only=False), candidate_level_fields)
    write_csv(OUTPUT_DIR / "top_warning_candidates.csv", base.top_rows(candidate_level_rows, warnings_only=True), candidate_level_fields)

    elapsed_s = time.perf_counter() - start
    write_readout(
        pair_rows=pair_rows,
        resolved_hashes=set(token_sequences),
        candidates=candidates,
        chunks=chunks,
        feature_rows=feature_rows,
        pairwise_rows=pairwise_rows,
        rollup_rows=rollup_rows,
        margin_sweep_rows=margin_sweep_rows,
        elapsed_s=elapsed_s,
    )
    copy_review_pack()

    print(f"[{RUN_LABEL}] complete pairs={len(pair_rows)} candidates={len(candidates)} chunks={len(chunks)} feature_rows={len(feature_rows)} elapsed={elapsed_s:.1f}s")
    print(f"[{RUN_LABEL}] output_dir={rel(OUTPUT_DIR)}")
    print(f"[{RUN_LABEL}] review_pack={rel(REVIEW_PACK_ZIP)}")


if __name__ == "__main__":
    main()
