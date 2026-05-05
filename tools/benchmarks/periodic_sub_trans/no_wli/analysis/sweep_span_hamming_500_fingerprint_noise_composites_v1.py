from __future__ import annotations

"""
Report-only sweep combining uncapped length/HD fingerprints with short-noise features.

This does not rescore text. It joins saved fixed-500 candidate rows by
token_hash/chunk_kind, standardizes feature columns per chunk, and evaluates
simple higher-is-better composite rules.
"""

import csv
import json
import math
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any, Callable, Iterable, Mapping, Sequence


RUN_LABEL = "span_hamming_500_fingerprint_noise_composites_v1"

PAIR_ROWS_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "historical_pairwise_rescore_v1/historical_pairwise_rescore_pairs.csv"
)
NORMALIZED_FEATURES_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "span_hamming_500_normalized_full_v1/span_hamming_500_normalized_candidate_features.csv"
)
FINGERPRINT_FEATURES_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "span_hamming_500_length_hd_fingerprint_full_v1/"
    "span_hamming_500_length_hd_fingerprint_candidate_features.csv"
)
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "span_hamming_500_fingerprint_noise_composites_v1"
)

NORMALIZED_CONFIG_ID = "strict_selected_len3_14_hd2_cap256_norm500"
FINGERPRINT_CONFIG_ID = "strict_selected_len6_10_hd_len_minus3_cap100000_norm500"
CHUNK_KINDS = ("prefix", "middle", "suffix")
AGGREGATORS = ("prefix", "middle", "suffix", "mean", "median", "max", "min", "vote_2_of_3")
LAMBDA_VALUES = (0.25, 0.5, 0.75, 1.0, 1.5, 2.0)


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError("Could not locate repo root from script path")


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

PAIR_ROWS = REPO_ROOT / PAIR_ROWS_REL
NORMALIZED_FEATURES = REPO_ROOT / NORMALIZED_FEATURES_REL
FINGERPRINT_FEATURES = REPO_ROOT / FINGERPRINT_FEATURES_REL
OUTPUT_DIR = REPO_ROOT / OUTPUT_DIR_REL


@dataclass(frozen=True)
class RuleSpec:
    rule_id: str
    family: str
    lambda_value: float
    formula: Callable[[Mapping[str, float]], float]


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _write_csv(path: Path, rows: Iterable[Mapping[str, Any]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _safe_float(value: object) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(out):
        return 0.0
    return out


def _zscore_maps(rows: Sequence[Mapping[str, Any]], feature_names: Sequence[str]) -> dict[tuple[str, str], float]:
    out: dict[tuple[str, str], float] = {}
    for chunk in CHUNK_KINDS:
        chunk_rows = [row for row in rows if str(row.get("chunk_kind")) == chunk]
        for feature in feature_names:
            values = [_safe_float(row.get(feature)) for row in chunk_rows]
            if not values:
                continue
            mean_value = sum(values) / float(len(values))
            variance = sum((value - mean_value) ** 2 for value in values) / float(max(1, len(values)))
            stdev = math.sqrt(variance)
            if stdev <= 1e-12:
                stdev = 1.0
            out[(chunk, feature, "mean")] = mean_value
            out[(chunk, feature, "stdev")] = stdev
    return out


def _joined_rows(normalized_rows: Sequence[Mapping[str, str]], fingerprint_rows: Sequence[Mapping[str, str]]) -> list[dict[str, Any]]:
    norm_by_key = {
        (str(row["token_hash"]), str(row["chunk_kind"])): row
        for row in normalized_rows
        if str(row.get("config_id")) == NORMALIZED_CONFIG_ID
    }
    out: list[dict[str, Any]] = []
    for fp in fingerprint_rows:
        if str(fp.get("config_id")) != FINGERPRINT_CONFIG_ID:
            continue
        key = (str(fp["token_hash"]), str(fp["chunk_kind"]))
        norm = norm_by_key.get(key)
        if norm is None:
            continue
        row: dict[str, Any] = {
            "token_hash": fp["token_hash"],
            "chunk_kind": fp["chunk_kind"],
            "sample_id": fp.get("sample_id", ""),
            "fp_selected_exact": _safe_float(fp.get("selected_fingerprint_exact_count_norm")),
            "fp_selected_close20": _safe_float(fp.get("selected_fingerprint_close20_count_norm")),
            "fp_selected_mean_error": _safe_float(fp.get("selected_fingerprint_mean_error_rate")),
            "fp_raw_exact": _safe_float(fp.get("raw_fingerprint_exact_count_norm")),
            "fp_raw_close20": _safe_float(fp.get("raw_fingerprint_close20_count_norm")),
            "fp_raw_mean_error": _safe_float(fp.get("raw_fingerprint_mean_error_rate")),
            "fp_selected_len6_exact": _safe_float(fp.get("selected_len6_hd0_count_norm")),
            "fp_raw_len6_exact": _safe_float(fp.get("raw_len6_hd0_count_norm")),
            "fp_selected_len8_close": _safe_float(fp.get("selected_len8_hd_le3_count_norm")),
            "fp_raw_len8_close": _safe_float(fp.get("raw_len8_hd_le3_count_norm")),
            "noise_short": _safe_float(norm.get("short_fuzzy_noise_len_le_4_norm")),
            "noise_short_count": _safe_float(norm.get("short_fuzzy_interval_count_norm")),
            "span_err20": _safe_float(norm.get("err20_len_ge_5_norm")),
            "span_exact5": _safe_float(norm.get("exact_len_ge_5_norm")),
        }
        out.append(row)
    z_features = [
        "fp_selected_exact",
        "fp_selected_close20",
        "fp_selected_mean_error",
        "fp_raw_exact",
        "fp_raw_close20",
        "fp_raw_mean_error",
        "fp_selected_len6_exact",
        "fp_raw_len6_exact",
        "fp_selected_len8_close",
        "fp_raw_len8_close",
        "noise_short",
        "noise_short_count",
        "span_err20",
        "span_exact5",
    ]
    zstats = _zscore_maps(out, z_features)
    for row in out:
        chunk = str(row["chunk_kind"])
        for feature in z_features:
            mean_value = zstats.get((chunk, feature, "mean"), 0.0)
            stdev = zstats.get((chunk, feature, "stdev"), 1.0)
            row[f"z_{feature}"] = (_safe_float(row.get(feature)) - mean_value) / stdev
    return out


def _rules() -> list[RuleSpec]:
    rules: list[RuleSpec] = []
    for lam in LAMBDA_VALUES:
        suffix = str(lam).replace(".", "p")
        rules.extend(
            [
                RuleSpec(
                    f"selected_exact_minus_noise_lam{suffix}",
                    "fp_exact_noise",
                    lam,
                    lambda f, lam=lam: f["z_fp_selected_exact"] - lam * f["z_noise_short"],
                ),
                RuleSpec(
                    f"selected_close_minus_noise_lam{suffix}",
                    "fp_close_noise",
                    lam,
                    lambda f, lam=lam: f["z_fp_selected_close20"] - lam * f["z_noise_short"],
                ),
                RuleSpec(
                    f"selected_clean_exact_minus_noise_lam{suffix}",
                    "fp_exact_error_noise",
                    lam,
                    lambda f, lam=lam: f["z_fp_selected_exact"] - f["z_fp_selected_mean_error"] - lam * f["z_noise_short"],
                ),
                RuleSpec(
                    f"selected_exact_span_minus_noise_lam{suffix}",
                    "fp_exact_span_noise",
                    lam,
                    lambda f, lam=lam: f["z_fp_selected_exact"] + f["z_span_err20"] + f["z_span_exact5"] - lam * f["z_noise_short"],
                ),
                RuleSpec(
                    f"raw_len6_exact_span_minus_noise_lam{suffix}",
                    "raw_len6_span_noise",
                    lam,
                    lambda f, lam=lam: f["z_fp_raw_len6_exact"] + f["z_span_err20"] - lam * f["z_noise_short"],
                ),
                RuleSpec(
                    f"raw_len8_close_span_minus_noise_lam{suffix}",
                    "raw_len8_span_noise",
                    lam,
                    lambda f, lam=lam: f["z_fp_raw_len8_close"] + f["z_span_err20"] - lam * f["z_noise_short"],
                ),
                RuleSpec(
                    f"span_exact5_err20_minus_noise_lam{suffix}",
                    "span_only_noise_control",
                    lam,
                    lambda f, lam=lam: f["z_span_err20"] + f["z_span_exact5"] - lam * f["z_noise_short"],
                ),
                RuleSpec(
                    f"span_exact5_err20_minus_short_count_lam{suffix}",
                    "span_only_count_control",
                    lam,
                    lambda f, lam=lam: f["z_span_err20"] + f["z_span_exact5"] - lam * f["z_noise_short_count"],
                ),
            ]
        )
    return rules


def _aggregate(values: Mapping[str, float], aggregator: str) -> float:
    vals = [float(values[k]) for k in CHUNK_KINDS if k in values]
    if not vals:
        return 0.0
    if aggregator in CHUNK_KINDS:
        return float(values.get(aggregator, 0.0))
    if aggregator == "mean":
        return sum(vals) / float(len(vals))
    if aggregator == "median":
        return float(median(vals))
    if aggregator == "max":
        return max(vals)
    if aggregator == "min":
        return min(vals)
    raise ValueError(f"unsupported numeric aggregator: {aggregator}")


def _preference(winner: float, challenger: float) -> str:
    if abs(winner - challenger) <= 1e-12:
        return "tie"
    return "truth_better" if winner > challenger else "truth_worse"


def _vote_preference(winner_values: Mapping[str, float], challenger_values: Mapping[str, float]) -> str:
    counts = {"truth_better": 0, "truth_worse": 0, "tie": 0}
    for chunk in CHUNK_KINDS:
        counts[_preference(float(winner_values.get(chunk, 0.0)), float(challenger_values.get(chunk, 0.0)))] += 1
    if counts["truth_better"] >= 2 and counts["truth_better"] > counts["truth_worse"]:
        return "truth_better"
    if counts["truth_worse"] >= 2 and counts["truth_worse"] > counts["truth_better"]:
        return "truth_worse"
    return "tie"


def _evaluate_rule(
    *,
    pair_rows: Sequence[Mapping[str, str]],
    scores_by_key: Mapping[tuple[str, str], dict[str, float]],
    rule_id: str,
    family: str,
    lambda_value: float,
    aggregator: str,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "rule_id": rule_id,
        "family": family,
        "lambda_value": lambda_value,
        "aggregator": aggregator,
        "pair_count": 0,
        "available_pair_count": 0,
        "truth_better": 0,
        "truth_worse": 0,
        "tie": 0,
        "rescues": 0,
        "breaks": 0,
        "current_misranked_pair_count": 0,
        "current_correct_control_pair_count": 0,
    }
    for pair in pair_rows:
        winner_hash = str(pair.get("winner_token_hash", "")).strip()
        challenger_hash = str(pair.get("challenger_token_hash", "")).strip()
        winner_values = scores_by_key.get((rule_id, winner_hash))
        challenger_values = scores_by_key.get((rule_id, challenger_hash))
        if winner_values is None or challenger_values is None:
            continue
        if aggregator == "vote_2_of_3":
            pref = _vote_preference(winner_values, challenger_values)
        else:
            pref = _preference(_aggregate(winner_values, aggregator), _aggregate(challenger_values, aggregator))

        current_correct = str(pair.get("current_score_correct", "")).strip() == "1"
        row["pair_count"] += 1
        if pref == "tie":
            row["tie"] += 1
        else:
            row["available_pair_count"] += 1
            row[pref] += 1
        if current_correct:
            row["current_correct_control_pair_count"] += 1
            if pref == "truth_worse":
                row["breaks"] += 1
        else:
            row["current_misranked_pair_count"] += 1
            if pref == "truth_better":
                row["rescues"] += 1
    row["net"] = int(row["rescues"]) - int(row["breaks"])
    return row


def _fixture_family(row: Mapping[str, str]) -> str:
    seed = str(row.get("fixture_seed") or "").strip()
    if seed.startswith("7"):
        return "seed_7000s"
    if seed.endswith("11"):
        return "seed_x11"
    if seed:
        return f"seed_{seed}"
    return "seed_missing"


def _split_predicates() -> list[tuple[str, Callable[[Mapping[str, str]], bool]]]:
    return [
        ("fixture_seed_even", lambda p: int(str(p.get("fixture_seed") or "0") or 0) % 2 == 0),
        ("fixture_seed_odd", lambda p: int(str(p.get("fixture_seed") or "0") or 0) % 2 == 1),
        ("current_score_margin_abs_lt_0p01", lambda p: abs(_safe_float(p.get("current_score_margin"))) < 0.01),
        ("current_score_margin_abs_ge_0p01", lambda p: abs(_safe_float(p.get("current_score_margin"))) >= 0.01),
        ("fixture_family_seed_7000s", lambda p: _fixture_family(p) == "seed_7000s"),
        ("fixture_family_seed_x11", lambda p: _fixture_family(p) == "seed_x11"),
    ]


def _split_validation(
    *,
    pair_rows: Sequence[Mapping[str, str]],
    summary_rows: Sequence[Mapping[str, Any]],
    scores_by_key: Mapping[tuple[str, str], dict[str, float]],
) -> list[dict[str, Any]]:
    top = sorted(summary_rows, key=lambda item: (int(item["net"]), int(item["rescues"])), reverse=True)[:20]
    out: list[dict[str, Any]] = []
    for summary in top:
        rule_id = str(summary["rule_id"])
        family = str(summary["family"])
        lambda_value = _safe_float(summary["lambda_value"])
        aggregator = str(summary["aggregator"])
        for split_name, predicate in _split_predicates():
            rows = [row for row in pair_rows if predicate(row)]
            if not rows:
                continue
            split_row = _evaluate_rule(
                pair_rows=rows,
                scores_by_key=scores_by_key,
                rule_id=rule_id,
                family=family,
                lambda_value=lambda_value,
                aggregator=aggregator,
            )
            split_row["split_name"] = split_name
            split_row["parent_net"] = summary["net"]
            out.append(split_row)
        seeds = sorted({str(row.get("fixture_seed") or "") for row in pair_rows if str(row.get("fixture_seed") or "")})
        for seed in seeds:
            rows = [row for row in pair_rows if str(row.get("fixture_seed") or "") == seed]
            seed_row = _evaluate_rule(
                pair_rows=rows,
                scores_by_key=scores_by_key,
                rule_id=rule_id,
                family=family,
                lambda_value=lambda_value,
                aggregator=aggregator,
            )
            seed_row["split_name"] = f"fixture_seed_{seed}"
            seed_row["parent_net"] = summary["net"]
            out.append(seed_row)
    return out


def _build_readout(summary: Mapping[str, Any], rows: Sequence[Mapping[str, Any]], split_rows: Sequence[Mapping[str, Any]]) -> str:
    lines = [
        "# Span-Hamming 500 Fingerprint + Noise Composites v1",
        "",
        "## Status",
        "",
        "- Report-only; no runtime behaviour changed.",
        f"- joined candidate rows: `{summary['joined_candidate_row_count']}`",
        f"- rule summary rows: `{summary['rule_summary_row_count']}`",
        f"- split validation rows: `{summary['split_validation_row_count']}`",
        f"- elapsed seconds: `{float(summary['elapsed_seconds']):.2f}`",
        "",
        "## Top Rows",
        "",
        "| rule | agg | rescues | breaks | net |",
        "|---|---|---:|---:|---:|",
    ]
    for row in rows[:15]:
        lines.append(f"| {row['rule_id']} | {row['aggregator']} | {row['rescues']} | {row['breaks']} | {row['net']} |")
    if rows:
        top = rows[0]
        top_splits = [row for row in split_rows if row["rule_id"] == top["rule_id"] and row["aggregator"] == top["aggregator"]]
        lines.extend(["", "## Top Row Splits", "", "| split | rescues | breaks | net |", "|---|---:|---:|---:|"])
        for row in top_splits[:24]:
            lines.append(f"| {row['split_name']} | {row['rescues']} | {row['breaks']} | {row['net']} |")
    return "\n".join(lines) + "\n"


def run_sweep() -> dict[str, Any]:
    started = time.perf_counter()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    pair_rows = _read_csv(PAIR_ROWS)
    normalized_rows = _read_csv(NORMALIZED_FEATURES)
    fingerprint_rows = _read_csv(FINGERPRINT_FEATURES)
    joined_rows = _joined_rows(normalized_rows, fingerprint_rows)
    rules = _rules()

    scores_by_key: dict[tuple[str, str], dict[str, float]] = {}
    for row in joined_rows:
        token_hash = str(row["token_hash"])
        chunk = str(row["chunk_kind"])
        for rule in rules:
            scores_by_key.setdefault((rule.rule_id, token_hash), {})[chunk] = float(rule.formula(row))

    summary_rows: list[dict[str, Any]] = []
    total = len(rules) * len(AGGREGATORS)
    done = 0
    for rule in rules:
        for aggregator in AGGREGATORS:
            summary_rows.append(
                _evaluate_rule(
                    pair_rows=pair_rows,
                    scores_by_key=scores_by_key,
                    rule_id=rule.rule_id,
                    family=rule.family,
                    lambda_value=rule.lambda_value,
                    aggregator=aggregator,
                )
            )
            done += 1
            if done == 1 or done % 50 == 0 or done == total:
                elapsed = time.perf_counter() - started
                print(
                    f"[span_hamming_500_fingerprint_noise_composites] progress {done}/{total} "
                    f"elapsed={elapsed:.1f}s",
                    flush=True,
                )

    summary_rows.sort(key=lambda item: (int(item["net"]), int(item["rescues"])), reverse=True)
    split_rows = _split_validation(pair_rows=pair_rows, summary_rows=summary_rows, scores_by_key=scores_by_key)
    split_rows.sort(key=lambda item: (str(item["rule_id"]), str(item["aggregator"]), str(item["split_name"])))

    summary_csv = OUTPUT_DIR / "span_hamming_500_fingerprint_noise_composite_summary.csv"
    split_csv = OUTPUT_DIR / "span_hamming_500_fingerprint_noise_composite_split_validation.csv"
    joined_csv = OUTPUT_DIR / "span_hamming_500_fingerprint_noise_joined_candidate_features.csv"
    summary_fields = [
        "rule_id",
        "family",
        "lambda_value",
        "aggregator",
        "pair_count",
        "available_pair_count",
        "truth_better",
        "truth_worse",
        "tie",
        "rescues",
        "breaks",
        "net",
        "current_misranked_pair_count",
        "current_correct_control_pair_count",
    ]
    split_fields = ["split_name", "parent_net", *summary_fields]
    joined_fields = list(joined_rows[0].keys()) if joined_rows else []
    _write_csv(summary_csv, summary_rows, summary_fields)
    _write_csv(split_csv, split_rows, split_fields)
    if joined_fields:
        _write_csv(joined_csv, joined_rows, joined_fields)

    summary = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "output_dir": _repo_rel(OUTPUT_DIR),
        "source_normalized_features": _repo_rel(NORMALIZED_FEATURES),
        "source_fingerprint_features": _repo_rel(FINGERPRINT_FEATURES),
        "normalized_config_id": NORMALIZED_CONFIG_ID,
        "fingerprint_config_id": FINGERPRINT_CONFIG_ID,
        "pair_row_count": len(pair_rows),
        "joined_candidate_row_count": len(joined_rows),
        "rule_count": len(rules),
        "aggregators": list(AGGREGATORS),
        "rule_summary_row_count": len(summary_rows),
        "split_validation_row_count": len(split_rows),
        "elapsed_seconds": time.perf_counter() - started,
        "summary_csv": _repo_rel(summary_csv),
        "split_validation_csv": _repo_rel(split_csv),
        "joined_features_csv": _repo_rel(joined_csv),
        "top_net_rows": summary_rows[:20],
        "caveats": [
            "report-only; no runtime solver behaviour changed",
            "feature values are z-scored per chunk before composite scoring",
            "split validation is diagnostic, not final holdout",
        ],
    }
    (OUTPUT_DIR / "span_hamming_500_fingerprint_noise_composite_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (OUTPUT_DIR / "span_hamming_500_fingerprint_noise_composite_readout.md").write_text(
        _build_readout(summary, summary_rows, split_rows),
        encoding="utf-8",
    )
    print(
        f"[span_hamming_500_fingerprint_noise_composites] done rows={len(summary_rows)} "
        f"elapsed={summary['elapsed_seconds']:.2f}s output={_repo_rel(OUTPUT_DIR)}",
        flush=True,
    )
    return summary


def main() -> None:
    run_sweep()


if __name__ == "__main__":
    main()
