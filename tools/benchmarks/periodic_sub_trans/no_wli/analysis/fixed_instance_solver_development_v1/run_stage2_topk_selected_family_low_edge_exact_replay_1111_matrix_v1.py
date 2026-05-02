from __future__ import annotations

import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from typing import Any, Mapping


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError(
        "Could not locate repo root from "
        "run_stage2_topk_selected_family_low_edge_exact_replay_1111_matrix_v1.py"
    )


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (  # noqa: E402
    verify_stage2_topk_selected_family_low_edge_exact_replay_1111_7004 as replay_mod,
)


RUN_LABEL = "stage2_topk_selected_family_low_edge_exact_replay_1111_matrix_v1"
OUTPUT_BASE_DIR = replay_mod.OUTPUT_BASE_DIR
FIXTURE_SEED = 1111
TARGET_SEARCH_SEEDS = (7004, 7001, 7003, 7005, 7002)
INTENDED_WALLCLOCK_BUDGET_HOURS = 8.0
MAX_WALLCLOCK_SECONDS = INTENDED_WALLCLOCK_BUDGET_HOURS * 3600.0
ANCHORED_PER_JOB_SECONDS = 4073.328
MECHANISM_LAYER = "selection"
QUESTION = (
    "Across the fixed 1111/search7001-7005 family, does the concrete upstream "
    "selector selected_family_low_edge_eps_0p016_v1 ever survive exact Stage-3 "
    "execution as a real improvement, or does the saved handoff gain collapse "
    "consistently at replay time?"
)
SUSPICION = (
    "The first 1111/search7004 exact replay may be only one local negative, and "
    "other fixed 1111 lanes may still convert the saved handoff gain into a real "
    "Stage-3 replay improvement."
)
MAIN_ALTERNATIVE = (
    "The saved handoff gain collapses consistently across the 1111 family, so the "
    "selector line should be closed before any second replay family or live "
    "runtime is launched."
)
IF_SUSPICION_TRUE_EXPECT = (
    "At least one additional exact replay should beat both the artifact baseline "
    "and the retained Stage-3 reference, making the selector family worth a "
    "tighter follow-up rather than closure."
)
IF_ALTERNATIVE_TRUE_EXPECT = (
    "The replays should stay flat or worse across the family, or the family mean "
    "should remain non-positive, which closes the selector line on exact gates."
)
TOMORROWS_DECISION_RULE = (
    "Advance only if the family produces at least two clean wins versus both the "
    "artifact baseline and retained Stage-3 reference; refine only for a mixed "
    "family with at least one clean win; close if the family remains flat or "
    "worse overall."
)
STOP_CONDITION = (
    "This batch is budgeted from the completed 1111/search7004 exact-replay "
    "anchor of about 01:07:53 per job. After each completed job, recompute the "
    "projected serial total. If the projection exceeds the 8h session budget, "
    "stop before launching another cell."
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_label() -> str:
    return _utc_now().strftime("%Y%m%dT%H%M%SZ")


def _utc_now_iso() -> str:
    return _utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")


def _relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _safe_str(value: Any) -> str:
    return str(value or "")


def _format_duration(seconds: float) -> str:
    total_seconds = max(0, int(round(float(seconds))))
    hours, rem = divmod(total_seconds, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _print_progress(message: str) -> None:
    print(f"[{_utc_now_iso()}] {message}", flush=True)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _append_jsonl(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(payload), sort_keys=True) + "\n")


def _expected_total_seconds(total_jobs: int) -> float:
    return float(total_jobs) * float(ANCHORED_PER_JOB_SECONDS)


def _project_total_seconds(completed_jobs: int, elapsed_seconds: float) -> float:
    if completed_jobs <= 0:
        return _expected_total_seconds(len(TARGET_SEARCH_SEEDS))
    return float(elapsed_seconds) / float(completed_jobs) * float(len(TARGET_SEARCH_SEEDS))


def build_matrix_recommendation(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "recommendation": "incomplete",
            "clean_win_count": 0,
            "baseline_win_count": 0,
            "family_mean_delta_vs_baseline": float("nan"),
            "reason": "no completed rows",
        }

    clean_win_count = 0
    baseline_win_count = 0
    deltas: list[float] = []
    best_row = max(
        rows,
        key=lambda row: (
            _safe_float(row.get("match_delta_vs_retained_stage3_reference")),
            _safe_float(row.get("match_delta_vs_baseline")),
        ),
    )
    for row in rows:
        delta_vs_baseline = _safe_float(row.get("match_delta_vs_baseline"))
        delta_vs_retained = _safe_float(
            row.get("match_delta_vs_retained_stage3_reference")
        )
        if math.isfinite(delta_vs_baseline):
            deltas.append(delta_vs_baseline)
        if delta_vs_baseline > 0.0:
            baseline_win_count += 1
        if delta_vs_baseline > 0.0 and delta_vs_retained > 0.0:
            clean_win_count += 1

    family_mean_delta = (
        sum(deltas) / float(len(deltas)) if deltas else float("nan")
    )
    if clean_win_count >= 2 and family_mean_delta > 0.0:
        recommendation = "advance"
        reason = "family exact replay produced multiple clean wins"
    elif clean_win_count >= 1 or baseline_win_count >= 1:
        recommendation = "refine"
        reason = "family exact replay is mixed but not uniformly negative"
    else:
        recommendation = "close"
        reason = "family exact replay stayed flat or worse on exact gates"
    return {
        "recommendation": recommendation,
        "clean_win_count": int(clean_win_count),
        "baseline_win_count": int(baseline_win_count),
        "family_mean_delta_vs_baseline": float(family_mean_delta),
        "best_search_seed": _safe_int(best_row.get("search_seed")),
        "best_delta_vs_baseline": _safe_float(best_row.get("match_delta_vs_baseline")),
        "best_delta_vs_retained_stage3_reference": _safe_float(
            best_row.get("match_delta_vs_retained_stage3_reference")
        ),
        "reason": reason,
    }


def _write_rows_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        fieldnames = [
            "search_seed",
            "status",
            "output_dir",
            "baseline_best_match_ratio",
            "retained_stage3_reference_match_ratio",
            "resume_best_match_ratio",
            "match_delta_vs_baseline",
            "match_delta_vs_retained_stage3_reference",
            "candidate_truth_delta_vs_baseline_row",
        ]
    else:
        fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_markdown(
    path: Path,
    *,
    rows: list[dict[str, Any]],
    recommendation: Mapping[str, Any],
    coverage: Mapping[str, Any],
) -> None:
    lines = [
        "# Selected-Family Low-Edge Exact Replay Matrix: 1111 Family",
        "",
        "Question:",
        f"- {QUESTION}",
        "",
        "Coverage:",
        f"- completed jobs: `{_safe_int(coverage.get('completed_jobs'))}` / `{_safe_int(coverage.get('planned_jobs'))}`",
        f"- status: `{_safe_str(coverage.get('status'))}`",
        "",
        "Recommendation:",
        f"- `{_safe_str(recommendation.get('recommendation'))}`",
        f"- clean wins: `{_safe_int(recommendation.get('clean_win_count'))}`",
        f"- baseline wins: `{_safe_int(recommendation.get('baseline_win_count'))}`",
        (
            "- family mean delta vs baseline: "
            f"`{_safe_float(recommendation.get('family_mean_delta_vs_baseline')):.3f}`"
        ),
        f"- best search seed: `{_safe_int(recommendation.get('best_search_seed'))}`",
        f"- reason: {_safe_str(recommendation.get('reason'))}",
        "",
        "Per-cell read:",
    ]
    for row in rows:
        lines.extend(
            [
                f"- `search{_safe_int(row.get('search_seed'))}`",
                f"  - replay best `{_safe_float(row.get('resume_best_match_ratio')):.3f}`",
                f"  - baseline `{_safe_float(row.get('baseline_best_match_ratio')):.3f}`",
                (
                    "  - retained Stage-3 reference "
                    f"`{_safe_float(row.get('retained_stage3_reference_match_ratio')):.3f}`"
                ),
                f"  - delta vs baseline `{_safe_float(row.get('match_delta_vs_baseline')):.3f}`",
                (
                    "  - delta vs retained Stage-3 reference "
                    f"`{_safe_float(row.get('match_delta_vs_retained_stage3_reference')):.3f}`"
                ),
                (
                    "  - saved-row truth delta "
                    f"`{_safe_float(row.get('candidate_truth_delta_vs_baseline_row')):.3f}`"
                ),
            ]
        )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _configure_replay_module_for_seed(search_seed: int) -> tuple[int, str]:
    old_search_seed = int(replay_mod.SEARCH_SEED)
    old_run_label = str(replay_mod.RUN_LABEL)
    replay_mod.SEARCH_SEED = int(search_seed)
    replay_mod.RUN_LABEL = (
        f"stage2_topk_selected_family_low_edge_exact_replay_1111_search{search_seed}_v1"
    )
    return old_search_seed, old_run_label


def _restore_replay_module(old_search_seed: int, old_run_label: str) -> None:
    replay_mod.SEARCH_SEED = int(old_search_seed)
    replay_mod.RUN_LABEL = str(old_run_label)


def _load_child_selector_summary(output_dir_relpath: str) -> dict[str, Any]:
    output_dir = REPO_ROOT / Path(output_dir_relpath)
    summary_path = output_dir / "selected_family_low_edge_exact_replay_summary.json"
    return json.loads(summary_path.read_text(encoding="utf-8"))


def _build_row_from_child(
    *,
    search_seed: int,
    child_run_summary: Mapping[str, Any],
) -> dict[str, Any]:
    output_dir_relpath = _safe_str(child_run_summary.get("output_dir"))
    selector_summary = _load_child_selector_summary(output_dir_relpath)
    return {
        "search_seed": int(search_seed),
        "status": "completed",
        "output_dir": output_dir_relpath,
        "baseline_best_match_ratio": _safe_float(
            child_run_summary.get("baseline_best_match_ratio")
        ),
        "retained_stage3_reference_match_ratio": _safe_float(
            child_run_summary.get("retained_stage3_reference_match_ratio")
        ),
        "resume_best_match_ratio": _safe_float(
            child_run_summary.get("resume_best_match_ratio")
        ),
        "match_delta_vs_baseline": _safe_float(
            child_run_summary.get("match_delta_vs_baseline")
        ),
        "match_delta_vs_retained_stage3_reference": _safe_float(
            child_run_summary.get("match_delta_vs_retained_stage3_reference")
        ),
        "candidate_truth_delta_vs_baseline_row": _safe_float(
            selector_summary.get("candidate_truth_delta_vs_baseline_row")
        ),
        "candidate_row_truth_match": _safe_float(
            selector_summary.get("candidate_row_truth_match")
        ),
        "baseline_row_truth_match": _safe_float(
            selector_summary.get("baseline_row_truth_match")
        ),
        "resume_best_stage": _safe_str(selector_summary.get("resume_best_stage")),
        "resume_source": _safe_str(selector_summary.get("resume_source")),
    }


def run_matrix() -> dict[str, Any]:
    started = monotonic()
    started_at_utc = _utc_now_iso()
    output_dir = OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)
    state_path = output_dir / "matrix_run_state.json"
    events_path = output_dir / "matrix_run_events.jsonl"
    rows_csv_path = output_dir / "selected_family_low_edge_exact_replay_1111_matrix_rows.csv"
    rows_jsonl_path = output_dir / "selected_family_low_edge_exact_replay_1111_matrix_rows.jsonl"
    summary_path = output_dir / "selected_family_low_edge_exact_replay_1111_matrix_summary.json"
    readout_path = output_dir / "selected_family_low_edge_exact_replay_1111_matrix_readout.md"
    planned_jobs = len(TARGET_SEARCH_SEEDS)
    expected_total_seconds = _expected_total_seconds(planned_jobs)
    budget_target_utc = datetime.fromtimestamp(
        _utc_now().timestamp() + MAX_WALLCLOCK_SECONDS, tz=timezone.utc
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    manifest = {
        "run_label": RUN_LABEL,
        "fixture_seed": FIXTURE_SEED,
        "target_search_seeds": [int(seed) for seed in TARGET_SEARCH_SEEDS],
        "planned_jobs": int(planned_jobs),
        "mechanism_layer": MECHANISM_LAYER,
        "question": QUESTION,
        "suspicion": SUSPICION,
        "main_alternative": MAIN_ALTERNATIVE,
        "if_suspicion_true_expect": IF_SUSPICION_TRUE_EXPECT,
        "if_alternative_true_expect": IF_ALTERNATIVE_TRUE_EXPECT,
        "tomorrows_decision_rule": TOMORROWS_DECISION_RULE,
        "stop_condition": STOP_CONDITION,
        "intended_wallclock_budget_hours": float(INTENDED_WALLCLOCK_BUDGET_HOURS),
        "anchored_per_job_seconds": float(ANCHORED_PER_JOB_SECONDS),
        "anchored_expected_total_seconds": float(expected_total_seconds),
        "budget_target_utc": budget_target_utc,
    }
    _write_json(output_dir / "attempt_manifest.json", manifest)

    rows: list[dict[str, Any]] = []
    state = {
        "run_label": RUN_LABEL,
        "status": "running",
        "started_at_utc": started_at_utc,
        "updated_at_utc": started_at_utc,
        "output_dir": _relative_path(output_dir),
        "fixture_seed": FIXTURE_SEED,
        "planned_jobs": int(planned_jobs),
        "completed_jobs": 0,
        "remaining_jobs": int(planned_jobs),
        "target_search_seeds": [int(seed) for seed in TARGET_SEARCH_SEEDS],
        "current_search_seed": None,
        "intended_wallclock_budget_hours": float(INTENDED_WALLCLOCK_BUDGET_HOURS),
        "budget_target_utc": budget_target_utc,
        "anchored_per_job_seconds": float(ANCHORED_PER_JOB_SECONDS),
        "anchored_expected_total_seconds": float(expected_total_seconds),
        "rows_csv_relpath": _relative_path(rows_csv_path),
        "rows_jsonl_relpath": _relative_path(rows_jsonl_path),
        "summary_json_relpath": _relative_path(summary_path),
    }
    _write_json(state_path, state)
    _append_jsonl(
        events_path,
        {
            "event": "run_started",
            "timestamp_utc": started_at_utc,
            "run_label": RUN_LABEL,
            "planned_jobs": int(planned_jobs),
            "budget_hours": float(INTENDED_WALLCLOCK_BUDGET_HOURS),
            "expected_total_seconds": float(expected_total_seconds),
            "output_dir": _relative_path(output_dir),
        },
    )
    _print_progress(
        "run_started "
        f"label={RUN_LABEL} "
        f"output_dir={_relative_path(output_dir)} "
        f"planned_jobs={planned_jobs} "
        f"budget={INTENDED_WALLCLOCK_BUDGET_HOURS:.2f}h "
        f"question=\"{QUESTION}\""
    )
    _print_progress(
        "decision_contract "
        f"if_suspicion=\"{IF_SUSPICION_TRUE_EXPECT}\" "
        f"if_alternative=\"{IF_ALTERNATIVE_TRUE_EXPECT}\" "
        f"decision_rule=\"{TOMORROWS_DECISION_RULE}\""
    )

    for index, search_seed in enumerate(TARGET_SEARCH_SEEDS, start=1):
        elapsed_seconds = float(monotonic() - started)
        projected_total_seconds = _project_total_seconds(len(rows), elapsed_seconds)
        if rows and projected_total_seconds > MAX_WALLCLOCK_SECONDS:
            state.update(
                {
                    "status": "stopped_projection_over_budget",
                    "updated_at_utc": _utc_now_iso(),
                    "remaining_jobs": int(planned_jobs - len(rows)),
                    "projected_total_seconds": float(projected_total_seconds),
                    "projected_total_hours": float(projected_total_seconds / 3600.0),
                }
            )
            _write_json(state_path, state)
            _append_jsonl(
                events_path,
                {
                    "event": "run_stopped_projection_over_budget",
                    "timestamp_utc": _utc_now_iso(),
                    "completed_jobs": int(len(rows)),
                    "planned_jobs": int(planned_jobs),
                    "projected_total_seconds": float(projected_total_seconds),
                },
            )
            _print_progress(
                "run_stopped "
                f"reason=projection_over_budget "
                f"completed={len(rows)}/{planned_jobs} "
                f"projected_total={_format_duration(projected_total_seconds)} "
                f"budget={_format_duration(MAX_WALLCLOCK_SECONDS)}"
            )
            break

        eta_seconds = max(
            0.0,
            _project_total_seconds(max(1, len(rows)), max(elapsed_seconds, ANCHORED_PER_JOB_SECONDS))
            - elapsed_seconds,
        )
        state.update(
            {
                "status": "running",
                "updated_at_utc": _utc_now_iso(),
                "current_search_seed": int(search_seed),
                "remaining_jobs": int(planned_jobs - len(rows)),
                "elapsed_seconds": float(elapsed_seconds),
                "elapsed": _format_duration(elapsed_seconds),
                "eta_seconds": float(eta_seconds),
                "eta": _format_duration(eta_seconds),
            }
        )
        _write_json(state_path, state)
        _append_jsonl(
            events_path,
            {
                "event": "job_started",
                "timestamp_utc": _utc_now_iso(),
                "job_index": int(index),
                "planned_jobs": int(planned_jobs),
                "search_seed": int(search_seed),
                "elapsed_seconds": float(elapsed_seconds),
                "eta_seconds": float(eta_seconds),
            },
        )
        _print_progress(
            "job_started "
            f"job={index}/{planned_jobs} "
            f"search_seed={search_seed} "
            f"elapsed={_format_duration(elapsed_seconds)} "
            f"eta={_format_duration(eta_seconds)}"
        )

        old_search_seed, old_run_label = _configure_replay_module_for_seed(search_seed)
        job_started = monotonic()
        try:
            child_run_summary = replay_mod.run_verification()
        except BaseException as exc:
            _restore_replay_module(old_search_seed, old_run_label)
            elapsed_seconds = float(monotonic() - started)
            state.update(
                {
                    "status": "failed",
                    "updated_at_utc": _utc_now_iso(),
                    "current_search_seed": int(search_seed),
                    "completed_jobs": int(len(rows)),
                    "remaining_jobs": int(planned_jobs - len(rows)),
                    "elapsed_seconds": float(elapsed_seconds),
                    "elapsed": _format_duration(elapsed_seconds),
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                }
            )
            _write_json(state_path, state)
            _append_jsonl(
                events_path,
                {
                    "event": "job_failed",
                    "timestamp_utc": _utc_now_iso(),
                    "job_index": int(index),
                    "search_seed": int(search_seed),
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                },
            )
            _print_progress(
                "job_failed "
                f"job={index}/{planned_jobs} "
                f"search_seed={search_seed} "
                f"error_type={type(exc).__name__}"
            )
            raise
        finally:
            _restore_replay_module(old_search_seed, old_run_label)

        row = _build_row_from_child(
            search_seed=search_seed,
            child_run_summary=child_run_summary,
        )
        rows.append(row)
        with rows_jsonl_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
        _write_rows_csv(rows_csv_path, rows)

        elapsed_seconds = float(monotonic() - started)
        job_elapsed_seconds = float(monotonic() - job_started)
        projected_total_seconds = _project_total_seconds(len(rows), elapsed_seconds)
        eta_seconds = max(0.0, projected_total_seconds - elapsed_seconds)
        state.update(
            {
                "status": "running",
                "updated_at_utc": _utc_now_iso(),
                "current_search_seed": None,
                "completed_jobs": int(len(rows)),
                "remaining_jobs": int(planned_jobs - len(rows)),
                "elapsed_seconds": float(elapsed_seconds),
                "elapsed": _format_duration(elapsed_seconds),
                "eta_seconds": float(eta_seconds),
                "eta": _format_duration(eta_seconds),
                "projected_total_seconds": float(projected_total_seconds),
                "projected_total_hours": float(projected_total_seconds / 3600.0),
                "latest_completed_search_seed": int(search_seed),
            }
        )
        _write_json(state_path, state)
        _append_jsonl(
            events_path,
            {
                "event": "job_finished",
                "timestamp_utc": _utc_now_iso(),
                "job_index": int(index),
                "planned_jobs": int(planned_jobs),
                "search_seed": int(search_seed),
                "job_elapsed_seconds": float(job_elapsed_seconds),
                "elapsed_seconds": float(elapsed_seconds),
                "eta_seconds": float(eta_seconds),
                "projected_total_seconds": float(projected_total_seconds),
                "resume_best_match_ratio": _safe_float(
                    row.get("resume_best_match_ratio")
                ),
                "match_delta_vs_baseline": _safe_float(
                    row.get("match_delta_vs_baseline")
                ),
            },
        )
        _print_progress(
            "job_finished "
            f"job={index}/{planned_jobs} "
            f"search_seed={search_seed} "
            f"delta_vs_baseline={_safe_float(row.get('match_delta_vs_baseline')):.3f} "
            f"delta_vs_retained={_safe_float(row.get('match_delta_vs_retained_stage3_reference')):.3f} "
            f"elapsed={_format_duration(elapsed_seconds)} "
            f"eta={_format_duration(eta_seconds)} "
            f"job_runtime={_format_duration(job_elapsed_seconds)}"
        )

    recommendation = build_matrix_recommendation(rows)
    final_status = _safe_str(state.get("status"))
    if final_status == "running":
        final_status = "completed"
    summary = {
        "run_label": RUN_LABEL,
        "output_dir": _relative_path(output_dir),
        "fixture_seed": FIXTURE_SEED,
        "planned_jobs": int(planned_jobs),
        "completed_jobs": int(len(rows)),
        "status": final_status,
        "started_at_utc": started_at_utc,
        "updated_at_utc": _utc_now_iso(),
        "elapsed_seconds": float(monotonic() - started),
        "elapsed": _format_duration(float(monotonic() - started)),
        "question": QUESTION,
        "mechanism_layer": MECHANISM_LAYER,
        "recommendation": dict(recommendation),
        "rows_csv_relpath": _relative_path(rows_csv_path),
        "rows_jsonl_relpath": _relative_path(rows_jsonl_path),
        "readout_md_relpath": _relative_path(readout_path),
    }
    _write_json(summary_path, summary)
    _write_markdown(
        readout_path,
        rows=rows,
        recommendation=recommendation,
        coverage=summary,
    )
    state.update(
        {
            "status": final_status,
            "updated_at_utc": summary["updated_at_utc"],
            "completed_jobs": int(len(rows)),
            "remaining_jobs": int(planned_jobs - len(rows)),
            "elapsed_seconds": float(summary["elapsed_seconds"]),
            "elapsed": str(summary["elapsed"]),
            "recommendation": dict(recommendation),
        }
    )
    _write_json(state_path, state)
    _append_jsonl(
        events_path,
        {
            "event": "run_finished",
            "timestamp_utc": _utc_now_iso(),
            "planned_jobs": int(planned_jobs),
            "completed_jobs": int(len(rows)),
            "status": final_status,
            "recommendation": _safe_str(recommendation.get("recommendation")),
            "best_search_seed": _safe_int(recommendation.get("best_search_seed")),
        },
    )
    _print_progress(
        "run_finished "
        f"label={RUN_LABEL} "
        f"elapsed={summary['elapsed']} "
        f"status={final_status} "
        f"recommendation={_safe_str(recommendation.get('recommendation'))} "
        f"completed_jobs={len(rows)}/{planned_jobs} "
        f"output_dir={_relative_path(output_dir)}"
    )
    return summary


def main() -> None:
    summary = run_matrix()
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
