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
        "extract_stage35_rank6_boundary_feature_audit_v1.py"
    )


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


RUN_LABEL = "stage35_rank6_boundary_feature_audit_v1"
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


def _read_json_relpath(relpath: str) -> dict[str, Any]:
    path = REPO_ROOT / relpath.replace("\\", "/")
    return dict(json.loads(path.read_text(encoding="utf-8")))


def _as_json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


def build_feature_rows(raw_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in raw_rows:
        cell_summary = _read_json_relpath(str(raw.get("cell_output_dir", "")) + "/summary.json")
        stage35 = dict(cell_summary.get("stage35", {}) or {})
        seed_source_counts = dict(stage35.get("seed_source_counts", {}) or {})
        audit_minus_shallow = _safe_float(raw.get("audit_minus_shallow"))
        selected_score = _safe_float(cell_summary.get("selected_candidate_final_score"))
        resume_score = _safe_float(cell_summary.get("resume_best_score"))
        baseline_score = _safe_float(stage35.get("baseline_score"))
        best_score = _safe_float(stage35.get("best_score"))
        baseline_search_score = _safe_float(stage35.get("baseline_search_score"))
        best_search_score = _safe_float(stage35.get("best_search_score"))
        rows.append(
            {
                "outcome_class": "positive" if audit_minus_shallow > 0.0 else "regression",
                "fixture_seed": _safe_int(raw.get("fixture_seed")),
                "search_seed": _safe_int(raw.get("search_seed")),
                "candidate_rank": _safe_int(raw.get("candidate_rank")),
                "candidate_hash": str(raw.get("candidate_hash", "") or ""),
                "purpose": str(raw.get("purpose", "") or ""),
                "selected_start_match_ratio": _safe_float(
                    raw.get("selected_start_match_ratio")
                ),
                "retained_best_match_ratio": _safe_float(
                    raw.get("retained_best_match_ratio")
                ),
                "shallow_resume_best_match_ratio": _safe_float(
                    raw.get("shallow_resume_best_match_ratio")
                ),
                "audit_resume_best_match_ratio": _safe_float(
                    raw.get("audit_resume_best_match_ratio")
                ),
                "shallow_minus_selected": _safe_float(raw.get("shallow_minus_selected")),
                "audit_minus_shallow": audit_minus_shallow,
                "audit_minus_selected": _safe_float(raw.get("audit_minus_selected")),
                "audit_minus_retained": _safe_float(raw.get("audit_resume_best_match_ratio"))
                - _safe_float(raw.get("retained_best_match_ratio")),
                "selected_headroom_vs_retained": _safe_float(
                    raw.get("selected_start_match_ratio")
                )
                - _safe_float(raw.get("retained_best_match_ratio")),
                "shallow_minus_retained": _safe_float(
                    raw.get("shallow_resume_best_match_ratio")
                )
                - _safe_float(raw.get("retained_best_match_ratio")),
                "selected_candidate_final_score": selected_score,
                "resume_best_score": resume_score,
                "resume_score_minus_selected_score": resume_score - selected_score,
                "stage35_baseline_score": baseline_score,
                "stage35_best_score": best_score,
                "stage35_best_minus_baseline_score": best_score - baseline_score,
                "stage35_baseline_search_score": baseline_search_score,
                "stage35_best_search_score": best_search_score,
                "stage35_best_minus_baseline_search_score": best_search_score
                - baseline_search_score,
                "stage35_best_depth": _safe_int(stage35.get("best_depth")),
                "stage35_archive_mean_substitution_hamming": _safe_float(
                    stage35.get("archive_mean_substitution_hamming")
                ),
                "stage35_archive_max_substitution_hamming": _safe_int(
                    stage35.get("archive_max_substitution_hamming")
                ),
                "stage35_archive_unique_keys": _safe_int(
                    stage35.get("archive_unique_keys")
                ),
                "stage35_archive_unique_seed_sources": _safe_int(
                    stage35.get("archive_unique_seed_sources")
                ),
                "stage35_archive_unique_target_slices": _safe_int(
                    stage35.get("archive_unique_target_slices")
                ),
                "stage35_seed_count": _safe_int(stage35.get("seed_count")),
                "stage35_seed_rows_scored": _safe_int(stage35.get("seed_rows_scored")),
                "stage35_evals": _safe_int(stage35.get("evals")),
                "stage35_runtime_seconds": _safe_float(stage35.get("runtime_seconds")),
                "stage35_best_seed_source": str(stage35.get("best_seed_source", "") or ""),
                "stage35_best_move_type": str(stage35.get("best_move_type", "") or ""),
                "stage35_best_target_slice": str(stage35.get("best_target_slice", "") or ""),
                "stage35_seed_source_counts_json": _as_json_text(seed_source_counts),
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


def scan_thresholds(
    feature_rows: list[Mapping[str, Any]],
    numeric_features: list[str],
) -> list[dict[str, Any]]:
    scans: list[dict[str, Any]] = []
    for feature in numeric_features:
        values = sorted({_safe_float(row.get(feature)) for row in feature_rows})
        if len(values) < 2:
            continue
        thresholds = [(values[idx] + values[idx + 1]) / 2.0 for idx in range(len(values) - 1)]
        for threshold in thresholds:
            for direction in ["ge", "le"]:
                tp = fp = tn = fn = 0
                kept: list[str] = []
                for row in feature_rows:
                    value = _safe_float(row.get(feature))
                    predicts_positive = value >= threshold if direction == "ge" else value <= threshold
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
                        kept.append(
                            f"{row.get('fixture_seed')}/{row.get('search_seed')}:{row.get('candidate_hash')}"
                        )
                scans.append(
                    {
                        "feature": feature,
                        "direction": direction,
                        "threshold": threshold,
                        "true_positive": tp,
                        "false_positive": fp,
                        "true_negative": tn,
                        "false_negative": fn,
                        "kept_rows": len(kept),
                        "kept_keys": "|".join(kept),
                    }
                )
    scans.sort(
        key=lambda row: (
            _safe_int(row.get("false_positive")),
            _safe_int(row.get("false_negative")),
            -_safe_int(row.get("true_positive")),
            str(row.get("feature", "")),
        )
    )
    return scans


def build_readout(
    *,
    summary: Mapping[str, Any],
    feature_summaries: list[Mapping[str, Any]],
    threshold_scans: list[Mapping[str, Any]],
) -> str:
    lines = [
        "# Stage35 Rank6 Boundary Feature Audit v1",
        "",
        "Question:",
        "",
        "- what boundary features separate the three rejected positives from the",
        "  two rejected regressions without simply widening the policy?",
        "",
        "Coverage:",
        "",
        f"- rows: `{summary['row_count']}`",
        f"- positives: `{summary['positive_rows']}`",
        f"- regressions: `{summary['regression_rows']}`",
        "",
        "Best Threshold Sketches:",
        "",
    ]
    for row in threshold_scans[:8]:
        lines.append(
            "- `{}` `{}` `{:.6f}`: TP `{}`, FP `{}`, TN `{}`, FN `{}`".format(
                row["feature"],
                row["direction"],
                float(row["threshold"]),
                row["true_positive"],
                row["false_positive"],
                row["true_negative"],
                row["false_negative"],
            )
        )
    lines.extend(["", "Largest Feature Gaps:", ""])
    ranked_features = sorted(
        feature_summaries,
        key=lambda row: max(
            abs(float(row["gap_positive_min_minus_regression_max"])),
            abs(float(row["gap_regression_min_minus_positive_max"])),
        ),
        reverse=True,
    )
    for row in ranked_features[:8]:
        lines.append(
            "- `{}`: positive range `[{:.6f}, {:.6f}]`, regression range `[{:.6f}, {:.6f}]`".format(
                row["feature"],
                float(row["positive_min"]),
                float(row["positive_max"]),
                float(row["regression_min"]),
                float(row["regression_max"]),
            )
        )
    lines.extend(
        [
            "",
            "Interpretation:",
            "",
            "- this is a five-row posthoc boundary audit, so even perfect",
            "  separators are hypotheses only",
            "- use the strongest non-seed separator as the next offline rule",
            "  candidate, not as runtime authorization",
            "",
            "Recommended Next:",
            "",
            "- write a compact rule-revision note using the best boundary features",
            "  and decide whether it is coherent enough for a later tiny canary",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def run_extract() -> dict[str, Any]:
    recall_path = REPO_ROOT / RECALL_ROWS_REL
    output_dir = OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)
    feature_rows = build_feature_rows(_read_csv(recall_path))
    numeric_features = [
        "selected_start_match_ratio",
        "retained_best_match_ratio",
        "shallow_resume_best_match_ratio",
        "shallow_minus_selected",
        "audit_minus_selected",
        "audit_minus_retained",
        "selected_headroom_vs_retained",
        "shallow_minus_retained",
        "selected_candidate_final_score",
        "resume_best_score",
        "resume_score_minus_selected_score",
        "stage35_baseline_score",
        "stage35_best_score",
        "stage35_best_minus_baseline_score",
        "stage35_baseline_search_score",
        "stage35_best_search_score",
        "stage35_best_minus_baseline_search_score",
        "stage35_best_depth",
        "stage35_archive_mean_substitution_hamming",
        "stage35_archive_max_substitution_hamming",
        "stage35_archive_unique_keys",
        "stage35_archive_unique_seed_sources",
        "stage35_archive_unique_target_slices",
        "stage35_seed_count",
        "stage35_seed_rows_scored",
        "stage35_evals",
        "stage35_runtime_seconds",
    ]
    feature_summaries = [
        summarize_feature(feature_rows, feature) for feature in numeric_features
    ]
    threshold_scans = scan_thresholds(feature_rows, numeric_features)
    perfect_scans = [
        row
        for row in threshold_scans
        if _safe_int(row.get("false_positive")) == 0
        and _safe_int(row.get("false_negative")) == 0
    ]
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
            1 for row in feature_rows if str(row.get("outcome_class")) == "regression"
        ),
        "numeric_feature_count": len(numeric_features),
        "threshold_scan_count": len(threshold_scans),
        "perfect_separator_count": len(perfect_scans),
        "best_separator_feature": str(perfect_scans[0]["feature"]) if perfect_scans else "",
        "best_separator_direction": str(perfect_scans[0]["direction"]) if perfect_scans else "",
        "best_separator_threshold": (
            float(perfect_scans[0]["threshold"]) if perfect_scans else 0.0
        ),
        "interpretation": "posthoc_boundary_feature_audit_hypothesis_only",
        "recommended_next": "write_rule_revision_note_before_more_runtime",
        "updated_utc": _utc_now_text(),
    }
    _write_csv(
        output_dir / "stage35_rank6_boundary_feature_rows.csv",
        feature_rows,
    )
    _write_csv(
        output_dir / "stage35_rank6_boundary_feature_summary_rows.csv",
        feature_summaries,
    )
    _write_csv(
        output_dir / "stage35_rank6_boundary_feature_threshold_scan_rows.csv",
        threshold_scans,
    )
    _write_json(
        output_dir / "stage35_rank6_boundary_feature_audit_summary.json",
        summary,
    )
    (output_dir / "stage35_rank6_boundary_feature_audit_readout.md").write_text(
        build_readout(
            summary=summary,
            feature_summaries=feature_summaries,
            threshold_scans=threshold_scans,
        ),
        encoding="utf-8",
    )
    print(json.dumps(summary, sort_keys=True), flush=True)
    return summary


def main() -> None:
    run_extract()


if __name__ == "__main__":
    main()
