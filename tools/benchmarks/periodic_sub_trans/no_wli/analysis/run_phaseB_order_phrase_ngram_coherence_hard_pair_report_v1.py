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
from typing import Any, Iterable, Mapping


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


RUN_LABEL = "phaseB_order_phrase_ngram_coherence_hard_pair_report_v1"
ANALYSIS_ROOT = REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis"
OUTPUT_DIR = ANALYSIS_ROOT / RUN_LABEL
HARD_PAIR_DIR = ANALYSIS_ROOT / "phaseB_span_hamming_hard_pair_road_test_v1"
MANUAL_DIR = ANALYSIS_ROOT / "phaseB_span_hamming_candidate_manual_inspection_v1"
MULTISCORE_DIR = ANALYSIS_ROOT / "phaseB_span_hamming_multiscore_hard_pair_report_v1"
REVIEW_PACK_DIR = (
    REPO_ROOT
    / "planning/projects/no_wli/40_review_summaries"
    / "phaseB_order_phrase_ngram_coherence_hard_pair_report_v1_review_pack_2026-05-14"
)
REVIEW_PACK_ZIP = REVIEW_PACK_DIR.with_suffix(".zip")

MARGIN_THRESHOLDS = (0.0, 0.025, 0.05, 0.075, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.75, 1.0)
TOP_N = 50
UNCERTAIN_CURRENT_MARGIN = 0.01
CONSERVATIVE_COMBINED_MARGIN = 0.25

COMMON_TRIGRAMS = (
    "THE", "AND", "ING", "ION", "ENT", "HER", "THA", "NTH", "ATI", "FOR",
    "TIO", "ERE", "TER", "EST", "ERS", "ATI", "HAT", "ATE", "ALL", "HES",
    "HIS", "OFT", "ETH", "DTH", "STH", "YOU", "WAS", "NOT", "WIT", "AVE",
)
COMMON_QUADGRAMS = (
    "TION", "THER", "WITH", "HERE", "OULD", "IGHT", "HAVE", "THAT", "MENT",
    "IONS", "EVER", "FROM", "OUGH", "TING", "THEM", "THEN", "WERE", "THIS",
    "ATIO", "NDTH", "EDTH", "OFTH", "TTHE", "INGT", "ATIO", "THEY",
)
COMMON_FIVEGRAMS = (
    "THERE", "WHICH", "THEIR", "WOULD", "ABOUT", "OTHER", "THESE", "FIRST",
    "AFTER", "COULD", "WHERE", "EVERY", "THROUGH", "THING", "THINK", "GREAT",
    "SHALL", "HOUSE", "BEFOR", "UNDER", "AGAIN", "PLACE", "RIGHT",
)
COMMON_PHRASELETS = (
    "THE", "AND", "THAT", "WITH", "HAVE", "THIS", "FROM", "WERE", "THEY",
    "WOULD", "THERE", "THEIR", "ABOUT", "COULD", "WHICH", "BEFORE", "AFTER",
    "INTO", "ONLY", "MORE", "WHEN", "WHAT", "OVER", "SAID", "WELL", "TIME",
)
BAD_BIGRAMS = (
    "JQ", "QJ", "QW", "QY", "QZ", "WQ", "WJ", "WV", "WX", "XJ", "XQ", "XZ",
    "ZJ", "ZQ", "ZX", "VV", "JJ", "QQ", "YY", "KKK",
)
VOWELS = set("AEIOU")


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


def norm_text(text: str) -> str:
    text = str(text).replace("(I)", "I")
    return "".join(ch for ch in text.upper() if "A" <= ch <= "Z")


def ngrams(text: str, n: int) -> list[str]:
    if len(text) < n:
        return []
    return [text[idx : idx + n] for idx in range(0, len(text) - n + 1)]


def hit_rate(text: str, grams: tuple[str, ...], n: int) -> float:
    seq = ngrams(text, n)
    if not seq:
        return 0.0
    gram_set = set(grams)
    return sum(1 for gram in seq if gram in gram_set) / len(seq)


def phraselet_density(text: str) -> float:
    if not text:
        return 0.0
    return sum(text.count(fragment) for fragment in COMMON_PHRASELETS) / len(text)


def repeated_ngram_rate(text: str, n: int) -> float:
    seq = ngrams(text, n)
    if not seq:
        return 0.0
    counts = Counter(seq)
    repeated = sum(count - 1 for count in counts.values() if count > 1)
    return repeated / len(seq)


def bad_bigram_rate(text: str) -> float:
    seq = ngrams(text, 2)
    if not seq:
        return 0.0
    bad = set(BAD_BIGRAMS)
    return sum(1 for gram in seq if gram in bad) / len(seq)


def max_run_fraction(text: str) -> float:
    if not text:
        return 0.0
    best = 1
    current = 1
    for prev, ch in zip(text, text[1:]):
        if ch == prev:
            current += 1
            best = max(best, current)
        else:
            current = 1
    return best / len(text)


def transition_entropy(text: str) -> float:
    if len(text) < 2:
        return 0.0
    counts = Counter(ngrams(text, 2))
    total = sum(counts.values())
    entropy = -sum((count / total) * math.log2(count / total) for count in counts.values())
    return entropy / math.log2(min(26 * 26, total)) if total > 1 else 0.0


def vowel_balance_score(text: str) -> float:
    if not text:
        return 0.0
    ratio = sum(1 for ch in text if ch in VOWELS) / len(text)
    return -abs(ratio - 0.38)


def zscore_maps(rows: list[dict[str, Any]], fields: list[str]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = defaultdict(dict)
    for field in fields:
        values = [as_float(row[field]) for row in rows]
        mu = mean(values)
        sigma = statistics.stdev(values) if len(values) >= 2 else 0.0
        for row in rows:
            out[row["candidate_id"]][field] = 0.0 if sigma <= 1e-12 else (as_float(row[field]) - mu) / sigma
    return out


def load_candidate_texts() -> dict[str, dict[str, Any]]:
    path = MANUAL_DIR / "candidate_full_texts.jsonl.gz"
    out: dict[str, dict[str, Any]] = {}
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            row["normalized_latin"] = norm_text(row.get("latin_render", ""))
            out[row["candidate_id"]] = row
    return out


def load_len7_hd2_exact_support() -> dict[str, float]:
    path = HARD_PAIR_DIR / "candidate_feature_rows.csv.gz"
    sums: dict[str, float] = defaultdict(float)
    counts: Counter = Counter()
    seen: set[tuple[str, str]] = set()
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("dictionary_cut") != "phaseA14_normal_selected":
                continue
            if row.get("span_length") != "7" or row.get("hd") != "2":
                continue
            if row.get("feature_name") != "exact_count_norm":
                continue
            if row.get("comparison_null_class") != "local_null":
                continue
            key = (row["candidate_id"], row["candidate_chunk_id"])
            if key in seen:
                continue
            seen.add(key)
            sums[row["candidate_id"]] += as_float(row.get("signed_effect_vs_local_null"))
            counts[row["candidate_id"]] += 1
    return {candidate_id: total / max(1, counts[candidate_id]) for candidate_id, total in sums.items()}


def load_multiscore_gaps() -> dict[str, dict[str, dict[str, str]]]:
    path = MULTISCORE_DIR / "pairwise_score_gaps.csv.gz"
    out: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["score_family"] in {"S0_panelA_baseline", "S5_local_null_positive_selected", "S7_current_uncertainty_support_margin_0.01", "S8_anti_break_conservative_margin_0.25"}:
                out[row["score_family"]][row["pair_id"]] = row
    return out


def build_candidate_rows(candidate_texts: Mapping[str, Mapping[str, Any]], multiscore_rows: list[dict[str, str]], len7_scores: Mapping[str, float]) -> list[dict[str, Any]]:
    by_candidate = {row["candidate_id"]: row for row in multiscore_rows}
    raw_rows: list[dict[str, Any]] = []
    for candidate_id, text_row in sorted(candidate_texts.items()):
        text = str(text_row.get("normalized_latin", ""))
        multi = by_candidate.get(candidate_id, {})
        raw_rows.append(
            {
                "candidate_id": candidate_id,
                "label": text_row.get("label", ""),
                "current_score": as_float(text_row.get("current_score")),
                "truth_match_ratio": as_float(text_row.get("truth_match_ratio")),
                "token_count": as_float(text_row.get("token_count")),
                "latin_length": len(text),
                "common_trigram_rate": hit_rate(text, COMMON_TRIGRAMS, 3),
                "common_quadgram_rate": hit_rate(text, COMMON_QUADGRAMS, 4),
                "common_fivegram_rate": hit_rate(text, COMMON_FIVEGRAMS, 5),
                "phraselet_density": phraselet_density(text),
                "repeated_3gram_rate": repeated_ngram_rate(text, 3),
                "repeated_4gram_rate": repeated_ngram_rate(text, 4),
                "bad_bigram_rate": bad_bigram_rate(text),
                "max_run_fraction": max_run_fraction(text),
                "transition_entropy": transition_entropy(text),
                "vowel_balance_score": vowel_balance_score(text),
                "panelA": as_float(multi.get("panelA")),
                "panelB": as_float(multi.get("panelB")),
                "panelD": as_float(multi.get("panelD")),
                "S5_local_null_positive_selected": as_float(multi.get("S5_local_null_positive_selected")),
                "len7_hd2_exact_support": len7_scores.get(candidate_id, 0.0),
            }
        )
    z = zscore_maps(
        raw_rows,
        [
            "common_trigram_rate",
            "common_quadgram_rate",
            "common_fivegram_rate",
            "phraselet_density",
            "repeated_3gram_rate",
            "repeated_4gram_rate",
            "bad_bigram_rate",
            "max_run_fraction",
            "transition_entropy",
            "vowel_balance_score",
            "panelA",
            "S5_local_null_positive_selected",
            "len7_hd2_exact_support",
        ],
    )
    rows: list[dict[str, Any]] = []
    for row in raw_rows:
        cid = row["candidate_id"]
        char_ngram = (
            z[cid]["common_trigram_rate"]
            + z[cid]["common_quadgram_rate"]
            + z[cid]["common_fivegram_rate"]
            - z[cid]["bad_bigram_rate"]
        ) / 4.0
        phrase = (z[cid]["phraselet_density"] + 0.5 * z[cid]["transition_entropy"] + 0.5 * z[cid]["vowel_balance_score"]) / 2.0
        repetition_penalty = -(z[cid]["repeated_3gram_rate"] + z[cid]["repeated_4gram_rate"] + z[cid]["max_run_fraction"]) / 3.0
        coherence = 0.45 * char_ngram + 0.35 * phrase + 0.20 * repetition_penalty
        row.update(
            {
                "C1_char_ngram_coherence": char_ngram,
                "C2_phrase_or_ngram_coherence_if_available": phrase,
                "C3_repetition_penalty": repetition_penalty,
                "coherence_composite": coherence,
                "C5_span_A_plus_coherence": z[cid]["panelA"] + 0.5 * coherence,
                "C6_S5_plus_coherence": z[cid]["S5_local_null_positive_selected"] + 0.5 * coherence,
                "C7_len7_hd2_exact_support_plus_coherence": z[cid]["len7_hd2_exact_support"] + 0.5 * coherence,
            }
        )
        rows.append(row)
    return rows


def score_maps(candidate_rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    fields = (
        "C1_char_ngram_coherence",
        "C2_phrase_or_ngram_coherence_if_available",
        "C3_repetition_penalty",
        "coherence_composite",
        "C5_span_A_plus_coherence",
        "C6_S5_plus_coherence",
        "C7_len7_hd2_exact_support_plus_coherence",
        "panelA",
        "S5_local_null_positive_selected",
        "len7_hd2_exact_support",
    )
    return {field: {row["candidate_id"]: as_float(row.get(field)) for row in candidate_rows} for field in fields}


def build_pair_rows(pairwise_rows: list[dict[str, str]], maps: Mapping[str, Mapping[str, float]], span_gaps: Mapping[str, Mapping[str, Mapping[str, str]]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in pairwise_rows:
        pair_id = row["pair_id"]
        a_id = row["candidate_a_id"]
        b_id = row["candidate_b_id"]
        current_correct = str(row.get("current_scorer_correct", "")).lower() == "true"
        base = {
            "pair_id": pair_id,
            "truth_better_candidate_id": a_id,
            "truth_worse_candidate_id": b_id,
            "current_score_gap": as_float(row.get("current_score_margin")),
            "current_scorer_correct": current_correct,
            "panelA_gap": as_float(span_gaps.get("S0_panelA_baseline", {}).get(pair_id, {}).get("score_gap")),
            "S5_gap": as_float(span_gaps.get("S5_local_null_positive_selected", {}).get(pair_id, {}).get("score_gap")),
            "panelA_rescue": span_gaps.get("S0_panelA_baseline", {}).get(pair_id, {}).get("rescues_current_misrank", "false") == "true",
            "panelA_break": span_gaps.get("S0_panelA_baseline", {}).get(pair_id, {}).get("breaks_current_correct", "false") == "true",
            "S5_rescue": span_gaps.get("S5_local_null_positive_selected", {}).get(pair_id, {}).get("rescues_current_misrank", "false") == "true",
            "S5_break": span_gaps.get("S5_local_null_positive_selected", {}).get(pair_id, {}).get("breaks_current_correct", "false") == "true",
            "panelA_threshold_0_4_support": abs(as_float(span_gaps.get("S0_panelA_baseline", {}).get(pair_id, {}).get("score_gap"))) >= 0.4,
            "S7_margin_0_01_support": span_gaps.get("S7_current_uncertainty_support_margin_0.01", {}).get(pair_id, {}).get("score_applies", "false") == "true",
            "S8_margin_0_25_support": span_gaps.get("S8_anti_break_conservative_margin_0.25", {}).get(pair_id, {}).get("score_applies", "false") == "true",
        }
        for score_name, scores in maps.items():
            base[f"{score_name}_gap"] = scores.get(a_id, 0.0) - scores.get(b_id, 0.0)
        out.append(base)
    return out


def evaluate_pairs(pair_rows: list[dict[str, Any]], score_name: str, *, threshold: float = 0.0, current_margin_gate: float | None = None, combined_positive_gate: bool = False) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    gap_field = f"{score_name}_gap"
    prefer = rescues = breaks = current_correct = current_wrong = applied = 0
    correct_pref = wrong_pref = 0
    gaps: list[float] = []
    current_gaps: list[float] = []
    panel_a_gaps: list[float] = []
    s5_gaps: list[float] = []
    details: list[dict[str, Any]] = []
    for row in pair_rows:
        gap = as_float(row.get(gap_field))
        gaps.append(gap)
        current_gaps.append(as_float(row.get("current_score_gap")))
        panel_a_gaps.append(as_float(row.get("panelA_gap")))
        s5_gaps.append(as_float(row.get("S5_gap")))
        is_current_correct = bool(row["current_scorer_correct"])
        current_correct += 1 if is_current_correct else 0
        current_wrong += 0 if is_current_correct else 1
        applies = abs(gap) > threshold
        if current_margin_gate is not None and abs(as_float(row["current_score_gap"])) >= current_margin_gate:
            applies = False
        if combined_positive_gate and not (gap > threshold and (row["panelA_gap"] > 0.0 or row["S5_gap"] > 0.0)):
            applies = False
        if applies:
            applied += 1
            prefers_truth = gap > 0.0
            prefer += 1 if prefers_truth else 0
            correct_pref += 1 if prefers_truth and is_current_correct else 0
            wrong_pref += 1 if prefers_truth and not is_current_correct else 0
            rescues += 1 if prefers_truth and not is_current_correct else 0
            breaks += 1 if (not prefers_truth) and is_current_correct else 0
        details.append(
            {
                "score_family": score_name,
                "pair_id": row["pair_id"],
                "truth_better_candidate_id": row["truth_better_candidate_id"],
                "truth_worse_candidate_id": row["truth_worse_candidate_id"],
                "score_gap": gap,
                "score_applies": "true" if applies else "false",
                "score_prefers_truth_better": "true" if applies and gap > 0.0 else "false",
                "current_scorer_correct": "true" if is_current_correct else "false",
                "current_score_gap": row["current_score_gap"],
                "panelA_gap": row["panelA_gap"],
                "S5_gap": row["S5_gap"],
                "rescues_current_misrank": "true" if applies and gap > 0.0 and not is_current_correct else "false",
                "breaks_current_correct": "true" if applies and gap < 0.0 and is_current_correct else "false",
                "suppresses_panelA_break": "true" if row["panelA_break"] and gap > 0.0 else "false",
                "preserves_panelA_rescue": "true" if row["panelA_rescue"] and gap > 0.0 else "false",
                "suppresses_S5_break": "true" if row["S5_break"] and gap > 0.0 else "false",
                "preserves_S5_rescue": "true" if row["S5_rescue"] and gap > 0.0 else "false",
            }
        )
    total = len(pair_rows)
    ci_low, ci_high = wilson_ci(prefer, total)
    return (
        {
            "score_family": score_name,
            "n_pairs": total,
            "truth_better_preference_count": prefer,
            "truth_better_preference_rate": prefer / total if total else 0.0,
            "truth_preference_95ci_low": ci_low,
            "truth_preference_95ci_high": ci_high,
            "rescues": rescues,
            "breaks": breaks,
            "net": rescues - breaks,
            "applied_count": applied,
            "current_scorer_correct_count": current_correct,
            "current_scorer_misrank_count": current_wrong,
            "truth_preference_when_current_correct": correct_pref / current_correct if current_correct else 0.0,
            "truth_preference_when_current_wrong": wrong_pref / current_wrong if current_wrong else 0.0,
            "correlation_with_current_score_margin": pearson(gaps, current_gaps),
            "correlation_with_panelA_margin": pearson(gaps, panel_a_gaps),
            "correlation_with_S5_margin": pearson(gaps, s5_gaps),
            "mean_gap": mean(gaps),
            "median_gap": median(gaps),
            "gap_q05": percentile(gaps, 5),
            "gap_q25": percentile(gaps, 25),
            "gap_q75": percentile(gaps, 75),
            "gap_q95": percentile(gaps, 95),
        },
        details,
    )


def margin_sweep(pair_rows: list[dict[str, Any]], score_name: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    misranks = sum(1 for row in pair_rows if not row["current_scorer_correct"])
    for threshold in MARGIN_THRESHOLDS:
        summary, _ = evaluate_pairs(pair_rows, score_name, threshold=threshold)
        applied = int(summary["applied_count"])
        rescues = int(summary["rescues"])
        out.append(
            {
                "score_family": score_name,
                "threshold": threshold,
                "override_count": applied,
                "rescues": rescues,
                "breaks": summary["breaks"],
                "net": summary["net"],
                "precision_of_overrides": rescues / applied if applied else 0.0,
                "recall_of_misranks": rescues / misranks if misranks else 0.0,
            }
        )
    return out


def rescue_break_audit(pair_rows: list[dict[str, Any]], score_names: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for span_name, rescue_field, break_field in (("PanelA", "panelA_rescue", "panelA_break"), ("S5", "S5_rescue", "S5_break")):
        rescue_rows = [row for row in pair_rows if row[rescue_field]]
        break_rows = [row for row in pair_rows if row[break_field]]
        for score_name in score_names:
            gap_field = f"{score_name}_gap"
            out.append(
                {
                    "span_signal": span_name,
                    "coherence_score": score_name,
                    "span_rescue_count": len(rescue_rows),
                    "span_break_count": len(break_rows),
                    "span_rescues_preserved_by_positive_coherence": sum(1 for row in rescue_rows if as_float(row.get(gap_field)) > 0),
                    "span_breaks_suppressed_by_positive_coherence": sum(1 for row in break_rows if as_float(row.get(gap_field)) > 0),
                    "span_breaks_reinforced_by_negative_coherence": sum(1 for row in break_rows if as_float(row.get(gap_field)) < 0),
                    "mean_coherence_gap_on_span_rescues": mean(as_float(row.get(gap_field)) for row in rescue_rows),
                    "mean_coherence_gap_on_span_breaks": mean(as_float(row.get(gap_field)) for row in break_rows),
                }
            )
    return out


def top_rows(details: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    rows = [row for row in details if row.get(field) == "true"]
    rows.sort(key=lambda row: abs(as_float(row.get("score_gap"))), reverse=True)
    return rows[:TOP_N]


def write_readout(score_summary: list[dict[str, Any]], audit_rows: list[dict[str, Any]], elapsed_s: float) -> None:
    ranked = sorted(score_summary, key=lambda row: (as_float(row["net"]), as_float(row["truth_better_preference_rate"])), reverse=True)
    best = ranked[0] if ranked else {}
    c1 = next((row for row in score_summary if row["score_family"] == "C1_char_ngram_coherence"), {})
    c6 = next((row for row in score_summary if row["score_family"] == "C6_S5_plus_coherence"), {})
    panel_audit = [row for row in audit_rows if row["span_signal"] == "PanelA" and row["coherence_score"] == "coherence_composite"]
    s5_audit = [row for row in audit_rows if row["span_signal"] == "S5" and row["coherence_score"] == "coherence_composite"]
    lines = [
        "# PhaseB Order/Phrase/Ngram Coherence Hard-Pair Report v1",
        "",
        f"Created UTC: {datetime.now(timezone.utc).isoformat()}",
        f"Elapsed seconds: {elapsed_s:.1f}",
        "",
        "## Scope",
        "",
        "- Report-only coherence analysis over the existing 2594 hard pairs.",
        "- Uses existing candidate text renderings and fixed span-Hamming carry-forward columns.",
        "- No calibration/data-taking run was launched.",
        "- No production scorer weights, defaults, or ranking policy were changed.",
        "",
        "## Main Answers",
        "",
        f"- Best report-only family by net then truth preference: {best.get('score_family', '')}, truth preference {as_float(best.get('truth_better_preference_rate')):.3f}, rescues {best.get('rescues', '')}, breaks {best.get('breaks', '')}, net {best.get('net', '')}.",
        f"- C1 char-ngram coherence: truth preference {as_float(c1.get('truth_better_preference_rate')):.3f}, rescues {c1.get('rescues', '')}, breaks {c1.get('breaks', '')}, net {c1.get('net', '')}.",
        f"- C6 S5 plus coherence: truth preference {as_float(c6.get('truth_better_preference_rate')):.3f}, rescues {c6.get('rescues', '')}, breaks {c6.get('breaks', '')}, net {c6.get('net', '')}.",
    ]
    if panel_audit:
        row = panel_audit[0]
        lines.append(
            f"- Coherence on Panel A cases: preserves {row['span_rescues_preserved_by_positive_coherence']} / {row['span_rescue_count']} rescues and suppresses {row['span_breaks_suppressed_by_positive_coherence']} / {row['span_break_count']} breaks."
        )
    if s5_audit:
        row = s5_audit[0]
        lines.append(
            f"- Coherence on S5 cases: preserves {row['span_rescues_preserved_by_positive_coherence']} / {row['span_rescue_count']} rescues and suppresses {row['span_breaks_suppressed_by_positive_coherence']} / {row['span_break_count']} breaks."
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- This v1 uses simple auditable character/phrase/repetition proxies, not a trained language model.",
            "- Positive coherence gap means the feature prefers the truth-better candidate.",
            "- Suppressed span-Hamming breaks are cases where span-Hamming preferred the truth-worse candidate but coherence prefers truth-better.",
            "- Preserved span-Hamming rescues are cases where both span-Hamming and coherence prefer truth-better.",
            "",
            "## Files",
            "",
            "- pairwise_coherence_feature_rows.csv.gz",
            "- candidate_coherence_summary.csv",
            "- score_family_pairwise_summary.csv",
            "- score_family_margin_sweep.csv",
            "- pairwise_score_gaps.csv.gz",
            "- coherence_vs_span_hamming_rescue_break_summary.csv",
            "- top_coherence_rescues.csv",
            "- top_coherence_breaks.csv",
            "- span_hamming_breaks_suppressed_by_coherence.csv",
            "- span_hamming_rescues_preserved_by_coherence.csv",
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
        "feature_definition_manifest.json",
        "candidate_coherence_summary.csv",
        "pairwise_coherence_feature_rows.csv.gz",
        "score_family_pairwise_summary.csv",
        "score_family_margin_sweep.csv",
        "pairwise_score_gaps.csv.gz",
        "coherence_vs_span_hamming_rescue_break_summary.csv",
        "top_coherence_rescues.csv",
        "top_coherence_breaks.csv",
        "span_hamming_breaks_suppressed_by_coherence.csv",
        "span_hamming_rescues_preserved_by_coherence.csv",
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
        "candidate_full_texts": MANUAL_DIR / "candidate_full_texts.jsonl.gz",
        "hard_pair_pairwise": HARD_PAIR_DIR / "pairwise_road_test_summary.csv",
        "multiscore_candidate_summary": MULTISCORE_DIR / "candidate_multiscore_summary.csv",
        "multiscore_pairwise_gaps": MULTISCORE_DIR / "pairwise_score_gaps.csv.gz",
        "hard_pair_candidate_features": HARD_PAIR_DIR / "candidate_feature_rows.csv.gz",
    }
    missing = [f"{name}: {rel(path)}" for name, path in required_paths.items() if not path.exists()]
    if missing:
        write_json(OUTPUT_DIR / "input_manifest.json", {"missing": missing})
        raise FileNotFoundError(f"missing required inputs: {missing}")

    write_json(
        OUTPUT_DIR / "config.json",
        {
            "run_label": RUN_LABEL,
            "report_only": True,
            "hard_pair_input_dir": rel(HARD_PAIR_DIR),
            "manual_inspection_input_dir": rel(MANUAL_DIR),
            "multiscore_input_dir": rel(MULTISCORE_DIR),
            "output_dir": rel(OUTPUT_DIR),
            "uncertain_current_margin": UNCERTAIN_CURRENT_MARGIN,
            "conservative_combined_margin": CONSERVATIVE_COMBINED_MARGIN,
            "scorer_policy": "report-only; no production weights/defaults/ranking changes",
        },
    )
    write_json(
        OUTPUT_DIR / "feature_definition_manifest.json",
        {
            "feature_families": {
                "C1_char_ngram_coherence": "z-scored common char 3/4/5-gram hit rates minus bad-bigram rate",
                "C2_phrase_or_ngram_coherence_if_available": "z-scored common phraselet density plus transition/vowel-balance support",
                "C3_repetition_penalty": "negative z-scored repeated 3/4-gram and max-run features",
                "coherence_composite": "0.45*C1 + 0.35*C2 + 0.20*C3",
                "C5_span_A_plus_coherence": "z(Panel A) + 0.5*coherence_composite",
                "C6_S5_plus_coherence": "z(S5) + 0.5*coherence_composite",
                "C7_len7_hd2_exact_support_plus_coherence": "z(normal length7 HD2 exact span-Hamming support) + 0.5*coherence_composite",
            },
            "common_trigrams": COMMON_TRIGRAMS,
            "common_quadgrams": COMMON_QUADGRAMS,
            "common_fivegrams": COMMON_FIVEGRAMS,
            "common_phraselets": COMMON_PHRASELETS,
            "bad_bigrams": BAD_BIGRAMS,
        },
    )

    candidate_texts = load_candidate_texts()
    multiscore_rows = read_csv_rows(MULTISCORE_DIR / "candidate_multiscore_summary.csv")
    pairwise_rows = read_csv_rows(HARD_PAIR_DIR / "pairwise_road_test_summary.csv")
    len7_scores = load_len7_hd2_exact_support()
    candidate_rows = build_candidate_rows(candidate_texts, multiscore_rows, len7_scores)
    maps = score_maps(candidate_rows)
    span_gaps = load_multiscore_gaps()
    pair_rows = build_pair_rows(pairwise_rows, maps, span_gaps)

    write_json(
        OUTPUT_DIR / "input_manifest.json",
        {
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "inputs": {name: {"path": rel(path), "exists": path.exists(), "bytes": path.stat().st_size if path.exists() else 0} for name, path in required_paths.items()},
            "candidate_count": len(candidate_rows),
            "pair_count": len(pair_rows),
            "missing": missing,
        },
    )

    pair_feature_fields = [
        "pair_id",
        "truth_better_candidate_id",
        "truth_worse_candidate_id",
        "current_score_gap",
        "current_scorer_correct",
        "panelA_gap",
        "S5_gap",
        "panelA_rescue",
        "panelA_break",
        "S5_rescue",
        "S5_break",
        "panelA_threshold_0_4_support",
        "S7_margin_0_01_support",
        "S8_margin_0_25_support",
        "C1_char_ngram_coherence_gap",
        "C2_phrase_or_ngram_coherence_if_available_gap",
        "C3_repetition_penalty_gap",
        "coherence_composite_gap",
        "C5_span_A_plus_coherence_gap",
        "C6_S5_plus_coherence_gap",
        "C7_len7_hd2_exact_support_plus_coherence_gap",
    ]
    write_csv_gz(OUTPUT_DIR / "pairwise_coherence_feature_rows.csv.gz", pair_rows, pair_feature_fields)
    candidate_fields = [
        "candidate_id",
        "label",
        "current_score",
        "truth_match_ratio",
        "token_count",
        "latin_length",
        "common_trigram_rate",
        "common_quadgram_rate",
        "common_fivegram_rate",
        "phraselet_density",
        "repeated_3gram_rate",
        "repeated_4gram_rate",
        "bad_bigram_rate",
        "max_run_fraction",
        "transition_entropy",
        "vowel_balance_score",
        "panelA",
        "S5_local_null_positive_selected",
        "len7_hd2_exact_support",
        "C1_char_ngram_coherence",
        "C2_phrase_or_ngram_coherence_if_available",
        "C3_repetition_penalty",
        "coherence_composite",
        "C5_span_A_plus_coherence",
        "C6_S5_plus_coherence",
        "C7_len7_hd2_exact_support_plus_coherence",
    ]
    write_csv(OUTPUT_DIR / "candidate_coherence_summary.csv", candidate_rows, candidate_fields)

    score_plan = {
        "C0_current_score_baseline": {"source": "current_score_gap", "special": "current"},
        "C1_char_ngram_coherence": {"source": "C1_char_ngram_coherence"},
        "C2_phrase_or_ngram_coherence_if_available": {"source": "C2_phrase_or_ngram_coherence_if_available"},
        "C3_repetition_penalty": {"source": "C3_repetition_penalty"},
        "C4_current_plus_coherence_margin_support": {"source": "coherence_composite", "current_margin_gate": UNCERTAIN_CURRENT_MARGIN},
        "C5_span_A_plus_coherence": {"source": "C5_span_A_plus_coherence"},
        "C6_S5_plus_coherence": {"source": "C6_S5_plus_coherence"},
        "C7_len7_hd2_exact_support_plus_coherence": {"source": "C7_len7_hd2_exact_support_plus_coherence"},
        "C8_span_plus_coherence_conservative": {"source": "coherence_composite", "threshold": CONSERVATIVE_COMBINED_MARGIN, "combined_positive_gate": True},
    }
    score_summary: list[dict[str, Any]] = []
    pair_gap_rows: list[dict[str, Any]] = []
    for family, spec in score_plan.items():
        source = str(spec["source"])
        if spec.get("special") == "current":
            for row in pair_rows:
                row["C0_current_score_baseline_gap"] = row["current_score_gap"]
            source = "C0_current_score_baseline"
        kwargs = {
            "threshold": as_float(spec.get("threshold")),
            "current_margin_gate": spec.get("current_margin_gate"),
            "combined_positive_gate": bool(spec.get("combined_positive_gate", False)),
        }
        summary, details = evaluate_pairs(pair_rows, source, **kwargs)
        summary["score_family"] = family
        for detail in details:
            detail["score_family"] = family
        score_summary.append(summary)
        pair_gap_rows.extend(details)

    summary_fields = [
        "score_family",
        "n_pairs",
        "truth_better_preference_count",
        "truth_better_preference_rate",
        "truth_preference_95ci_low",
        "truth_preference_95ci_high",
        "rescues",
        "breaks",
        "net",
        "applied_count",
        "current_scorer_correct_count",
        "current_scorer_misrank_count",
        "truth_preference_when_current_correct",
        "truth_preference_when_current_wrong",
        "correlation_with_current_score_margin",
        "correlation_with_panelA_margin",
        "correlation_with_S5_margin",
        "mean_gap",
        "median_gap",
        "gap_q05",
        "gap_q25",
        "gap_q75",
        "gap_q95",
    ]
    write_csv(OUTPUT_DIR / "score_family_pairwise_summary.csv", score_summary, summary_fields)
    gap_fields = [
        "score_family",
        "pair_id",
        "truth_better_candidate_id",
        "truth_worse_candidate_id",
        "score_gap",
        "score_applies",
        "score_prefers_truth_better",
        "current_scorer_correct",
        "current_score_gap",
        "panelA_gap",
        "S5_gap",
        "rescues_current_misrank",
        "breaks_current_correct",
        "suppresses_panelA_break",
        "preserves_panelA_rescue",
        "suppresses_S5_break",
        "preserves_S5_rescue",
    ]
    write_csv_gz(OUTPUT_DIR / "pairwise_score_gaps.csv.gz", pair_gap_rows, gap_fields)

    sweep_rows: list[dict[str, Any]] = []
    for name in ("C1_char_ngram_coherence", "C2_phrase_or_ngram_coherence_if_available", "C3_repetition_penalty", "coherence_composite", "C5_span_A_plus_coherence", "C6_S5_plus_coherence", "C7_len7_hd2_exact_support_plus_coherence"):
        sweep_rows.extend(margin_sweep(pair_rows, name))
    write_csv(OUTPUT_DIR / "score_family_margin_sweep.csv", sweep_rows, ["score_family", "threshold", "override_count", "rescues", "breaks", "net", "precision_of_overrides", "recall_of_misranks"])

    audit_rows = rescue_break_audit(pair_rows, ["C1_char_ngram_coherence", "C2_phrase_or_ngram_coherence_if_available", "C3_repetition_penalty", "coherence_composite", "C6_S5_plus_coherence"])
    audit_fields = [
        "span_signal",
        "coherence_score",
        "span_rescue_count",
        "span_break_count",
        "span_rescues_preserved_by_positive_coherence",
        "span_breaks_suppressed_by_positive_coherence",
        "span_breaks_reinforced_by_negative_coherence",
        "mean_coherence_gap_on_span_rescues",
        "mean_coherence_gap_on_span_breaks",
    ]
    write_csv(OUTPUT_DIR / "coherence_vs_span_hamming_rescue_break_summary.csv", audit_rows, audit_fields)

    write_csv(OUTPUT_DIR / "top_coherence_rescues.csv", top_rows(pair_gap_rows, "rescues_current_misrank"), gap_fields)
    write_csv(OUTPUT_DIR / "top_coherence_breaks.csv", top_rows(pair_gap_rows, "breaks_current_correct"), gap_fields)
    write_csv(OUTPUT_DIR / "span_hamming_breaks_suppressed_by_coherence.csv", top_rows(pair_gap_rows, "suppresses_S5_break"), gap_fields)
    write_csv(OUTPUT_DIR / "span_hamming_rescues_preserved_by_coherence.csv", top_rows(pair_gap_rows, "preserves_S5_rescue"), gap_fields)

    elapsed_s = time.perf_counter() - start
    write_readout(score_summary, audit_rows, elapsed_s)
    copy_review_pack()

    print(f"[{RUN_LABEL}] complete candidates={len(candidate_rows)} pairs={len(pair_rows)} elapsed={elapsed_s:.1f}s")
    print(f"[{RUN_LABEL}] output_dir={rel(OUTPUT_DIR)}")
    print(f"[{RUN_LABEL}] review_pack={rel(REVIEW_PACK_ZIP)}")


if __name__ == "__main__":
    main()
