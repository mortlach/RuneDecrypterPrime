from __future__ import annotations

import csv
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


RUN_LABEL = "current_scorer_failure_v1"
RUN_ROOT_REL = "output/tools/benchmarks/periodic_sub_trans/no_wli"
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "current_scorer_failure_v1"
)

ALLOWED_FAILURE_TYPES = frozenset(
    {
        "local_ngram_overfit",
        "bad_window_hidden_by_average",
        "missing_word_or_span_signal",
        "component_weighting_failure",
        "calibration_failure",
        "candidate_generation_failure",
        "truth_positive_present_but_under_scored",
        "truth_positive_not_present",
        "short_or_medium_text_length_mismatch",
        "motif_false_positive",
        "unknown",
    }
)

EVALUATION_FIELDS = (
    "winner_truth_match",
    "challenger_truth_match",
    "truth_gap_challenger_minus_winner",
    "current_scorer_chose_truth_better",
    "truth_better_candidate_hash",
)

CANDIDATE_FEATURE_FIELDS = (
    "winner_current_score",
    "challenger_current_score",
    "score_gap_challenger_minus_winner",
    "winner_source",
    "winner_source_rank",
    "challenger_source",
    "challenger_source_rank",
    "winner_text_length",
    "challenger_text_length",
    "winner_char_lm_score",
    "challenger_char_lm_score",
    "winner_window_mean",
    "challenger_window_mean",
    "winner_window_worst",
    "challenger_window_worst",
    "winner_window_lower_quartile",
    "challenger_window_lower_quartile",
    "winner_window_variance",
    "challenger_window_variance",
    "winner_span_score",
    "challenger_span_score",
    "winner_word_ngram_score",
    "challenger_word_ngram_score",
    "winner_repeated_ngram_rate",
    "challenger_repeated_ngram_rate",
    "winner_low_diversity_penalty",
    "challenger_low_diversity_penalty",
)

ROW_FIELDS = (
    "fixture_seed",
    "search_seed",
    "stage",
    "run_id",
    "bundle_path",
    "winner_candidate_hash",
    "challenger_candidate_hash",
    "winner_truth_match",
    "challenger_truth_match",
    "truth_gap_challenger_minus_winner",
    "winner_current_score",
    "challenger_current_score",
    "score_gap_challenger_minus_winner",
    "current_scorer_chose_truth_better",
    "truth_better_candidate_hash",
    "winner_source",
    "winner_source_rank",
    "challenger_source",
    "challenger_source_rank",
    "winner_text_length",
    "challenger_text_length",
    "failure_type",
    "failure_notes",
    "component_scores_available",
    "missing_component_score_reason",
    "winner_char_lm_score",
    "challenger_char_lm_score",
    "winner_window_mean",
    "challenger_window_mean",
    "winner_window_worst",
    "challenger_window_worst",
    "winner_window_lower_quartile",
    "challenger_window_lower_quartile",
    "winner_window_variance",
    "challenger_window_variance",
    "winner_span_score",
    "challenger_span_score",
    "winner_word_ngram_score",
    "challenger_word_ngram_score",
    "winner_repeated_ngram_rate",
    "challenger_repeated_ngram_rate",
    "winner_low_diversity_penalty",
    "challenger_low_diversity_penalty",
)

COMPONENT_SCORE_FIELDS = (
    "winner_char_lm_score",
    "challenger_char_lm_score",
    "winner_window_mean",
    "challenger_window_mean",
    "winner_window_worst",
    "challenger_window_worst",
    "winner_window_lower_quartile",
    "challenger_window_lower_quartile",
    "winner_window_variance",
    "challenger_window_variance",
    "winner_span_score",
    "challenger_span_score",
    "winner_word_ngram_score",
    "challenger_word_ngram_score",
    "winner_repeated_ngram_rate",
    "challenger_repeated_ngram_rate",
    "winner_low_diversity_penalty",
    "challenger_low_diversity_penalty",
)


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError("Could not locate repo root")


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli.phasec_truth_gap_dataset import (  # noqa: E402
    collect_phasec_truth_gap_rows,
)


RUN_ROOT = REPO_ROOT / RUN_ROOT_REL
OUTPUT_DIR = REPO_ROOT / OUTPUT_DIR_REL


def _utc_now_text() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix().replace("\\", "/")


def _display_path_text(value: Any) -> str:
    text = str(value or "").replace("\\", "/")
    if not text:
        return ""
    candidate = Path(text)
    if candidate.is_absolute():
        return _repo_rel(candidate)
    return text


def _safe_float(value: Any) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return out if math.isfinite(out) else float("nan")


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _blank_component_scores() -> dict[str, str]:
    return {field: "" for field in COMPONENT_SCORE_FIELDS}


def _candidate_with_higher_score(
    *,
    winner_hash: str,
    challenger_hash: str,
    winner_score: float,
    challenger_score: float,
) -> str:
    if math.isfinite(winner_score) and math.isfinite(challenger_score):
        if challenger_score > winner_score:
            return challenger_hash
        return winner_hash
    if math.isfinite(winner_score):
        return winner_hash
    if math.isfinite(challenger_score):
        return challenger_hash
    return ""


def _truth_better_candidate(
    *,
    winner_hash: str,
    challenger_hash: str,
    winner_truth: float,
    challenger_truth: float,
) -> str:
    if not math.isfinite(winner_truth) or not math.isfinite(challenger_truth):
        return ""
    if challenger_truth > winner_truth:
        return challenger_hash
    return winner_hash


def _classify_failure(row: Mapping[str, Any]) -> tuple[str, str]:
    truth_better = str(row.get("truth_better_candidate_hash", "") or "")
    score_better = _candidate_with_higher_score(
        winner_hash=str(row.get("winner_candidate_hash", "") or ""),
        challenger_hash=str(row.get("challenger_candidate_hash", "") or ""),
        winner_score=_safe_float(row.get("winner_current_score")),
        challenger_score=_safe_float(row.get("challenger_current_score")),
    )
    challenger_hash = str(row.get("challenger_candidate_hash", "") or "")
    truth_gap = _safe_float(row.get("truth_gap_challenger_minus_winner"))
    score_gap = _safe_float(row.get("score_gap_challenger_minus_winner"))

    if not truth_better:
        return "unknown", "missing truth labels; excluded from pairwise accuracy"
    if not challenger_hash:
        return "truth_positive_not_present", "no challenger candidate hash was available"
    if score_better == truth_better:
        return "unknown", "current score selected the truth-better candidate"
    if math.isfinite(truth_gap) and truth_gap > 0.0 and math.isfinite(score_gap) and score_gap < 0.0:
        return (
            "truth_positive_present_but_under_scored",
            "challenger has higher truth match but lower current score",
        )
    if math.isfinite(score_gap) and abs(score_gap) <= 1e-12:
        return "calibration_failure", "truth-better candidate tied or nearly tied under current score"
    return "component_weighting_failure", "truth-better candidate was available but not selected by current score"


def build_failure_row(source_row: Mapping[str, Any]) -> dict[str, Any]:
    winner_hash = str(source_row.get("winner_candidate_hash", "") or "")
    challenger_hash = str(source_row.get("challenger_candidate_hash", "") or "")
    winner_truth = _safe_float(source_row.get("winner_truth_match"))
    challenger_truth = _safe_float(source_row.get("challenger_truth_match"))
    winner_score = _safe_float(source_row.get("winner_score", source_row.get("winner_current_score")))
    challenger_score = _safe_float(
        source_row.get("challenger_score", source_row.get("challenger_current_score"))
    )
    truth_better = _truth_better_candidate(
        winner_hash=winner_hash,
        challenger_hash=challenger_hash,
        winner_truth=winner_truth,
        challenger_truth=challenger_truth,
    )
    score_better = _candidate_with_higher_score(
        winner_hash=winner_hash,
        challenger_hash=challenger_hash,
        winner_score=winner_score,
        challenger_score=challenger_score,
    )
    row: dict[str, Any] = {
        "fixture_seed": _safe_int(source_row.get("key_seed", source_row.get("fixture_seed"))),
        "search_seed": _safe_int(source_row.get("search_seed"), default=0),
        "stage": str(source_row.get("best_stage", source_row.get("stage", "")) or ""),
        "run_id": str(source_row.get("run_id", "") or ""),
        "bundle_path": _display_path_text(
            source_row.get("run_dir", source_row.get("bundle_path", source_row.get("artifact_path", "")))
        ),
        "winner_candidate_hash": winner_hash,
        "challenger_candidate_hash": challenger_hash,
        "winner_truth_match": "" if not math.isfinite(winner_truth) else winner_truth,
        "challenger_truth_match": "" if not math.isfinite(challenger_truth) else challenger_truth,
        "truth_gap_challenger_minus_winner": (
            "" if not (math.isfinite(winner_truth) and math.isfinite(challenger_truth)) else challenger_truth - winner_truth
        ),
        "winner_current_score": "" if not math.isfinite(winner_score) else winner_score,
        "challenger_current_score": "" if not math.isfinite(challenger_score) else challenger_score,
        "score_gap_challenger_minus_winner": (
            "" if not (math.isfinite(winner_score) and math.isfinite(challenger_score)) else challenger_score - winner_score
        ),
        "current_scorer_chose_truth_better": int(bool(truth_better) and score_better == truth_better),
        "truth_better_candidate_hash": truth_better,
        "winner_source": str(source_row.get("winner_source", "") or ""),
        "winner_source_rank": source_row.get("winner_source_rank", ""),
        "challenger_source": str(source_row.get("challenger_source", "") or ""),
        "challenger_source_rank": source_row.get("challenger_source_rank", ""),
        "winner_text_length": source_row.get("winner_text_length", ""),
        "challenger_text_length": source_row.get("challenger_text_length", ""),
        "component_scores_available": 0,
        "missing_component_score_reason": (
            "component-level scorer sidecars are not present in the current truth-gap row"
        ),
    }
    row.update(_blank_component_scores())
    failure_type, notes = _classify_failure(row)
    if failure_type not in ALLOWED_FAILURE_TYPES:
        raise ValueError(f"Unknown failure_type: {failure_type}")
    row["failure_type"] = failure_type
    row["failure_notes"] = notes
    return {field: row.get(field, "") for field in ROW_FIELDS}


def build_failure_rows(source_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [build_failure_row(row) for row in source_rows]


def _valid_accuracy_row(row: Mapping[str, Any]) -> bool:
    return bool(str(row.get("truth_better_candidate_hash", "") or ""))


def _values(rows: Sequence[Mapping[str, Any]], key: str) -> list[float]:
    vals: list[float] = []
    for row in rows:
        val = _safe_float(row.get(key))
        if math.isfinite(val):
            vals.append(val)
    return vals


def _mean(vals: Sequence[float]) -> float | None:
    if not vals:
        return None
    return float(sum(vals) / len(vals))


def _median(vals: Sequence[float]) -> float | None:
    if not vals:
        return None
    sorted_vals = sorted(float(v) for v in vals)
    mid = len(sorted_vals) // 2
    if len(sorted_vals) % 2:
        return float(sorted_vals[mid])
    return float((sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0)


def _count_by(rows: Sequence[Mapping[str, Any]], key: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in rows:
        value = str(row.get(key, "") or "unknown")
        out[value] = int(out.get(value, 0) + 1)
    return dict(sorted(out.items()))


def _candidate_pair_key(row: Mapping[str, Any]) -> str:
    return "{winner}|{challenger}".format(
        winner=str(row.get("winner_candidate_hash", "") or ""),
        challenger=str(row.get("challenger_candidate_hash", "") or ""),
    )


def _fixture_search_key(row: Mapping[str, Any]) -> str:
    return "{fixture}|{search}".format(
        fixture=str(row.get("fixture_seed", "") or ""),
        search=str(row.get("search_seed", "") or ""),
    )


def _counts_by_key(rows: Sequence[Mapping[str, Any]], key_fn) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in rows:
        key = str(key_fn(row) or "unknown")
        out[key] = int(out.get(key, 0) + 1)
    return dict(sorted(out.items(), key=lambda item: (-item[1], item[0])))


def _dominant_count(counts: Mapping[str, int]) -> int:
    return int(max(counts.values()) if counts else 0)


def summarize_failure_rows(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    row_list = [dict(row) for row in rows]
    valid_rows = [row for row in row_list if _valid_accuracy_row(row)]
    wrong_rows = [
        row
        for row in valid_rows
        if int(row.get("current_scorer_chose_truth_better", 0) or 0) == 0
    ]
    correct_count = len(valid_rows) - len(wrong_rows)
    truth_gaps_wrong = _values(wrong_rows, "truth_gap_challenger_minus_winner")
    score_gaps_wrong = _values(wrong_rows, "score_gap_challenger_minus_winner")
    candidate_pair_counts = _counts_by_key(row_list, _candidate_pair_key)
    fixture_search_counts = _counts_by_key(row_list, _fixture_search_key)
    dominant_pair_count = _dominant_count(candidate_pair_counts)
    return {
        "run_label": RUN_LABEL,
        "updated_utc": _utc_now_text(),
        "row_occurrence_count": len(row_list),
        "pair_count": len(row_list),
        "unique_candidate_pair_count": len(candidate_pair_counts),
        "unique_fixture_search_count": len(fixture_search_counts),
        "candidate_pair_counts": candidate_pair_counts,
        "fixture_search_counts": fixture_search_counts,
        "dominant_pair_count": dominant_pair_count,
        "dominant_pair_fraction": (
            None if not row_list else float(dominant_pair_count / len(row_list))
        ),
        "valid_accuracy_pair_count": len(valid_rows),
        "current_scorer_correct_count": correct_count,
        "current_scorer_wrong_count": len(wrong_rows),
        "current_scorer_pairwise_accuracy": (
            None if not valid_rows else float(correct_count / len(valid_rows))
        ),
        "mean_truth_gap_when_wrong": _mean(truth_gaps_wrong),
        "median_truth_gap_when_wrong": _median(truth_gaps_wrong),
        "max_truth_gap_when_wrong": (max(truth_gaps_wrong) if truth_gaps_wrong else None),
        "mean_score_gap_when_wrong": _mean(score_gaps_wrong),
        "median_score_gap_when_wrong": _median(score_gaps_wrong),
        "failure_type_counts": _count_by(row_list, "failure_type"),
        "stage_counts": _count_by(row_list, "stage"),
        "source_counts": _count_by(row_list, "winner_source"),
        "component_scores_available_count": sum(
            int(row.get("component_scores_available", 0) or 0) for row in row_list
        ),
        "component_scores_missing_count": sum(
            1 for row in row_list if not int(row.get("component_scores_available", 0) or 0)
        ),
        "largest_truth_gap_rows": sorted(
            row_list,
            key=lambda row: _safe_float(row.get("truth_gap_challenger_minus_winner")),
            reverse=True,
        )[:10],
        "worst_score_gap_rows": sorted(
            row_list,
            key=lambda row: _safe_float(row.get("score_gap_challenger_minus_winner")),
        )[:10],
        "most_instructive_rows": sorted(
            wrong_rows,
            key=lambda row: (
                _safe_float(row.get("truth_gap_challenger_minus_winner")),
                -_safe_float(row.get("score_gap_challenger_minus_winner")),
            ),
            reverse=True,
        )[:10],
        "candidate_feature_fields": list(CANDIDATE_FEATURE_FIELDS),
        "evaluation_fields": list(EVALUATION_FIELDS),
    }


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(ROW_FIELDS))
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in ROW_FIELDS})


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(dict(row), ensure_ascii=True, sort_keys=True) for row in rows]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_readout(rows: Sequence[Mapping[str, Any]], summary: Mapping[str, Any]) -> str:
    wrong = int(summary.get("current_scorer_wrong_count", 0) or 0)
    correct = int(summary.get("current_scorer_correct_count", 0) or 0)
    accuracy = summary.get("current_scorer_pairwise_accuracy")
    accuracy_text = "n/a" if accuracy is None else f"{float(accuracy):.3f}"
    lines = [
        "# Current Scorer Failure Study v1",
        "",
        "## Summary",
        "",
        f"- row occurrences: `{summary['row_occurrence_count']}`",
        f"- unique winner/challenger candidate pairs: `{summary['unique_candidate_pair_count']}`",
        f"- unique fixture/search groups: `{summary['unique_fixture_search_count']}`",
        f"- dominant candidate-pair row count: `{summary['dominant_pair_count']}`",
        f"- dominant candidate-pair fraction: `{float(summary['dominant_pair_fraction'] or 0.0):.3f}`",
        f"- valid accuracy row occurrences: `{summary['valid_accuracy_pair_count']}`",
        f"- current scorer correct: `{correct}`",
        f"- current scorer wrong: `{wrong}`",
        f"- selected truth-gap slice pairwise accuracy: `{accuracy_text}`",
        f"- component-score rows available: `{summary['component_scores_available_count']}`",
        f"- component-score rows missing: `{summary['component_scores_missing_count']}`",
        "",
        "## What the current scorer gets right",
        "",
        "- Rows where the current-score-selected candidate is also truth-better are counted as correct.",
        "",
        "## What the current scorer gets wrong",
        "",
    ]
    if wrong <= 0:
        lines.append("- No wrong truth-gap pairs were found in the current input set.")
    else:
        for failure_type, count in dict(summary.get("failure_type_counts", {})).items():
            lines.append(f"- `{failure_type}`: `{count}`")
    lines.extend(["", "## Candidate Pair Repetition", ""])
    for key, count in list(dict(summary.get("candidate_pair_counts", {})).items())[:10]:
        lines.append(f"- `{key}`: `{count}` row occurrences")
    lines.extend(["", "## Largest truth-gap mistakes", ""])
    for row in list(summary.get("largest_truth_gap_rows", []) or [])[:5]:
        lines.append(
            "- `{bundle}` winner `{winner}` challenger `{challenger}` truth gap `{gap}` score gap `{score_gap}`".format(
                bundle=str(row.get("bundle_path", "")),
                winner=str(row.get("winner_candidate_hash", "")),
                challenger=str(row.get("challenger_candidate_hash", "")),
                gap=row.get("truth_gap_challenger_minus_winner", ""),
                score_gap=row.get("score_gap_challenger_minus_winner", ""),
            )
        )
    lines.extend(
        [
            "",
            "## Common failure modes",
            "",
            "- The current report can distinguish candidate absence from truth-positive-present under-scoring.",
            "- Accuracy is reported only for this selected truth-gap slice; it is not a global scorer accuracy estimate.",
            "- Component-level labels stay conservative until scorer sidecar fields are available.",
            "",
            "## Component-level clues",
            "",
            "- Component scores are left blank when missing; they are not coerced to zero.",
            "- Missing component-score reason is recorded per row.",
            "",
            "## What existing scorer components may help",
            "",
            "- Stage 1 inventory points at span-Hamming and word-ngram reports as first report-only clues.",
            "- Current LM and ECDF components remain the baseline score context.",
            "",
            "## Recommendation for Stage 3 design",
            "",
            "- Do not start Stage 3 until component-sidecar coverage is either produced or explicitly scoped out.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def write_failure_outputs(
    *,
    rows: Sequence[Mapping[str, Any]],
    output_dir: Path = OUTPUT_DIR,
) -> dict[str, Any]:
    resolved_output = output_dir.resolve()
    try:
        resolved_output.relative_to(REPO_ROOT.resolve())
    except ValueError as exc:
        raise ValueError(f"Output directory must stay under repo root: {output_dir}") from exc
    resolved_output.mkdir(parents=True, exist_ok=True)
    row_list = [dict(row) for row in rows]
    summary = summarize_failure_rows(row_list)
    summary["output_dir"] = _repo_rel(resolved_output)
    _write_csv(resolved_output / "current_scorer_failure_rows.csv", row_list)
    _write_jsonl(resolved_output / "current_scorer_failure_rows.jsonl", row_list)
    _write_json(resolved_output / "current_scorer_failure_summary.json", summary)
    (resolved_output / "current_scorer_failure_readout.md").write_text(
        build_readout(row_list, summary),
        encoding="utf-8",
    )
    return summary


def run_study() -> dict[str, Any]:
    started = time.perf_counter()
    source_rows = collect_phasec_truth_gap_rows(RUN_ROOT)
    rows = build_failure_rows(source_rows)
    summary = write_failure_outputs(rows=rows)
    summary["elapsed_seconds"] = float(time.perf_counter() - started)
    _write_json(OUTPUT_DIR / "current_scorer_failure_summary.json", summary)
    print(
        "[current_scorer_failure_v1] "
        f"rows={summary['row_occurrence_count']} "
        f"unique_pairs={summary['unique_candidate_pair_count']} "
        f"wrong={summary['current_scorer_wrong_count']} "
        f"output_dir={summary['output_dir']}",
        flush=True,
    )
    return summary


def main() -> None:
    run_study()


if __name__ == "__main__":
    main()
