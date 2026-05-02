from __future__ import annotations

import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError(
        "Could not locate repo root from "
        "extract_stage35_frontier_space_acceptance_boundary_audit_v1.py"
    )


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


RUN_LABEL = "stage35_frontier_space_acceptance_boundary_audit_v1"
OUTPUT_BASE_DIR = REPO_ROOT / (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "fixed_instance_solver_development_v1"
)
ROBUSTNESS_ROWS_REL = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "fixed_instance_solver_development_v1/"
    "20260501T161846Z__stage35_frontier_space_robustness_harvest_v1/"
    "stage35_frontier_space_robustness_rows.csv"
)


def _utc_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _utc_now_text() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix().replace("\\", "/")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return float(default)
    if not math.isfinite(result):
        return float(default)
    return result


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _write_csv(path: Path, rows: list[Mapping[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(dict(payload), ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _mean(values: Iterable[float]) -> float:
    vals = list(values)
    if not vals:
        return 0.0
    return float(sum(vals) / len(vals))


def _load_json_relpath(relpath: str) -> dict[str, Any]:
    path = REPO_ROOT / relpath.replace("\\", "/")
    return dict(json.loads(path.read_text(encoding="utf-8")))


def _key_of(row: Mapping[str, Any]) -> list[int]:
    raw = row.get("key_idx")
    if raw is None:
        raw = row.get("key")
    if not isinstance(raw, list):
        return []
    return [_safe_int(item) for item in raw]


def _hamming(left: list[int], right: list[int]) -> int:
    if not left or not right or len(left) != len(right):
        return 0
    return sum(1 for a, b in zip(left, right) if a != b)


def _row_key(row: Mapping[str, Any]) -> str:
    return "{}:{}:{}:{}".format(
        row.get("fixture_seed", ""),
        row.get("search_seed", ""),
        row.get("candidate_rank", ""),
        row.get("candidate_hash", ""),
    )


def _classify_row(raw: Mapping[str, Any]) -> str:
    if _safe_int(raw.get("stage35_selected")) != 1:
        return "guard_failed"
    if (
        _safe_float(raw.get("resume_minus_selected")) < 0.0
        or _safe_float(raw.get("resume_minus_shallow")) < 0.0
    ):
        return "accepted_regression"
    return "accepted_positive"


def _candidate_pool_row(artifact: Mapping[str, Any], candidate_hash: str) -> dict[str, Any]:
    diagnostics = dict(artifact.get("stage3_diagnostics", {}) or {})
    rows = list(diagnostics.get("phaseC_candidate_pool_rows", []) or [])
    for row in rows:
        if str(dict(row).get("candidate_hash", "") or "") == candidate_hash:
            return dict(row)
    return {}


def _anchor_pool_row(artifact: Mapping[str, Any]) -> dict[str, Any]:
    diagnostics = dict(artifact.get("stage3_diagnostics", {}) or {})
    anchor_hash = str(diagnostics.get("phaseC_anchor_candidate_hash", "") or "")
    rows = list(diagnostics.get("phaseC_candidate_pool_rows", []) or [])
    for row in rows:
        if str(dict(row).get("candidate_hash", "") or "") == anchor_hash:
            return dict(row)
    return {}


def build_feature_rows(raw_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in raw_rows:
        cell_summary = _load_json_relpath(str(raw.get("cell_output_dir", "")) + "/summary.json")
        artifact = _load_json_relpath(str(raw.get("artifact_relpath", "")))
        stage35 = dict(cell_summary.get("stage35", {}) or {})
        telemetry = dict(stage35.get("telemetry", {}) or {})
        candidate_hash = str(raw.get("candidate_hash", "") or "")
        candidate_row = _candidate_pool_row(artifact, candidate_hash)
        anchor_row = _anchor_pool_row(artifact)
        candidate_key = _key_of(candidate_row)
        anchor_key = _key_of(anchor_row)
        selected_start = _safe_float(raw.get("selected_start_match_ratio"))
        shallow_resume = _safe_float(raw.get("shallow_resume_best_match_ratio"))
        retained = _safe_float(raw.get("retained_best_match_ratio"))
        deep_resume = _safe_float(raw.get("resume_best_match_ratio"))
        baseline_score = _safe_float(stage35.get("baseline_score"))
        best_score = _safe_float(stage35.get("best_score"))
        baseline_search_score = _safe_float(stage35.get("baseline_search_score"))
        best_search_score = _safe_float(stage35.get("best_search_score"))
        phasec_score_winner_match = _safe_float(
            stage35.get("phasec_score_winner_candidate_final_match")
        )
        source = str(candidate_row.get("source", "") or raw.get("selected_source", "") or "")
        source_rank = _safe_int(candidate_row.get("source_rank"))
        row = {
            "outcome_class": _classify_row(raw),
            "fixture_seed": _safe_int(raw.get("fixture_seed")),
            "search_seed": _safe_int(raw.get("search_seed")),
            "candidate_rank": _safe_int(raw.get("candidate_rank")),
            "candidate_hash": candidate_hash,
            "robustness_stratum": str(raw.get("robustness_stratum", "") or ""),
            "prior_deepened": _safe_int(raw.get("prior_deepened")),
            "selected_source": source,
            "selected_lane": str(raw.get("selected_lane", "") or ""),
            "candidate_source_rank": source_rank,
            "candidate_source_rank_eq_1": int(source_rank == 1),
            "candidate_source_rank_le_2": int(source_rank <= 2 and source_rank > 0),
            "candidate_selected_by_phasec_start": _safe_int(
                candidate_row.get("selected_by_phasec_start")
            ),
            "candidate_eligible_novel_challenger": _safe_int(
                candidate_row.get("eligible_novel_challenger")
            ),
            "candidate_novelty_distance_to_anchor": _safe_int(
                candidate_row.get("novelty_distance_to_anchor")
            ),
            "candidate_distance_to_anchor": _hamming(candidate_key, anchor_key),
            "retained_best_match_ratio": retained,
            "selected_start_match_ratio": selected_start,
            "selected_headroom_vs_retained": selected_start - retained,
            "shallow_resume_best_match_ratio": shallow_resume,
            "shallow_resume_minus_selected": shallow_resume - selected_start,
            "shallow_resume_minus_retained": shallow_resume - retained,
            "deep_resume_best_match_ratio": deep_resume,
            "deep_resume_minus_selected": deep_resume - selected_start,
            "deep_resume_minus_shallow": deep_resume - shallow_resume,
            "deep_resume_minus_retained": deep_resume - retained,
            "phasec_score_winner_candidate_final_match": phasec_score_winner_match,
            "selected_minus_phasec_score_winner": selected_start
            - phasec_score_winner_match,
            "stage35_selected": _safe_int(raw.get("stage35_selected")),
            "stage35_accept_reason": str(raw.get("stage35_accept_reason", "") or ""),
            "stage35_selected_archive_rank": _safe_int(
                raw.get("stage35_selected_archive_rank")
            ),
            "stage35_selected_via_guard_passing_selector": _safe_int(
                raw.get("stage35_selected_via_guard_passing_selector")
            ),
            "stage35_rounds_completed": _safe_int(raw.get("stage35_rounds_completed")),
            "stage35_evals": _safe_int(raw.get("stage35_evals")),
            "stage35_archive_rows": _safe_int(raw.get("stage35_archive_rows")),
            "stage35_mini_search_count": _safe_int(
                raw.get("stage35_mini_search_count")
            ),
            "stage35_rows_scored": _safe_int(raw.get("stage35_rows_scored")),
            "stage35_runtime_seconds": _safe_float(stage35.get("runtime_seconds")),
            "stage35_archive_unique_keys": _safe_int(
                stage35.get("archive_unique_keys")
            ),
            "stage35_archive_unique_seed_sources": _safe_int(
                stage35.get("archive_unique_seed_sources")
            ),
            "stage35_archive_unique_target_slices": _safe_int(
                stage35.get("archive_unique_target_slices")
            ),
            "stage35_archive_mean_substitution_hamming": _safe_float(
                stage35.get("archive_mean_substitution_hamming")
            ),
            "stage35_archive_max_substitution_hamming": _safe_int(
                stage35.get("archive_max_substitution_hamming")
            ),
            "stage35_best_depth": _safe_int(stage35.get("best_depth")),
            "stage35_best_seed_source": str(stage35.get("best_seed_source", "") or ""),
            "stage35_best_source_rank": _safe_int(stage35.get("best_source_rank")),
            "stage35_best_stage3_source": str(
                stage35.get("best_stage3_source", "") or ""
            ),
            "stage35_best_move_type": str(stage35.get("best_move_type", "") or ""),
            "stage35_best_target_slice": _safe_int(stage35.get("best_target_slice")),
            "stage35_baseline_score": baseline_score,
            "stage35_best_score": best_score,
            "stage35_best_minus_baseline_score": best_score - baseline_score,
            "stage35_baseline_search_score": baseline_search_score,
            "stage35_best_search_score": best_search_score,
            "stage35_best_minus_baseline_search_score": best_search_score
            - baseline_search_score,
            "stage35_mini_search_rows_kept": _safe_int(
                stage35.get("mini_search_rows_kept")
            ),
            "stage35_mini_search_collected_rows": _safe_int(
                stage35.get("mini_search_collected_rows")
            ),
            "stage35_telemetry_rows_scored": _safe_int(
                telemetry.get("mini_search_rows_scored")
            ),
        }
        rows.append(row)
    rows.sort(
        key=lambda row: (
            str(row["outcome_class"]),
            str(row["robustness_stratum"]),
            _safe_int(row["fixture_seed"]),
            _safe_int(row["search_seed"]),
            _safe_int(row["candidate_rank"]),
        )
    )
    return rows


def _numeric_thresholds(rows: list[Mapping[str, Any]], feature: str) -> list[float]:
    values = sorted({_safe_float(row.get(feature)) for row in rows})
    if len(values) < 2:
        return []
    return [(values[idx] + values[idx + 1]) / 2.0 for idx in range(len(values) - 1)]


def _predict_numeric(
    row: Mapping[str, Any],
    *,
    feature: str,
    direction: str,
    threshold: float,
) -> bool:
    value = _safe_float(row.get(feature))
    if direction == "ge":
        return value >= threshold
    return value <= threshold


def _score_rule(
    rows: list[Mapping[str, Any]],
    predictions: list[bool],
) -> dict[str, Any]:
    tp = fp = tn = fn = 0
    kept: list[str] = []
    for row, predicted_keep in zip(rows, predictions):
        is_positive = str(row.get("outcome_class")) == "accepted_positive"
        if predicted_keep and is_positive:
            tp += 1
        elif predicted_keep and not is_positive:
            fp += 1
        elif not predicted_keep and is_positive:
            fn += 1
        else:
            tn += 1
        if predicted_keep:
            kept.append(_row_key(row))
    return {
        "true_positive": tp,
        "false_positive": fp,
        "true_negative": tn,
        "false_negative": fn,
        "kept_rows": len(kept),
        "kept_keys": "|".join(kept),
    }


def scan_single_rules(
    rows: list[Mapping[str, Any]],
    *,
    numeric_features: list[str],
    categorical_features: list[str],
) -> list[dict[str, Any]]:
    scans: list[dict[str, Any]] = []
    for feature in numeric_features:
        for threshold in _numeric_thresholds(rows, feature):
            for direction in ("ge", "le"):
                predictions = [
                    _predict_numeric(
                        row,
                        feature=feature,
                        direction=direction,
                        threshold=threshold,
                    )
                    for row in rows
                ]
                scan = {
                    "rule_kind": "single_numeric",
                    "feature_a": feature,
                    "direction_a": direction,
                    "threshold_a": threshold,
                    "feature_b": "",
                    "direction_b": "",
                    "threshold_b": "",
                    "category_value_b": "",
                }
                scan.update(_score_rule(rows, predictions))
                scans.append(scan)
    for feature in categorical_features:
        values = sorted({str(row.get(feature, "")) for row in rows})
        for value in values:
            predictions = [str(row.get(feature, "")) == value for row in rows]
            scan = {
                "rule_kind": "single_category",
                "feature_a": feature,
                "direction_a": "eq",
                "threshold_a": "",
                "feature_b": "",
                "direction_b": "",
                "threshold_b": "",
                "category_value_b": value,
            }
            scan.update(_score_rule(rows, predictions))
            scans.append(scan)
    scans.sort(key=_scan_sort_key)
    return scans


def scan_two_feature_rules(
    rows: list[Mapping[str, Any]],
    *,
    numeric_features: list[str],
    categorical_features: list[str],
) -> list[dict[str, Any]]:
    scans: list[dict[str, Any]] = []
    for feature_a in numeric_features:
        for threshold_a in _numeric_thresholds(rows, feature_a):
            for direction_a in ("ge", "le"):
                left = [
                    _predict_numeric(
                        row,
                        feature=feature_a,
                        direction=direction_a,
                        threshold=threshold_a,
                    )
                    for row in rows
                ]
                for feature_b in categorical_features:
                    values = sorted({str(row.get(feature_b, "")) for row in rows})
                    for value in values:
                        predictions = [
                            bool(is_left) and str(row.get(feature_b, "")) == value
                            for row, is_left in zip(rows, left)
                        ]
                        scan = {
                            "rule_kind": "numeric_and_category",
                            "feature_a": feature_a,
                            "direction_a": direction_a,
                            "threshold_a": threshold_a,
                            "feature_b": feature_b,
                            "direction_b": "eq",
                            "threshold_b": "",
                            "category_value_b": value,
                        }
                        scan.update(_score_rule(rows, predictions))
                        scans.append(scan)
    scans.sort(key=_scan_sort_key)
    return scans


def _scan_sort_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        _safe_int(row.get("false_positive")),
        _safe_int(row.get("false_negative")),
        -_safe_int(row.get("true_positive")),
        str(row.get("rule_kind", "")),
        str(row.get("feature_a", "")),
        str(row.get("feature_b", "")),
    )


def _rule_text(row: Mapping[str, Any]) -> str:
    if str(row.get("rule_kind")) == "single_category":
        return "{} == {}".format(row.get("feature_a", ""), row.get("category_value_b", ""))
    first = "{} {} {:.6f}".format(
        row.get("feature_a", ""),
        row.get("direction_a", ""),
        _safe_float(row.get("threshold_a")),
    )
    if str(row.get("rule_kind")) == "single_numeric":
        return first
    return "{} AND {} == {}".format(
        first,
        row.get("feature_b", ""),
        row.get("category_value_b", ""),
    )


def summarize_features(rows: list[Mapping[str, Any]], features: list[str]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    positives = [row for row in rows if str(row.get("outcome_class")) == "accepted_positive"]
    regressions = [row for row in rows if str(row.get("outcome_class")) == "accepted_regression"]
    for feature in features:
        pos_vals = [_safe_float(row.get(feature)) for row in positives]
        reg_vals = [_safe_float(row.get(feature)) for row in regressions]
        summaries.append(
            {
                "feature": feature,
                "positive_count": len(pos_vals),
                "regression_count": len(reg_vals),
                "positive_min": min(pos_vals) if pos_vals else 0.0,
                "positive_max": max(pos_vals) if pos_vals else 0.0,
                "positive_mean": _mean(pos_vals),
                "regression_min": min(reg_vals) if reg_vals else 0.0,
                "regression_max": max(reg_vals) if reg_vals else 0.0,
                "regression_mean": _mean(reg_vals),
                "gap_positive_min_minus_regression_max": (
                    min(pos_vals) - max(reg_vals) if pos_vals and reg_vals else 0.0
                ),
            }
        )
    summaries.sort(
        key=lambda row: abs(_safe_float(row["gap_positive_min_minus_regression_max"])),
        reverse=True,
    )
    return summaries


def _counts_by(rows: list[Mapping[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row.get(field, "") or "")
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def build_readout(
    *,
    summary: Mapping[str, Any],
    single_scans: list[Mapping[str, Any]],
    two_feature_scans: list[Mapping[str, Any]],
) -> str:
    lines = [
        "# Stage35 Frontier Space Acceptance Boundary Audit v1",
        "",
        "Question:",
        "",
        "- can action-safe features separate accepted local-rescue positives from",
        "  accepted regressions in the completed frontier-space robustness harvest?",
        "",
        "Coverage:",
        "",
        f"- rows: `{summary['row_count']}`",
        f"- accepted positives: `{summary['accepted_positive_rows']}`",
        f"- accepted regressions: `{summary['accepted_regression_rows']}`",
        f"- guard failures: `{summary['guard_failed_rows']}`",
        f"- single-rule perfect separators: `{summary['single_perfect_separator_count']}`",
        f"- two-feature perfect separators: `{summary['two_feature_perfect_separator_count']}`",
        "",
        "Best Single-Feature Sketches:",
        "",
    ]
    for row in single_scans[:8]:
        lines.append(
            "- `{}`: TP `{}`, FP `{}`, TN `{}`, FN `{}`".format(
                _rule_text(row),
                row["true_positive"],
                row["false_positive"],
                row["true_negative"],
                row["false_negative"],
            )
        )
    lines.extend(["", "Best Two-Feature Sketches:", ""])
    for row in two_feature_scans[:8]:
        lines.append(
            "- `{}`: TP `{}`, FP `{}`, TN `{}`, FN `{}`".format(
                _rule_text(row),
                row["true_positive"],
                row["false_positive"],
                row["true_negative"],
                row["false_negative"],
            )
        )
    lines.extend(
        [
            "",
            "Interpretation:",
            "",
            "- this is a posthoc audit on the same harvest that exposed the signal",
            "- separators are feature-design leads only, not runtime authorization",
            "- if the best simple separator keeps only a narrow slice, close broad",
            "  local-rescue policy widening and preserve the data as mechanism",
            "  evidence",
            "",
            "Recommended Next:",
            "",
            f"- `{summary['recommended_next']}`",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def run_extract() -> dict[str, Any]:
    rows_path = REPO_ROOT / ROBUSTNESS_ROWS_REL
    output_dir = OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)
    feature_rows = build_feature_rows(_read_csv(rows_path))
    supervised_rows = [
        row
        for row in feature_rows
        if str(row.get("outcome_class")) in {"accepted_positive", "accepted_regression"}
    ]
    numeric_features = [
        "candidate_rank",
        "candidate_source_rank",
        "candidate_source_rank_eq_1",
        "candidate_source_rank_le_2",
        "candidate_selected_by_phasec_start",
        "candidate_eligible_novel_challenger",
        "candidate_novelty_distance_to_anchor",
        "candidate_distance_to_anchor",
        "retained_best_match_ratio",
        "selected_start_match_ratio",
        "selected_headroom_vs_retained",
        "shallow_resume_best_match_ratio",
        "shallow_resume_minus_selected",
        "shallow_resume_minus_retained",
        "phasec_score_winner_candidate_final_match",
        "selected_minus_phasec_score_winner",
        "stage35_selected_archive_rank",
        "stage35_rounds_completed",
        "stage35_evals",
        "stage35_runtime_seconds",
        "stage35_archive_unique_keys",
        "stage35_archive_unique_seed_sources",
        "stage35_archive_unique_target_slices",
        "stage35_archive_mean_substitution_hamming",
        "stage35_archive_max_substitution_hamming",
        "stage35_best_depth",
        "stage35_best_source_rank",
        "stage35_best_target_slice",
        "stage35_baseline_score",
        "stage35_best_score",
        "stage35_best_minus_baseline_score",
        "stage35_baseline_search_score",
        "stage35_best_search_score",
        "stage35_best_minus_baseline_search_score",
        "stage35_mini_search_rows_kept",
    ]
    categorical_features = [
        "robustness_stratum",
        "selected_source",
        "selected_lane",
        "stage35_accept_reason",
        "stage35_best_seed_source",
        "stage35_best_stage3_source",
        "stage35_best_move_type",
    ]
    single_scans = scan_single_rules(
        supervised_rows,
        numeric_features=numeric_features,
        categorical_features=categorical_features,
    )
    two_feature_scans = scan_two_feature_rules(
        supervised_rows,
        numeric_features=numeric_features,
        categorical_features=categorical_features,
    )
    single_perfect = [
        row
        for row in single_scans
        if _safe_int(row.get("false_positive")) == 0
        and _safe_int(row.get("false_negative")) == 0
    ]
    two_perfect = [
        row
        for row in two_feature_scans
        if _safe_int(row.get("false_positive")) == 0
        and _safe_int(row.get("false_negative")) == 0
    ]
    accepted_positive_rows = [
        row for row in feature_rows if str(row.get("outcome_class")) == "accepted_positive"
    ]
    accepted_regression_rows = [
        row for row in feature_rows if str(row.get("outcome_class")) == "accepted_regression"
    ]
    guard_failed_rows = [
        row for row in feature_rows if str(row.get("outcome_class")) == "guard_failed"
    ]
    best_single = single_scans[0] if single_scans else {}
    best_two = two_feature_scans[0] if two_feature_scans else {}
    recommendation = (
        "close_broad_policy_widening_after_offline_lead"
        if not single_perfect
        else "treat_best_separator_as_posthoc_lead_only"
    )
    summary = {
        "run_label": RUN_LABEL,
        "status": "completed",
        "output_dir": _repo_rel(output_dir),
        "robustness_rows_path": _repo_rel(rows_path),
        "row_count": len(feature_rows),
        "supervised_selected_rows": len(supervised_rows),
        "accepted_positive_rows": len(accepted_positive_rows),
        "accepted_regression_rows": len(accepted_regression_rows),
        "guard_failed_rows": len(guard_failed_rows),
        "outcome_class_counts": _counts_by(feature_rows, "outcome_class"),
        "regression_stratum_counts": _counts_by(
            accepted_regression_rows, "robustness_stratum"
        ),
        "guard_failed_stratum_counts": _counts_by(guard_failed_rows, "robustness_stratum"),
        "numeric_feature_count": len(numeric_features),
        "categorical_feature_count": len(categorical_features),
        "single_rule_scan_count": len(single_scans),
        "two_feature_scan_count": len(two_feature_scans),
        "single_perfect_separator_count": len(single_perfect),
        "two_feature_perfect_separator_count": len(two_perfect),
        "best_single_rule": _rule_text(best_single) if best_single else "",
        "best_single_rule_true_positive": _safe_int(best_single.get("true_positive")),
        "best_single_rule_false_positive": _safe_int(best_single.get("false_positive")),
        "best_single_rule_false_negative": _safe_int(best_single.get("false_negative")),
        "best_two_feature_rule": _rule_text(best_two) if best_two else "",
        "best_two_feature_rule_true_positive": _safe_int(best_two.get("true_positive")),
        "best_two_feature_rule_false_positive": _safe_int(best_two.get("false_positive")),
        "best_two_feature_rule_false_negative": _safe_int(best_two.get("false_negative")),
        "interpretation": (
            "posthoc_boundary_audit_no_runtime_authorization"
        ),
        "recommended_next": recommendation,
        "updated_utc": _utc_now_text(),
    }
    feature_summaries = summarize_features(supervised_rows, numeric_features)
    _write_csv(output_dir / "stage35_frontier_space_acceptance_boundary_feature_rows.csv", feature_rows)
    _write_csv(output_dir / "stage35_frontier_space_acceptance_boundary_feature_summary_rows.csv", feature_summaries)
    _write_csv(output_dir / "stage35_frontier_space_acceptance_boundary_single_rule_scan_rows.csv", single_scans)
    _write_csv(output_dir / "stage35_frontier_space_acceptance_boundary_two_feature_scan_rows.csv", two_feature_scans)
    _write_json(output_dir / "stage35_frontier_space_acceptance_boundary_summary.json", summary)
    (output_dir / "stage35_frontier_space_acceptance_boundary_readout.md").write_text(
        build_readout(
            summary=summary,
            single_scans=single_scans,
            two_feature_scans=two_feature_scans,
        ),
        encoding="utf-8",
    )
    print(json.dumps(summary, sort_keys=True), flush=True)
    return summary


def main() -> None:
    run_extract()


if __name__ == "__main__":
    main()
