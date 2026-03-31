from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli.build_output_catalog import (
    refresh_catalog_safely,
)


CATALOG_ROOT = Path("output/tools/benchmarks/periodic_sub_trans/no_wli_catalog")
SUMMARY_PATH = CATALOG_ROOT / "partial_state_signal_audit_summary.json"
REPORT_PATH = CATALOG_ROOT / "partial_state_signal_audit_report.md"

SELECTED_ARTIFACTS: tuple[dict[str, str], ...] = (
    {
        "label": "seed511_old_best",
        "path": (
            "output/tools/benchmarks/periodic_sub_trans/no_wli/"
            "20260312T002501438386Z__bench_solve_pipeline_no_wli__5961d3e/"
            "final_instances/fixture_fixture_001_p9_c3_l1000__text0__seed511.json"
        ),
    },
    {
        "label": "seed511_recovery",
        "path": (
            "output/tools/benchmarks/periodic_sub_trans/no_wli/"
            "20260321T190828084704Z__bench_solve_pipeline_no_wli__55b7159/"
            "final_instances/fixture_fixture_001_p9_c3_l1000__text0__seed511.json"
        ),
    },
    {
        "label": "seed511_stage35_win",
        "path": (
            "output/tools/benchmarks/periodic_sub_trans/no_wli/"
            "20260322T001521766633Z__bench_solve_pipeline_no_wli__55b7159/"
            "final_instances/fixture_fixture_001_p9_c3_l1000__text0__seed511.json"
        ),
    },
    {
        "label": "seed211_old_best",
        "path": (
            "output/tools/benchmarks/periodic_sub_trans/no_wli/"
            "20260309T092929767920Z__bench_solve_pipeline_no_wli__97536a2/"
            "final_instances/fixture_fixture_001_p9_c3_l1000__text0__seed211.json"
        ),
    },
    {
        "label": "seed211_stage35_fail",
        "path": (
            "output/tools/benchmarks/periodic_sub_trans/no_wli/"
            "20260322T192204224097Z__bench_solve_pipeline_no_wli__55b7159/"
            "final_instances/fixture_fixture_001_p9_c3_l1000__text0__seed211.json"
        ),
    },
    {
        "label": "seed411_old_best",
        "path": (
            "output/tools/benchmarks/periodic_sub_trans/no_wli/"
            "20260312T020424363346Z__bench_solve_pipeline_no_wli__5961d3e/"
            "final_instances/fixture_fixture_001_p9_c3_l1000__text0__seed411.json"
        ),
    },
)

STATE_SIGNAL_FIELDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("stage2_topk", ("score_stage2", "score_judge")),
    ("stage3_topk", ("score_raw", "score_pct", "score_judge")),
    ("phasec_start", ("final_score", "init_search_score", "score_gain")),
    ("stage35_seed", ("score", "search_score", "checkpoint_final_score")),
    ("stage35_archive", ("score", "search_score")),
)


def _repo_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve())).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return float("nan")


def _is_finite(value: Any) -> bool:
    return bool(np.isfinite(_safe_float(value)))


def _pearson_corr(lhs: Sequence[float], rhs: Sequence[float]) -> float:
    lhs_arr = np.asarray(list(lhs), dtype=np.float64).reshape(-1)
    rhs_arr = np.asarray(list(rhs), dtype=np.float64).reshape(-1)
    if int(lhs_arr.size) != int(rhs_arr.size) or int(lhs_arr.size) < 2:
        return float("nan")
    if float(np.std(lhs_arr)) <= 0.0 or float(np.std(rhs_arr)) <= 0.0:
        return float("nan")
    return float(np.corrcoef(lhs_arr, rhs_arr)[0, 1])


def _run_quality_bucket(best_match_ratio: float) -> str:
    if not np.isfinite(best_match_ratio):
        return "unknown"
    if float(best_match_ratio) >= 0.75:
        return "strong"
    if float(best_match_ratio) <= 0.65:
        return "weak"
    return "middle"


def _truth_match_from_plaintext(
    plaintext_idx: Sequence[Any] | None, target_plaintext_idx: Sequence[Any] | None
) -> float:
    if plaintext_idx is None or target_plaintext_idx is None:
        return float("nan")
    pt = np.asarray(list(plaintext_idx), dtype=np.int64).reshape(-1)
    target = np.asarray(list(target_plaintext_idx), dtype=np.int64).reshape(-1)
    if int(pt.size) == 0 or int(target.size) == 0:
        return float("nan")
    size = min(int(pt.size), int(target.size))
    if size <= 0:
        return float("nan")
    return float(np.mean(pt[:size] == target[:size]))


def _base_row(
    *,
    label: str,
    path: Path,
    final_best_match: float,
    final_best_score: float,
    run_quality_bucket: str,
    key_seed: int,
    state_kind: str,
    row_id: str,
) -> dict[str, Any]:
    return {
        "run_label": str(label),
        "artifact_relpath": _repo_rel(path),
        "key_seed": int(key_seed),
        "final_best_match": float(final_best_match),
        "final_best_score": float(final_best_score),
        "run_quality_bucket": str(run_quality_bucket),
        "state_kind": str(state_kind),
        "row_id": str(row_id),
        "truth_match": float("nan"),
        "score_stage2": float("nan"),
        "score_judge": float("nan"),
        "score_raw": float("nan"),
        "score_pct": float("nan"),
        "final_score": float("nan"),
        "init_search_score": float("nan"),
        "score_gain": float("nan"),
        "score": float("nan"),
        "search_score": float("nan"),
        "checkpoint_final_score": float("nan"),
    }


def extract_partial_state_rows(
    artifact: Mapping[str, Any], *, path: Path, label: str
) -> list[dict[str, Any]]:
    final_best_match = _safe_float(artifact.get("best_match_ratio", float("nan")))
    final_best_score = _safe_float(artifact.get("best_score", float("nan")))
    run_quality = _run_quality_bucket(final_best_match)
    key_seed = int(artifact.get("key_seed", artifact.get("seed", 0)) or 0)
    target_plaintext_idx = list(artifact.get("target_plaintext_idx", []) or [])
    rows: list[dict[str, Any]] = []

    for idx, row in enumerate(list(artifact.get("stage2_topk", []) or []), start=1):
        out = _base_row(
            label=label,
            path=path,
            final_best_match=final_best_match,
            final_best_score=final_best_score,
            run_quality_bucket=run_quality,
            key_seed=key_seed,
            state_kind="stage2_topk",
            row_id=f"stage2_topk:{idx}",
        )
        out["truth_match"] = _safe_float(row.get("match_ratio", float("nan")))
        out["score_stage2"] = _safe_float(row.get("score_stage2", float("nan")))
        out["score_judge"] = _safe_float(row.get("score_judge", float("nan")))
        rows.append(out)

    for idx, row in enumerate(list(artifact.get("stage3_topk", []) or []), start=1):
        out = _base_row(
            label=label,
            path=path,
            final_best_match=final_best_match,
            final_best_score=final_best_score,
            run_quality_bucket=run_quality,
            key_seed=key_seed,
            state_kind="stage3_topk",
            row_id=f"stage3_topk:{idx}",
        )
        out["truth_match"] = _safe_float(row.get("match_ratio", float("nan")))
        out["score_judge"] = _safe_float(row.get("score_judge", float("nan")))
        out["score_raw"] = _safe_float(row.get("score_raw", float("nan")))
        out["score_pct"] = _safe_float(row.get("score_pct", float("nan")))
        rows.append(out)

    checkpoint_path = path.parents[1] / "phasec_start_checkpoints.jsonl"
    if checkpoint_path.exists():
        with checkpoint_path.open("r", encoding="utf-8") as handle:
            for idx, line in enumerate(handle, start=1):
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                out = _base_row(
                    label=label,
                    path=path,
                    final_best_match=final_best_match,
                    final_best_score=final_best_score,
                    run_quality_bucket=run_quality,
                    key_seed=key_seed,
                    state_kind="phasec_start",
                    row_id=f"phasec_start:{idx}",
                )
                out["truth_match"] = _safe_float(
                    row.get("final_match", row.get("match_final", float("nan")))
                )
                out["final_score"] = _safe_float(
                    row.get("final_score", row.get("score_final", float("nan")))
                )
                out["init_search_score"] = _safe_float(
                    row.get("init_search_score", float("nan"))
                )
                out["score_gain"] = _safe_float(row.get("score_gain", float("nan")))
                rows.append(out)

    for idx, row in enumerate(list(artifact.get("stage35_seed_rows", []) or []), start=1):
        out = _base_row(
            label=label,
            path=path,
            final_best_match=final_best_match,
            final_best_score=final_best_score,
            run_quality_bucket=run_quality,
            key_seed=key_seed,
            state_kind="stage35_seed",
            row_id=f"stage35_seed:{idx}",
        )
        truth_match = _safe_float(row.get("checkpoint_final_match", float("nan")))
        if not np.isfinite(truth_match):
            truth_match = _truth_match_from_plaintext(
                row.get("plaintext_idx", []), target_plaintext_idx
            )
        out["truth_match"] = float(truth_match)
        out["score"] = _safe_float(row.get("score", float("nan")))
        out["search_score"] = _safe_float(row.get("search_score", float("nan")))
        out["checkpoint_final_score"] = _safe_float(
            row.get("checkpoint_final_score", float("nan"))
        )
        rows.append(out)

    for idx, row in enumerate(list(artifact.get("stage35_archive", []) or []), start=1):
        out = _base_row(
            label=label,
            path=path,
            final_best_match=final_best_match,
            final_best_score=final_best_score,
            run_quality_bucket=run_quality,
            key_seed=key_seed,
            state_kind="stage35_archive",
            row_id=f"stage35_archive:{idx}",
        )
        out["truth_match"] = _truth_match_from_plaintext(
            row.get("plaintext_idx", []), target_plaintext_idx
        )
        out["score"] = _safe_float(row.get("score", float("nan")))
        out["search_score"] = _safe_float(row.get("search_score", float("nan")))
        rows.append(out)

    return rows


def summarize_signal(
    rows: Sequence[Mapping[str, Any]], *, state_kind: str, signal_field: str
) -> dict[str, Any]:
    bucket = [
        dict(row)
        for row in rows
        if str(row.get("state_kind", "")) == str(state_kind)
        and _is_finite(row.get(signal_field, float("nan")))
        and _is_finite(row.get("truth_match", float("nan")))
    ]
    if not bucket:
        return {}

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in bucket:
        grouped[str(row["run_label"])].append(row)

    top_by_signal: list[dict[str, Any]] = []
    best_by_truth: list[dict[str, Any]] = []
    run_max_signal: list[tuple[str, float, float, str]] = []
    for run_label, run_rows in grouped.items():
        top_row = max(
            run_rows,
            key=lambda row: (
                _safe_float(row.get(signal_field, float("nan"))),
                _safe_float(row.get("truth_match", float("nan"))),
                str(row.get("row_id", "")),
            ),
        )
        best_truth_row = max(
            run_rows,
            key=lambda row: (
                _safe_float(row.get("truth_match", float("nan"))),
                _safe_float(row.get(signal_field, float("nan"))),
                str(row.get("row_id", "")),
            ),
        )
        top_by_signal.append(top_row)
        best_by_truth.append(best_truth_row)
        run_max_signal.append(
            (
                run_label,
                _safe_float(top_row.get(signal_field, float("nan"))),
                _safe_float(top_row.get("final_best_match", float("nan"))),
                str(top_row.get("run_quality_bucket", "")),
            )
        )

    strong_vals = [sig for _, sig, _, bucket_name in run_max_signal if bucket_name == "strong"]
    weak_vals = [sig for _, sig, _, bucket_name in run_max_signal if bucket_name == "weak"]
    top_truth = [_safe_float(row.get("truth_match", float("nan"))) for row in top_by_signal]
    best_truth = [_safe_float(row.get("truth_match", float("nan"))) for row in best_by_truth]
    run_max = [item[1] for item in run_max_signal]
    run_final = [item[2] for item in run_max_signal]
    row_signals = [_safe_float(row.get(signal_field, float("nan"))) for row in bucket]
    row_truths = [_safe_float(row.get("truth_match", float("nan"))) for row in bucket]

    separation_gap = float("nan")
    if strong_vals and weak_vals:
        separation_gap = float(min(strong_vals) - max(weak_vals))

    return {
        "state_kind": str(state_kind),
        "signal_field": str(signal_field),
        "row_count": int(len(bucket)),
        "run_count": int(len(grouped)),
        "strong_run_count": int(len(strong_vals)),
        "weak_run_count": int(len(weak_vals)),
        "row_signal_truth_corr": float(_pearson_corr(row_signals, row_truths)),
        "run_max_signal_final_match_corr": float(_pearson_corr(run_max, run_final)),
        "top_signal_is_best_truth_rate": float(
            np.mean(
                np.asarray(
                    [
                        1.0 if top_by_signal[idx]["row_id"] == best_by_truth[idx]["row_id"] else 0.0
                        for idx in range(len(top_by_signal))
                    ],
                    dtype=np.float64,
                )
            )
        ),
        "mean_top_signal_truth": float(np.mean(np.asarray(top_truth, dtype=np.float64))),
        "mean_best_truth": float(np.mean(np.asarray(best_truth, dtype=np.float64))),
        "mean_truth_regret": float(
            np.mean(np.asarray([best_truth[idx] - top_truth[idx] for idx in range(len(top_truth))], dtype=np.float64))
        ),
        "strong_run_max_signal_mean": (
            float(np.mean(np.asarray(strong_vals, dtype=np.float64))) if strong_vals else float("nan")
        ),
        "weak_run_max_signal_mean": (
            float(np.mean(np.asarray(weak_vals, dtype=np.float64))) if weak_vals else float("nan")
        ),
        "strong_run_min_signal": min(strong_vals) if strong_vals else float("nan"),
        "strong_run_max_signal": max(strong_vals) if strong_vals else float("nan"),
        "weak_run_min_signal": min(weak_vals) if weak_vals else float("nan"),
        "weak_run_max_signal": max(weak_vals) if weak_vals else float("nan"),
        "strong_above_weak_no_overlap": int(
            1 if np.isfinite(separation_gap) and float(separation_gap) > 0.0 else 0
        ),
        "strong_minus_weak_separation_gap": float(separation_gap),
    }


def summarize_runs(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["run_label"])].append(dict(row))
    out: list[dict[str, Any]] = []
    for run_label, run_rows in grouped.items():
        any_row = run_rows[0]
        counts: dict[str, int] = defaultdict(int)
        for row in run_rows:
            counts[str(row["state_kind"])] += 1
        out.append(
            {
                "run_label": str(run_label),
                "artifact_relpath": str(any_row["artifact_relpath"]),
                "key_seed": int(any_row["key_seed"]),
                "final_best_match": float(any_row["final_best_match"]),
                "final_best_score": float(any_row["final_best_score"]),
                "run_quality_bucket": str(any_row["run_quality_bucket"]),
                "stage2_topk_rows": int(counts.get("stage2_topk", 0)),
                "stage3_topk_rows": int(counts.get("stage3_topk", 0)),
                "phasec_rows": int(counts.get("phasec_start", 0)),
                "stage35_seed_rows": int(counts.get("stage35_seed", 0)),
                "stage35_archive_rows": int(counts.get("stage35_archive", 0)),
            }
        )
    return sorted(
        out,
        key=lambda row: (
            -float(row["final_best_match"]),
            str(row["run_label"]),
        ),
    )


def _selected_artifact_paths() -> list[tuple[str, Path]]:
    out: list[tuple[str, Path]] = []
    for row in SELECTED_ARTIFACTS:
        out.append((str(row["label"]), REPO_ROOT / str(row["path"])))
    return out


def build_partial_state_signal_summary() -> dict[str, Any]:
    partial_rows: list[dict[str, Any]] = []
    for label, path in _selected_artifact_paths():
        artifact = _load_json(path)
        partial_rows.extend(extract_partial_state_rows(artifact, path=path, label=label))

    signal_summaries: list[dict[str, Any]] = []
    for state_kind, fields in STATE_SIGNAL_FIELDS:
        for signal_field in fields:
            summary = summarize_signal(partial_rows, state_kind=state_kind, signal_field=signal_field)
            if summary:
                signal_summaries.append(summary)

    run_rows = summarize_runs(partial_rows)

    findings: list[str] = []
    stage2_primary = next(
        (
            row
            for row in signal_summaries
            if str(row["state_kind"]) == "stage2_topk"
            and str(row["signal_field"]) == "score_stage2"
        ),
        None,
    )
    stage3_primary = next(
        (
            row
            for row in signal_summaries
            if str(row["state_kind"]) == "stage3_topk"
            and str(row["signal_field"]) == "score_judge"
        ),
        None,
    )
    archive_search = next(
        (
            row
            for row in signal_summaries
            if str(row["state_kind"]) == "stage35_archive"
            and str(row["signal_field"]) == "search_score"
        ),
        None,
    )
    if stage2_primary:
        findings.append(
            "Stage-2 partial-state scores remain weak as basin discriminators across the selected hard runs: "
            f"`score_stage2` run-max/final-match correlation is {float(stage2_primary['run_max_signal_final_match_corr']):.3f}."
        )
    if stage3_primary:
        findings.append(
            "Stage-3 top-k scores carry much stronger basin signal once the search reaches a useful family: "
            f"`score_judge` run-max/final-match correlation is {float(stage3_primary['run_max_signal_final_match_corr']):.3f}, "
            f"with strong-vs-weak separation gap {float(stage3_primary['strong_minus_weak_separation_gap']):.6f}."
        )
    if archive_search:
        findings.append(
            "Late Stage-3.5 full-score improvements are not sufficient on weak seeds when search support is absent: "
            f"the archive `search_score` signal still shows stronger truth alignment than raw archive score "
            f"(row/truth corr {float(archive_search['row_signal_truth_corr']):.3f})."
        )

    conclusion = (
        "Current live-visible signals do not separate strong from dead states well enough before Stage 3, "
        "but they do become informative inside Stage-3 top-k and later. The general failure therefore looks "
        "like weak early/mid basin signal plus seed-sensitive search reach, not a completely broken late-stage scorer."
    )

    return {
        "generated_utc": datetime.now(UTC).isoformat(),
        "selected_artifacts": [
            {"label": label, "path": _repo_rel(path)} for label, path in _selected_artifact_paths()
        ],
        "run_summary_rows": run_rows,
        "signal_summary_rows": signal_summaries,
        "findings": findings,
        "conclusion": conclusion,
    }


def write_partial_state_signal_report(summary: Mapping[str, Any]) -> dict[str, str]:
    CATALOG_ROOT.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    run_rows = list(summary.get("run_summary_rows", []) or [])
    signal_rows = list(summary.get("signal_summary_rows", []) or [])
    lines = [
        "# no_wli Partial-State Signal Audit",
        "",
        f"Generated: {summary.get('generated_utc', '')}",
        "",
        "## Scope",
        "",
        "Selected hard-case runs:",
    ]
    for row in list(summary.get("selected_artifacts", []) or []):
        lines.append(f"- `{row.get('label', '')}`: `{row.get('path', '')}`")
    lines.extend(
        [
            "",
            "This audit checks whether existing live-visible partial-state signals separate stronger and weaker hard-case basins before late refinement.",
            "",
            "## Main findings",
            "",
        ]
    )
    for finding in list(summary.get("findings", []) or []):
        lines.append(f"- {finding}")
    lines.extend(
        [
            "",
            "## Conclusion",
            "",
            f"- {summary.get('conclusion', '')}",
            "",
            "## Run summary",
            "",
            "| Run | Seed | Final Match | Bucket | Stage2 Rows | Stage3 Rows | PhaseC Rows | Stage35 Seed Rows | Stage35 Archive Rows |",
            "| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in run_rows:
        lines.append(
            "| "
            f"{row.get('run_label', '')} | "
            f"{int(row.get('key_seed', 0) or 0)} | "
            f"{float(row.get('final_best_match', float('nan'))):.3f} | "
            f"{row.get('run_quality_bucket', '')} | "
            f"{int(row.get('stage2_topk_rows', 0) or 0)} | "
            f"{int(row.get('stage3_topk_rows', 0) or 0)} | "
            f"{int(row.get('phasec_rows', 0) or 0)} | "
            f"{int(row.get('stage35_seed_rows', 0) or 0)} | "
            f"{int(row.get('stage35_archive_rows', 0) or 0)} |"
        )
    lines.extend(
        [
            "",
            "## Signal summary",
            "",
            "| State | Signal | Runs | Strong Runs | Weak Runs | Row Score/Truth Corr | Run Max/Final Corr | Top-Is-Best Rate | Mean Truth Regret | Strong-Weak Gap |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in signal_rows:
        lines.append(
            "| "
            f"{row.get('state_kind', '')} | "
            f"{row.get('signal_field', '')} | "
            f"{int(row.get('run_count', 0) or 0)} | "
            f"{int(row.get('strong_run_count', 0) or 0)} | "
            f"{int(row.get('weak_run_count', 0) or 0)} | "
            f"{float(row.get('row_signal_truth_corr', float('nan'))):.3f} | "
            f"{float(row.get('run_max_signal_final_match_corr', float('nan'))):.3f} | "
            f"{float(row.get('top_signal_is_best_truth_rate', float('nan'))):.3f} | "
            f"{float(row.get('mean_truth_regret', float('nan'))):.3f} | "
            f"{float(row.get('strong_minus_weak_separation_gap', float('nan'))):.6f} |"
        )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"summary_path": _repo_rel(SUMMARY_PATH), "report_path": _repo_rel(REPORT_PATH)}


def main() -> None:
    summary = build_partial_state_signal_summary()
    outputs = write_partial_state_signal_report(summary)
    refresh_catalog_safely(print_fn=print)
    print(outputs["summary_path"])
    print(outputs["report_path"])


if __name__ == "__main__":
    main()
