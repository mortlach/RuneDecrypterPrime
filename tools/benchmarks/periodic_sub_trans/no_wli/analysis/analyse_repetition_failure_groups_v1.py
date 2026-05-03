from __future__ import annotations

import csv
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any, Mapping, Sequence


RUN_LABEL = "repetition_failure_groups_v1"
INPUT_ROWS_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "repetition_window_consistency_probe_v1/repetition_window_consistency_probe_rows.csv"
)
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "repetition_failure_groups_v1"
)
NGRAM_SIZES = (3, 4, 5, 6)


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError("Could not locate repo root")


REPO_ROOT = _find_repo_root()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.probe_repetition_window_consistency_v1 import (  # noqa: E402
    repeated_ngram_rate,
)
from tools.benchmarks.periodic_sub_trans.no_wli.phasec_frontier_rows import (  # noqa: E402
    load_phasec_frontier_rows,
)


INPUT_ROWS = REPO_ROOT / INPUT_ROWS_REL
OUTPUT_DIR = REPO_ROOT / OUTPUT_DIR_REL


ROW_FIELDS = (
    "group",
    "artifact_path",
    "bundle_path",
    "best_stage",
    "fixture_seed",
    "search_seed",
    "candidate_pair_key",
    "truth_better_hash",
    "truth_worse_hash",
    "truth_better_source",
    "truth_worse_source",
    "truth_better_source_rank",
    "truth_worse_source_rank",
    "truth_gap_abs",
    "score_gap_abs",
    "truth_better_current_score",
    "truth_worse_current_score",
    "truth_better_text_length",
    "truth_worse_text_length",
    "repeated_3gram_prefers_truth_better",
    "repeated_4gram_prefers_truth_better",
    "repeated_5gram_prefers_truth_better",
    "repeated_6gram_prefers_truth_better",
    "truth_better_repeated_3gram_rate",
    "truth_worse_repeated_3gram_rate",
    "truth_better_repeated_4gram_rate",
    "truth_worse_repeated_4gram_rate",
    "truth_better_repeated_5gram_rate",
    "truth_worse_repeated_5gram_rate",
    "truth_better_repeated_6gram_rate",
    "truth_worse_repeated_6gram_rate",
    "window_worst_repeated_4gram_prefers_truth_better",
    "window_mean_repeated_4gram_prefers_truth_better",
)


def _utc_now_text() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix().replace("\\", "/")


def _safe_float(value: Any) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return out if math.isfinite(out) else float("nan")


def _finite_or_blank(value: Any) -> float | str:
    out = _safe_float(value)
    return float(out) if math.isfinite(out) else ""


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _read_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _candidate_pair_key(row: Mapping[str, Any]) -> str:
    return "|".join(sorted([str(row.get("candidate_a_hash", "") or ""), str(row.get("candidate_b_hash", "") or "")]))


def _unique_misranked_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        if int(row.get("current_score_chose_truth_better", 0) or 0) != 0:
            continue
        key = _candidate_pair_key(row)
        if key in seen:
            continue
        seen.add(key)
        out.append(dict(row))
    return out


def _load_artifact(path_text: Any) -> tuple[Path, dict[str, Any]]:
    path = Path(str(path_text or ""))
    if not path.is_absolute():
        path = (REPO_ROOT / path).resolve()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        payload = {}
    return path, dict(payload) if isinstance(payload, Mapping) else {}


def _candidate_by_hash(rows: Sequence[Mapping[str, Any]], candidate_hash: str) -> dict[str, Any]:
    for row in rows:
        if str(row.get("candidate_hash", "") or "") == str(candidate_hash):
            return dict(row)
    return {}


def _prefer_lower(a: Any, b: Any) -> str:
    av = _safe_float(a)
    bv = _safe_float(b)
    if not math.isfinite(av) or not math.isfinite(bv):
        return ""
    if av < bv:
        return "truth_better"
    if bv < av:
        return "truth_worse"
    return "tie"


def build_failure_group_row(source_row: Mapping[str, Any]) -> dict[str, Any]:
    artifact_path, artifact = _load_artifact(source_row.get("artifact_path"))
    truth_side = str(source_row.get("truth_better_side", "") or "")
    if truth_side == "a":
        truth_better_hash = str(source_row.get("candidate_a_hash", "") or "")
        truth_worse_hash = str(source_row.get("candidate_b_hash", "") or "")
        truth_better_source = str(source_row.get("candidate_a_source", "") or "")
        truth_worse_source = str(source_row.get("candidate_b_source", "") or "")
        truth_better_rank = source_row.get("candidate_a_source_rank", "")
        truth_worse_rank = source_row.get("candidate_b_source_rank", "")
        truth_better_score = source_row.get("candidate_a_current_score")
        truth_worse_score = source_row.get("candidate_b_current_score")
    else:
        truth_better_hash = str(source_row.get("candidate_b_hash", "") or "")
        truth_worse_hash = str(source_row.get("candidate_a_hash", "") or "")
        truth_better_source = str(source_row.get("candidate_b_source", "") or "")
        truth_worse_source = str(source_row.get("candidate_a_source", "") or "")
        truth_better_rank = source_row.get("candidate_b_source_rank", "")
        truth_worse_rank = source_row.get("candidate_a_source_rank", "")
        truth_better_score = source_row.get("candidate_b_current_score")
        truth_worse_score = source_row.get("candidate_a_current_score")

    frontier_rows = load_phasec_frontier_rows(artifact_path=artifact_path, artifact=artifact) if artifact else []
    truth_better_candidate = _candidate_by_hash(frontier_rows, truth_better_hash)
    truth_worse_candidate = _candidate_by_hash(frontier_rows, truth_worse_hash)
    truth_better_tokens = [int(v) for v in list(truth_better_candidate.get("final_plaintext_idx", []) or [])]
    truth_worse_tokens = [int(v) for v in list(truth_worse_candidate.get("final_plaintext_idx", []) or [])]

    row: dict[str, Any] = {
        "group": (
            "repeated_4gram_helps"
            if int(source_row.get("repeated_4gram_prefers_truth_better", 0) or 0)
            else "repeated_4gram_not_help"
        ),
        "artifact_path": str(source_row.get("artifact_path", "") or ""),
        "bundle_path": str(source_row.get("bundle_path", "") or ""),
        "best_stage": str(artifact.get("best_stage", "") or ""),
        "fixture_seed": _safe_int(source_row.get("fixture_seed"), 0),
        "search_seed": _safe_int(source_row.get("search_seed"), 0),
        "candidate_pair_key": _candidate_pair_key(source_row),
        "truth_better_hash": truth_better_hash,
        "truth_worse_hash": truth_worse_hash,
        "truth_better_source": truth_better_source,
        "truth_worse_source": truth_worse_source,
        "truth_better_source_rank": truth_better_rank,
        "truth_worse_source_rank": truth_worse_rank,
        "truth_gap_abs": _finite_or_blank(source_row.get("truth_gap_abs")),
        "score_gap_abs": _finite_or_blank(source_row.get("score_gap_abs")),
        "truth_better_current_score": _finite_or_blank(truth_better_score),
        "truth_worse_current_score": _finite_or_blank(truth_worse_score),
        "truth_better_text_length": len(truth_better_tokens),
        "truth_worse_text_length": len(truth_worse_tokens),
        "window_worst_repeated_4gram_prefers_truth_better": _safe_int(
            source_row.get("window_worst_repeated_4gram_prefers_truth_better"), 0
        ),
        "window_mean_repeated_4gram_prefers_truth_better": _safe_int(
            source_row.get("window_mean_repeated_4gram_prefers_truth_better"), 0
        ),
    }
    for n in NGRAM_SIZES:
        better_rate = repeated_ngram_rate(truth_better_tokens, n=n)
        worse_rate = repeated_ngram_rate(truth_worse_tokens, n=n)
        row[f"truth_better_repeated_{n}gram_rate"] = _finite_or_blank(better_rate)
        row[f"truth_worse_repeated_{n}gram_rate"] = _finite_or_blank(worse_rate)
        row[f"repeated_{n}gram_prefers_truth_better"] = int(_prefer_lower(better_rate, worse_rate) == "truth_better")
    return {field: row.get(field, "") for field in ROW_FIELDS}


def build_failure_group_rows(source_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [build_failure_group_row(row) for row in _unique_misranked_rows(source_rows)]


def _numeric_values(rows: Sequence[Mapping[str, Any]], key: str) -> list[float]:
    return [val for val in (_safe_float(row.get(key)) for row in rows) if math.isfinite(val)]


def _stat_summary(rows: Sequence[Mapping[str, Any]], key: str) -> dict[str, Any]:
    vals = _numeric_values(rows, key)
    return {
        "count": len(vals),
        "mean": None if not vals else float(mean(vals)),
        "median": None if not vals else float(median(vals)),
        "min": None if not vals else float(min(vals)),
        "max": None if not vals else float(max(vals)),
    }


def _count_by(rows: Sequence[Mapping[str, Any]], key: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in rows:
        value = str(row.get(key, "") or "none")
        out[value] = int(out.get(value, 0) + 1)
    return dict(sorted(out.items()))


def _group_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    row_list = [dict(row) for row in rows]
    return {
        "count": len(row_list),
        "truth_gap_abs": _stat_summary(row_list, "truth_gap_abs"),
        "score_gap_abs": _stat_summary(row_list, "score_gap_abs"),
        "truth_better_current_score": _stat_summary(row_list, "truth_better_current_score"),
        "truth_worse_current_score": _stat_summary(row_list, "truth_worse_current_score"),
        "truth_better_text_length": _stat_summary(row_list, "truth_better_text_length"),
        "truth_worse_text_length": _stat_summary(row_list, "truth_worse_text_length"),
        "best_stage_counts": _count_by(row_list, "best_stage"),
        "fixture_counts": _count_by(row_list, "fixture_seed"),
        "truth_better_source_counts": _count_by(row_list, "truth_better_source"),
        "truth_worse_source_counts": _count_by(row_list, "truth_worse_source"),
        "repeated_ngram_truth_better_counts": {
            f"n{n}": sum(int(row.get(f"repeated_{n}gram_prefers_truth_better", 0) or 0) for row in row_list)
            for n in NGRAM_SIZES
        },
        "window_worst_repeated_4gram_truth_better_count": sum(
            int(row.get("window_worst_repeated_4gram_prefers_truth_better", 0) or 0) for row in row_list
        ),
        "window_mean_repeated_4gram_truth_better_count": sum(
            int(row.get("window_mean_repeated_4gram_prefers_truth_better", 0) or 0) for row in row_list
        ),
    }


def summarize_failure_group_rows(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    row_list = [dict(row) for row in rows]
    helps = [row for row in row_list if str(row.get("group", "") or "") == "repeated_4gram_helps"]
    not_help = [row for row in row_list if str(row.get("group", "") or "") == "repeated_4gram_not_help"]
    return {
        "run_label": RUN_LABEL,
        "updated_utc": _utc_now_text(),
        "input_rows": _repo_rel(INPUT_ROWS),
        "unique_misranked_pair_count": len(row_list),
        "repeated_4gram_helps_count": len(helps),
        "repeated_4gram_not_help_count": len(not_help),
        "groups": {
            "repeated_4gram_helps": _group_summary(helps),
            "repeated_4gram_not_help": _group_summary(not_help),
        },
        "missing_diagnostics": [
            "current LM bad-window/lower-quartile scores are not in the probe rows",
            "word-ngram judge scores are not in the probe rows",
            "span/dictionary coverage scores are not in the probe rows",
        ],
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
    path.write_text(json.dumps(dict(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_readout(summary: Mapping[str, Any]) -> str:
    groups = dict(summary.get("groups", {}) or {})
    helps = dict(groups.get("repeated_4gram_helps", {}) or {})
    not_help = dict(groups.get("repeated_4gram_not_help", {}) or {})
    lines = [
        "# Repetition Failure Groups v1",
        "",
        "## Summary",
        "",
        f"- unique score-misranked pairs: `{summary['unique_misranked_pair_count']}`",
        f"- repeated 4-gram helps: `{summary['repeated_4gram_helps_count']}`",
        f"- repeated 4-gram does not help: `{summary['repeated_4gram_not_help_count']}`",
        "",
        "## Group Comparison",
        "",
        f"- helps truth-gap stats: `{json.dumps(dict(helps.get('truth_gap_abs', {})), sort_keys=True)}`",
        f"- not-help truth-gap stats: `{json.dumps(dict(not_help.get('truth_gap_abs', {})), sort_keys=True)}`",
        f"- helps score-gap stats: `{json.dumps(dict(helps.get('score_gap_abs', {})), sort_keys=True)}`",
        f"- not-help score-gap stats: `{json.dumps(dict(not_help.get('score_gap_abs', {})), sort_keys=True)}`",
        "",
        "## Source / Stage Counts",
        "",
        f"- helps best stages: `{json.dumps(dict(helps.get('best_stage_counts', {})), sort_keys=True)}`",
        f"- not-help best stages: `{json.dumps(dict(not_help.get('best_stage_counts', {})), sort_keys=True)}`",
        f"- helps truth-better sources: `{json.dumps(dict(helps.get('truth_better_source_counts', {})), sort_keys=True)}`",
        f"- not-help truth-better sources: `{json.dumps(dict(not_help.get('truth_better_source_counts', {})), sort_keys=True)}`",
        f"- helps truth-worse sources: `{json.dumps(dict(helps.get('truth_worse_source_counts', {})), sort_keys=True)}`",
        f"- not-help truth-worse sources: `{json.dumps(dict(not_help.get('truth_worse_source_counts', {})), sort_keys=True)}`",
        "",
        "## Alternate Repetition Sizes",
        "",
        f"- helps repeated n-gram counts: `{json.dumps(dict(helps.get('repeated_ngram_truth_better_counts', {})), sort_keys=True)}`",
        f"- not-help repeated n-gram counts: `{json.dumps(dict(not_help.get('repeated_ngram_truth_better_counts', {})), sort_keys=True)}`",
        "",
        "## Missing Diagnostics",
        "",
    ]
    for item in list(summary.get("missing_diagnostics", []) or []):
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- This report is diagnostic only and does not change runtime behavior.",
            "- It compares only unique score-misranked candidate pairs from the repetition/window probe.",
            "- Missing diagnostics are named explicitly rather than inferred.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def write_failure_group_outputs(
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
    summary = summarize_failure_group_rows(row_list)
    summary["output_dir"] = _repo_rel(resolved_output)
    _write_csv(resolved_output / "repetition_failure_group_rows.csv", row_list)
    _write_jsonl(resolved_output / "repetition_failure_group_rows.jsonl", row_list)
    _write_json(resolved_output / "repetition_failure_group_summary.json", summary)
    (resolved_output / "repetition_failure_group_readout.md").write_text(
        build_readout(summary),
        encoding="utf-8",
    )
    return summary


def run_analysis() -> dict[str, Any]:
    started = time.perf_counter()
    source_rows = _read_csv_rows(INPUT_ROWS)
    rows = build_failure_group_rows(source_rows)
    summary = write_failure_group_outputs(rows=rows)
    summary["elapsed_seconds"] = float(time.perf_counter() - started)
    _write_json(OUTPUT_DIR / "repetition_failure_group_summary.json", summary)
    print(
        "[repetition_failure_groups_v1] "
        f"unique_misranked_pairs={summary['unique_misranked_pair_count']} "
        f"helps={summary['repeated_4gram_helps_count']} "
        f"not_help={summary['repeated_4gram_not_help_count']} "
        f"output_dir={summary['output_dir']}",
        flush=True,
    )
    return summary


def main() -> None:
    run_analysis()


if __name__ == "__main__":
    main()
