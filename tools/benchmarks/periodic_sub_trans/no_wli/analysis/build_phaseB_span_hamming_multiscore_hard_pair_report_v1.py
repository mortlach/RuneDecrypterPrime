from __future__ import annotations

import csv
import gzip
import json
import math
import shutil
import statistics
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, NamedTuple


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


RUN_LABEL = "phaseB_span_hamming_multiscore_hard_pair_report_v1"
ANALYSIS_ROOT = REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis"
OUTPUT_DIR = ANALYSIS_ROOT / RUN_LABEL
HARD_PAIR_DIR = ANALYSIS_ROOT / "phaseB_span_hamming_hard_pair_road_test_v1"
STAGE12_DIR = ANALYSIS_ROOT / "stage1_stage2_fwd_full_len2_14_combined_v1"
STAGE3_DIR = ANALYSIS_ROOT / "stage3_fwd_full_len5_14_pcb"
STAGE4_DIR = ANALYSIS_ROOT / "stage4_fwd_full_len8_14_pcb"
REVIEW_PACK_DIR = (
    REPO_ROOT
    / "planning/projects/no_wli/40_review_summaries"
    / "phaseB_span_hamming_multiscore_hard_pair_report_v1_review_pack_2026-05-14"
)
REVIEW_PACK_ZIP = REVIEW_PACK_DIR.with_suffix(".zip")

LOCAL_NULL_MODELS = ("uniform_random", "global_frequency_random", "within_chunk_shuffle")
BLOCK_NULL_MODELS = ("block_shuffle_10", "block_shuffle_25", "block_shuffle_50")
MAIN_FEATURE_NAMES = ("exact_count_norm", "hd_le_count_norm")
DIAGNOSTIC_FEATURE_NAMES = ("exact_count", "hd_le_count", "matched_window_count", "no_match_count", "window_count")
DICTIONARY_NORMAL = "phaseA14_normal_selected"
DICTIONARY_STRICT = "phaseA14_strict_selected"
PRIMARY_REFERENCE = "merged_word_local_substitution_0.20"
MARGIN_THRESHOLDS = (0.0, 0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.75, 1.00, 1.50, 2.00)
UNCERTAINTY_THRESHOLDS = (0.01, 0.025, 0.05, 0.10)
CONSERVATIVE_THRESHOLDS = (0.25, 0.50, 0.75, 1.00, 1.50)
TOP_N = 50

REQUIRED_SINGLE_REFERENCES = (
    ("word_local_substitution", "0.20"),
    ("word_local_substitution", "0.40"),
    ("independent_substitution", "0.40"),
    ("frequency_matched_global", "0.40"),
    ("frequency_matched_book", "0.40"),
    ("burst_substitution", "0.40"),
    ("lane_period_substitution", "0.40"),
)
POOLED_REFERENCES = (
    ("pooled_all_damage_models_0.40", ("burst_substitution", "frequency_matched_book", "frequency_matched_global", "independent_substitution", "lane_period_substitution", "word_local_substitution"), ("0.40",)),
    ("pooled_all_damage_models_0.20_0.60", ("burst_substitution", "frequency_matched_book", "frequency_matched_global", "independent_substitution", "lane_period_substitution", "word_local_substitution"), ("0.20", "0.30", "0.40", "0.50", "0.60")),
    ("pooled_word_local_substitution_0.20_0.60", ("word_local_substitution",), ("0.20", "0.30", "0.40", "0.50", "0.60")),
)


class FeatureKey(NamedTuple):
    direction: str
    score_region: str
    start_shift: str
    dictionary_cut: str
    span_length: int
    hd: int
    feature_name: str


class CalKey(NamedTuple):
    dictionary_cut: str
    span_length: int
    hd: int
    feature_name: str
    damage_model: str
    damage_level: str
    null_model: str


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


def mean(values: Iterable[float]) -> float:
    seq = list(values)
    return statistics.fmean(seq) if seq else 0.0


def median(values: Iterable[float]) -> float:
    seq = sorted(values)
    return statistics.median(seq) if seq else 0.0


def percentile(values: Iterable[float], q: float) -> float:
    seq = sorted(values)
    if not seq:
        return 0.0
    if len(seq) == 1:
        return seq[0]
    pos = (len(seq) - 1) * q / 100.0
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return seq[lo]
    return seq[lo] + (seq[hi] - seq[lo]) * (pos - lo)


def stdev(values: Iterable[float]) -> float:
    seq = list(values)
    return statistics.stdev(seq) if len(seq) >= 2 else 0.0


def cohen_d(a_values: list[float], b_values: list[float]) -> float:
    if not a_values or not b_values:
        return 0.0
    pooled = math.sqrt(max(0.0, (stdev(a_values) ** 2 + stdev(b_values) ** 2) / 2.0))
    if pooled <= 1e-12:
        return 0.0
    return (statistics.fmean(a_values) - statistics.fmean(b_values)) / pooled


def pearson(xs: list[float], ys: list[float]) -> float:
    pairs = [(x, y) for x, y in zip(xs, ys) if math.isfinite(x) and math.isfinite(y)]
    if len(pairs) < 2:
        return 0.0
    xvals = [p[0] for p in pairs]
    yvals = [p[1] for p in pairs]
    xm = statistics.fmean(xvals)
    ym = statistics.fmean(yvals)
    xden = math.sqrt(sum((x - xm) ** 2 for x in xvals))
    yden = math.sqrt(sum((y - ym) ** 2 for y in yvals))
    if xden <= 1e-12 or yden <= 1e-12:
        return 0.0
    return sum((x - xm) * (y - ym) for x, y in pairs) / (xden * yden)


def wilson_ci(successes: int, total: int) -> tuple[float, float]:
    if total <= 0:
        return 0.0, 0.0
    z = 1.959963984540054
    p = successes / total
    denom = 1.0 + z * z / total
    centre = p + z * z / (2.0 * total)
    spread = z * math.sqrt((p * (1.0 - p) + z * z / (4.0 * total)) / total)
    return (centre - spread) / denom, (centre + spread) / denom


def signed_effect(value: float, cal: Mapping[str, str]) -> float:
    damaged_mean = as_float(cal.get("damaged_mean"))
    damaged_stddev = as_float(cal.get("damaged_stddev"))
    null_mean = as_float(cal.get("null_mean"))
    null_stddev = as_float(cal.get("null_stddev"))
    diff = damaged_mean - null_mean
    pooled = math.sqrt(max(0.0, (damaged_stddev * damaged_stddev + null_stddev * null_stddev) / 2.0))
    if pooled <= 1e-12:
        return 0.0
    sign = 1.0 if diff >= 0.0 else -1.0
    return ((value - null_mean) * sign) / pooled


def feature_key_from_row(row: Mapping[str, str]) -> FeatureKey:
    return FeatureKey(
        row.get("direction", ""),
        row.get("score_region", ""),
        str(row.get("start_shift", "")),
        row.get("dictionary_cut", ""),
        int(row.get("span_length", 0)),
        int(row.get("hd", 0)),
        row.get("feature_name", ""),
    )


def cal_key_from_row(row: Mapping[str, str]) -> CalKey:
    return CalKey(
        row["dictionary_cut"],
        int(row["span_length"]),
        int(row["hd"]),
        row["feature_name"],
        row["damage_model"],
        row["damage_level"],
        row["null_model"],
    )


def parse_panel_scores(text: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for part in str(text).split(";"):
        if "=" not in part:
            continue
        name, value = part.split("=", 1)
        out[name] = as_float(value)
    return out


def load_calibration_stage(stage_name: str, path: Path) -> dict[CalKey, dict[str, str]]:
    out: dict[CalKey, dict[str, str]] = {}
    file_path = path / "damaged_vs_null_summary.csv"
    if not file_path.exists():
        return out
    for row in read_csv_rows(file_path):
        row = dict(row)
        row["stage"] = stage_name
        out[cal_key_from_row(row)] = row
    return out


def choose_calibration(cal3: dict[CalKey, dict[str, str]], cal4: dict[CalKey, dict[str, str]], key: CalKey) -> dict[str, str] | None:
    if key.span_length >= 8 and key in cal4:
        return cal4[key]
    return cal3.get(key) or cal4.get(key)


def reference_specs() -> list[dict[str, Any]]:
    specs = [
        {
            "reference_id": f"merged_{model}_{level}",
            "damage_models": (model,),
            "damage_levels": (level,),
            "pooled": False,
        }
        for model, level in REQUIRED_SINGLE_REFERENCES
    ]
    for ref_id, models, levels in POOLED_REFERENCES:
        specs.append({"reference_id": f"merged_{ref_id}", "damage_models": models, "damage_levels": levels, "pooled": True})
    return specs


def calibrate_value(
    *,
    value: float,
    feature: FeatureKey,
    ref: Mapping[str, Any],
    null_models: tuple[str, ...],
    cal3: dict[CalKey, dict[str, str]],
    cal4: dict[CalKey, dict[str, str]],
) -> tuple[float, list[dict[str, str]]]:
    scores: list[float] = []
    used: list[dict[str, str]] = []
    for model in ref["damage_models"]:
        for level in ref["damage_levels"]:
            for null_model in null_models:
                key = CalKey(feature.dictionary_cut, feature.span_length, feature.hd, feature.feature_name, model, level, null_model)
                cal = choose_calibration(cal3, cal4, key)
                if cal is None:
                    continue
                scores.append(signed_effect(value, cal))
                used.append(cal)
    return mean(scores), used


def load_candidate_inputs() -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, dict[str, str]], dict[str, dict[str, float]], dict[FeatureKey, dict[str, float]], dict[FeatureKey, set[str]], Counter]:
    candidate_manifest = read_csv_rows(HARD_PAIR_DIR / "candidate_manifest_resolved.csv")
    pair_rows = read_csv_rows(HARD_PAIR_DIR / "pairwise_road_test_summary.csv")
    candidate_meta = {row["candidate_id"]: row for row in candidate_manifest}
    panel_scores: dict[str, dict[str, float]] = defaultdict(dict)
    for row in read_csv_rows(HARD_PAIR_DIR / "candidate_level_summary.csv"):
        panel_scores[row["candidate_id"]][row["panel_id"]] = as_float(row.get("mean_chunk_score"))

    raw_sums: dict[FeatureKey, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    raw_counts: dict[FeatureKey, Counter] = defaultdict(Counter)
    seen_chunk_features: set[tuple[str, str, FeatureKey]] = set()
    feature_nulls: dict[FeatureKey, set[str]] = defaultdict(set)
    shape_counts: Counter = Counter()
    feature_path = HARD_PAIR_DIR / "candidate_feature_rows.csv.gz"
    with gzip.open(feature_path, "rt", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            feature = feature_key_from_row(row)
            feature_nulls[feature].add(row.get("comparison_null_model", ""))
            shape_counts[(feature.direction, feature.score_region, feature.start_shift)] += 1
            dedupe_key = (row["candidate_id"], row["candidate_chunk_id"], feature)
            if dedupe_key in seen_chunk_features:
                continue
            seen_chunk_features.add(dedupe_key)
            raw_sums[feature][row["candidate_id"]] += as_float(row.get("candidate_value"))
            raw_counts[feature][row["candidate_id"]] += 1

    candidate_values: dict[FeatureKey, dict[str, float]] = {}
    for feature, sums_by_candidate in raw_sums.items():
        candidate_values[feature] = {
            candidate_id: total / max(1, raw_counts[feature][candidate_id])
            for candidate_id, total in sums_by_candidate.items()
        }
    return candidate_manifest, pair_rows, candidate_meta, panel_scores, candidate_values, feature_nulls, shape_counts


def build_pair_model(pair_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    pairs: list[dict[str, Any]] = []
    for row in pair_rows:
        a_id = row["candidate_a_id"]
        b_id = row["candidate_b_id"]
        current_correct = str(row.get("current_scorer_correct", "")).lower() == "true"
        pairs.append(
            {
                "pair_id": row["pair_id"],
                "truth_better": a_id,
                "truth_worse": b_id,
                "current_scorer_correct": current_correct,
                "current_scorer_preferred": row.get("current_scorer_preferred", ""),
                "current_score_margin": as_float(row.get("current_score_margin")),
                "current_score_a": as_float(row.get("winner_current_score")),
                "current_score_b": as_float(row.get("challenger_current_score")),
                "winner_truth_match": as_float(row.get("winner_truth_match")),
                "challenger_truth_match": as_float(row.get("challenger_truth_match")),
                "source_family": row.get("source_family", ""),
            }
        )
    return pairs


def evaluate_pair_scores(pairs: list[dict[str, Any]], scores: Mapping[str, float], *, threshold: float = 0.0, keep_current_outside_margin: float | None = None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    gaps: list[float] = []
    prefer_truth = 0
    rescues = 0
    breaks = 0
    current_correct_count = 0
    current_wrong_count = 0
    details: list[dict[str, Any]] = []
    for pair in pairs:
        a_score = scores.get(pair["truth_better"], 0.0)
        b_score = scores.get(pair["truth_worse"], 0.0)
        gap = a_score - b_score
        gaps.append(gap)
        current_correct = bool(pair["current_scorer_correct"])
        current_correct_count += 1 if current_correct else 0
        current_wrong_count += 0 if current_correct else 1
        applies = True
        if keep_current_outside_margin is not None and abs(pair["current_score_margin"]) >= keep_current_outside_margin:
            applies = False
        if abs(gap) <= threshold:
            applies = False
        if applies:
            prefers_truth = gap > 0.0
            prefer_truth += 1 if prefers_truth else 0
            rescues += 1 if (prefers_truth and not current_correct) else 0
            breaks += 1 if ((not prefers_truth) and current_correct) else 0
            preferred = pair["truth_better"] if prefers_truth else pair["truth_worse"]
        else:
            prefers_truth = False
            preferred = "tie_or_keep_current"
        details.append(
            {
                "pair_id": pair["pair_id"],
                "truth_better_candidate_id": pair["truth_better"],
                "truth_worse_candidate_id": pair["truth_worse"],
                "truth_better_score": f"{a_score:.12g}",
                "truth_worse_score": f"{b_score:.12g}",
                "score_gap": f"{gap:.12g}",
                "score_preferred": preferred,
                "score_prefers_truth_better": "true" if applies and gap > 0.0 else "false",
                "score_applies": "true" if applies else "false",
                "current_scorer_correct": "true" if current_correct else "false",
                "current_score_margin": f"{pair['current_score_margin']:.12g}",
                "rescues_current_misrank": "true" if applies and gap > 0.0 and not current_correct else "false",
                "breaks_current_correct": "true" if applies and gap < 0.0 and current_correct else "false",
            }
        )
    total = len(pairs)
    ci_low, ci_high = wilson_ci(prefer_truth, total)
    return (
        {
            "n_pairs": total,
            "truth_better_preference_count": prefer_truth,
            "truth_better_preference_rate": prefer_truth / total if total else 0.0,
            "truth_preference_95ci_low": ci_low,
            "truth_preference_95ci_high": ci_high,
            "rescues": rescues,
            "breaks": breaks,
            "net_rescues": rescues - breaks,
            "current_scorer_correct_count": current_correct_count,
            "current_scorer_misrank_count": current_wrong_count,
            "mean_gap": mean(gaps),
            "median_gap": median(gaps),
            "gap_q05": percentile(gaps, 5),
            "gap_q25": percentile(gaps, 25),
            "gap_q75": percentile(gaps, 75),
            "gap_q95": percentile(gaps, 95),
        },
        details,
    )


def row_status(pref_rate: float, rescues: int, breaks: int, local_effect: float, block_effect: float, n_samples: float) -> str:
    if n_samples <= 0:
        return "needs_more_data"
    if pref_rate >= 0.68 and rescues >= breaks and local_effect > 0.5:
        return "core_candidate"
    if pref_rate >= 0.60 and rescues >= breaks and local_effect > 0.25:
        return "supporting_candidate"
    if pref_rate >= 0.56 and breaks <= rescues * 2 and local_effect > 0.0:
        return "precision_candidate"
    if breaks > rescues and breaks >= 20:
        return "risky_breaks_too_many"
    if pref_rate < 0.50:
        return "weak"
    if block_effect < -1.0:
        return "diagnostic_only"
    return "weak"


def build_row_efficacy(
    *,
    candidate_values: Mapping[FeatureKey, Mapping[str, float]],
    refs: list[dict[str, Any]],
    cal3: dict[CalKey, dict[str, str]],
    cal4: dict[CalKey, dict[str, str]],
    candidate_meta: Mapping[str, Mapping[str, str]],
    pairs: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, dict[FeatureKey, dict[str, float]]], dict[str, dict[FeatureKey, dict[str, Any]]]]:
    row_scores: dict[str, dict[FeatureKey, dict[str, float]]] = defaultdict(dict)
    row_cal_meta: dict[str, dict[FeatureKey, dict[str, Any]]] = defaultdict(dict)
    out: list[dict[str, Any]] = []

    for ref in refs:
        ref_id = str(ref["reference_id"])
        for feature, values_by_candidate in sorted(candidate_values.items(), key=lambda item: item[0]):
            scores: dict[str, float] = {}
            local_cals_used: list[dict[str, str]] = []
            block_cals_used: list[dict[str, str]] = []
            for candidate_id, value in values_by_candidate.items():
                local_score, local_cals = calibrate_value(value=value, feature=feature, ref=ref, null_models=LOCAL_NULL_MODELS, cal3=cal3, cal4=cal4)
                block_score, block_cals = calibrate_value(value=value, feature=feature, ref=ref, null_models=BLOCK_NULL_MODELS, cal3=cal3, cal4=cal4)
                if not local_cals:
                    continue
                scores[candidate_id] = local_score
                local_cals_used.extend(local_cals[:1])
                block_cals_used.extend(block_cals[:1])
            if not scores:
                continue
            row_scores[ref_id][feature] = scores
            stages = sorted({cal.get("stage", "") for cal in local_cals_used if cal.get("stage")})
            damaged_means = [as_float(cal.get("damaged_mean")) for cal in local_cals_used]
            local_null_means = [as_float(cal.get("null_mean")) for cal in local_cals_used]
            block_null_means = [as_float(cal.get("null_mean")) for cal in block_cals_used]
            local_effects = [as_float(cal.get("cohen_d")) for cal in local_cals_used]
            block_effects = [as_float(cal.get("cohen_d")) for cal in block_cals_used]
            n_chunks = max([as_float(cal.get("damaged_count")) for cal in local_cals_used] or [0.0])
            n_samples = sum(as_float(cal.get("damaged_count")) + as_float(cal.get("null_count")) for cal in local_cals_used)
            local_effect = mean(local_effects)
            block_effect = mean(block_effects)
            row_cal_meta[ref_id][feature] = {
                "stages": stages,
                "calibration_damaged_mean": mean(damaged_means),
                "calibration_local_null_mean": mean(local_null_means),
                "calibration_block_shuffle_mean": mean(block_null_means),
                "calibration_local_null_effect": local_effect,
                "calibration_block_shuffle_effect": block_effect,
                "calibration_n_chunks": n_chunks,
                "calibration_n_samples": n_samples,
            }

            label_groups: dict[str, list[float]] = defaultdict(list)
            current_scores: list[float] = []
            feature_scores_for_corr: list[float] = []
            for candidate_id, score in scores.items():
                meta = candidate_meta.get(candidate_id, {})
                label_groups[str(meta.get("label", "unknown"))].append(score)
                current_scores.append(as_float(meta.get("current_score")))
                feature_scores_for_corr.append(score)

            gaps: list[float] = []
            margins: list[float] = []
            pref = rescues = breaks = current_correct_pref = current_wrong_pref = 0
            current_correct_total = current_wrong_total = 0
            for pair in pairs:
                if pair["truth_better"] not in scores or pair["truth_worse"] not in scores:
                    continue
                gap = scores[pair["truth_better"]] - scores[pair["truth_worse"]]
                gaps.append(gap)
                margins.append(pair["current_score_margin"])
                if gap > 0:
                    pref += 1
                if pair["current_scorer_correct"]:
                    current_correct_total += 1
                    current_correct_pref += 1 if gap > 0 else 0
                    breaks += 1 if gap < 0 else 0
                else:
                    current_wrong_total += 1
                    current_wrong_pref += 1 if gap > 0 else 0
                    rescues += 1 if gap > 0 else 0

            n_pairs = len(gaps)
            ci_low, ci_high = wilson_ci(pref, n_pairs)
            pref_rate = pref / n_pairs if n_pairs else 0.0
            good_values = label_groups["known_good"] + label_groups["likely_good"]
            bad_values = label_groups["known_bad"] + label_groups["likely_bad"]
            out.append(
                {
                    "calibration_reference": ref_id,
                    "direction": feature.direction,
                    "score_region": feature.score_region,
                    "start_shift": feature.start_shift,
                    "dictionary_cut": feature.dictionary_cut,
                    "span_length": feature.span_length,
                    "hd": feature.hd,
                    "feature_name": feature.feature_name,
                    "known_good_mean": mean(label_groups["known_good"]),
                    "known_bad_mean": mean(label_groups["known_bad"]),
                    "likely_good_mean": mean(label_groups["likely_good"]),
                    "likely_bad_mean": mean(label_groups["likely_bad"]),
                    "unknown_mean": mean(label_groups["unknown"]),
                    "good_minus_bad_difference": mean(good_values) - mean(bad_values),
                    "good_vs_bad_cohen_d": cohen_d(good_values, bad_values),
                    "truth_better_preference_count": pref,
                    "truth_better_preference_rate": pref_rate,
                    "truth_preference_95ci_low": ci_low,
                    "truth_preference_95ci_high": ci_high,
                    "mean_truth_gap": mean(gaps),
                    "median_truth_gap": median(gaps),
                    "gap_q05": percentile(gaps, 5),
                    "gap_q25": percentile(gaps, 25),
                    "gap_q75": percentile(gaps, 75),
                    "gap_q95": percentile(gaps, 95),
                    "rescues": rescues,
                    "breaks": breaks,
                    "net_rescues": rescues - breaks,
                    "correlation_with_current_score": pearson(feature_scores_for_corr, current_scores),
                    "correlation_with_current_score_margin": pearson(gaps, margins),
                    "truth_gap_mean_when_current_correct": mean([gap for gap, pair in zip(gaps, [p for p in pairs if p["truth_better"] in scores and p["truth_worse"] in scores]) if pair["current_scorer_correct"]]),
                    "truth_gap_mean_when_current_wrong": mean([gap for gap, pair in zip(gaps, [p for p in pairs if p["truth_better"] in scores and p["truth_worse"] in scores]) if not pair["current_scorer_correct"]]),
                    "truth_preference_when_current_correct": current_correct_pref / current_correct_total if current_correct_total else 0.0,
                    "truth_preference_when_current_wrong": current_wrong_pref / current_wrong_total if current_wrong_total else 0.0,
                    "calibration_damaged_mean": row_cal_meta[ref_id][feature]["calibration_damaged_mean"],
                    "calibration_local_null_mean": row_cal_meta[ref_id][feature]["calibration_local_null_mean"],
                    "calibration_block_shuffle_mean": row_cal_meta[ref_id][feature]["calibration_block_shuffle_mean"],
                    "calibration_local_null_effect": local_effect,
                    "calibration_block_shuffle_effect": block_effect,
                    "calibration_n_chunks": n_chunks,
                    "calibration_n_samples": n_samples,
                    "convergence_status": "",
                    "calibration_stages_used": ";".join(stages),
                    "recommended_status": row_status(pref_rate, rescues, breaks, local_effect, block_effect, n_samples),
                }
            )
    return out, row_scores, row_cal_meta


def average_scores(candidate_ids: Iterable[str], score_maps: Iterable[Mapping[str, float]], *, cap: float | None = None) -> dict[str, float]:
    out: dict[str, float] = {}
    maps = list(score_maps)
    for candidate_id in candidate_ids:
        vals = []
        for scores in maps:
            value = scores.get(candidate_id)
            if value is None:
                continue
            if cap is not None:
                value = max(-cap, min(cap, value))
            vals.append(value)
        out[candidate_id] = mean(vals)
    return out


def per_length_capped(candidate_ids: Iterable[str], keys: list[FeatureKey], row_scores: Mapping[FeatureKey, Mapping[str, float]], *, cap: float) -> dict[str, float]:
    by_length: dict[int, list[Mapping[str, float]]] = defaultdict(list)
    for key in keys:
        if key in row_scores:
            by_length[key.span_length].append(row_scores[key])
    length_scores = [average_scores(candidate_ids, maps, cap=cap) for _, maps in sorted(by_length.items())]
    return average_scores(candidate_ids, length_scores)


def build_score_families(
    *,
    candidate_ids: list[str],
    panel_scores: Mapping[str, Mapping[str, float]],
    row_scores: Mapping[str, Mapping[FeatureKey, Mapping[str, float]]],
    row_efficacy: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, float]], list[dict[str, Any]], dict[str, Any]]:
    primary_rows = row_scores.get(PRIMARY_REFERENCE, {})
    definitions: dict[str, Any] = {}
    score_families: dict[str, dict[str, float]] = {}
    panel_a = {cid: panel_scores.get(cid, {}).get("A_core_medium_local", 0.0) for cid in candidate_ids}
    score_families["S0_panelA_baseline"] = panel_a
    definitions["S0_panelA_baseline"] = {"type": "existing_panel", "panel": "A_core_medium_local"}

    normal_5_9 = [key for key in primary_rows if key.dictionary_cut == DICTIONARY_NORMAL and 5 <= key.span_length <= 9 and key.feature_name in MAIN_FEATURE_NAMES]
    normal_5_14 = [key for key in primary_rows if key.dictionary_cut == DICTIONARY_NORMAL and 5 <= key.span_length <= 14 and key.feature_name in MAIN_FEATURE_NAMES]
    strict_5_9 = [key for key in primary_rows if key.dictionary_cut == DICTIONARY_STRICT and 5 <= key.span_length <= 9 and key.feature_name in MAIN_FEATURE_NAMES]
    strict_5_14 = [key for key in primary_rows if key.dictionary_cut == DICTIONARY_STRICT and 5 <= key.span_length <= 14 and key.feature_name in MAIN_FEATURE_NAMES]
    score_families["S1_normal_len5_9_capped"] = per_length_capped(candidate_ids, normal_5_9, primary_rows, cap=3.0)
    score_families["S2_normal_len5_14_capped"] = per_length_capped(candidate_ids, normal_5_14, primary_rows, cap=3.0)
    score_families["S3a_strict_len5_9"] = per_length_capped(candidate_ids, strict_5_9, primary_rows, cap=3.0)
    score_families["S3b_strict_len5_14"] = per_length_capped(candidate_ids, strict_5_14, primary_rows, cap=3.0)
    score_families["S4_normal_len5_9_plus_strict_support"] = {
        cid: score_families["S1_normal_len5_9_capped"].get(cid, 0.0) + 0.35 * score_families["S3a_strict_len5_9"].get(cid, 0.0)
        for cid in candidate_ids
    }
    definitions.update(
        {
            "S1_normal_len5_9_capped": {"type": "per_length_capped_average", "dictionary": DICTIONARY_NORMAL, "lengths": "5..9", "cap": 3.0, "reference": PRIMARY_REFERENCE},
            "S2_normal_len5_14_capped": {"type": "per_length_capped_average", "dictionary": DICTIONARY_NORMAL, "lengths": "5..14", "cap": 3.0, "reference": PRIMARY_REFERENCE},
            "S3a_strict_len5_9": {"type": "strict_only", "dictionary": DICTIONARY_STRICT, "lengths": "5..9", "cap": 3.0, "reference": PRIMARY_REFERENCE},
            "S3b_strict_len5_14": {"type": "strict_only", "dictionary": DICTIONARY_STRICT, "lengths": "5..14", "cap": 3.0, "reference": PRIMARY_REFERENCE},
            "S4_normal_len5_9_plus_strict_support": {"type": "linear_transparent_support", "base": "S1", "strict_support_weight": 0.35, "reference": PRIMARY_REFERENCE},
        }
    )

    efficacy_by_key = {
        FeatureKey(str(row["direction"]), str(row["score_region"]), str(row["start_shift"]), str(row["dictionary_cut"]), int(row["span_length"]), int(row["hd"]), str(row["feature_name"])): row
        for row in row_efficacy
        if row["calibration_reference"] == PRIMARY_REFERENCE
    }
    selected_keys = [
        key
        for key, row in efficacy_by_key.items()
        if key in primary_rows
        and key.feature_name in MAIN_FEATURE_NAMES
        and as_float(row["calibration_local_null_effect"]) > 0.0
        and as_float(row["calibration_block_shuffle_effect"]) > -1.0
        and as_float(row["truth_better_preference_rate"]) >= 0.55
    ]
    score_families["S5_local_null_positive_selected"] = average_scores(candidate_ids, (primary_rows[key] for key in selected_keys), cap=3.0)
    definitions["S5_local_null_positive_selected"] = {"type": "selected_rows", "selected_row_count": len(selected_keys), "selection": "local_effect>0 and block_effect>-1 and pair_pref>=0.55", "reference": PRIMARY_REFERENCE}

    low_hd = [key for key in primary_rows if key.hd in {0, 1} and key.feature_name in MAIN_FEATURE_NAMES]
    mid_hd = [key for key in primary_rows if key.hd in {2, 3} and key.feature_name in MAIN_FEATURE_NAMES]
    relaxed_hd = [key for key in primary_rows if key.hd in {4, 5, 6} and key.feature_name in MAIN_FEATURE_NAMES]
    low_scores = average_scores(candidate_ids, (primary_rows[key] for key in low_hd), cap=3.0)
    mid_scores = average_scores(candidate_ids, (primary_rows[key] for key in mid_hd), cap=3.0)
    relaxed_scores = average_scores(candidate_ids, (primary_rows[key] for key in relaxed_hd), cap=3.0)
    score_families["S6_per_hd_band"] = {cid: 0.4 * low_scores.get(cid, 0.0) + 0.4 * mid_scores.get(cid, 0.0) + 0.2 * relaxed_scores.get(cid, 0.0) for cid in candidate_ids}
    definitions["S6_per_hd_band"] = {"type": "hd_band_weighted", "low_hd_weight": 0.4, "mid_hd_weight": 0.4, "relaxed_hd_weight": 0.2, "reference": PRIMARY_REFERENCE}

    for threshold in UNCERTAINTY_THRESHOLDS:
        name = f"S7_current_uncertainty_support_margin_{threshold:g}"
        score_families[name] = score_families["S4_normal_len5_9_plus_strict_support"]
        definitions[name] = {"type": "decision_policy", "base_score": "S4_normal_len5_9_plus_strict_support", "only_apply_when_abs_current_margin_lt": threshold}
    for threshold in CONSERVATIVE_THRESHOLDS:
        name = f"S8_anti_break_conservative_margin_{threshold:g}"
        score_families[name] = score_families["S4_normal_len5_9_plus_strict_support"]
        definitions[name] = {"type": "decision_policy", "base_score": "S4_normal_len5_9_plus_strict_support", "only_apply_when_abs_span_margin_gt": threshold}

    selected_manifest = [
        {
            "dictionary_cut": key.dictionary_cut,
            "span_length": key.span_length,
            "hd": key.hd,
            "feature_name": key.feature_name,
            "truth_better_preference_rate": efficacy_by_key[key]["truth_better_preference_rate"],
            "net_rescues": efficacy_by_key[key]["net_rescues"],
            "recommended_status": efficacy_by_key[key]["recommended_status"],
        }
        for key in selected_keys
    ]
    return score_families, selected_manifest, definitions


def summarize_groups(row_efficacy: list[dict[str, Any]], group_fields: list[str]) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    rows = [row for row in row_efficacy if row["calibration_reference"] == PRIMARY_REFERENCE]
    for row in rows:
        grouped[tuple(row[field] for field in group_fields)].append(row)
    out: list[dict[str, Any]] = []
    for key, items in sorted(grouped.items()):
        pref_rates = [as_float(row["truth_better_preference_rate"]) for row in items]
        rescues = sum(int(row["rescues"]) for row in items)
        breaks = sum(int(row["breaks"]) for row in items)
        summary = {field: value for field, value in zip(group_fields, key)}
        summary.update(
            {
                "row_count": len(items),
                "calibration_local_null_effect": mean(as_float(row["calibration_local_null_effect"]) for row in items),
                "calibration_block_shuffle_effect": mean(as_float(row["calibration_block_shuffle_effect"]) for row in items),
                "hard_pair_truth_preference": mean(pref_rates),
                "rescues": rescues,
                "breaks": breaks,
                "net": rescues - breaks,
                "mean_gap": mean(as_float(row["mean_truth_gap"]) for row in items),
                "median_gap": mean(as_float(row["median_truth_gap"]) for row in items),
                "correlation_with_current_scorer": mean(as_float(row["correlation_with_current_score_margin"]) for row in items),
                "recommended_status": Counter(str(row["recommended_status"]) for row in items).most_common(1)[0][0],
            }
        )
        out.append(summary)
    return out


def margin_sweep(score_name: str, pairs: list[dict[str, Any]], scores: Mapping[str, float]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    misranks = sum(1 for pair in pairs if not pair["current_scorer_correct"])
    for threshold in MARGIN_THRESHOLDS:
        summary, details = evaluate_pair_scores(pairs, scores, threshold=threshold)
        overrides = sum(1 for row in details if row["score_applies"] == "true")
        rescues = int(summary["rescues"])
        breaks = int(summary["breaks"])
        out.append(
            {
                "score_family": score_name,
                "threshold": threshold,
                "override_count": overrides,
                "rescues": rescues,
                "breaks": breaks,
                "net_rescues": rescues - breaks,
                "precision_of_overrides": rescues / overrides if overrides else 0.0,
                "recall_of_misranks": rescues / misranks if misranks else 0.0,
            }
        )
    return out


def top_pair_rows(pair_gap_rows: list[dict[str, Any]], *, want_rescue: bool) -> list[dict[str, Any]]:
    field = "rescues_current_misrank" if want_rescue else "breaks_current_correct"
    rows = [row for row in pair_gap_rows if row[field] == "true"]
    rows.sort(key=lambda row: abs(as_float(row["score_gap"])), reverse=True)
    return rows[:TOP_N]


def write_readout(
    *,
    score_summary: list[dict[str, Any]],
    length_summary: list[dict[str, Any]],
    hd_summary: list[dict[str, Any]],
    row_efficacy: list[dict[str, Any]],
    missing: list[str],
    elapsed_s: float,
) -> None:
    by_name = {row["score_family"]: row for row in score_summary}
    ranked = sorted(score_summary, key=lambda row: (as_float(row["net_rescues"]), as_float(row["truth_better_preference_rate"])), reverse=True)
    best = ranked[0] if ranked else {}
    panel_a = by_name.get("S0_panelA_baseline", {})
    span_only_beats_panel_a = [
        row for row in score_summary
        if row["score_family"] != "S0_panelA_baseline"
        and as_float(row["truth_better_preference_rate"]) > as_float(panel_a.get("truth_better_preference_rate"))
    ]
    positive_net = [row for row in score_summary if as_float(row["net_rescues"]) > 0]
    best_lengths = sorted(length_summary, key=lambda row: as_float(row["hard_pair_truth_preference"]), reverse=True)[:5]
    best_hds = sorted(hd_summary, key=lambda row: as_float(row["hard_pair_truth_preference"]), reverse=True)[:5]
    strict_rows = [row for row in row_efficacy if row["calibration_reference"] == PRIMARY_REFERENCE and row["dictionary_cut"] == DICTIONARY_STRICT]
    normal_rows = [row for row in row_efficacy if row["calibration_reference"] == PRIMARY_REFERENCE and row["dictionary_cut"] == DICTIONARY_NORMAL]
    long_rows = [row for row in row_efficacy if row["calibration_reference"] == PRIMARY_REFERENCE and int(row["span_length"]) >= 10]
    lines = [
        "# Whole-Ladder Span-Hamming Multi-Score Hard-Pair Report v1",
        "",
        f"Created UTC: {datetime.now(timezone.utc).isoformat()}",
        f"Elapsed seconds: {elapsed_s:.1f}",
        "",
        "## Scope",
        "",
        "- Report-only analysis over existing hard-pair candidate feature rows and existing calibration summaries.",
        "- No calibration/data-taking run was launched.",
        "- No production scorer weights, defaults, ranking policy, or calibration outputs were changed.",
        "- Primary merged calibration view uses Stage 4 where available for lengths 8-14 and Stage 3 otherwise.",
        "",
        "## Main Answers",
        "",
        f"- Best score family by net rescue then truth preference: {best.get('score_family', '')} with truth preference {as_float(best.get('truth_better_preference_rate')):.3f}, rescues {best.get('rescues', '')}, breaks {best.get('breaks', '')}, net {best.get('net_rescues', '')}.",
        f"- Panel A baseline: truth preference {as_float(panel_a.get('truth_better_preference_rate')):.3f}, rescues {panel_a.get('rescues', '')}, breaks {panel_a.get('breaks', '')}, net {panel_a.get('net_rescues', '')}.",
        f"- Span-Hamming-only scores beating Panel A by truth-preference rate: {len(span_only_beats_panel_a)}.",
        f"- Score families with positive net rescues: {len(positive_net)}.",
        f"- Normal rows mean truth preference: {mean(as_float(row['truth_better_preference_rate']) for row in normal_rows):.3f}.",
        f"- Strict rows mean truth preference: {mean(as_float(row['truth_better_preference_rate']) for row in strict_rows):.3f}.",
        f"- Long length 10-14 rows mean truth preference: {mean(as_float(row['truth_better_preference_rate']) for row in long_rows):.3f}.",
        "",
        "## Helpful Lengths",
        "",
    ]
    for row in best_lengths:
        lines.append(f"- length {row['span_length']}: truth preference {as_float(row['hard_pair_truth_preference']):.3f}, net {row['net']}, status {row['recommended_status']}")
    lines.extend(["", "## Helpful HD Rungs", ""])
    for row in best_hds:
        lines.append(f"- HD {row['hd']}: truth preference {as_float(row['hard_pair_truth_preference']):.3f}, net {row['net']}, status {row['recommended_status']}")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Span-Hamming remains local evidence. High local-word evidence can still coexist with poor order/coherence.",
            "- Conservative threshold and current-margin support rows should be read as support-policy simulations, not production thresholds.",
            "- Phrase/order/ngram evidence is still the natural next layer if span-Hamming-only net rescue is weak or break-heavy.",
            "",
            "## Missing / Coverage Notes",
            "",
        ]
    )
    if missing:
        lines.extend(f"- {item}" for item in missing)
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Key Output Files",
            "",
            "- row_efficacy_report.csv",
            "- length_hd_efficacy_report.csv",
            "- score_family_pairwise_summary.csv",
            "- score_family_margin_sweep.csv",
            "- pairwise_score_gaps.csv.gz",
            "- candidate_multiscore_summary.csv",
        ]
    )
    (OUTPUT_DIR / "readout.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def copy_review_pack() -> None:
    if REVIEW_PACK_DIR.exists():
        shutil.rmtree(REVIEW_PACK_DIR)
    REVIEW_PACK_DIR.mkdir(parents=True, exist_ok=True)
    for name in (
        "config.json",
        "input_manifest.json",
        "calibration_manifest.json",
        "score_definition_manifest.json",
        "row_efficacy_report.csv",
        "length_hd_efficacy_report.csv",
        "length_summary.csv",
        "hd_summary.csv",
        "dictionary_cut_summary.csv",
        "feature_name_summary.csv",
        "score_family_pairwise_summary.csv",
        "score_family_margin_sweep.csv",
        "pairwise_score_gaps.csv.gz",
        "candidate_multiscore_summary.csv",
        "top_rescues_by_score.csv",
        "top_breaks_by_score.csv",
        "top_supported_candidates.csv",
        "top_warning_candidates.csv",
        "known_bad_high_span_hamming.csv",
        "known_good_low_span_hamming.csv",
        "unknown_high_span_hamming.csv",
        "readout.md",
    ):
        source = OUTPUT_DIR / name
        if source.exists():
            shutil.copy2(source, REVIEW_PACK_DIR / name)
    if REVIEW_PACK_ZIP.exists():
        REVIEW_PACK_ZIP.unlink()
    shutil.make_archive(str(REVIEW_PACK_DIR), "zip", REVIEW_PACK_DIR)


def main() -> None:
    start = time.perf_counter()
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    required_paths = {
        "hard_pair_candidate_feature_rows": HARD_PAIR_DIR / "candidate_feature_rows.csv.gz",
        "hard_pair_candidate_manifest": HARD_PAIR_DIR / "candidate_manifest_resolved.csv",
        "hard_pair_candidate_level_summary": HARD_PAIR_DIR / "candidate_level_summary.csv",
        "hard_pair_pairwise_summary": HARD_PAIR_DIR / "pairwise_road_test_summary.csv",
        "stage3_damaged_vs_null_summary": STAGE3_DIR / "damaged_vs_null_summary.csv",
        "stage4_damaged_vs_null_summary": STAGE4_DIR / "damaged_vs_null_summary.csv",
    }
    missing = [f"missing required input {name}: {rel(path)}" for name, path in required_paths.items() if not path.exists()]
    if missing:
        write_json(OUTPUT_DIR / "input_manifest.json", {"missing": missing})
        raise FileNotFoundError("; ".join(missing))

    refs = reference_specs()
    candidate_manifest, pair_rows_raw, candidate_meta, panel_scores, candidate_values, feature_nulls, shape_counts = load_candidate_inputs()
    pairs = build_pair_model(pair_rows_raw)
    candidate_ids = sorted(candidate_meta)
    cal3 = load_calibration_stage("stage3_fwd_full_len5_14_pcb", STAGE3_DIR)
    cal4 = load_calibration_stage("stage4_fwd_full_len8_14_pcb", STAGE4_DIR)

    diagnostic_present = sorted({key.feature_name for key in candidate_values if key.feature_name in DIAGNOSTIC_FEATURE_NAMES})
    if set(DIAGNOSTIC_FEATURE_NAMES) - set(diagnostic_present):
        missing.append("candidate_feature_rows.csv.gz does not include all raw diagnostic count/window fields; diagnostics limited to available feature rows")
    if not any(key.span_length < 5 for key in candidate_values):
        missing.append("hard-pair candidate feature rows cover lengths 5..14 only; lengths 2..4 remain calibration-side diagnostics")

    write_json(
        OUTPUT_DIR / "config.json",
        {
            "run_label": RUN_LABEL,
            "report_only": True,
            "hard_pair_input_dir": rel(HARD_PAIR_DIR),
            "output_dir": rel(OUTPUT_DIR),
            "primary_reference": PRIMARY_REFERENCE,
            "local_null_models": LOCAL_NULL_MODELS,
            "block_null_models": BLOCK_NULL_MODELS,
            "main_feature_names": MAIN_FEATURE_NAMES,
            "diagnostic_feature_names": DIAGNOSTIC_FEATURE_NAMES,
            "margin_thresholds": MARGIN_THRESHOLDS,
            "uncertainty_thresholds": UNCERTAINTY_THRESHOLDS,
            "conservative_thresholds": CONSERVATIVE_THRESHOLDS,
            "scorer_policy": "report-only; no production weights/defaults/ranking changes",
        },
    )
    write_json(
        OUTPUT_DIR / "input_manifest.json",
        {
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "inputs": {name: {"path": rel(path), "exists": path.exists(), "bytes": path.stat().st_size if path.exists() else 0} for name, path in required_paths.items()},
            "candidate_count": len(candidate_manifest),
            "pair_count": len(pair_rows_raw),
            "feature_key_count": len(candidate_values),
            "observed_feature_shapes": {"|".join(map(str, key)): count for key, count in shape_counts.items()},
            "missing_or_limited_coverage": missing,
        },
    )
    write_json(
        OUTPUT_DIR / "calibration_manifest.json",
        {
            "stage1_stage2_combined": {"path": rel(STAGE12_DIR), "exists": STAGE12_DIR.exists(), "role": "available compact earlier calibration context; not used for primary merged row scoring because full row shape differs"},
            "stage3": {"path": rel(STAGE3_DIR), "rows_loaded": len(cal3), "role": "primary calibration for lengths 5..7 and fallback for 8..14"},
            "stage4": {"path": rel(STAGE4_DIR), "rows_loaded": len(cal4), "role": "preferred calibration for overlapping lengths 8..14"},
            "references": refs,
            "merge_rule": "use Stage 4 when span_length >= 8 and row key exists; otherwise use Stage 3",
        },
    )

    row_efficacy, row_scores_by_ref, row_cal_meta = build_row_efficacy(
        candidate_values=candidate_values,
        refs=refs,
        cal3=cal3,
        cal4=cal4,
        candidate_meta=candidate_meta,
        pairs=pairs,
    )
    row_efficacy_fields = [
        "calibration_reference",
        "direction",
        "score_region",
        "start_shift",
        "dictionary_cut",
        "span_length",
        "hd",
        "feature_name",
        "known_good_mean",
        "known_bad_mean",
        "likely_good_mean",
        "likely_bad_mean",
        "unknown_mean",
        "good_minus_bad_difference",
        "good_vs_bad_cohen_d",
        "truth_better_preference_count",
        "truth_better_preference_rate",
        "truth_preference_95ci_low",
        "truth_preference_95ci_high",
        "mean_truth_gap",
        "median_truth_gap",
        "gap_q05",
        "gap_q25",
        "gap_q75",
        "gap_q95",
        "rescues",
        "breaks",
        "net_rescues",
        "correlation_with_current_score",
        "correlation_with_current_score_margin",
        "truth_gap_mean_when_current_correct",
        "truth_gap_mean_when_current_wrong",
        "truth_preference_when_current_correct",
        "truth_preference_when_current_wrong",
        "calibration_damaged_mean",
        "calibration_local_null_mean",
        "calibration_block_shuffle_mean",
        "calibration_local_null_effect",
        "calibration_block_shuffle_effect",
        "calibration_n_chunks",
        "calibration_n_samples",
        "convergence_status",
        "calibration_stages_used",
        "recommended_status",
    ]
    write_csv(OUTPUT_DIR / "row_efficacy_report.csv", row_efficacy, row_efficacy_fields)

    length_hd = summarize_groups(row_efficacy, ["span_length", "hd", "dictionary_cut", "feature_name"])
    length_summary = summarize_groups(row_efficacy, ["span_length"])
    hd_summary = summarize_groups(row_efficacy, ["hd"])
    dictionary_summary = summarize_groups(row_efficacy, ["dictionary_cut"])
    feature_summary = summarize_groups(row_efficacy, ["feature_name"])
    summary_fields = ["row_count", "calibration_local_null_effect", "calibration_block_shuffle_effect", "hard_pair_truth_preference", "rescues", "breaks", "net", "mean_gap", "median_gap", "correlation_with_current_scorer", "recommended_status"]
    write_csv(OUTPUT_DIR / "length_hd_efficacy_report.csv", length_hd, ["span_length", "hd", "dictionary_cut", "feature_name", *summary_fields])
    write_csv(OUTPUT_DIR / "length_summary.csv", length_summary, ["span_length", *summary_fields])
    write_csv(OUTPUT_DIR / "hd_summary.csv", hd_summary, ["hd", *summary_fields])
    write_csv(OUTPUT_DIR / "dictionary_cut_summary.csv", dictionary_summary, ["dictionary_cut", *summary_fields])
    write_csv(OUTPUT_DIR / "feature_name_summary.csv", feature_summary, ["feature_name", *summary_fields])

    score_families, selected_manifest, score_definitions = build_score_families(
        candidate_ids=candidate_ids,
        panel_scores=panel_scores,
        row_scores=row_scores_by_ref,
        row_efficacy=row_efficacy,
    )
    write_json(OUTPUT_DIR / "score_definition_manifest.json", {"score_definitions": score_definitions, "selected_rows": selected_manifest})

    score_summary: list[dict[str, Any]] = []
    pair_gap_rows: list[dict[str, Any]] = []
    for score_name, scores in score_families.items():
        definition = score_definitions.get(score_name, {})
        if definition.get("type") == "decision_policy" and "only_apply_when_abs_current_margin_lt" in definition:
            summary, details = evaluate_pair_scores(pairs, scores, keep_current_outside_margin=float(definition["only_apply_when_abs_current_margin_lt"]))
        elif definition.get("type") == "decision_policy" and "only_apply_when_abs_span_margin_gt" in definition:
            summary, details = evaluate_pair_scores(pairs, scores, threshold=float(definition["only_apply_when_abs_span_margin_gt"]))
        else:
            summary, details = evaluate_pair_scores(pairs, scores)
        summary["score_family"] = score_name
        score_summary.append(summary)
        for row in details:
            row["score_family"] = score_name
        pair_gap_rows.extend(details)
    score_summary_fields = ["score_family", "n_pairs", "truth_better_preference_count", "truth_better_preference_rate", "truth_preference_95ci_low", "truth_preference_95ci_high", "rescues", "breaks", "net_rescues", "current_scorer_correct_count", "current_scorer_misrank_count", "mean_gap", "median_gap", "gap_q05", "gap_q25", "gap_q75", "gap_q95"]
    write_csv(OUTPUT_DIR / "score_family_pairwise_summary.csv", score_summary, score_summary_fields)
    pair_gap_fields = ["score_family", "pair_id", "truth_better_candidate_id", "truth_worse_candidate_id", "truth_better_score", "truth_worse_score", "score_gap", "score_preferred", "score_prefers_truth_better", "score_applies", "current_scorer_correct", "current_score_margin", "rescues_current_misrank", "breaks_current_correct"]
    write_csv_gz(OUTPUT_DIR / "pairwise_score_gaps.csv.gz", pair_gap_rows, pair_gap_fields)

    sweep_rows: list[dict[str, Any]] = []
    for score_name, scores in score_families.items():
        sweep_rows.extend(margin_sweep(score_name, pairs, scores))
    write_csv(OUTPUT_DIR / "score_family_margin_sweep.csv", sweep_rows, ["score_family", "threshold", "override_count", "rescues", "breaks", "net_rescues", "precision_of_overrides", "recall_of_misranks"])
    write_csv(OUTPUT_DIR / "top_rescues_by_score.csv", top_pair_rows(pair_gap_rows, want_rescue=True), pair_gap_fields)
    write_csv(OUTPUT_DIR / "top_breaks_by_score.csv", top_pair_rows(pair_gap_rows, want_rescue=False), pair_gap_fields)

    candidate_rows: list[dict[str, Any]] = []
    for candidate_id in candidate_ids:
        meta = candidate_meta[candidate_id]
        row = {
            "candidate_id": candidate_id,
            "label": meta.get("label", ""),
            "current_score": meta.get("current_score", ""),
            "current_rank": meta.get("candidate_rank", ""),
            "truth_match_ratio": meta.get("truth_match_ratio", ""),
            "panelA": panel_scores.get(candidate_id, {}).get("A_core_medium_local", 0.0),
            "panelB": panel_scores.get(candidate_id, {}).get("B_longer_span", 0.0),
            "panelD": panel_scores.get(candidate_id, {}).get("D_strict_precision", 0.0),
            "top_supporting_features": "",
            "top_warning_features": "",
        }
        for score_name, scores in score_families.items():
            row[score_name] = scores.get(candidate_id, 0.0)
        candidate_rows.append(row)
    candidate_score_fields = ["candidate_id", "label", "current_score", "current_rank", "truth_match_ratio", *score_families.keys(), "panelA", "panelB", "panelD", "top_supporting_features", "top_warning_features"]
    write_csv(OUTPUT_DIR / "candidate_multiscore_summary.csv", candidate_rows, candidate_score_fields)
    by_s5 = sorted(candidate_rows, key=lambda row: as_float(row.get("S5_local_null_positive_selected")), reverse=True)
    write_csv(OUTPUT_DIR / "top_supported_candidates.csv", by_s5[:TOP_N], candidate_score_fields)
    write_csv(OUTPUT_DIR / "top_warning_candidates.csv", sorted(candidate_rows, key=lambda row: as_float(row.get("S5_local_null_positive_selected")))[:TOP_N], candidate_score_fields)
    write_csv(OUTPUT_DIR / "known_bad_high_span_hamming.csv", [row for row in by_s5 if row["label"] in {"known_bad", "likely_bad"}][:TOP_N], candidate_score_fields)
    write_csv(OUTPUT_DIR / "known_good_low_span_hamming.csv", sorted([row for row in candidate_rows if row["label"] in {"known_good", "likely_good"}], key=lambda row: as_float(row.get("S5_local_null_positive_selected")))[:TOP_N], candidate_score_fields)
    write_csv(OUTPUT_DIR / "unknown_high_span_hamming.csv", [row for row in by_s5 if row["label"] == "unknown"][:TOP_N], candidate_score_fields)

    elapsed_s = time.perf_counter() - start
    write_readout(
        score_summary=score_summary,
        length_summary=length_summary,
        hd_summary=hd_summary,
        row_efficacy=row_efficacy,
        missing=missing,
        elapsed_s=elapsed_s,
    )
    copy_review_pack()
    print(f"[{RUN_LABEL}] complete candidates={len(candidate_ids)} pairs={len(pairs)} feature_keys={len(candidate_values)} row_efficacy={len(row_efficacy)} elapsed={elapsed_s:.1f}s")
    print(f"[{RUN_LABEL}] output_dir={rel(OUTPUT_DIR)}")
    print(f"[{RUN_LABEL}] review_pack={rel(REVIEW_PACK_ZIP)}")


if __name__ == "__main__":
    main()
