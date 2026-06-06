from __future__ import annotations

"""
Report-only Stage 2 composite-rule sweep over saved fixed-500 span features.

This does not rescore text. It combines features already written by
`span_hamming_500_normalized_full_v1` and evaluates pairwise rescue/break
behaviour for chunk-level and aggregate rules.
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


RUN_LABEL = "span_hamming_500_composite_rules_v1"

PAIR_ROWS_REL = (
    "assets/evaluation_corpora/failed_decryptions/historical_partial_solves_v1/source/historical_pairwise_rescore_v1/historical_pairwise_rescore_pairs.csv"
)
CANDIDATE_FEATURES_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "span_hamming_500_normalized_full_v1/span_hamming_500_normalized_candidate_features.csv"
)
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "span_hamming_500_composite_rules_v1"
)

CHUNK_KINDS = ("prefix", "middle", "suffix")
LAMBDA_VALUES = (0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0)
EPSILON_VALUES = (0.01, 0.03, 0.05, 0.10)
AGGREGATORS = ("prefix", "middle", "suffix", "mean", "median", "max", "min", "vote_2_of_3")


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
CANDIDATE_FEATURES = REPO_ROOT / CANDIDATE_FEATURES_REL
OUTPUT_DIR = REPO_ROOT / OUTPUT_DIR_REL


@dataclass(frozen=True)
class RuleSpec:
    rule_id: str
    formula_family: str
    lambda_value: float
    epsilon: float
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


def _feature_map(row: Mapping[str, str]) -> dict[str, float]:
    return {
        "err20": _safe_float(row.get("err20_len_ge_5_norm")),
        "weighted_err20": _safe_float(row.get("weighted_err20_gamma2_len_ge_5_norm")),
        "short_noise": _safe_float(row.get("short_fuzzy_noise_len_le_4_norm")),
        "short_count": _safe_float(row.get("short_fuzzy_interval_count_norm")),
        "exact5": _safe_float(row.get("exact_len_ge_5_norm")),
        "exact8": _safe_float(row.get("exact_len_ge_8_norm")),
        "interval_count": _safe_float(row.get("selected_interval_count_norm")),
        "cap_pruned": _safe_float(row.get("candidate_cap_pruned_rate")),
    }


def _rules() -> list[RuleSpec]:
    rules: list[RuleSpec] = []
    for lam in LAMBDA_VALUES:
        suffix = str(lam).replace(".", "p")
        rules.append(
            RuleSpec(
                rule_id=f"err20_minus_noise_lam{suffix}",
                formula_family="linear_err20_noise",
                lambda_value=lam,
                epsilon=0.0,
                formula=lambda f, lam=lam: f["err20"] - lam * f["short_noise"],
            )
        )
        rules.append(
            RuleSpec(
                rule_id=f"weighted_err20_minus_noise_lam{suffix}",
                formula_family="linear_weighted_err20_noise",
                lambda_value=lam,
                epsilon=0.0,
                formula=lambda f, lam=lam: f["weighted_err20"] - lam * f["short_noise"],
            )
        )
        rules.append(
            RuleSpec(
                rule_id=f"err20_exact5_minus_noise_lam{suffix}",
                formula_family="linear_err20_exact5_noise",
                lambda_value=lam,
                epsilon=0.0,
                formula=lambda f, lam=lam: f["err20"] + f["exact5"] - lam * f["short_noise"],
            )
        )
        rules.append(
            RuleSpec(
                rule_id=f"err20_minus_short_count_lam{suffix}",
                formula_family="linear_err20_short_count",
                lambda_value=lam,
                epsilon=0.0,
                formula=lambda f, lam=lam: f["err20"] - lam * f["short_count"],
            )
        )
    for eps in EPSILON_VALUES:
        suffix = str(eps).replace(".", "p")
        rules.append(
            RuleSpec(
                rule_id=f"err20_over_noise_eps{suffix}",
                formula_family="ratio_err20_noise",
                lambda_value=0.0,
                epsilon=eps,
                formula=lambda f, eps=eps: f["err20"] / (eps + f["short_noise"]),
            )
        )
        rules.append(
            RuleSpec(
                rule_id=f"weighted_err20_over_noise_eps{suffix}",
                formula_family="ratio_weighted_err20_noise",
                lambda_value=0.0,
                epsilon=eps,
                formula=lambda f, eps=eps: f["weighted_err20"] / (eps + f["short_noise"]),
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


def _evaluate_rule(
    *,
    pair_rows: Sequence[Mapping[str, str]],
    scores_by_key: Mapping[tuple[str, str, str], dict[str, float]],
    config_id: str,
    rule: RuleSpec,
    aggregator: str,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "config_id": config_id,
        "rule_id": rule.rule_id,
        "formula_family": rule.formula_family,
        "lambda_value": rule.lambda_value,
        "epsilon": rule.epsilon,
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
    rescue_pairs: set[str] = set()
    break_pairs: set[str] = set()

    for pair in pair_rows:
        winner_hash = str(pair.get("winner_token_hash", "")).strip()
        challenger_hash = str(pair.get("challenger_token_hash", "")).strip()
        winner_values = scores_by_key.get((config_id, rule.rule_id, winner_hash))
        challenger_values = scores_by_key.get((config_id, rule.rule_id, challenger_hash))
        if winner_values is None or challenger_values is None:
            continue
        if aggregator == "vote_2_of_3":
            pref = _vote_preference(winner_values, challenger_values)
        else:
            pref = _preference(_aggregate(winner_values, aggregator), _aggregate(challenger_values, aggregator))

        current_correct = str(pair.get("current_score_correct", "")).strip() == "1"
        pair_id = str(pair.get("pair_id", f"{winner_hash}|{challenger_hash}"))
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
                break_pairs.add(pair_id)
        else:
            row["current_misranked_pair_count"] += 1
            if pref == "truth_better":
                row["rescues"] += 1
                rescue_pairs.add(pair_id)

    row["net"] = int(row["rescues"]) - int(row["breaks"])
    row["unique_misranked_rescue_pair_count"] = len(rescue_pairs)
    row["unique_control_break_pair_count"] = len(break_pairs)
    return row


def _split_rows(pair_rows: Sequence[Mapping[str, str]], summary_rows: Sequence[Mapping[str, Any]], scores_by_key: Mapping[tuple[str, str, str], dict[str, float]]) -> list[dict[str, Any]]:
    top = sorted(summary_rows, key=lambda item: (int(item["net"]), int(item["rescues"])), reverse=True)[:20]
    out: list[dict[str, Any]] = []
    for summary in top:
        config_id = str(summary["config_id"])
        rule = next(r for r in _rules() if r.rule_id == summary["rule_id"])
        aggregator = str(summary["aggregator"])
        for split_name, predicate in (
            ("fixture_seed_even", lambda p: int(str(p.get("fixture_seed") or "0") or 0) % 2 == 0),
            ("fixture_seed_odd", lambda p: int(str(p.get("fixture_seed") or "0") or 0) % 2 == 1),
            ("current_score_margin_abs_lt_0p01", lambda p: abs(_safe_float(p.get("current_score_margin"))) < 0.01),
            ("current_score_margin_abs_ge_0p01", lambda p: abs(_safe_float(p.get("current_score_margin"))) >= 0.01),
        ):
            rows = [p for p in pair_rows if predicate(p)]
            if not rows:
                continue
            split_eval = _evaluate_rule(
                pair_rows=rows,
                scores_by_key=scores_by_key,
                config_id=config_id,
                rule=rule,
                aggregator=aggregator,
            )
            split_eval["split_name"] = split_name
            split_eval["parent_net"] = summary["net"]
            out.append(split_eval)
    return out


def _build_readout(summary: Mapping[str, Any], rows: Sequence[Mapping[str, Any]]) -> str:
    lines = [
        "# Span-Hamming 500 Composite Rules v1",
        "",
        "## Status",
        "",
        "- Report-only; no runtime behaviour changed.",
        f"- rule summary rows: `{summary['rule_summary_row_count']}`",
        f"- split validation rows: `{summary['split_validation_row_count']}`",
        f"- elapsed seconds: `{float(summary['elapsed_seconds']):.2f}`",
        "",
        "## Top Rows",
        "",
        "| config | rule | agg | rescues | breaks | net |",
        "|---|---|---|---:|---:|---:|",
    ]
    for row in rows[:15]:
        lines.append(
            f"| {row['config_id']} | {row['rule_id']} | {row['aggregator']} | "
            f"{row['rescues']} | {row['breaks']} | {row['net']} |"
        )
    return "\n".join(lines) + "\n"


def run_sweep() -> dict[str, Any]:
    started = time.perf_counter()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pair_rows = _read_csv(PAIR_ROWS)
    candidate_rows = _read_csv(CANDIDATE_FEATURES)
    rules = _rules()
    config_ids = sorted({str(row["config_id"]) for row in candidate_rows})

    scores_by_key: dict[tuple[str, str, str], dict[str, float]] = {}
    for row in candidate_rows:
        config_id = str(row["config_id"])
        token_hash = str(row["token_hash"])
        chunk_kind = str(row["chunk_kind"])
        fmap = _feature_map(row)
        for rule in rules:
            scores_by_key.setdefault((config_id, rule.rule_id, token_hash), {})[chunk_kind] = float(rule.formula(fmap))

    summary_rows: list[dict[str, Any]] = []
    total = len(config_ids) * len(rules) * len(AGGREGATORS)
    done = 0
    for config_id in config_ids:
        for rule in rules:
            for aggregator in AGGREGATORS:
                summary_rows.append(
                    _evaluate_rule(
                        pair_rows=pair_rows,
                        scores_by_key=scores_by_key,
                        config_id=config_id,
                        rule=rule,
                        aggregator=aggregator,
                    )
                )
                done += 1
                if done == 1 or done % 100 == 0 or done == total:
                    elapsed = time.perf_counter() - started
                    print(
                        f"[span_hamming_500_composite_rules] progress {done}/{total} "
                        f"elapsed={elapsed:.1f}s last_config={config_id}",
                        flush=True,
                    )

    summary_rows.sort(key=lambda item: (int(item["net"]), int(item["rescues"])), reverse=True)
    split_rows = _split_rows(pair_rows, summary_rows, scores_by_key)
    split_rows.sort(key=lambda item: (str(item["config_id"]), str(item["rule_id"]), str(item["aggregator"]), str(item["split_name"])))

    summary_csv = OUTPUT_DIR / "span_hamming_500_composite_rule_summary.csv"
    split_csv = OUTPUT_DIR / "span_hamming_500_composite_split_validation.csv"
    summary_fields = [
        "config_id",
        "rule_id",
        "formula_family",
        "lambda_value",
        "epsilon",
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
        "unique_misranked_rescue_pair_count",
        "unique_control_break_pair_count",
    ]
    split_fields = ["split_name", "parent_net", *summary_fields]
    _write_csv(summary_csv, summary_rows, summary_fields)
    _write_csv(split_csv, split_rows, split_fields)

    summary = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "output_dir": _repo_rel(OUTPUT_DIR),
        "source_candidate_features": _repo_rel(CANDIDATE_FEATURES),
        "pair_row_count": len(pair_rows),
        "candidate_row_count": len(candidate_rows),
        "config_count": len(config_ids),
        "rule_count": len(rules),
        "aggregators": list(AGGREGATORS),
        "rule_summary_row_count": len(summary_rows),
        "split_validation_row_count": len(split_rows),
        "elapsed_seconds": time.perf_counter() - started,
        "summary_csv": _repo_rel(summary_csv),
        "split_validation_csv": _repo_rel(split_csv),
        "top_net_rows": summary_rows[:20],
        "caveats": [
            "report-only; no runtime solver behaviour changed",
            "composite formulas use saved fixed-500 candidate rows",
            "split validation is diagnostic, not a final holdout",
        ],
    }
    (OUTPUT_DIR / "span_hamming_500_composite_rules_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (OUTPUT_DIR / "span_hamming_500_composite_rules_readout.md").write_text(
        _build_readout(summary, summary_rows),
        encoding="utf-8",
    )
    print(
        f"[span_hamming_500_composite_rules] done rows={len(summary_rows)} "
        f"elapsed={summary['elapsed_seconds']:.2f}s output={_repo_rel(OUTPUT_DIR)}",
        flush=True,
    )
    return summary


def main() -> None:
    run_sweep()


if __name__ == "__main__":
    main()
