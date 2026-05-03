from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


RUN_LABEL = "scorer_checkpoint_gate_simulation_v1"

S1_PAIR_ROWS = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "historical_pairwise_rescore_v1/historical_pairwise_rescore_pairs.csv"
)
S1B_CANDIDATE_FEATURES = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "scorer_component_feature_audit_v1/scorer_component_feature_audit_candidate_features.csv"
)
S1F_SPAN_CANDIDATE_FEATURES = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "span_hamming_full_calibration_v1/span_hamming_full_calibration_candidate_features.csv"
)
OUTPUT_DIR = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "scorer_checkpoint_gate_simulation_v1"
)

SIDE_WINNER = "winner"
SIDE_CHALLENGER = "challenger"
SIDE_NONE = "no_decision"


@dataclass(frozen=True)
class FeatureSpec:
    source: str
    feature_name: str
    direction: str
    config_id: str = ""
    threshold: float = 0.0
    require_selected_word_active: bool = False
    max_cap_pruned_rate: float | None = None


@dataclass(frozen=True)
class GateRule:
    rule_id: str
    family: str
    current_margin_max_abs: float | None
    specs: tuple[FeatureSpec, ...]
    combine: str = "single"
    notes: str = ""


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def _rel(root: Path, rel_path: str) -> Path:
    return root / rel_path


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        out = float(text)
    except ValueError:
        return None
    if math.isnan(out):
        return None
    return out


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def _feature_side(winner_value: float | None, challenger_value: float | None, direction: str, threshold: float) -> str:
    if winner_value is None or challenger_value is None:
        return SIDE_NONE
    margin = winner_value - challenger_value
    if direction == "higher":
        if margin > threshold:
            return SIDE_WINNER
        if margin < -threshold:
            return SIDE_CHALLENGER
        return SIDE_NONE
    if direction == "lower":
        if margin < -threshold:
            return SIDE_WINNER
        if margin > threshold:
            return SIDE_CHALLENGER
        return SIDE_NONE
    raise ValueError(f"unknown feature direction: {direction}")


def _load_s1b_features(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {str(row["token_hash"]): row for row in rows}


def _load_span_features(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    out: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        out[(str(row["config_id"]), str(row["token_hash"]))] = row
    return out


def _gate_rules() -> list[GateRule]:
    rules: list[GateRule] = []
    for margin in (0.005, 0.01, 0.02, 0.05):
        for threshold in (0.0025, 0.005, 0.01, 0.02):
            rules.append(
                GateRule(
                    rule_id=f"exact_span_coverage_m{margin:g}_t{threshold:g}",
                    family="exact_span",
                    current_margin_max_abs=margin,
                    specs=(
                        FeatureSpec(
                            source="span",
                            config_id="raw_selected__len1_14_hd0_exact__cap256",
                            feature_name="span_coverage_selected",
                            direction="higher",
                            threshold=threshold,
                            max_cap_pruned_rate=0.05,
                        ),
                    ),
                    notes="Exact-span coverage with cap-pressure no-decision guardrail.",
                )
            )
    for margin in (0.005, 0.01, 0.02, 0.05):
        for threshold in (0.0025, 0.005, 0.01, 0.02):
            rules.append(
                GateRule(
                    rule_id=f"s1b_span_raw_m{margin:g}_t{threshold:g}",
                    family="broad_span",
                    current_margin_max_abs=margin,
                    specs=(
                        FeatureSpec(
                            source="span",
                            config_id="raw_selected__len3_14_hd2_s1b_shape__cap512",
                            feature_name="span_raw_selected_current",
                            direction="higher",
                            threshold=threshold,
                            max_cap_pruned_rate=0.35,
                        ),
                    ),
                    notes="S1b-shape span raw score, guarded by cap pressure.",
                )
            )
    for margin in (0.005, 0.01, 0.02, 0.05):
        for threshold in (1.0, 3.0, 5.0, 10.0):
            rules.append(
                GateRule(
                    rule_id=f"long_span_count_m{margin:g}_t{threshold:g}",
                    family="long_span",
                    current_margin_max_abs=margin,
                    specs=(
                        FeatureSpec(
                            source="span",
                            config_id="raw_selected__len8_14_hd2_long_signal__cap1024",
                            feature_name="span_interval_count_selected",
                            direction="higher",
                            threshold=threshold,
                            max_cap_pruned_rate=0.35,
                        ),
                    ),
                    notes="Long-span selected interval count.",
                )
            )
    for margin in (0.005, 0.01, 0.02, 0.05):
        for threshold in (0.05, 0.1, 0.2, 0.3):
            rules.append(
                GateRule(
                    rule_id=f"word_trust_m{margin:g}_t{threshold:g}",
                    family="word_trust",
                    current_margin_max_abs=margin,
                    specs=(
                        FeatureSpec(
                            source="s1b",
                            feature_name="word_ngram_trust_score",
                            direction="higher",
                            threshold=threshold,
                            require_selected_word_active=True,
                        ),
                    ),
                    notes="Word-ngram trust only; inactive selected side is no-decision.",
                )
            )
    for margin in (0.005, 0.01, 0.02, 0.05):
        for threshold in (0.005, 0.01, 0.02, 0.05):
            rules.append(
                GateRule(
                    rule_id=f"repeated3_m{margin:g}_t{threshold:g}",
                    family="repetition",
                    current_margin_max_abs=margin,
                    specs=(
                        FeatureSpec(
                            source="s1b",
                            feature_name="repeated_3gram_rate",
                            direction="lower",
                            threshold=threshold,
                        ),
                    ),
                    notes="Lower repeated 3-gram rate diagnostic.",
                )
            )
    for margin in (0.01, 0.02, 0.05):
        rules.append(
            GateRule(
                rule_id=f"exact_span_and_word_trust_m{margin:g}",
                family="span_word_conjunction",
                current_margin_max_abs=margin,
                specs=(
                    FeatureSpec(
                        source="span",
                        config_id="raw_selected__len1_14_hd0_exact__cap256",
                        feature_name="span_coverage_selected",
                        direction="higher",
                        threshold=0.005,
                        max_cap_pruned_rate=0.05,
                    ),
                    FeatureSpec(
                        source="s1b",
                        feature_name="word_ngram_trust_score",
                        direction="higher",
                        threshold=0.05,
                        require_selected_word_active=True,
                    ),
                ),
                combine="all_same",
                notes="Exact-span and active word-trust must prefer the same side.",
            )
        )
    for margin in (0.01, 0.02, 0.05):
        rules.append(
            GateRule(
                rule_id=f"exact_span_and_repeated3_m{margin:g}",
                family="span_repetition_conjunction",
                current_margin_max_abs=margin,
                specs=(
                    FeatureSpec(
                        source="span",
                        config_id="raw_selected__len1_14_hd0_exact__cap256",
                        feature_name="span_coverage_selected",
                        direction="higher",
                        threshold=0.005,
                        max_cap_pruned_rate=0.05,
                    ),
                    FeatureSpec(
                        source="s1b",
                        feature_name="repeated_3gram_rate",
                        direction="lower",
                        threshold=0.01,
                    ),
                ),
                combine="all_same",
                notes="Exact-span and repeated-3 diagnostic must prefer the same side.",
            )
        )
    return rules


def _candidate_row(
    spec: FeatureSpec,
    token_hash: str,
    s1b_by_token: dict[str, dict[str, str]],
    span_by_config_token: dict[tuple[str, str], dict[str, str]],
) -> dict[str, str] | None:
    if spec.source == "s1b":
        return s1b_by_token.get(token_hash)
    if spec.source == "span":
        return span_by_config_token.get((spec.config_id, token_hash))
    raise ValueError(f"unknown feature source: {spec.source}")


def _spec_side(
    spec: FeatureSpec,
    pair: dict[str, str],
    s1b_by_token: dict[str, dict[str, str]],
    span_by_config_token: dict[tuple[str, str], dict[str, str]],
) -> tuple[str, str]:
    winner_hash = str(pair["winner_token_hash"])
    challenger_hash = str(pair["challenger_token_hash"])
    winner_row = _candidate_row(spec, winner_hash, s1b_by_token, span_by_config_token)
    challenger_row = _candidate_row(spec, challenger_hash, s1b_by_token, span_by_config_token)
    if winner_row is None or challenger_row is None:
        return SIDE_NONE, "missing_candidate_feature"

    if spec.max_cap_pruned_rate is not None:
        winner_cap = _safe_float(winner_row.get("candidate_cap_pruned_rate"))
        challenger_cap = _safe_float(challenger_row.get("candidate_cap_pruned_rate"))
        if winner_cap is None or challenger_cap is None:
            return SIDE_NONE, "missing_cap_pressure"
        if winner_cap > spec.max_cap_pruned_rate or challenger_cap > spec.max_cap_pruned_rate:
            return SIDE_NONE, "cap_pressure_guardrail"

    winner_value = _safe_float(winner_row.get(spec.feature_name))
    challenger_value = _safe_float(challenger_row.get(spec.feature_name))
    side = _feature_side(winner_value, challenger_value, spec.direction, spec.threshold)
    if side == SIDE_NONE:
        return SIDE_NONE, "feature_tie_or_below_threshold"

    if spec.require_selected_word_active:
        selected_row = winner_row if side == SIDE_WINNER else challenger_row
        if _safe_int(selected_row.get("word_ngram_active")) != 1:
            return SIDE_NONE, "selected_word_ngram_inactive"

    return side, ""


def simulate_rule(
    rule: GateRule,
    pair: dict[str, str],
    s1b_by_token: dict[str, dict[str, str]],
    span_by_config_token: dict[tuple[str, str], dict[str, str]],
) -> dict[str, Any]:
    current_margin = _safe_float(pair.get("current_score_margin"))
    if current_margin is None:
        return {
            "shadow_selected_side": SIDE_NONE,
            "gate_fired": 0,
            "no_decision_reason": "missing_current_score_margin",
        }
    current_selected = SIDE_WINNER if current_margin > 0 else SIDE_CHALLENGER
    if rule.current_margin_max_abs is not None and abs(current_margin) > rule.current_margin_max_abs:
        return {
            "shadow_selected_side": current_selected,
            "gate_fired": 0,
            "no_decision_reason": "current_margin_too_large",
        }

    sides: list[str] = []
    reasons: list[str] = []
    for spec in rule.specs:
        side, reason = _spec_side(spec, pair, s1b_by_token, span_by_config_token)
        sides.append(side)
        if reason:
            reasons.append(reason)

    if rule.combine == "single":
        selected = sides[0]
    elif rule.combine == "all_same":
        real_sides = [side for side in sides if side != SIDE_NONE]
        selected = real_sides[0] if len(real_sides) == len(sides) and len(set(real_sides)) == 1 else SIDE_NONE
        if selected == SIDE_NONE and not reasons:
            reasons.append("feature_disagreement_or_tie")
    else:
        raise ValueError(f"unknown combine policy: {rule.combine}")

    if selected == SIDE_NONE:
        return {
            "shadow_selected_side": current_selected,
            "gate_fired": 0,
            "no_decision_reason": ";".join(sorted(set(reasons))) or "feature_no_decision",
        }
    return {
        "shadow_selected_side": selected,
        "gate_fired": int(selected != current_selected),
        "no_decision_reason": "",
    }


def _text_pair_key(pair: dict[str, str]) -> str:
    return f"{pair['winner_token_hash']}__{pair['challenger_token_hash']}"


def _candidate_pair_key(pair: dict[str, str]) -> str:
    return f"{pair['winner_candidate_hash']}__{pair['challenger_candidate_hash']}"


def _summarise_rule(rule: GateRule, decisions: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(str(row["outcome"]) for row in decisions)
    no_decision_reasons = Counter(str(row["no_decision_reason"]) for row in decisions if row["no_decision_reason"])
    overrides = [row for row in decisions if int(row["gate_fired"]) == 1]
    override_pair_counts = Counter(str(row["text_pair_key"]) for row in overrides)
    dominant_override_pair_count = max(override_pair_counts.values()) if override_pair_counts else 0
    unique_misranked_rescues = {
        str(row["text_pair_key"])
        for row in decisions
        if row["pair_group"] == "current_score_misranked" and row["outcome"] == "rescue"
    }
    unique_control_breaks = {
        str(row["text_pair_key"])
        for row in decisions
        if row["pair_group"] == "current_score_correct" and row["outcome"] == "break"
    }
    return {
        "rule_id": rule.rule_id,
        "family": rule.family,
        "current_margin_max_abs": "" if rule.current_margin_max_abs is None else rule.current_margin_max_abs,
        "combine": rule.combine,
        "notes": rule.notes,
        "pair_count": len(decisions),
        "current_misranked_pair_count": sum(1 for row in decisions if row["pair_group"] == "current_score_misranked"),
        "current_correct_control_pair_count": sum(1 for row in decisions if row["pair_group"] == "current_score_correct"),
        "gate_fired_count": len(overrides),
        "rescue_count": counts["rescue"],
        "break_count": counts["break"],
        "net_count": counts["rescue"] - counts["break"],
        "same_correct_count": counts["same_correct"],
        "same_wrong_count": counts["same_wrong"],
        "no_decision_count": sum(1 for row in decisions if int(row["gate_fired"]) == 0),
        "unique_text_pair_count": len({str(row["text_pair_key"]) for row in decisions}),
        "unique_misranked_rescue_pair_count": len(unique_misranked_rescues),
        "unique_control_break_pair_count": len(unique_control_breaks),
        "dominant_override_pair_count": dominant_override_pair_count,
        "dominant_override_pair_fraction": (
            dominant_override_pair_count / len(overrides) if overrides else 0.0
        ),
        "no_decision_reason_counts": json.dumps(dict(sorted(no_decision_reasons.items())), sort_keys=True),
    }


def _decision_outcome(pair: dict[str, str], shadow_selected_side: str) -> str:
    current_correct = _safe_int(pair.get("current_score_correct")) == 1
    shadow_correct = shadow_selected_side == SIDE_WINNER
    if current_correct and shadow_correct:
        return "same_correct"
    if current_correct and not shadow_correct:
        return "break"
    if not current_correct and shadow_correct:
        return "rescue"
    return "same_wrong"


def run() -> dict[str, Any]:
    root = _repo_root()
    output_dir = _rel(root, OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    pairs = _read_csv(_rel(root, S1_PAIR_ROWS))
    s1b_by_token = _load_s1b_features(_read_csv(_rel(root, S1B_CANDIDATE_FEATURES)))
    span_by_config_token = _load_span_features(_read_csv(_rel(root, S1F_SPAN_CANDIDATE_FEATURES)))

    rules = _gate_rules()
    all_decisions: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    for rule in rules:
        decisions: list[dict[str, Any]] = []
        for pair in pairs:
            current_correct = _safe_int(pair.get("current_score_correct")) == 1
            result = simulate_rule(rule, pair, s1b_by_token, span_by_config_token)
            outcome = _decision_outcome(pair, str(result["shadow_selected_side"]))
            decision = {
                "rule_id": rule.rule_id,
                "family": rule.family,
                "pair_id": pair["pair_id"],
                "artifact_path": pair["artifact_path"],
                "fixture_id": pair.get("fixture_id", ""),
                "fixture_seed": pair.get("fixture_seed", ""),
                "search_seed": pair.get("search_seed", ""),
                "token_length": pair["token_length"],
                "winner_token_hash": pair["winner_token_hash"],
                "challenger_token_hash": pair["challenger_token_hash"],
                "winner_candidate_hash": pair["winner_candidate_hash"],
                "challenger_candidate_hash": pair["challenger_candidate_hash"],
                "text_pair_key": _text_pair_key(pair),
                "candidate_pair_key": _candidate_pair_key(pair),
                "truth_gap": pair["truth_gap"],
                "current_score_margin": pair["current_score_margin"],
                "current_score_correct": int(current_correct),
                "pair_group": "current_score_correct" if current_correct else "current_score_misranked",
                "shadow_selected_side": result["shadow_selected_side"],
                "gate_fired": result["gate_fired"],
                "outcome": outcome,
                "no_decision_reason": result["no_decision_reason"],
            }
            decisions.append(decision)
            all_decisions.append(decision)
        summary_rows.append(_summarise_rule(rule, decisions))

    summary_rows.sort(
        key=lambda row: (
            -int(row["net_count"]),
            int(row["break_count"]),
            -int(row["rescue_count"]),
            str(row["rule_id"]),
        )
    )

    decision_fields = [
        "rule_id",
        "family",
        "pair_id",
        "artifact_path",
        "fixture_id",
        "fixture_seed",
        "search_seed",
        "token_length",
        "winner_token_hash",
        "challenger_token_hash",
        "winner_candidate_hash",
        "challenger_candidate_hash",
        "text_pair_key",
        "candidate_pair_key",
        "truth_gap",
        "current_score_margin",
        "current_score_correct",
        "pair_group",
        "shadow_selected_side",
        "gate_fired",
        "outcome",
        "no_decision_reason",
    ]
    summary_fields = [
        "rule_id",
        "family",
        "current_margin_max_abs",
        "combine",
        "notes",
        "pair_count",
        "current_misranked_pair_count",
        "current_correct_control_pair_count",
        "gate_fired_count",
        "rescue_count",
        "break_count",
        "net_count",
        "same_correct_count",
        "same_wrong_count",
        "no_decision_count",
        "unique_text_pair_count",
        "unique_misranked_rescue_pair_count",
        "unique_control_break_pair_count",
        "dominant_override_pair_count",
        "dominant_override_pair_fraction",
        "no_decision_reason_counts",
    ]
    _write_csv(output_dir / "scorer_checkpoint_gate_simulation_pair_decisions.csv", all_decisions, decision_fields)
    _write_csv(output_dir / "scorer_checkpoint_gate_simulation_rule_summary.csv", summary_rows, summary_fields)

    top_low_break = [
        row for row in summary_rows if int(row["break_count"]) <= 20 and int(row["rescue_count"]) > 0
    ][:20]
    top_net = summary_rows[:20]
    summary = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "output_dir": OUTPUT_DIR,
        "report_only": True,
        "runtime_changed": False,
        "truth_fields_are_evaluation_only": True,
        "pair_count": len(pairs),
        "rule_count": len(rules),
        "decision_row_count": len(all_decisions),
        "current_score_misranked_pair_count": sum(
            1 for row in pairs if _safe_int(row.get("current_score_correct")) != 1
        ),
        "current_score_correct_control_pair_count": sum(
            1 for row in pairs if _safe_int(row.get("current_score_correct")) == 1
        ),
        "top_net_rules": top_net[:10],
        "top_low_break_rules": top_low_break[:10],
        "caveats": [
            "This is a report-only shadow decision simulation.",
            "Truth labels are used only to score rescues and breaks.",
            "Rules are hand-declared diagnostics, not learned weights.",
            "No runtime selector, scorer, or acceptance behaviour changed.",
            "Inactive word-ngram selected side is treated as no-decision.",
            "Span rules use cap-pressure guardrails.",
        ],
    }
    (output_dir / "scorer_checkpoint_gate_simulation_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_readout(output_dir / "scorer_checkpoint_gate_simulation_readout.md", summary, top_net, top_low_break)
    return summary


def _markdown_table(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return ["No rows met this filter."]
    out = [
        "| rule | family | rescues | breaks | net | unique rescues | unique breaks | fired | no decision |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        out.append(
            "| "
            f"{row['rule_id']} | {row['family']} | {row['rescue_count']} | "
            f"{row['break_count']} | {row['net_count']} | "
            f"{row['unique_misranked_rescue_pair_count']} | "
            f"{row['unique_control_break_pair_count']} | {row['gate_fired_count']} | "
            f"{row['no_decision_count']} |"
        )
    return out


def _write_readout(path: Path, summary: dict[str, Any], top_net: list[dict[str, Any]], top_low_break: list[dict[str, Any]]) -> None:
    lines = [
        "# Scorer Checkpoint Gate Simulation v1",
        "",
        "## Purpose",
        "",
        "Report-only simulation of conservative checkpoint rules on the S1 current-rescored pair dataset.",
        "",
        "## Dataset",
        "",
        f"- pair count: {summary['pair_count']}",
        f"- current-score misranked pairs: {summary['current_score_misranked_pair_count']}",
        f"- current-score correct controls: {summary['current_score_correct_control_pair_count']}",
        f"- rules simulated: {summary['rule_count']}",
        "",
        "## Top Net Rules",
        "",
        *_markdown_table(top_net[:10]),
        "",
        "## Low-Break Rules",
        "",
        *_markdown_table(top_low_break[:10]),
        "",
        "## Interpretation",
        "",
        "This is not a scorer replacement. A useful rule must rescue current-score failures while breaking very few controls, and must work by unique pair rather than only repeated row count.",
        "",
        "## Caveats",
        "",
    ]
    lines.extend(f"- {item}" for item in summary["caveats"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    out = run()
    print(
        f"{RUN_LABEL}: rules={out['rule_count']} pairs={out['pair_count']} "
        f"output_dir={out['output_dir']}"
    )
