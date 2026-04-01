from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Sequence

from tools.benchmarks.periodic_sub_trans.no_wli import artifact_resume as resume_mod


DEFAULT_SELECTOR_ORDER: tuple[str, ...] = (
    "legacy",
    "score_plus_novelty",
    "score_plus_novelty_plus_source_penalties",
)


def _safe_float(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return float(out)


def load_selected_trial_material_rows(path: Path) -> list[Dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return [dict(row) for row in list(payload or []) if isinstance(row, Mapping)]


def _selector_order_key(selector: str) -> tuple[int, str]:
    try:
        idx = DEFAULT_SELECTOR_ORDER.index(str(selector))
    except ValueError:
        idx = len(DEFAULT_SELECTOR_ORDER)
    return (idx, str(selector))


def run_selected_trial_row_continuations(
    *,
    selected_rows: Sequence[Mapping[str, Any]],
    runner_fn: Callable[..., Dict[str, Any]] | None = None,
) -> list[Dict[str, Any]]:
    run_selected = runner_fn or resume_mod.run_stage35_from_selected_trial_row
    case_cache: dict[str, Any] = {}
    results: list[Dict[str, Any]] = []
    for row_obj in sorted(
        [dict(row) for row in list(selected_rows or []) if isinstance(row, Mapping)],
        key=lambda row: (
            str(row.get("fixture_label", "") or ""),
            _selector_order_key(str(row.get("selector", "") or "")),
        ),
    ):
        selector = str(row_obj.get("selector", "") or "")
        if selector not in DEFAULT_SELECTOR_ORDER:
            continue
        artifact_relpath = str(row_obj.get("source_artifact_path", "") or "")
        if not artifact_relpath:
            raise ValueError("Selected trial row is missing source_artifact_path")
        case = case_cache.get(artifact_relpath)
        if case is None:
            case = resume_mod.load_artifact_case(artifact_path=Path(artifact_relpath))
            case_cache[artifact_relpath] = case
        results.append(
            dict(
                run_selected(
                    case,
                    selected_row=row_obj,
                )
            )
        )
    return results


def _build_continuation_summary_rows(
    rows: Sequence[Mapping[str, Any]],
) -> list[Dict[str, Any]]:
    out: list[Dict[str, Any]] = []
    for row_obj in list(rows or []):
        row = dict(row_obj or {})
        stage35 = dict(row.get("stage35", {}) or {})
        selected_truth = _safe_float(row.get("selected_candidate_final_match"))
        resumed_truth = _safe_float(row.get("resume_best_match_ratio"))
        out.append(
            dict(
                fixture_label=str(row.get("fixture_label", "") or ""),
                selector=str(row.get("selector", "") or ""),
                artifact_relpath=str(row.get("artifact_relpath", "") or ""),
                selected_candidate_hash=str(
                    row.get("selected_candidate_hash", "") or ""
                ),
                selected_candidate_source=str(
                    row.get("selected_candidate_source", "") or ""
                ),
                selected_candidate_lane=str(
                    row.get("selected_candidate_lane", "") or ""
                ),
                selected_truth_match=selected_truth,
                selected_final_score=_safe_float(
                    row.get("selected_candidate_final_score")
                ),
                replay_material_complete=int(
                    row.get("replay_material_complete", 0) or 0
                ),
                stage35_selected=int(stage35.get("selected", 0) or 0),
                stage35_accept_reason=str(stage35.get("accept_reason", "") or ""),
                stage35_best_candidate_hash=str(
                    stage35.get("best_candidate_hash", "") or ""
                ),
                stage35_best_seed_source=str(
                    stage35.get("best_seed_source", "") or ""
                ),
                stage35_best_stage3_source=str(
                    stage35.get("best_stage3_source", "") or ""
                ),
                stage35_best_lane=str(stage35.get("best_lane", "") or ""),
                stage35_best_source_rank=int(
                    stage35.get("best_source_rank", 0) or 0
                ),
                stage35_best_score=_safe_float(row.get("resume_best_score")),
                stage35_best_truth_match=resumed_truth,
                stage35_truth_gain_vs_selected=(
                    float(resumed_truth) - float(selected_truth)
                    if resumed_truth is not None and selected_truth is not None
                    else None
                ),
                stage35_archive_count=int(stage35.get("archive_count", 0) or 0),
                stage35_seed_count=int(stage35.get("seed_count", 0) or 0),
                stage35_rounds_completed=int(
                    stage35.get("rounds_completed", 0) or 0
                ),
                stage35_evals=int(stage35.get("evals", 0) or 0),
                stage35_runtime_seconds=_safe_float(
                    stage35.get("runtime_seconds", 0.0)
                ),
            )
        )
    return out


def write_stageb_continuation_report(
    *,
    continuation_rows: Sequence[Mapping[str, Any]],
    output_dir: Path,
) -> Dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    row_summaries = _build_continuation_summary_rows(continuation_rows)
    summary = dict(
        row_count=int(len(row_summaries)),
        rows=[dict(row) for row in row_summaries],
    )
    (output_dir / "continuation_results.json").write_text(
        json.dumps([dict(row) for row in continuation_rows], indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    lines = [
        "# Late-Stage Selector Stage B Continuation",
        "",
    ]
    for row in row_summaries:
        lines.extend(
            [
                f"## {str(row['fixture_label'])} / {str(row['selector'])}",
                "",
                f"- selected candidate: `{str(row['selected_candidate_hash'])}`",
                f"- selected truth: `{row['selected_truth_match']}`",
                f"- stage35 selected: `{int(row['stage35_selected'])}`",
                f"- stage35 accept reason: `{str(row['stage35_accept_reason'])}`",
                f"- stage35 best candidate: `{str(row['stage35_best_candidate_hash'])}`",
                f"- stage35 best truth: `{row['stage35_best_truth_match']}`",
                f"- stage35 truth gain vs selected: `{row['stage35_truth_gain_vs_selected']}`",
                "",
            ]
        )
    (output_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    return summary


def load_and_write_stageb_continuation_report(
    *,
    selected_rows_path: Path,
    output_dir: Path,
    runner_fn: Callable[..., Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    rows = load_selected_trial_material_rows(selected_rows_path)
    continuation_rows = run_selected_trial_row_continuations(
        selected_rows=rows,
        runner_fn=runner_fn,
    )
    return write_stageb_continuation_report(
        continuation_rows=continuation_rows,
        output_dir=output_dir,
    )
