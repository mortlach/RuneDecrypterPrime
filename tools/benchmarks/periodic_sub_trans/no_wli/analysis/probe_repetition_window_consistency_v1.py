from __future__ import annotations

import csv
import json
import math
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from statistics import mean, median
from typing import Any, Mapping, Sequence


RUN_LABEL = "repetition_window_consistency_probe_v1"
RUN_ROOT_REL = "output/tools/benchmarks/periodic_sub_trans/no_wli"
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "repetition_window_consistency_probe_v1"
)
MIN_TRUTH_GAP = 0.05
REPEATED_NGRAM_N = 4
WINDOW_SIZE = 100
WINDOW_STEP = 50


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError("Could not locate repo root")


REPO_ROOT = _find_repo_root()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.benchmarks.periodic_sub_trans.no_wli.phasec_frontier_rows import (  # noqa: E402
    load_phasec_frontier_rows,
)


RUN_ROOT = REPO_ROOT / RUN_ROOT_REL
OUTPUT_DIR = REPO_ROOT / OUTPUT_DIR_REL


ROW_FIELDS = (
    "artifact_path",
    "bundle_path",
    "fixture_seed",
    "search_seed",
    "candidate_a_hash",
    "candidate_b_hash",
    "truth_better_side",
    "score_better_side",
    "current_score_chose_truth_better",
    "truth_gap_abs",
    "score_gap_abs",
    "candidate_a_truth_match",
    "candidate_b_truth_match",
    "candidate_a_current_score",
    "candidate_b_current_score",
    "candidate_a_source",
    "candidate_b_source",
    "candidate_a_source_rank",
    "candidate_b_source_rank",
    "candidate_a_text_length",
    "candidate_b_text_length",
    "candidate_a_repeated_4gram_rate",
    "candidate_b_repeated_4gram_rate",
    "repeated_4gram_prefers_truth_better",
    "candidate_a_window_repeated_4gram_mean",
    "candidate_b_window_repeated_4gram_mean",
    "candidate_a_window_repeated_4gram_worst",
    "candidate_b_window_repeated_4gram_worst",
    "candidate_a_window_repeated_4gram_variance",
    "candidate_b_window_repeated_4gram_variance",
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


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _finite_or_blank(value: Any) -> float | str:
    out = _safe_float(value)
    return float(out) if math.isfinite(out) else ""


def _prefer_higher(a: Any, b: Any) -> str:
    av = _safe_float(a)
    bv = _safe_float(b)
    if not math.isfinite(av) or not math.isfinite(bv):
        return ""
    if av > bv:
        return "a"
    if bv > av:
        return "b"
    return "tie"


def _prefer_lower(a: Any, b: Any) -> str:
    av = _safe_float(a)
    bv = _safe_float(b)
    if not math.isfinite(av) or not math.isfinite(bv):
        return ""
    if av < bv:
        return "a"
    if bv < av:
        return "b"
    return "tie"


def repeated_ngram_rate(tokens: Sequence[int], *, n: int = REPEATED_NGRAM_N) -> float | str:
    vals = [int(v) for v in tokens]
    if len(vals) < n:
        return ""
    grams = [tuple(vals[idx : idx + n]) for idx in range(0, len(vals) - n + 1)]
    counts = Counter(grams)
    repeated_positions = sum(count for count in counts.values() if count > 1)
    return float(repeated_positions / max(1, len(grams)))


def window_repeated_ngram_metrics(
    tokens: Sequence[int],
    *,
    window_size: int = WINDOW_SIZE,
    window_step: int = WINDOW_STEP,
    n: int = REPEATED_NGRAM_N,
) -> dict[str, Any]:
    vals = [int(v) for v in tokens]
    if len(vals) < max(n, window_size):
        return {"mean": "", "worst": "", "variance": "", "window_count": 0}
    rates: list[float] = []
    for start in range(0, len(vals) - window_size + 1, max(1, window_step)):
        rate = repeated_ngram_rate(vals[start : start + window_size], n=n)
        if isinstance(rate, float) and math.isfinite(rate):
            rates.append(rate)
    if not rates:
        return {"mean": "", "worst": "", "variance": "", "window_count": 0}
    avg = float(mean(rates))
    var = float(mean([(rate - avg) ** 2 for rate in rates]))
    return {
        "mean": avg,
        "worst": float(max(rates)),
        "variance": var,
        "window_count": len(rates),
    }


def _candidate_is_usable(row: Mapping[str, Any]) -> bool:
    return (
        bool(str(row.get("candidate_hash", "") or ""))
        and bool(list(row.get("final_plaintext_idx", []) or []))
        and math.isfinite(_safe_float(row.get("final_match")))
        and math.isfinite(_safe_float(row.get("final_score")))
    )


def _candidate_pair_key(row: Mapping[str, Any]) -> str:
    hashes = sorted([str(row.get("candidate_a_hash", "") or ""), str(row.get("candidate_b_hash", "") or "")])
    return "|".join(hashes)


def _counts_by(rows: Sequence[Mapping[str, Any]], key: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in rows:
        value = str(row.get(key, "") or "none")
        out[value] = int(out.get(value, 0) + 1)
    return dict(sorted(out.items()))


def _unique_by_pair(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        key = _candidate_pair_key(row)
        if key in seen:
            continue
        seen.add(key)
        out.append(dict(row))
    return out


def _preference_summary(rows: Sequence[Mapping[str, Any]], key: str) -> dict[str, int]:
    row_list = [dict(row) for row in rows]
    truth_better_count = sum(int(row.get(key, 0) or 0) for row in row_list)
    return {
        "row_count": len(row_list),
        "truth_better_count": truth_better_count,
        "not_truth_better_count": len(row_list) - truth_better_count,
    }


def build_probe_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for artifact_path in sorted(RUN_ROOT.glob("*/final_instances/*.json")):
        try:
            artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(artifact, Mapping):
            continue
        frontier_rows = [dict(row) for row in load_phasec_frontier_rows(artifact_path=artifact_path, artifact=artifact)]
        usable = [row for row in frontier_rows if _candidate_is_usable(row)]
        if len(usable) < 2:
            continue
        for cand_a, cand_b in combinations(usable, 2):
            truth_a = _safe_float(cand_a.get("final_match"))
            truth_b = _safe_float(cand_b.get("final_match"))
            truth_gap = abs(truth_a - truth_b)
            if not math.isfinite(truth_gap) or truth_gap < MIN_TRUTH_GAP:
                continue
            score_a = _safe_float(cand_a.get("final_score"))
            score_b = _safe_float(cand_b.get("final_score"))
            truth_better = _prefer_higher(truth_a, truth_b)
            score_better = _prefer_higher(score_a, score_b)
            if truth_better in ("", "tie") or score_better in ("", "tie"):
                continue
            a_tokens = [int(v) for v in list(cand_a.get("final_plaintext_idx", []) or [])]
            b_tokens = [int(v) for v in list(cand_b.get("final_plaintext_idx", []) or [])]
            a_rep = repeated_ngram_rate(a_tokens)
            b_rep = repeated_ngram_rate(b_tokens)
            a_window = window_repeated_ngram_metrics(a_tokens)
            b_window = window_repeated_ngram_metrics(b_tokens)
            repeated_pref = _prefer_lower(a_rep, b_rep)
            window_worst_pref = _prefer_lower(a_window.get("worst"), b_window.get("worst"))
            window_mean_pref = _prefer_lower(a_window.get("mean"), b_window.get("mean"))
            row = {
                "artifact_path": _repo_rel(artifact_path),
                "bundle_path": _repo_rel(artifact_path.parents[1]),
                "fixture_seed": _safe_int(artifact.get("key_seed"), 0),
                "search_seed": _safe_int(artifact.get("search_seed"), 0),
                "candidate_a_hash": str(cand_a.get("candidate_hash", "") or ""),
                "candidate_b_hash": str(cand_b.get("candidate_hash", "") or ""),
                "truth_better_side": truth_better,
                "score_better_side": score_better,
                "current_score_chose_truth_better": int(score_better == truth_better),
                "truth_gap_abs": float(truth_gap),
                "score_gap_abs": float(abs(score_a - score_b)),
                "candidate_a_truth_match": float(truth_a),
                "candidate_b_truth_match": float(truth_b),
                "candidate_a_current_score": float(score_a),
                "candidate_b_current_score": float(score_b),
                "candidate_a_source": str(cand_a.get("source", "") or ""),
                "candidate_b_source": str(cand_b.get("source", "") or ""),
                "candidate_a_source_rank": cand_a.get("source_rank", ""),
                "candidate_b_source_rank": cand_b.get("source_rank", ""),
                "candidate_a_text_length": len(a_tokens),
                "candidate_b_text_length": len(b_tokens),
                "candidate_a_repeated_4gram_rate": _finite_or_blank(a_rep),
                "candidate_b_repeated_4gram_rate": _finite_or_blank(b_rep),
                "repeated_4gram_prefers_truth_better": int(repeated_pref == truth_better),
                "candidate_a_window_repeated_4gram_mean": _finite_or_blank(a_window.get("mean")),
                "candidate_b_window_repeated_4gram_mean": _finite_or_blank(b_window.get("mean")),
                "candidate_a_window_repeated_4gram_worst": _finite_or_blank(a_window.get("worst")),
                "candidate_b_window_repeated_4gram_worst": _finite_or_blank(b_window.get("worst")),
                "candidate_a_window_repeated_4gram_variance": _finite_or_blank(a_window.get("variance")),
                "candidate_b_window_repeated_4gram_variance": _finite_or_blank(b_window.get("variance")),
                "window_worst_repeated_4gram_prefers_truth_better": int(window_worst_pref == truth_better),
                "window_mean_repeated_4gram_prefers_truth_better": int(window_mean_pref == truth_better),
            }
            rows.append({field: row.get(field, "") for field in ROW_FIELDS})
    rows.sort(
        key=lambda row: (
            int(row.get("current_score_chose_truth_better", 0) or 0),
            -_safe_float(row.get("truth_gap_abs")),
            str(row.get("artifact_path", "")),
        )
    )
    return rows


def summarize_probe_rows(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    row_list = [dict(row) for row in rows]
    unique_rows = _unique_by_pair(row_list)
    misranked = [row for row in row_list if not int(row.get("current_score_chose_truth_better", 0) or 0)]
    correct = [row for row in row_list if int(row.get("current_score_chose_truth_better", 0) or 0)]
    unique_misranked = _unique_by_pair(misranked)
    unique_correct = _unique_by_pair(correct)
    truth_gaps = [_safe_float(row.get("truth_gap_abs")) for row in row_list if math.isfinite(_safe_float(row.get("truth_gap_abs")))]
    return {
        "run_label": RUN_LABEL,
        "updated_utc": _utc_now_text(),
        "min_truth_gap": MIN_TRUTH_GAP,
        "row_occurrence_count": len(row_list),
        "unique_candidate_pair_count": len(unique_rows),
        "score_misranked_row_count": len(misranked),
        "score_correct_row_count": len(correct),
        "score_misranked_unique_pair_count": len(unique_misranked),
        "score_correct_unique_pair_count": len(unique_correct),
        "median_truth_gap": None if not truth_gaps else float(median(truth_gaps)),
        "max_truth_gap": None if not truth_gaps else float(max(truth_gaps)),
        "repeated_4gram_misranked_rows": _preference_summary(misranked, "repeated_4gram_prefers_truth_better"),
        "repeated_4gram_misranked_unique_pairs": _preference_summary(unique_misranked, "repeated_4gram_prefers_truth_better"),
        "repeated_4gram_correct_rows": _preference_summary(correct, "repeated_4gram_prefers_truth_better"),
        "repeated_4gram_correct_unique_pairs": _preference_summary(unique_correct, "repeated_4gram_prefers_truth_better"),
        "window_worst_misranked_rows": _preference_summary(misranked, "window_worst_repeated_4gram_prefers_truth_better"),
        "window_worst_misranked_unique_pairs": _preference_summary(unique_misranked, "window_worst_repeated_4gram_prefers_truth_better"),
        "window_mean_misranked_rows": _preference_summary(misranked, "window_mean_repeated_4gram_prefers_truth_better"),
        "window_mean_misranked_unique_pairs": _preference_summary(unique_misranked, "window_mean_repeated_4gram_prefers_truth_better"),
        "fixture_counts": _counts_by(row_list, "fixture_seed"),
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
    lines = [
        "# Repetition / Window-Consistency Probe v1",
        "",
        "## Summary",
        "",
        f"- row occurrences: `{summary['row_occurrence_count']}`",
        f"- unique candidate pairs: `{summary['unique_candidate_pair_count']}`",
        f"- score-misranked row occurrences: `{summary['score_misranked_row_count']}`",
        f"- score-misranked unique pairs: `{summary['score_misranked_unique_pair_count']}`",
        f"- score-correct row occurrences: `{summary['score_correct_row_count']}`",
        f"- score-correct unique pairs: `{summary['score_correct_unique_pair_count']}`",
        f"- minimum truth gap: `{summary['min_truth_gap']}`",
        "",
        "## Repeated 4-Gram Diagnostic",
        "",
        f"- misranked rows: `{json.dumps(dict(summary['repeated_4gram_misranked_rows']), sort_keys=True)}`",
        f"- misranked unique pairs: `{json.dumps(dict(summary['repeated_4gram_misranked_unique_pairs']), sort_keys=True)}`",
        f"- score-correct rows: `{json.dumps(dict(summary['repeated_4gram_correct_rows']), sort_keys=True)}`",
        f"- score-correct unique pairs: `{json.dumps(dict(summary['repeated_4gram_correct_unique_pairs']), sort_keys=True)}`",
        "",
        "## Window Repeated 4-Gram Diagnostics",
        "",
        f"- worst-window misranked rows: `{json.dumps(dict(summary['window_worst_misranked_rows']), sort_keys=True)}`",
        f"- worst-window misranked unique pairs: `{json.dumps(dict(summary['window_worst_misranked_unique_pairs']), sort_keys=True)}`",
        f"- mean-window misranked rows: `{json.dumps(dict(summary['window_mean_misranked_rows']), sort_keys=True)}`",
        f"- mean-window misranked unique pairs: `{json.dumps(dict(summary['window_mean_misranked_unique_pairs']), sort_keys=True)}`",
        "",
        "## Interpretation Rules",
        "",
        "- This is report-only and does not change solver runtime behavior.",
        "- Truth fields are evaluation labels only.",
        "- Row occurrence counts and unique-pair counts are both reported; do not treat rows as independent pairs.",
        "- The probe tests repeated 4-gram and token-window repetition diagnostics only, not a broad scorer replacement.",
    ]
    return "\n".join(lines).rstrip() + "\n"


def write_probe_outputs(*, rows: Sequence[Mapping[str, Any]], output_dir: Path = OUTPUT_DIR) -> dict[str, Any]:
    resolved_output = output_dir.resolve()
    try:
        resolved_output.relative_to(REPO_ROOT.resolve())
    except ValueError as exc:
        raise ValueError(f"Output directory must stay under repo root: {output_dir}") from exc
    resolved_output.mkdir(parents=True, exist_ok=True)
    row_list = [dict(row) for row in rows]
    summary = summarize_probe_rows(row_list)
    summary["output_dir"] = _repo_rel(resolved_output)
    _write_csv(resolved_output / "repetition_window_consistency_probe_rows.csv", row_list)
    _write_jsonl(resolved_output / "repetition_window_consistency_probe_rows.jsonl", row_list)
    _write_json(resolved_output / "repetition_window_consistency_probe_summary.json", summary)
    (resolved_output / "repetition_window_consistency_probe_readout.md").write_text(
        build_readout(summary),
        encoding="utf-8",
    )
    return summary


def run_probe() -> dict[str, Any]:
    started = time.perf_counter()
    rows = build_probe_rows()
    summary = write_probe_outputs(rows=rows)
    summary["elapsed_seconds"] = float(time.perf_counter() - started)
    _write_json(OUTPUT_DIR / "repetition_window_consistency_probe_summary.json", summary)
    print(
        "[repetition_window_consistency_probe_v1] "
        f"rows={summary['row_occurrence_count']} "
        f"unique_pairs={summary['unique_candidate_pair_count']} "
        f"misranked_rows={summary['score_misranked_row_count']} "
        f"misranked_unique_pairs={summary['score_misranked_unique_pair_count']} "
        f"output_dir={summary['output_dir']}",
        flush=True,
    )
    return summary


def main() -> None:
    run_probe()


if __name__ == "__main__":
    main()
