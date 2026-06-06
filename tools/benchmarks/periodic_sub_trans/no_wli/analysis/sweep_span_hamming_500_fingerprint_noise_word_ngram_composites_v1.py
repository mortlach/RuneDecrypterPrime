from __future__ import annotations

"""
Report-only sweep combining span fingerprint/noise features with word-ngram features.

Uses saved candidate rows only. No text is rescored and no runtime selection
logic is changed.
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


RUN_LABEL = "span_hamming_500_fingerprint_noise_word_ngram_composites_v1"

PAIR_ROWS_REL = (
    "assets/evaluation_corpora/failed_decryptions/historical_partial_solves_v1/source/historical_pairwise_rescore_v1/historical_pairwise_rescore_pairs.csv"
)
SPAN_JOINED_FEATURES_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "span_hamming_500_fingerprint_noise_composites_v1/"
    "span_hamming_500_fingerprint_noise_joined_candidate_features.csv"
)
COMPONENT_FEATURES_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "scorer_component_feature_audit_v1/scorer_component_feature_audit_candidate_features.csv"
)
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "span_hamming_500_fingerprint_noise_word_ngram_composites_v1"
)

CHUNK_KINDS = ("prefix", "middle", "suffix")
AGGREGATORS = ("prefix", "middle", "suffix", "mean", "median", "min", "vote_2_of_3")
NOISE_LAMBDAS = (0.25, 0.5, 0.75, 1.0, 1.5)
WORD_NGRAM_WEIGHTS = (0.25, 0.5, 0.75, 1.0, 1.5, 2.0)


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
SPAN_JOINED_FEATURES = REPO_ROOT / SPAN_JOINED_FEATURES_REL
COMPONENT_FEATURES = REPO_ROOT / COMPONENT_FEATURES_REL
OUTPUT_DIR = REPO_ROOT / OUTPUT_DIR_REL


@dataclass(frozen=True)
class RuleSpec:
    rule_id: str
    family: str
    noise_lambda: float
    word_ngram_weight: float
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


def _zscore_feature(rows: Sequence[dict[str, Any]], feature_name: str) -> None:
    values = [_safe_float(row.get(feature_name)) for row in rows]
    mean_value = sum(values) / float(max(1, len(values)))
    variance = sum((value - mean_value) ** 2 for value in values) / float(max(1, len(values)))
    stdev = math.sqrt(variance)
    if stdev <= 1e-12:
        stdev = 1.0
    for row in rows:
        row[f"z_{feature_name}"] = (_safe_float(row.get(feature_name)) - mean_value) / stdev


def _joined_rows(span_rows: Sequence[Mapping[str, str]], component_rows: Sequence[Mapping[str, str]]) -> list[dict[str, Any]]:
    component_by_hash = {str(row["token_hash"]): row for row in component_rows}
    out: list[dict[str, Any]] = []
    for span in span_rows:
        token_hash = str(span["token_hash"])
        comp = component_by_hash.get(token_hash)
        if comp is None:
            continue
        row = dict(span)
        for key, value in list(row.items()):
            if str(key).startswith("z_"):
                row[key] = _safe_float(value)
        row.update(
            {
                "word_ngram_active": _safe_float(comp.get("word_ngram_active")),
                "word_ngram_trust_score": _safe_float(comp.get("word_ngram_trust_score")),
                "word_ngram_xent": _safe_float(comp.get("word_ngram_xent")),
                "word_ngram_backoff_xent": _safe_float(comp.get("word_ngram_backoff_xent")),
                "word_ngram_miss_rate": _safe_float(comp.get("word_ngram_miss_rate")),
                "word_ngram_backoff_used_rate": _safe_float(comp.get("word_ngram_backoff_used_rate")),
            }
        )
        out.append(row)
    for feature in (
        "word_ngram_active",
        "word_ngram_trust_score",
        "word_ngram_xent",
        "word_ngram_backoff_xent",
        "word_ngram_miss_rate",
        "word_ngram_backoff_used_rate",
    ):
        _zscore_feature(out, feature)
    return out


def _rules() -> list[RuleSpec]:
    rules: list[RuleSpec] = []
    base_formulas: tuple[tuple[str, Callable[[Mapping[str, float], float], float]], ...] = (
        (
            "selected_exact_span_noise",
            lambda f, noise: f["z_fp_selected_exact"] + f["z_span_err20"] + f["z_span_exact5"] - noise * f["z_noise_short"],
        ),
        (
            "raw_len6_exact_span_noise",
            lambda f, noise: f["z_fp_raw_len6_exact"] + f["z_span_err20"] - noise * f["z_noise_short"],
        ),
        (
            "span_exact5_err20_noise",
            lambda f, noise: f["z_span_err20"] + f["z_span_exact5"] - noise * f["z_noise_short"],
        ),
        (
            "selected_exact_noise",
            lambda f, noise: f["z_fp_selected_exact"] - noise * f["z_noise_short"],
        ),
    )
    word_ngram_terms: tuple[tuple[str, Callable[[Mapping[str, float]], float]], ...] = (
        ("trust", lambda f: f["z_word_ngram_trust_score"]),
        ("active_trust", lambda f: f["z_word_ngram_active"] + f["z_word_ngram_trust_score"]),
        ("trust_xent", lambda f: f["z_word_ngram_trust_score"] - f["z_word_ngram_xent"]),
        ("trust_miss", lambda f: f["z_word_ngram_trust_score"] - f["z_word_ngram_miss_rate"]),
        ("trust_backoff", lambda f: f["z_word_ngram_trust_score"] - f["z_word_ngram_backoff_used_rate"]),
    )
    for noise_lambda in NOISE_LAMBDAS:
        noise_id = str(noise_lambda).replace(".", "p")
        for base_name, base_formula in base_formulas:
            rules.append(
                RuleSpec(
                    rule_id=f"{base_name}_lam{noise_id}",
                    family=base_name,
                    noise_lambda=noise_lambda,
                    word_ngram_weight=0.0,
                    formula=lambda f, base_formula=base_formula, noise_lambda=noise_lambda: base_formula(f, noise_lambda),
                )
            )
            for word_ngram_name, word_ngram_formula in word_ngram_terms:
                for weight in WORD_NGRAM_WEIGHTS:
                    weight_id = str(weight).replace(".", "p")
                    rules.append(
                        RuleSpec(
                            rule_id=f"{base_name}_plus_word_ngram_{word_ngram_name}_lam{noise_id}_w{weight_id}",
                            family=f"{base_name}+{word_ngram_name}",
                            noise_lambda=noise_lambda,
                            word_ngram_weight=weight,
                            formula=lambda f, base_formula=base_formula, word_ngram_formula=word_ngram_formula, noise_lambda=noise_lambda, weight=weight: (
                                base_formula(f, noise_lambda) + weight * word_ngram_formula(f)
                            ),
                        )
                    )
    for word_ngram_name, word_ngram_formula in word_ngram_terms:
        for weight in WORD_NGRAM_WEIGHTS:
            weight_id = str(weight).replace(".", "p")
            rules.append(
                RuleSpec(
                    rule_id=f"word_ngram_{word_ngram_name}_w{weight_id}",
                    family=f"word_ngram_{word_ngram_name}",
                    noise_lambda=0.0,
                    word_ngram_weight=weight,
                    formula=lambda f, word_ngram_formula=word_ngram_formula, weight=weight: weight * word_ngram_formula(f),
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
    rule: RuleSpec,
    aggregator: str,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "rule_id": rule.rule_id,
        "family": rule.family,
        "noise_lambda": rule.noise_lambda,
        "word_ngram_weight": rule.word_ngram_weight,
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
        winner_values = scores_by_key.get((rule.rule_id, winner_hash))
        challenger_values = scores_by_key.get((rule.rule_id, challenger_hash))
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


def _split_predicates() -> list[tuple[str, Callable[[Mapping[str, str]], bool]]]:
    return [
        ("fixture_seed_even", lambda p: int(str(p.get("fixture_seed") or "0") or 0) % 2 == 0),
        ("fixture_seed_odd", lambda p: int(str(p.get("fixture_seed") or "0") or 0) % 2 == 1),
        ("fixture_family_seed_7000s", lambda p: str(p.get("fixture_seed") or "").startswith("7")),
        ("fixture_family_seed_x11", lambda p: str(p.get("fixture_seed") or "").endswith("11")),
        ("current_score_margin_abs_lt_0p01", lambda p: abs(_safe_float(p.get("current_score_margin"))) < 0.01),
        ("current_score_margin_abs_ge_0p01", lambda p: abs(_safe_float(p.get("current_score_margin"))) >= 0.01),
    ]


def _split_validation(
    *,
    pair_rows: Sequence[Mapping[str, str]],
    summary_rows: Sequence[Mapping[str, Any]],
    scores_by_key: Mapping[tuple[str, str], dict[str, float]],
    rules_by_id: Mapping[str, RuleSpec],
) -> list[dict[str, Any]]:
    top = sorted(summary_rows, key=lambda item: (int(item["net"]), int(item["rescues"])), reverse=True)[:30]
    out: list[dict[str, Any]] = []
    for summary in top:
        rule = rules_by_id[str(summary["rule_id"])]
        aggregator = str(summary["aggregator"])
        for split_name, predicate in _split_predicates():
            rows = [row for row in pair_rows if predicate(row)]
            if not rows:
                continue
            split_row = _evaluate_rule(pair_rows=rows, scores_by_key=scores_by_key, rule=rule, aggregator=aggregator)
            split_row["split_name"] = split_name
            split_row["parent_net"] = summary["net"]
            out.append(split_row)
    return out


def _build_readout(summary: Mapping[str, Any], rows: Sequence[Mapping[str, Any]], split_rows: Sequence[Mapping[str, Any]]) -> str:
    lines = [
        "# Span-Hamming 500 Fingerprint + Noise + Word-Ngram Composites v1",
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
        for row in top_splits:
            lines.append(f"| {row['split_name']} | {row['rescues']} | {row['breaks']} | {row['net']} |")
    return "\n".join(lines) + "\n"


def run_sweep() -> dict[str, Any]:
    started = time.perf_counter()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pair_rows = _read_csv(PAIR_ROWS)
    span_rows = _read_csv(SPAN_JOINED_FEATURES)
    component_rows = _read_csv(COMPONENT_FEATURES)
    joined_rows = _joined_rows(span_rows, component_rows)
    rules = _rules()
    rules_by_id = {rule.rule_id: rule for rule in rules}

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
            summary_rows.append(_evaluate_rule(pair_rows=pair_rows, scores_by_key=scores_by_key, rule=rule, aggregator=aggregator))
            done += 1
            if done == 1 or done % 200 == 0 or done == total:
                print(f"[span_hamming_500_fingerprint_noise_word_ngram] progress {done}/{total} elapsed={time.perf_counter() - started:.1f}s", flush=True)

    summary_rows.sort(key=lambda item: (int(item["net"]), int(item["rescues"])), reverse=True)
    split_rows = _split_validation(pair_rows=pair_rows, summary_rows=summary_rows, scores_by_key=scores_by_key, rules_by_id=rules_by_id)
    split_rows.sort(key=lambda item: (str(item["rule_id"]), str(item["aggregator"]), str(item["split_name"])))

    summary_csv = OUTPUT_DIR / "span_hamming_500_fingerprint_noise_word_ngram_composite_summary.csv"
    split_csv = OUTPUT_DIR / "span_hamming_500_fingerprint_noise_word_ngram_composite_split_validation.csv"
    joined_csv = OUTPUT_DIR / "span_hamming_500_fingerprint_noise_word_ngram_joined_candidate_features.csv"
    summary_fields = [
        "rule_id",
        "family",
        "noise_lambda",
        "word_ngram_weight",
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
    _write_csv(summary_csv, summary_rows, summary_fields)
    _write_csv(split_csv, split_rows, split_fields)
    if joined_rows:
        _write_csv(joined_csv, joined_rows, list(joined_rows[0].keys()))

    summary = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "output_dir": _repo_rel(OUTPUT_DIR),
        "source_span_joined_features": _repo_rel(SPAN_JOINED_FEATURES),
        "source_component_features": _repo_rel(COMPONENT_FEATURES),
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
            "word-ngram candidate features are from scorer_component_feature_audit_v1",
            "split validation is diagnostic, not final holdout",
        ],
    }
    (OUTPUT_DIR / "span_hamming_500_fingerprint_noise_word_ngram_composite_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (OUTPUT_DIR / "span_hamming_500_fingerprint_noise_word_ngram_composite_readout.md").write_text(
        _build_readout(summary, summary_rows, split_rows),
        encoding="utf-8",
    )
    print(
        f"[span_hamming_500_fingerprint_noise_word_ngram] done rows={len(summary_rows)} "
        f"elapsed={summary['elapsed_seconds']:.2f}s output={_repo_rel(OUTPUT_DIR)}",
        flush=True,
    )
    return summary


def main() -> None:
    run_sweep()


if __name__ == "__main__":
    main()
