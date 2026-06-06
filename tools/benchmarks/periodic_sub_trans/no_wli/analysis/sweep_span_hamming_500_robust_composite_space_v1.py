from __future__ import annotations

"""
Report-only robust sweep over saved fixed-500 z-scored fingerprint/noise features.

This is deliberately constrained: positive evidence terms are added with unit
weight; penalty terms are subtracted with a shared lambda. Rows are ranked by
diagnostic split robustness before headline net.
"""

import csv
import itertools
import json
import math
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any, Callable, Iterable, Mapping, Sequence


RUN_LABEL = "span_hamming_500_robust_composite_space_v1"

PAIR_ROWS_REL = (
    "assets/evaluation_corpora/failed_decryptions/historical_partial_solves_v1/source/historical_pairwise_rescore_v1/historical_pairwise_rescore_pairs.csv"
)
JOINED_FEATURES_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "span_hamming_500_fingerprint_noise_composites_v1/"
    "span_hamming_500_fingerprint_noise_joined_candidate_features.csv"
)
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "span_hamming_500_robust_composite_space_v1"
)

CHUNK_KINDS = ("prefix", "middle", "suffix")
AGGREGATORS = ("prefix", "middle", "suffix", "mean", "median", "max", "min", "vote_2_of_3")
POSITIVE_FEATURES = (
    "z_fp_selected_exact",
    "z_fp_selected_close20",
    "z_fp_raw_exact",
    "z_fp_raw_close20",
    "z_fp_selected_len6_exact",
    "z_fp_raw_len6_exact",
    "z_fp_selected_len8_close",
    "z_fp_raw_len8_close",
    "z_span_err20",
    "z_span_exact5",
)
PENALTY_FEATURES = (
    "z_noise_short",
    "z_noise_short_count",
    "z_fp_selected_mean_error",
    "z_fp_raw_mean_error",
)
POSITIVE_COMBO_SIZES = (1, 2, 3)
PENALTY_COMBO_SIZES = (0, 1, 2)
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
JOINED_FEATURES = REPO_ROOT / JOINED_FEATURES_REL
OUTPUT_DIR = REPO_ROOT / OUTPUT_DIR_REL


@dataclass(frozen=True)
class RuleSpec:
    rule_id: str
    positive_features: tuple[str, ...]
    penalty_features: tuple[str, ...]
    lambda_value: float


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


def _short_feature_name(name: str) -> str:
    out = name
    for prefix in ("z_fp_", "z_", "selected_", "raw_", "fingerprint_"):
        out = out.replace(prefix, "")
    return out.replace("_", "")


def build_rules() -> list[RuleSpec]:
    rules: list[RuleSpec] = []
    for pos_size in POSITIVE_COMBO_SIZES:
        for positives in itertools.combinations(POSITIVE_FEATURES, pos_size):
            for pen_size in PENALTY_COMBO_SIZES:
                for penalties in itertools.combinations(PENALTY_FEATURES, pen_size):
                    lambdas = (0.0,) if not penalties else LAMBDA_VALUES
                    for lambda_value in lambdas:
                        pos_id = "p_" + "_".join(_short_feature_name(name) for name in positives)
                        pen_id = "none" if not penalties else "n_" + "_".join(_short_feature_name(name) for name in penalties)
                        lam_id = str(lambda_value).replace(".", "p")
                        rules.append(
                            RuleSpec(
                                rule_id=f"{pos_id}__{pen_id}__lam{lam_id}",
                                positive_features=tuple(positives),
                                penalty_features=tuple(penalties),
                                lambda_value=float(lambda_value),
                            )
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


def _pair_eval(
    *,
    pair_rows: Sequence[Mapping[str, str]],
    token_scores: Mapping[str, dict[str, float]],
    aggregator: str,
) -> dict[str, int]:
    out = {
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
        winner_values = token_scores.get(winner_hash)
        challenger_values = token_scores.get(challenger_hash)
        if winner_values is None or challenger_values is None:
            continue
        if aggregator == "vote_2_of_3":
            pref = _vote_preference(winner_values, challenger_values)
        else:
            pref = _preference(_aggregate(winner_values, aggregator), _aggregate(challenger_values, aggregator))
        current_correct = str(pair.get("current_score_correct", "")).strip() == "1"
        out["pair_count"] += 1
        if pref == "tie":
            out["tie"] += 1
        else:
            out["available_pair_count"] += 1
            out[pref] += 1
        if current_correct:
            out["current_correct_control_pair_count"] += 1
            if pref == "truth_worse":
                out["breaks"] += 1
        else:
            out["current_misranked_pair_count"] += 1
            if pref == "truth_better":
                out["rescues"] += 1
    out["net"] = int(out["rescues"]) - int(out["breaks"])
    return out


def _split_predicates() -> list[tuple[str, Callable[[Mapping[str, str]], bool]]]:
    return [
        ("even", lambda p: int(str(p.get("fixture_seed") or "0") or 0) % 2 == 0),
        ("odd", lambda p: int(str(p.get("fixture_seed") or "0") or 0) % 2 == 1),
        ("seed_7000s", lambda p: str(p.get("fixture_seed") or "").startswith("7")),
        ("seed_x11", lambda p: str(p.get("fixture_seed") or "").endswith("11")),
        ("margin_lt_0p01", lambda p: abs(_safe_float(p.get("current_score_margin"))) < 0.01),
        ("margin_ge_0p01", lambda p: abs(_safe_float(p.get("current_score_margin"))) >= 0.01),
    ]


def _score_rule(joined_rows: Sequence[Mapping[str, str]], rule: RuleSpec) -> dict[str, dict[str, float]]:
    token_scores: dict[str, dict[str, float]] = {}
    for row in joined_rows:
        token_hash = str(row["token_hash"])
        chunk = str(row["chunk_kind"])
        positive = sum(_safe_float(row.get(feature)) for feature in rule.positive_features)
        penalty = sum(_safe_float(row.get(feature)) for feature in rule.penalty_features)
        token_scores.setdefault(token_hash, {})[chunk] = positive - rule.lambda_value * penalty
    return token_scores


def _row_for_eval(rule: RuleSpec, aggregator: str, overall: Mapping[str, int], split_evals: Mapping[str, Mapping[str, int]]) -> dict[str, Any]:
    split_nets = {name: int(values["net"]) for name, values in split_evals.items()}
    seed_nets = [split_nets[name] for name in ("even", "odd", "seed_7000s", "seed_x11")]
    margin_nets = [split_nets[name] for name in ("margin_lt_0p01", "margin_ge_0p01")]
    return {
        "rule_id": rule.rule_id,
        "aggregator": aggregator,
        "positive_features": ";".join(rule.positive_features),
        "penalty_features": ";".join(rule.penalty_features),
        "lambda_value": rule.lambda_value,
        **overall,
        "robust_min_seed_net": min(seed_nets),
        "robust_min_margin_net": min(margin_nets),
        "robust_min_key_split_net": min([*seed_nets, *margin_nets]),
        "even_net": split_nets["even"],
        "odd_net": split_nets["odd"],
        "seed_7000s_net": split_nets["seed_7000s"],
        "seed_x11_net": split_nets["seed_x11"],
        "margin_lt_0p01_net": split_nets["margin_lt_0p01"],
        "margin_ge_0p01_net": split_nets["margin_ge_0p01"],
    }


def _build_readout(summary: Mapping[str, Any], rows: Sequence[Mapping[str, Any]], robust_rows: Sequence[Mapping[str, Any]]) -> str:
    lines = [
        "# Span-Hamming 500 Robust Composite Space v1",
        "",
        "## Status",
        "",
        "- Report-only; no runtime behaviour changed.",
        f"- rule/aggregator rows: `{summary['row_count']}`",
        f"- elapsed seconds: `{float(summary['elapsed_seconds']):.2f}`",
        "",
        "## Top Headline Net",
        "",
        "| rule | agg | net | even | odd | min split |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in rows[:12]:
        lines.append(
            f"| {row['rule_id']} | {row['aggregator']} | {row['net']} | {row['even_net']} | "
            f"{row['odd_net']} | {row['robust_min_key_split_net']} |"
        )
    lines.extend(["", "## Top Robust Rows", "", "| rule | agg | net | even | odd | min split |", "|---|---|---:|---:|---:|---:|"])
    for row in robust_rows[:12]:
        lines.append(
            f"| {row['rule_id']} | {row['aggregator']} | {row['net']} | {row['even_net']} | "
            f"{row['odd_net']} | {row['robust_min_key_split_net']} |"
        )
    return "\n".join(lines) + "\n"


def run_sweep() -> dict[str, Any]:
    started = time.perf_counter()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pair_rows = _read_csv(PAIR_ROWS)
    joined_rows = _read_csv(JOINED_FEATURES)
    split_row_sets = [(name, [row for row in pair_rows if predicate(row)]) for name, predicate in _split_predicates()]
    rules = build_rules()

    rows: list[dict[str, Any]] = []
    total = len(rules) * len(AGGREGATORS)
    done = 0
    for rule in rules:
        token_scores = _score_rule(joined_rows, rule)
        for aggregator in AGGREGATORS:
            overall = _pair_eval(pair_rows=pair_rows, token_scores=token_scores, aggregator=aggregator)
            split_evals = {
                name: _pair_eval(pair_rows=split_rows, token_scores=token_scores, aggregator=aggregator)
                for name, split_rows in split_row_sets
            }
            rows.append(_row_for_eval(rule, aggregator, overall, split_evals))
            done += 1
            if done == 1 or done % 1000 == 0 or done == total:
                elapsed = time.perf_counter() - started
                print(
                    f"[span_hamming_500_robust_composite_space] progress {done}/{total} elapsed={elapsed:.1f}s",
                    flush=True,
                )

    headline_rows = sorted(rows, key=lambda item: (int(item["net"]), int(item["rescues"])), reverse=True)
    robust_rows = sorted(
        rows,
        key=lambda item: (
            int(item["robust_min_key_split_net"]),
            int(item["robust_min_seed_net"]),
            int(item["net"]),
            int(item["rescues"]),
        ),
        reverse=True,
    )

    fieldnames = [
        "rule_id",
        "aggregator",
        "positive_features",
        "penalty_features",
        "lambda_value",
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
        "robust_min_seed_net",
        "robust_min_margin_net",
        "robust_min_key_split_net",
        "even_net",
        "odd_net",
        "seed_7000s_net",
        "seed_x11_net",
        "margin_lt_0p01_net",
        "margin_ge_0p01_net",
    ]
    headline_csv = OUTPUT_DIR / "span_hamming_500_robust_composite_space_headline_sorted.csv"
    robust_csv = OUTPUT_DIR / "span_hamming_500_robust_composite_space_robust_sorted.csv"
    _write_csv(headline_csv, headline_rows, fieldnames)
    _write_csv(robust_csv, robust_rows, fieldnames)

    summary = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "output_dir": _repo_rel(OUTPUT_DIR),
        "source_joined_features": _repo_rel(JOINED_FEATURES),
        "pair_row_count": len(pair_rows),
        "joined_candidate_row_count": len(joined_rows),
        "rule_count": len(rules),
        "aggregators": list(AGGREGATORS),
        "row_count": len(rows),
        "elapsed_seconds": time.perf_counter() - started,
        "headline_sorted_csv": _repo_rel(headline_csv),
        "robust_sorted_csv": _repo_rel(robust_csv),
        "top_headline_rows": headline_rows[:20],
        "top_robust_rows": robust_rows[:20],
        "caveats": [
            "report-only; no runtime solver behaviour changed",
            "broad search over saved features; robust ranking is diagnostic, not final holdout",
            "positive terms use unit weights; penalties share one lambda",
        ],
    }
    (OUTPUT_DIR / "span_hamming_500_robust_composite_space_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (OUTPUT_DIR / "span_hamming_500_robust_composite_space_readout.md").write_text(
        _build_readout(summary, headline_rows, robust_rows),
        encoding="utf-8",
    )
    print(
        f"[span_hamming_500_robust_composite_space] done rows={len(rows)} "
        f"elapsed={summary['elapsed_seconds']:.2f}s output={_repo_rel(OUTPUT_DIR)}",
        flush=True,
    )
    return summary


def main() -> None:
    run_sweep()


if __name__ == "__main__":
    main()
