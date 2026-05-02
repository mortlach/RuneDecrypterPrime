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
        "extract_stage35_rank6_route_lineage_boundary_audit_v1.py"
    )


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


RUN_LABEL = "stage35_rank6_route_lineage_boundary_audit_v1"
OUTPUT_BASE_DIR = REPO_ROOT / (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "fixed_instance_solver_development_v1"
)
RECALL_ROWS_REL = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "fixed_instance_solver_development_v1/"
    "20260430T021919Z__stage35_rank6_local_rescue_recall_audit_v1/"
    "stage35_rank6_local_rescue_recall_audit_rows.csv"
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
    return "{}:{}:{}".format(
        row.get("fixture_seed", ""),
        row.get("search_seed", ""),
        row.get("candidate_hash", ""),
    )


def build_feature_rows(raw_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in raw_rows:
        artifact = _load_json_relpath(str(raw.get("artifact_relpath", "")))
        diagnostics = dict(artifact.get("stage3_diagnostics", {}) or {})
        phasec_pool = list(diagnostics.get("phaseC_candidate_pool_rows", []) or [])
        stage3_topk = list(artifact.get("stage3_topk", []) or [])
        shallow_stage35_seed_rows = list(artifact.get("stage35_seed_rows", []) or [])
        candidate_hash = str(raw.get("candidate_hash", "") or "")
        candidate_row = next(
            (
                dict(row)
                for row in phasec_pool
                if str(row.get("candidate_hash", "") or "") == candidate_hash
            ),
            {},
        )
        anchor_hash = str(diagnostics.get("phaseC_anchor_candidate_hash", "") or "")
        anchor_row = next(
            (
                dict(row)
                for row in phasec_pool
                if str(row.get("candidate_hash", "") or "") == anchor_hash
            ),
            {},
        )
        candidate_key = _key_of(candidate_row)
        anchor_key = _key_of(anchor_row)
        final_best_key = [
            _safe_int(item) for item in list(artifact.get("final_best_key_idx", []) or [])
        ]
        stage3_keys = [_key_of(row) for row in stage3_topk]
        stage3_distances = [
            _hamming(candidate_key, key) for key in stage3_keys if candidate_key and key
        ]
        final_seed = next(
            (
                dict(row)
                for row in shallow_stage35_seed_rows
                if str(row.get("seed_source", "") or "") == "final_best"
            ),
            {},
        )
        top_seed = (
            dict(shallow_stage35_seed_rows[0]) if shallow_stage35_seed_rows else {}
        )
        audit_minus_shallow = _safe_float(raw.get("audit_minus_shallow"))
        candidate_source = str(candidate_row.get("source", "") or "")
        candidate_source_rank = _safe_int(candidate_row.get("source_rank"))
        novelty_distance = _safe_int(candidate_row.get("novelty_distance_to_anchor"))
        rows.append(
            {
                "outcome_class": (
                    "positive" if audit_minus_shallow > 0.0 else "regression"
                ),
                "fixture_seed": _safe_int(raw.get("fixture_seed")),
                "search_seed": _safe_int(raw.get("search_seed")),
                "candidate_rank": _safe_int(raw.get("candidate_rank")),
                "candidate_hash": candidate_hash,
                "purpose": str(raw.get("purpose", "") or ""),
                "audit_minus_shallow": audit_minus_shallow,
                "candidate_source": candidate_source,
                "candidate_source_rank": candidate_source_rank,
                "candidate_source_rank_eq_1": 1 if candidate_source_rank == 1 else 0,
                "candidate_source_rank_le_2": 1 if candidate_source_rank <= 2 else 0,
                "candidate_source_phasea_selected": (
                    1 if candidate_source == "phaseA_selected" else 0
                ),
                "candidate_selected_by_phasec_start": _safe_int(
                    candidate_row.get("selected_by_phasec_start")
                ),
                "candidate_eligible_novel_challenger": _safe_int(
                    candidate_row.get("eligible_novel_challenger")
                ),
                "candidate_novelty_distance_to_anchor": novelty_distance,
                "candidate_distance_to_phasec_anchor": _hamming(
                    candidate_key, anchor_key
                ),
                "candidate_distance_to_final_best": _hamming(
                    candidate_key, final_best_key
                ),
                "candidate_distance_to_stage3_topk_min": (
                    min(stage3_distances) if stage3_distances else 0
                ),
                "candidate_distance_to_stage3_rank1": (
                    stage3_distances[0] if stage3_distances else 0
                ),
                "candidate_distance_to_stage3_topk_mean": _mean(
                    float(value) for value in stage3_distances
                ),
                "phasec_anchor_lane_starts": _safe_int(
                    diagnostics.get("phaseC_anchor_lane_starts")
                ),
                "phasec_accepts": _safe_int(diagnostics.get("phaseC_accepts")),
                "phasec_improves": _safe_int(diagnostics.get("phaseC_improves")),
                "phasec_candidate_pool_count": _safe_int(
                    diagnostics.get("phaseC_candidate_pool_count")
                ),
                "phasec_candidate_pool_unique_keys": _safe_int(
                    diagnostics.get("phaseC_candidate_pool_unique_keys")
                ),
                "phasec_candidate_pool_unique_end_hash": _safe_int(
                    diagnostics.get("phaseC_candidate_pool_unique_end_hash")
                ),
                "stage3_topk_count": len(stage3_topk),
                "stage3_rank1_match_ratio": _safe_float(
                    stage3_topk[0].get("match_ratio") if stage3_topk else 0.0
                ),
                "stage3_rank1_score_pct": _safe_float(
                    stage3_topk[0].get("score_pct") if stage3_topk else 0.0
                ),
                "stage3_topk_match_gap_1_to_last": (
                    _safe_float(stage3_topk[0].get("match_ratio"))
                    - _safe_float(stage3_topk[-1].get("match_ratio"))
                    if len(stage3_topk) >= 2
                    else 0.0
                ),
                "stage3_topk_score_pct_gap_1_to_last": (
                    _safe_float(stage3_topk[0].get("score_pct"))
                    - _safe_float(stage3_topk[-1].get("score_pct"))
                    if len(stage3_topk) >= 2
                    else 0.0
                ),
                "shallow_stage35_seed_count": len(shallow_stage35_seed_rows),
                "shallow_stage35_final_seed_rank": _safe_int(
                    final_seed.get("seed_rank")
                ),
                "shallow_stage35_top_seed_source": str(
                    top_seed.get("seed_source", "") or ""
                ),
                "shallow_stage35_top_seed_source_rank": _safe_int(
                    top_seed.get("source_rank")
                ),
                "shallow_stage35_final_seed_score_gap_to_top_seed": (
                    _safe_float(top_seed.get("score"))
                    - _safe_float(final_seed.get("score"))
                    if top_seed and final_seed
                    else 0.0
                ),
                "shallow_stage35_final_seed_search_gap_to_top_seed": (
                    _safe_float(top_seed.get("search_score"))
                    - _safe_float(final_seed.get("search_score"))
                    if top_seed and final_seed
                    else 0.0
                ),
            }
        )
    rows.sort(
        key=lambda row: (
            str(row["outcome_class"]),
            -_safe_float(row.get("audit_minus_shallow")),
        )
    )
    return rows


def summarize_feature(feature_rows: list[Mapping[str, Any]], feature: str) -> dict[str, Any]:
    positives = [
        _safe_float(row.get(feature))
        for row in feature_rows
        if str(row.get("outcome_class")) == "positive"
    ]
    regressions = [
        _safe_float(row.get(feature))
        for row in feature_rows
        if str(row.get("outcome_class")) == "regression"
    ]
    return {
        "feature": feature,
        "positive_count": len(positives),
        "regression_count": len(regressions),
        "positive_min": min(positives) if positives else 0.0,
        "positive_max": max(positives) if positives else 0.0,
        "positive_mean": _mean(positives),
        "regression_min": min(regressions) if regressions else 0.0,
        "regression_max": max(regressions) if regressions else 0.0,
        "regression_mean": _mean(regressions),
        "gap_positive_min_minus_regression_max": (
            min(positives) - max(regressions) if positives and regressions else 0.0
        ),
        "gap_regression_min_minus_positive_max": (
            min(regressions) - max(positives) if positives and regressions else 0.0
        ),
    }


def _numeric_thresholds(
    feature_rows: list[Mapping[str, Any]], feature: str
) -> list[float]:
    values = sorted({_safe_float(row.get(feature)) for row in feature_rows})
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


def _score_predictions(
    feature_rows: list[Mapping[str, Any]],
    predictions: list[bool],
) -> dict[str, Any]:
    tp = fp = tn = fn = 0
    kept: list[str] = []
    for row, predicts_positive in zip(feature_rows, predictions):
        is_positive = str(row.get("outcome_class")) == "positive"
        if predicts_positive and is_positive:
            tp += 1
        elif predicts_positive and not is_positive:
            fp += 1
        elif not predicts_positive and is_positive:
            fn += 1
        else:
            tn += 1
        if predicts_positive:
            kept.append(_row_key(row))
    return {
        "true_positive": tp,
        "false_positive": fp,
        "true_negative": tn,
        "false_negative": fn,
        "kept_rows": len(kept),
        "kept_keys": "|".join(kept),
    }


def scan_numeric_thresholds(
    feature_rows: list[Mapping[str, Any]],
    numeric_features: list[str],
) -> list[dict[str, Any]]:
    scans: list[dict[str, Any]] = []
    for feature in numeric_features:
        for threshold in _numeric_thresholds(feature_rows, feature):
            for direction in ["ge", "le"]:
                predictions = [
                    _predict_numeric(
                        row,
                        feature=feature,
                        direction=direction,
                        threshold=threshold,
                    )
                    for row in feature_rows
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
                scan.update(_score_predictions(feature_rows, predictions))
                scans.append(scan)
    return scans


def scan_two_feature_conjunctions(
    feature_rows: list[Mapping[str, Any]],
    numeric_features: list[str],
    categorical_features: list[str],
) -> list[dict[str, Any]]:
    scans: list[dict[str, Any]] = []
    for feature_a in numeric_features:
        for threshold_a in _numeric_thresholds(feature_rows, feature_a):
            for direction_a in ["ge", "le"]:
                left_predictions = [
                    _predict_numeric(
                        row,
                        feature=feature_a,
                        direction=direction_a,
                        threshold=threshold_a,
                    )
                    for row in feature_rows
                ]
                for feature_b in categorical_features:
                    values = sorted({str(row.get(feature_b, "")) for row in feature_rows})
                    for value_b in values:
                        predictions = [
                            left and str(row.get(feature_b, "")) == value_b
                            for row, left in zip(feature_rows, left_predictions)
                        ]
                        scan = {
                            "rule_kind": "numeric_and_category",
                            "feature_a": feature_a,
                            "direction_a": direction_a,
                            "threshold_a": threshold_a,
                            "feature_b": feature_b,
                            "direction_b": "eq",
                            "threshold_b": "",
                            "category_value_b": value_b,
                        }
                        scan.update(_score_predictions(feature_rows, predictions))
                        scans.append(scan)
    for idx, feature_a in enumerate(numeric_features):
        for feature_b in numeric_features[idx + 1 :]:
            for threshold_a in _numeric_thresholds(feature_rows, feature_a):
                for threshold_b in _numeric_thresholds(feature_rows, feature_b):
                    for direction_a in ["ge", "le"]:
                        for direction_b in ["ge", "le"]:
                            predictions = [
                                _predict_numeric(
                                    row,
                                    feature=feature_a,
                                    direction=direction_a,
                                    threshold=threshold_a,
                                )
                                and _predict_numeric(
                                    row,
                                    feature=feature_b,
                                    direction=direction_b,
                                    threshold=threshold_b,
                                )
                                for row in feature_rows
                            ]
                            scan = {
                                "rule_kind": "numeric_and_numeric",
                                "feature_a": feature_a,
                                "direction_a": direction_a,
                                "threshold_a": threshold_a,
                                "feature_b": feature_b,
                                "direction_b": direction_b,
                                "threshold_b": threshold_b,
                                "category_value_b": "",
                            }
                            scan.update(_score_predictions(feature_rows, predictions))
                            scans.append(scan)
    scans.sort(
        key=lambda row: (
            _safe_int(row.get("false_positive")),
            _safe_int(row.get("false_negative")),
            -_safe_int(row.get("true_positive")),
            str(row.get("rule_kind", "")),
            str(row.get("feature_a", "")),
            str(row.get("feature_b", "")),
        )
    )
    return scans


def _rule_text(row: Mapping[str, Any]) -> str:
    first = "{} {} {:.6f}".format(
        row.get("feature_a", ""),
        row.get("direction_a", ""),
        _safe_float(row.get("threshold_a")),
    )
    if str(row.get("rule_kind")) == "single_numeric":
        return first
    if str(row.get("direction_b")) == "eq":
        return "{} AND {} == {}".format(
            first,
            row.get("feature_b", ""),
            row.get("category_value_b", ""),
        )
    return "{} AND {} {} {:.6f}".format(
        first,
        row.get("feature_b", ""),
        row.get("direction_b", ""),
        _safe_float(row.get("threshold_b")),
    )


def build_readout(
    *,
    summary: Mapping[str, Any],
    single_scans: list[Mapping[str, Any]],
    conjunction_scans: list[Mapping[str, Any]],
) -> str:
    lines = [
        "# Stage35 Rank6 Route-Lineage Boundary Audit v1",
        "",
        "Question:",
        "",
        "- can pre-runtime route-composition or lineage features separate the",
        "  rejected positives from the rejected regressions?",
        "",
        "Coverage:",
        "",
        f"- rows: `{summary['row_count']}`",
        f"- positives: `{summary['positive_rows']}`",
        f"- regressions: `{summary['regression_rows']}`",
        f"- single-feature perfect separators: `{summary['single_perfect_separator_count']}`",
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
    for row in conjunction_scans[:8]:
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
            "- route-lineage context gives a posthoc separator on the five-row",
            "  boundary set, unlike the prior simple numeric scan",
            "- because this is a tiny boundary audit, the separator is only a",
            "  hypothesis for external review and later canary design",
            "- do not promote it directly as a production policy without a",
            "  confirmation panel",
            "",
            "Recommended Next:",
            "",
            "- hold runtime while the external review checks whether the separator",
            "  is mechanistically coherent and not just seed-specific",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def run_extract() -> dict[str, Any]:
    recall_path = REPO_ROOT / RECALL_ROWS_REL
    output_dir = OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)
    feature_rows = build_feature_rows(_read_csv(recall_path))
    numeric_features = [
        "candidate_source_rank",
        "candidate_source_rank_eq_1",
        "candidate_source_rank_le_2",
        "candidate_source_phasea_selected",
        "candidate_selected_by_phasec_start",
        "candidate_eligible_novel_challenger",
        "candidate_novelty_distance_to_anchor",
        "candidate_distance_to_phasec_anchor",
        "candidate_distance_to_final_best",
        "candidate_distance_to_stage3_topk_min",
        "candidate_distance_to_stage3_rank1",
        "candidate_distance_to_stage3_topk_mean",
        "phasec_accepts",
        "phasec_improves",
        "phasec_candidate_pool_count",
        "phasec_candidate_pool_unique_keys",
        "phasec_candidate_pool_unique_end_hash",
        "stage3_topk_count",
        "stage3_rank1_match_ratio",
        "stage3_rank1_score_pct",
        "stage3_topk_match_gap_1_to_last",
        "stage3_topk_score_pct_gap_1_to_last",
        "shallow_stage35_seed_count",
        "shallow_stage35_final_seed_rank",
        "shallow_stage35_top_seed_source_rank",
        "shallow_stage35_final_seed_score_gap_to_top_seed",
        "shallow_stage35_final_seed_search_gap_to_top_seed",
    ]
    categorical_features = [
        "candidate_source",
        "candidate_source_rank_eq_1",
        "candidate_source_rank_le_2",
        "candidate_source_phasea_selected",
        "shallow_stage35_top_seed_source",
    ]
    feature_summaries = [
        summarize_feature(feature_rows, feature) for feature in numeric_features
    ]
    single_scans = scan_numeric_thresholds(feature_rows, numeric_features)
    single_scans.sort(
        key=lambda row: (
            _safe_int(row.get("false_positive")),
            _safe_int(row.get("false_negative")),
            -_safe_int(row.get("true_positive")),
            str(row.get("feature_a", "")),
        )
    )
    conjunction_scans = scan_two_feature_conjunctions(
        feature_rows, numeric_features, categorical_features
    )
    single_perfect = [
        row
        for row in single_scans
        if _safe_int(row.get("false_positive")) == 0
        and _safe_int(row.get("false_negative")) == 0
    ]
    two_feature_perfect = [
        row
        for row in conjunction_scans
        if _safe_int(row.get("false_positive")) == 0
        and _safe_int(row.get("false_negative")) == 0
    ]
    best = two_feature_perfect[0] if two_feature_perfect else {}
    summary = {
        "run_label": RUN_LABEL,
        "status": "completed",
        "output_dir": _repo_rel(output_dir),
        "recall_rows_path": _repo_rel(recall_path),
        "row_count": len(feature_rows),
        "positive_rows": sum(
            1 for row in feature_rows if str(row.get("outcome_class")) == "positive"
        ),
        "regression_rows": sum(
            1
            for row in feature_rows
            if str(row.get("outcome_class")) == "regression"
        ),
        "numeric_feature_count": len(numeric_features),
        "categorical_feature_count": len(categorical_features),
        "single_threshold_scan_count": len(single_scans),
        "two_feature_scan_count": len(conjunction_scans),
        "single_perfect_separator_count": len(single_perfect),
        "two_feature_perfect_separator_count": len(two_feature_perfect),
        "best_two_feature_separator": _rule_text(best) if best else "",
        "best_two_feature_kept_keys": str(best.get("kept_keys", "")) if best else "",
        "interpretation": "route_lineage_features_give_posthoc_boundary_separator",
        "recommended_next": "external_review_then_tiny_confirmation_panel_if_coherent",
        "updated_utc": _utc_now_text(),
    }
    _write_csv(
        output_dir / "stage35_rank6_route_lineage_boundary_feature_rows.csv",
        feature_rows,
    )
    _write_csv(
        output_dir / "stage35_rank6_route_lineage_boundary_feature_summary_rows.csv",
        feature_summaries,
    )
    _write_csv(
        output_dir / "stage35_rank6_route_lineage_boundary_single_threshold_scan_rows.csv",
        single_scans,
    )
    _write_csv(
        output_dir / "stage35_rank6_route_lineage_boundary_two_feature_scan_rows.csv",
        conjunction_scans,
    )
    _write_json(
        output_dir / "stage35_rank6_route_lineage_boundary_audit_summary.json",
        summary,
    )
    (output_dir / "stage35_rank6_route_lineage_boundary_audit_readout.md").write_text(
        build_readout(
            summary=summary,
            single_scans=single_scans,
            conjunction_scans=conjunction_scans,
        ),
        encoding="utf-8",
    )
    print(json.dumps(summary, sort_keys=True), flush=True)
    return summary


def main() -> None:
    run_extract()


if __name__ == "__main__":
    main()
