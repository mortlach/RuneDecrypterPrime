from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


RUN_LABEL = "scorer_feature_overlap_v1"
INPUT_PAIR_FEATURES_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "scorer_component_feature_audit_v1/scorer_component_feature_audit_pair_features.csv"
)
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "scorer_feature_overlap_v1"
)

SELECTED_FEATURES = (
    "current_score",
    "span_raw_score",
    "span_quality",
    "word_ngram_trust_score",
    "word_ngram_n_positions",
    "repeated_3gram_rate",
    "repeated_4gram_rate",
    "max_ngram_repeat_count_5",
    "period_lane_repeat_rate_spread_p5",
    "period_lane_diversity_spread_p4",
)


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError("Could not locate repo root")


REPO_ROOT = _find_repo_root()
INPUT_PAIR_FEATURES = REPO_ROOT / INPUT_PAIR_FEATURES_REL
OUTPUT_DIR = REPO_ROOT / OUTPUT_DIR_REL

PAIR_FLAG_FIELDS = (
    "pair_id",
    "artifact_path",
    "fixture_id",
    "fixture_seed",
    "search_seed",
    "token_length",
    "winner_candidate_hash",
    "challenger_candidate_hash",
    "winner_token_hash",
    "challenger_token_hash",
    "truth_gap",
    "current_score_correct",
    "pair_group",
    "text_pair_key",
    "candidate_hash_pair_key",
)
for _feature in SELECTED_FEATURES:
    PAIR_FLAG_FIELDS += (
        f"{_feature}_prefers_truth_better",
        f"{_feature}_prefers_truth_worse",
        f"{_feature}_tie",
        f"{_feature}_missing",
    )

OVERLAP_FIELDS = (
    "feature_a",
    "feature_b",
    "scope",
    "pair_count",
    "current_misranked_count",
    "current_correct_control_count",
    "a_rescues",
    "b_rescues",
    "both_rescue",
    "a_only_rescue",
    "b_only_rescue",
    "either_rescue",
    "rescue_jaccard",
    "a_breaks",
    "b_breaks",
    "both_break",
    "a_only_break",
    "b_only_break",
    "either_break",
    "break_jaccard",
)

FEATURE_ROLLUP_FIELDS = (
    "feature_name",
    "scope",
    "pair_count",
    "current_misranked_count",
    "current_correct_control_count",
    "rescues",
    "breaks",
    "ties_on_misranked",
    "ties_on_controls",
    "missing_on_misranked",
    "missing_on_controls",
    "net",
    "dominant_rescue_text_pair_fraction",
    "dominant_break_text_pair_fraction",
)


def _utc_now_text() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _safe_float(value: Any) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return out if math.isfinite(out) else float("nan")


def _dominant_fraction(values: Sequence[str]) -> float:
    counts = Counter(str(value) for value in values if str(value))
    total = sum(counts.values())
    return float(max(counts.values()) / total) if total else 0.0


def _load_pair_feature_rows() -> list[dict[str, Any]]:
    with INPUT_PAIR_FEATURES.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def build_pair_flag_rows(pair_feature_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    selected = set(SELECTED_FEATURES)
    for row in pair_feature_rows:
        feature_name = str(row.get("feature_name", "") or "")
        pair_id = str(row.get("pair_id", "") or "")
        if feature_name not in selected or not pair_id:
            continue
        base = grouped.setdefault(
            pair_id,
            {
                "pair_id": pair_id,
                "artifact_path": str(row.get("artifact_path", "") or ""),
                "fixture_id": str(row.get("fixture_id", "") or ""),
                "fixture_seed": str(row.get("fixture_seed", "") or ""),
                "search_seed": str(row.get("search_seed", "") or ""),
                "token_length": str(row.get("token_length", "") or ""),
                "winner_candidate_hash": str(row.get("winner_candidate_hash", "") or ""),
                "challenger_candidate_hash": str(row.get("challenger_candidate_hash", "") or ""),
                "winner_token_hash": str(row.get("winner_token_hash", "") or ""),
                "challenger_token_hash": str(row.get("challenger_token_hash", "") or ""),
                "truth_gap": row.get("truth_gap", ""),
                "current_score_correct": row.get("current_score_correct", ""),
                "pair_group": str(row.get("pair_group", "") or ""),
                "text_pair_key": str(row.get("text_pair_key", "") or ""),
                "candidate_hash_pair_key": str(row.get("candidate_hash_pair_key", "") or ""),
            },
        )
        base[f"{feature_name}_prefers_truth_better"] = _safe_int(row.get("feature_prefers_truth_better"))
        base[f"{feature_name}_prefers_truth_worse"] = _safe_int(row.get("feature_prefers_truth_worse"))
        base[f"{feature_name}_tie"] = _safe_int(row.get("feature_tie"))
        base[f"{feature_name}_missing"] = _safe_int(row.get("feature_missing"))

    out: list[dict[str, Any]] = []
    for row in grouped.values():
        for feature in SELECTED_FEATURES:
            row.setdefault(f"{feature}_prefers_truth_better", 0)
            row.setdefault(f"{feature}_prefers_truth_worse", 0)
            row.setdefault(f"{feature}_tie", 0)
            row.setdefault(f"{feature}_missing", 1)
        out.append({field: row.get(field, "") for field in PAIR_FLAG_FIELDS})
    out.sort(key=lambda row: str(row.get("pair_id", "")))
    return out


def _is_misranked(row: Mapping[str, Any]) -> bool:
    return _safe_int(row.get("current_score_correct")) == 0


def _is_control(row: Mapping[str, Any]) -> bool:
    return _safe_int(row.get("current_score_correct")) == 1


def _rescue(row: Mapping[str, Any], feature: str) -> bool:
    return _is_misranked(row) and _safe_int(row.get(f"{feature}_prefers_truth_better")) == 1


def _break(row: Mapping[str, Any], feature: str) -> bool:
    return _is_control(row) and _safe_int(row.get(f"{feature}_prefers_truth_worse")) == 1


def _tie_on_group(row: Mapping[str, Any], feature: str) -> bool:
    return _safe_int(row.get(f"{feature}_tie")) == 1


def _missing_on_group(row: Mapping[str, Any], feature: str) -> bool:
    return _safe_int(row.get(f"{feature}_missing")) == 1


def _unique_text_scope(rows: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    out: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        out.setdefault(str(row.get("text_pair_key", "") or ""), row)
    return list(out.values())


def _scope_rows(rows: Sequence[Mapping[str, Any]], scope: str) -> list[Mapping[str, Any]]:
    if scope == "row_occurrence":
        return list(rows)
    if scope == "unique_text_pair":
        return _unique_text_scope(rows)
    raise ValueError(f"unknown scope: {scope}")


def build_feature_rollup_rows(pair_flag_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for scope in ("row_occurrence", "unique_text_pair"):
        rows = _scope_rows(pair_flag_rows, scope)
        for feature in SELECTED_FEATURES:
            misranked = [row for row in rows if _is_misranked(row)]
            controls = [row for row in rows if _is_control(row)]
            rescue_rows = [row for row in rows if _rescue(row, feature)]
            break_rows = [row for row in rows if _break(row, feature)]
            out.append(
                {
                    "feature_name": feature,
                    "scope": scope,
                    "pair_count": len(rows),
                    "current_misranked_count": len(misranked),
                    "current_correct_control_count": len(controls),
                    "rescues": len(rescue_rows),
                    "breaks": len(break_rows),
                    "ties_on_misranked": sum(int(_tie_on_group(row, feature)) for row in misranked),
                    "ties_on_controls": sum(int(_tie_on_group(row, feature)) for row in controls),
                    "missing_on_misranked": sum(int(_missing_on_group(row, feature)) for row in misranked),
                    "missing_on_controls": sum(int(_missing_on_group(row, feature)) for row in controls),
                    "net": len(rescue_rows) - len(break_rows),
                    "dominant_rescue_text_pair_fraction": _dominant_fraction(
                        [str(row.get("text_pair_key", "")) for row in rescue_rows]
                    ),
                    "dominant_break_text_pair_fraction": _dominant_fraction(
                        [str(row.get("text_pair_key", "")) for row in break_rows]
                    ),
                }
            )
    return out


def _jaccard(intersection_count: int, union_count: int) -> float:
    return float(intersection_count / union_count) if union_count else 0.0


def build_overlap_rows(pair_flag_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for scope in ("row_occurrence", "unique_text_pair"):
        rows = _scope_rows(pair_flag_rows, scope)
        for feature_a in SELECTED_FEATURES:
            for feature_b in SELECTED_FEATURES:
                a_rescue = [row for row in rows if _rescue(row, feature_a)]
                b_rescue = [row for row in rows if _rescue(row, feature_b)]
                both_rescue = [row for row in rows if _rescue(row, feature_a) and _rescue(row, feature_b)]
                a_only_rescue = [
                    row for row in rows if _rescue(row, feature_a) and not _rescue(row, feature_b)
                ]
                b_only_rescue = [
                    row for row in rows if _rescue(row, feature_b) and not _rescue(row, feature_a)
                ]
                either_rescue = [
                    row for row in rows if _rescue(row, feature_a) or _rescue(row, feature_b)
                ]

                a_break = [row for row in rows if _break(row, feature_a)]
                b_break = [row for row in rows if _break(row, feature_b)]
                both_break = [row for row in rows if _break(row, feature_a) and _break(row, feature_b)]
                a_only_break = [row for row in rows if _break(row, feature_a) and not _break(row, feature_b)]
                b_only_break = [row for row in rows if _break(row, feature_b) and not _break(row, feature_a)]
                either_break = [row for row in rows if _break(row, feature_a) or _break(row, feature_b)]

                out.append(
                    {
                        "feature_a": feature_a,
                        "feature_b": feature_b,
                        "scope": scope,
                        "pair_count": len(rows),
                        "current_misranked_count": sum(int(_is_misranked(row)) for row in rows),
                        "current_correct_control_count": sum(int(_is_control(row)) for row in rows),
                        "a_rescues": len(a_rescue),
                        "b_rescues": len(b_rescue),
                        "both_rescue": len(both_rescue),
                        "a_only_rescue": len(a_only_rescue),
                        "b_only_rescue": len(b_only_rescue),
                        "either_rescue": len(either_rescue),
                        "rescue_jaccard": _jaccard(len(both_rescue), len(either_rescue)),
                        "a_breaks": len(a_break),
                        "b_breaks": len(b_break),
                        "both_break": len(both_break),
                        "a_only_break": len(a_only_break),
                        "b_only_break": len(b_only_break),
                        "either_break": len(either_break),
                        "break_jaccard": _jaccard(len(both_break), len(either_break)),
                    }
                )
    return out


def _row_lookup(
    rows: Sequence[Mapping[str, Any]],
    *,
    feature_a: str,
    feature_b: str,
    scope: str,
) -> Mapping[str, Any]:
    for row in rows:
        if (
            str(row.get("feature_a", "")) == feature_a
            and str(row.get("feature_b", "")) == feature_b
            and str(row.get("scope", "")) == scope
        ):
            return row
    return {}


def build_summary(
    *,
    pair_flag_rows: Sequence[Mapping[str, Any]],
    feature_rollup_rows: Sequence[Mapping[str, Any]],
    overlap_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    row_scope = [row for row in feature_rollup_rows if str(row.get("scope", "")) == "row_occurrence"]
    unique_scope = [row for row in feature_rollup_rows if str(row.get("scope", "")) == "unique_text_pair"]
    top_row_features = sorted(
        row_scope,
        key=lambda row: (int(row.get("net", 0) or 0), int(row.get("rescues", 0) or 0)),
        reverse=True,
    )[:10]
    top_unique_features = sorted(
        unique_scope,
        key=lambda row: (int(row.get("net", 0) or 0), int(row.get("rescues", 0) or 0)),
        reverse=True,
    )[:10]
    span_word = _row_lookup(
        overlap_rows,
        feature_a="span_raw_score",
        feature_b="word_ngram_trust_score",
        scope="row_occurrence",
    )
    span_repeat = _row_lookup(
        overlap_rows,
        feature_a="span_raw_score",
        feature_b="repeated_3gram_rate",
        scope="row_occurrence",
    )
    return {
        "run_label": RUN_LABEL,
        "updated_utc": _utc_now_text(),
        "input_pair_features": INPUT_PAIR_FEATURES_REL,
        "output_dir": OUTPUT_DIR_REL,
        "runtime_behavior_changed": False,
        "truth_is_evaluation_only": True,
        "selected_features": list(SELECTED_FEATURES),
        "pair_count": len(pair_flag_rows),
        "unique_numeric_text_pair_count": len({str(row.get("text_pair_key", "")) for row in pair_flag_rows}),
        "current_score_misranked_pair_count": sum(int(_is_misranked(row)) for row in pair_flag_rows),
        "current_score_correct_control_pair_count": sum(int(_is_control(row)) for row in pair_flag_rows),
        "top_row_occurrence_features_by_net": [dict(row) for row in top_row_features],
        "top_unique_text_pair_features_by_net": [dict(row) for row in top_unique_features],
        "span_raw_vs_word_trust_row_overlap": dict(span_word),
        "span_raw_vs_repeated_3gram_row_overlap": dict(span_repeat),
        "interpretation_caveat": (
            "This is an overlap/correlation report for existing feature preferences, not a gate "
            "simulation and not a runtime scorer design."
        ),
    }


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields))
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_readout(summary: Mapping[str, Any]) -> str:
    span_word = dict(summary.get("span_raw_vs_word_trust_row_overlap", {}))
    span_repeat = dict(summary.get("span_raw_vs_repeated_3gram_row_overlap", {}))
    top_unique = list(summary.get("top_unique_text_pair_features_by_net", []))[:5]
    lines = [
        "# Scorer Feature Overlap v1",
        "",
        "## Purpose",
        "",
        "Measure overlap between S1b single-feature rescues and breaks.",
        "This is report-only S1 analysis, not a combined scorer or gate simulation.",
        "",
        "## Dataset",
        "",
        f"- pair rows: `{summary['pair_count']}`",
        f"- unique numeric text pairs: `{summary['unique_numeric_text_pair_count']}`",
        f"- current-score misranked pairs: `{summary['current_score_misranked_pair_count']}`",
        f"- current-score correct controls: `{summary['current_score_correct_control_pair_count']}`",
        "",
        "## Span raw vs word-ngram trust",
        "",
        f"- span rescues: `{span_word.get('a_rescues', 0)}`",
        f"- word-trust rescues: `{span_word.get('b_rescues', 0)}`",
        f"- both rescue: `{span_word.get('both_rescue', 0)}`",
        f"- span-only rescue: `{span_word.get('a_only_rescue', 0)}`",
        f"- word-only rescue: `{span_word.get('b_only_rescue', 0)}`",
        f"- either rescue: `{span_word.get('either_rescue', 0)}`",
        f"- span breaks: `{span_word.get('a_breaks', 0)}`",
        f"- word-trust breaks: `{span_word.get('b_breaks', 0)}`",
        f"- both break: `{span_word.get('both_break', 0)}`",
        "",
        "## Span raw vs repeated 3-gram",
        "",
        f"- span rescues: `{span_repeat.get('a_rescues', 0)}`",
        f"- repeated-3gram rescues: `{span_repeat.get('b_rescues', 0)}`",
        f"- both rescue: `{span_repeat.get('both_rescue', 0)}`",
        f"- either rescue: `{span_repeat.get('either_rescue', 0)}`",
        f"- span breaks: `{span_repeat.get('a_breaks', 0)}`",
        f"- repeated-3gram breaks: `{span_repeat.get('b_breaks', 0)}`",
        f"- both break: `{span_repeat.get('both_break', 0)}`",
        "",
        "## Top unique-pair features by net",
        "",
    ]
    for row in top_unique:
        lines.append(
            f"- `{row['feature_name']}`: rescues `{row['rescues']}`, breaks `{row['breaks']}`, net `{row['net']}`"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Use this as review evidence before S2. It can show whether features cover distinct failure subsets,",
            "but it does not establish a safe combined rule by itself.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_outputs() -> dict[str, Any]:
    print(f"[{RUN_LABEL}] loading {INPUT_PAIR_FEATURES_REL}")
    pair_feature_rows = _load_pair_feature_rows()
    pair_flag_rows = build_pair_flag_rows(pair_feature_rows)
    feature_rollup_rows = build_feature_rollup_rows(pair_flag_rows)
    overlap_rows = build_overlap_rows(pair_flag_rows)
    summary = build_summary(
        pair_flag_rows=pair_flag_rows,
        feature_rollup_rows=feature_rollup_rows,
        overlap_rows=overlap_rows,
    )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _write_csv(OUTPUT_DIR / "scorer_feature_overlap_pair_flags.csv", pair_flag_rows, PAIR_FLAG_FIELDS)
    _write_csv(OUTPUT_DIR / "scorer_feature_overlap_feature_rollup.csv", feature_rollup_rows, FEATURE_ROLLUP_FIELDS)
    _write_csv(OUTPUT_DIR / "scorer_feature_overlap_matrix.csv", overlap_rows, OVERLAP_FIELDS)
    _write_json(OUTPUT_DIR / "scorer_feature_overlap_summary.json", summary)
    (OUTPUT_DIR / "scorer_feature_overlap_readout.md").write_text(build_readout(summary), encoding="utf-8")
    print(
        f"[{RUN_LABEL}] done pairs={summary['pair_count']} "
        f"unique_text_pairs={summary['unique_numeric_text_pair_count']} output_dir={summary['output_dir']}"
    )
    return summary


def main() -> None:
    write_outputs()


if __name__ == "__main__":
    main()
