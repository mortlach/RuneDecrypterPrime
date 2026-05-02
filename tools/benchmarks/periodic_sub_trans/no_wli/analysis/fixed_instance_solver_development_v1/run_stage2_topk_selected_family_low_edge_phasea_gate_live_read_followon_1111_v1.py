from __future__ import annotations

import csv
import json
import math
import sys
import time
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
        "run_stage2_topk_selected_family_low_edge_phasea_gate_live_read_followon_1111_v1.py"
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


RUN_LABEL = "stage2_topk_selected_family_low_edge_phasea_gate_live_read_followon_1111_v1"
PREDECESSOR_RUN_LABEL = "stage2_topk_selected_family_low_edge_exact_replay_1111_search7004_v1"
OUTPUT_BASE_DIR = replay_mod.OUTPUT_BASE_DIR
FIXTURE_SEED = 1111
PREDECESSOR_SEARCH_SEED = 7004
FOLLOWON_SEARCH_SEEDS = (7001, 7003, 7005, 7002)
FAMILY_SEARCH_SEEDS = (7004, 7001, 7003, 7005, 7002)
INTENDED_WALLCLOCK_BUDGET_HOURS = 8.0
MAX_WALLCLOCK_SECONDS = INTENDED_WALLCLOCK_BUDGET_HOURS * 3600.0
ANCHORED_PER_JOB_SECONDS = 4073.328
PHASEA_GATE_THRESHOLD = 0.30
PREDECESSOR_POLL_SECONDS = 60.0
MECHANISM_LAYER = "selection"
QUESTION = (
    "Once the active 1111/search7004 live-read canary finishes, do the remaining "
    "fixed 1111 exact replays also emit the new Phase-A gate snapshot cleanly, "
    "and does that live snapshot reproduce the known keep/filter split across "
    "the rest of the family?"
)
SUSPICION = (
    "The new Phase-A gate snapshot will persist cleanly across the full 1111 "
    "family, and the live read will match the offline split: keep 7003/7004/7005 "
    "and filter 7001/7002."
)
MAIN_ALTERNATIVE = (
    "The new snapshot may be missing, too late, or inconsistent enough across "
    "the family that the branch still cannot choose a real fallback/stop action."
)
IF_SUSPICION_TRUE_EXPECT = (
    "All completed cells should expose a usable phasea_gate_snapshot, and the "
    "derived live gate verdicts should agree with the current offline family read."
)
IF_ALTERNATIVE_TRUE_EXPECT = (
    "One or more cells should fail to write the snapshot cleanly or disagree "
    "with the current keep/filter split, which keeps the branch in instrumentation "
    "refinement rather than action selection."
)
TOMORROWS_DECISION_RULE = (
    "Advance only if the predecessor canary completes with a real gate snapshot, "
    "all follow-on cells expose the same snapshot surface, and the live gate "
    "verdict matches the known family split on every completed cell. Refine "
    "for any partial artifact or verdict mismatch."
)
STOP_CONDITION = (
    "This follow-on is budgeted from the completed exact-replay anchor of about "
    "01:07:53 per family cell. The session counts the predecessor 7004 canary "
    "plus the four remaining cells. After each completed follow-on cell, "
    "recompute the projected five-cell total from observed elapsed. If the "
    "projection exceeds the 8h session budget, stop before launching another cell."
)
EXPECTED_GATE_VERDICTS = {
    7001: "filter",
    7002: "filter",
    7003: "keep",
    7004: "keep",
    7005: "keep",
}


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


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_utc_timestamp(value: str) -> datetime:
    return datetime.strptime(str(value), "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=timezone.utc
    )


def _expected_total_seconds() -> float:
    return float(len(FAMILY_SEARCH_SEEDS)) * float(ANCHORED_PER_JOB_SECONDS)


def _project_total_seconds(
    *,
    completed_rows: list[Mapping[str, Any]],
) -> float:
    elapsed_values = [
        _safe_float(row.get("elapsed_seconds"))
        for row in completed_rows
        if math.isfinite(_safe_float(row.get("elapsed_seconds")))
    ]
    if not elapsed_values:
        return _expected_total_seconds()
    return (
        sum(elapsed_values)
        / float(len(elapsed_values))
        * float(len(FAMILY_SEARCH_SEEDS))
    )


def _gate_verdict(phasea_rank1_init_match: float) -> str:
    if not math.isfinite(float(phasea_rank1_init_match)):
        return "unknown"
    if float(phasea_rank1_init_match) >= float(PHASEA_GATE_THRESHOLD):
        return "keep"
    return "filter"


def _snapshot_is_usable(
    snapshot_payload: Mapping[str, Any],
) -> bool:
    return math.isfinite(_safe_float(snapshot_payload.get("phaseA_rank1_init_match")))


def _find_latest_predecessor_dir() -> Path:
    matches: list[tuple[datetime, Path]] = []
    for candidate in OUTPUT_BASE_DIR.iterdir():
        if not candidate.is_dir():
            continue
        if not candidate.name.endswith(f"__{PREDECESSOR_RUN_LABEL}"):
            continue
        attempt_status_path = candidate / "attempt_status.json"
        if not attempt_status_path.exists():
            continue
        attempt_status = _load_json(attempt_status_path)
        started_at_utc = _safe_str(attempt_status.get("started_at_utc"))
        if not started_at_utc:
            continue
        matches.append((_parse_utc_timestamp(started_at_utc), candidate))
    if not matches:
        raise RuntimeError(
            "No predecessor 1111/search7004 live-read canary attempt_status.json found"
        )
    matches.sort(key=lambda item: item[0])
    return matches[-1][1]


def _build_row_from_output_dir(
    *,
    output_dir_relpath: str,
    cell_origin: str,
) -> dict[str, Any]:
    output_dir = REPO_ROOT / Path(output_dir_relpath)
    attempt_status = _load_json(output_dir / "attempt_status.json")
    run_summary = _load_json(output_dir / "run_summary.json")
    selector_summary = _load_json(
        output_dir / "selected_family_low_edge_exact_replay_summary.json"
    )
    snapshot_relpath = _safe_str(attempt_status.get("phasea_gate_snapshot_json_relpath"))
    snapshot_path = REPO_ROOT / Path(snapshot_relpath) if snapshot_relpath else Path()
    snapshot_exists = bool(snapshot_relpath) and snapshot_path.exists()
    snapshot_payload = _load_json(snapshot_path) if snapshot_exists else {}
    snapshot_usable = int(1 if _snapshot_is_usable(snapshot_payload) else 0)
    snapshot_ts = _safe_str(snapshot_payload.get("ts_utc"))
    started_at_utc = _safe_str(attempt_status.get("started_at_utc"))
    snapshot_elapsed_seconds = float("nan")
    if snapshot_ts and started_at_utc:
        snapshot_elapsed_seconds = (
            _parse_utc_timestamp(snapshot_ts) - _parse_utc_timestamp(started_at_utc)
        ).total_seconds()
    total_elapsed_seconds = _safe_float(attempt_status.get("elapsed_seconds"))
    snapshot_elapsed_share = float("nan")
    if math.isfinite(snapshot_elapsed_seconds) and math.isfinite(total_elapsed_seconds):
        if total_elapsed_seconds > 0.0:
            snapshot_elapsed_share = snapshot_elapsed_seconds / total_elapsed_seconds
    phasea_rank1_init_match = _safe_float(
        snapshot_payload.get("phaseA_rank1_init_match")
    )
    gate_verdict = _gate_verdict(phasea_rank1_init_match)
    expected_verdict = EXPECTED_GATE_VERDICTS.get(
        _safe_int(run_summary.get("search_seed")),
        "",
    )
    return {
        "search_seed": _safe_int(run_summary.get("search_seed")),
        "cell_origin": str(cell_origin),
        "status": _safe_str(attempt_status.get("status")),
        "output_dir": output_dir_relpath,
        "elapsed_seconds": float(total_elapsed_seconds),
        "elapsed": _safe_str(attempt_status.get("elapsed")),
        "baseline_best_match_ratio": _safe_float(
            run_summary.get("baseline_best_match_ratio")
        ),
        "retained_stage3_reference_match_ratio": _safe_float(
            run_summary.get("retained_stage3_reference_match_ratio")
        ),
        "resume_best_match_ratio": _safe_float(
            run_summary.get("resume_best_match_ratio")
        ),
        "match_delta_vs_baseline": _safe_float(
            run_summary.get("match_delta_vs_baseline")
        ),
        "match_delta_vs_retained_stage3_reference": _safe_float(
            run_summary.get("match_delta_vs_retained_stage3_reference")
        ),
        "candidate_truth_delta_vs_baseline_row": _safe_float(
            selector_summary.get("candidate_truth_delta_vs_baseline_row")
        ),
        "phasea_gate_snapshot_present": int(1 if snapshot_exists else 0),
        "phasea_gate_snapshot_usable": int(snapshot_usable),
        "phasea_gate_snapshot_json_relpath": snapshot_relpath,
        "phasea_gate_snapshot_elapsed_seconds": float(snapshot_elapsed_seconds),
        "phasea_gate_snapshot_elapsed_share": float(snapshot_elapsed_share),
        "phasea_rank1_init_match": float(phasea_rank1_init_match),
        "phasea_best_init_match": _safe_float(
            snapshot_payload.get("phaseA_best_init_match")
        ),
        "phasea_best_final_match": _safe_float(
            snapshot_payload.get("phaseA_best_final_match")
        ),
        "phasea_rank1_plateau_would_stop": _safe_int(
            snapshot_payload.get("phaseA_rank1_plateau_would_stop")
        ),
        "phaseB_ready_reason": _safe_str(snapshot_payload.get("phaseB_ready_reason")),
        "phaseB_ran": _safe_int(snapshot_payload.get("phaseB_ran")),
        "gate_threshold": float(PHASEA_GATE_THRESHOLD),
        "gate_verdict": gate_verdict,
        "expected_gate_verdict": str(expected_verdict),
        "gate_verdict_matches_expected": int(
            1 if expected_verdict and gate_verdict == expected_verdict else 0
        ),
    }


def build_live_read_recommendation(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "recommendation": "blocked",
            "snapshot_present_count": 0,
            "verdict_match_count": 0,
            "reason": "no completed family rows",
        }

    snapshot_present_count = sum(
        int(_safe_int(row.get("phasea_gate_snapshot_present"))) for row in rows
    )
    snapshot_usable_count = sum(
        int(_safe_int(row.get("phasea_gate_snapshot_usable"))) for row in rows
    )
    verdict_match_count = sum(
        int(_safe_int(row.get("gate_verdict_matches_expected"))) for row in rows
    )
    snapshot_elapsed_seconds = [
        _safe_float(row.get("phasea_gate_snapshot_elapsed_seconds"))
        for row in rows
        if math.isfinite(_safe_float(row.get("phasea_gate_snapshot_elapsed_seconds")))
    ]
    snapshot_elapsed_share = [
        _safe_float(row.get("phasea_gate_snapshot_elapsed_share"))
        for row in rows
        if math.isfinite(_safe_float(row.get("phasea_gate_snapshot_elapsed_share")))
    ]
    if (
        snapshot_present_count == len(rows)
        and snapshot_usable_count == len(rows)
        and verdict_match_count == len(rows)
    ):
        recommendation = "advance"
        reason = "snapshot persisted on every cell and reproduced the known family split"
    elif snapshot_present_count == len(rows) and snapshot_usable_count == len(rows):
        recommendation = "refine"
        reason = "snapshot persisted everywhere but at least one live verdict mismatched"
    else:
        recommendation = "hold"
        reason = "one or more cells failed to expose a usable live gate snapshot"
    return {
        "recommendation": recommendation,
        "snapshot_present_count": int(snapshot_present_count),
        "snapshot_usable_count": int(snapshot_usable_count),
        "verdict_match_count": int(verdict_match_count),
        "family_completed_rows": int(len(rows)),
        "mean_phasea_gate_snapshot_elapsed_seconds": (
            sum(snapshot_elapsed_seconds) / float(len(snapshot_elapsed_seconds))
            if snapshot_elapsed_seconds
            else float("nan")
        ),
        "mean_phasea_gate_snapshot_elapsed_share": (
            sum(snapshot_elapsed_share) / float(len(snapshot_elapsed_share))
            if snapshot_elapsed_share
            else float("nan")
        ),
        "reason": reason,
    }


def _write_rows_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        fieldnames = [
            "search_seed",
            "cell_origin",
            "status",
            "output_dir",
            "phasea_gate_snapshot_present",
            "phasea_gate_snapshot_usable",
            "phasea_gate_snapshot_elapsed_seconds",
            "phasea_rank1_init_match",
            "gate_verdict",
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
        "# Phase-A Gate Live-Read Follow-On: 1111 Family",
        "",
        "Question:",
        f"- {QUESTION}",
        "",
        "Coverage:",
        (
            "- completed family cells: "
            f"`{_safe_int(coverage.get('family_completed_jobs'))}` / "
            f"`{_safe_int(coverage.get('family_planned_jobs'))}`"
        ),
        (
            "- completed follow-on cells: "
            f"`{_safe_int(coverage.get('followon_completed_jobs'))}` / "
            f"`{_safe_int(coverage.get('followon_planned_jobs'))}`"
        ),
        f"- status: `{_safe_str(coverage.get('status'))}`",
        "",
        "Recommendation:",
        f"- `{_safe_str(recommendation.get('recommendation'))}`",
        f"- snapshot-present count: `{_safe_int(recommendation.get('snapshot_present_count'))}`",
        f"- snapshot-usable count: `{_safe_int(recommendation.get('snapshot_usable_count'))}`",
        f"- verdict-match count: `{_safe_int(recommendation.get('verdict_match_count'))}`",
        (
            "- mean gate snapshot elapsed: "
            f"`{_safe_float(recommendation.get('mean_phasea_gate_snapshot_elapsed_seconds')):.1f}s`"
        ),
        (
            "- mean gate snapshot share of total elapsed: "
            f"`{_safe_float(recommendation.get('mean_phasea_gate_snapshot_elapsed_share')):.3f}`"
        ),
        f"- reason: {_safe_str(recommendation.get('reason'))}",
        "",
        "Per-cell live-read:",
    ]
    for row in rows:
        lines.extend(
            [
                f"- `search{_safe_int(row.get('search_seed'))}`",
                f"  - origin `{_safe_str(row.get('cell_origin'))}`",
                f"  - gate snapshot present `{_safe_int(row.get('phasea_gate_snapshot_present'))}`",
                f"  - gate snapshot usable `{_safe_int(row.get('phasea_gate_snapshot_usable'))}`",
                (
                    "  - snapshot elapsed "
                    f"`{_safe_float(row.get('phasea_gate_snapshot_elapsed_seconds')):.1f}s`"
                ),
                (
                    "  - rank1 init match "
                    f"`{_safe_float(row.get('phasea_rank1_init_match')):.3f}`"
                ),
                f"  - gate verdict `{_safe_str(row.get('gate_verdict'))}`",
                f"  - expected verdict `{_safe_str(row.get('expected_gate_verdict'))}`",
                (
                    "  - delta vs baseline "
                    f"`{_safe_float(row.get('match_delta_vs_baseline')):.3f}`"
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


def _wait_for_predecessor_completion(
    *,
    predecessor_dir: Path,
    state_path: Path,
    events_path: Path,
    state_payload: dict[str, Any],
) -> dict[str, Any]:
    attempt_status_path = predecessor_dir / "attempt_status.json"
    if not attempt_status_path.exists():
        raise RuntimeError(
            f"Missing predecessor attempt status: {_relative_path(attempt_status_path)}"
        )
    while True:
        attempt_status = _load_json(attempt_status_path)
        predecessor_status = _safe_str(attempt_status.get("status"))
        state_payload.update(
            {
                "status": "waiting_on_predecessor",
                "predecessor_status": predecessor_status,
                "updated_at_utc": _utc_now_iso(),
            }
        )
        _write_json(state_path, state_payload)
        if predecessor_status == "completed":
            _append_jsonl(
                events_path,
                {
                    "event": "predecessor_completed",
                    "ts_utc": _utc_now_iso(),
                    "predecessor_output_dir": _relative_path(predecessor_dir),
                },
            )
            return attempt_status
        if predecessor_status in {"interrupted_or_failed", "failed"}:
            raise RuntimeError(
                f"Predecessor canary finished with non-completed status: {predecessor_status}"
            )
        _print_progress(
            "waiting_on_predecessor "
            f"label={PREDECESSOR_RUN_LABEL} "
            f"status={predecessor_status} "
            f"poll_seconds={int(PREDECESSOR_POLL_SECONDS)} "
            f"predecessor_output_dir={_relative_path(predecessor_dir)}"
        )
        time.sleep(float(PREDECESSOR_POLL_SECONDS))


def run_followon() -> dict[str, Any]:
    started = monotonic()
    started_at_utc = _utc_now_iso()
    output_dir = OUTPUT_BASE_DIR / f"{_utc_label()}__{RUN_LABEL}"
    output_dir.mkdir(parents=True, exist_ok=False)
    state_path = output_dir / "matrix_run_state.json"
    events_path = output_dir / "matrix_run_events.jsonl"
    rows_csv_path = (
        output_dir / "selected_family_low_edge_phasea_gate_live_read_followon_rows.csv"
    )
    rows_jsonl_path = (
        output_dir / "selected_family_low_edge_phasea_gate_live_read_followon_rows.jsonl"
    )
    summary_path = (
        output_dir / "selected_family_low_edge_phasea_gate_live_read_followon_summary.json"
    )
    readout_path = (
        output_dir / "selected_family_low_edge_phasea_gate_live_read_followon_readout.md"
    )
    predecessor_dir = _find_latest_predecessor_dir()
    state_payload: dict[str, Any] = {
        "status": "waiting_on_predecessor",
        "started_at_utc": started_at_utc,
        "updated_at_utc": started_at_utc,
        "run_label": RUN_LABEL,
        "output_dir": _relative_path(output_dir),
        "mechanism_layer": MECHANISM_LAYER,
        "question": QUESTION,
        "suspicion": SUSPICION,
        "main_alternative": MAIN_ALTERNATIVE,
        "if_suspicion_true_expect": IF_SUSPICION_TRUE_EXPECT,
        "if_alternative_true_expect": IF_ALTERNATIVE_TRUE_EXPECT,
        "decision_rule": TOMORROWS_DECISION_RULE,
        "stop_condition": STOP_CONDITION,
        "family_planned_jobs": len(FAMILY_SEARCH_SEEDS),
        "family_completed_jobs": 0,
        "followon_planned_jobs": len(FOLLOWON_SEARCH_SEEDS),
        "followon_completed_jobs": 0,
        "budget_hours": INTENDED_WALLCLOCK_BUDGET_HOURS,
        "anchored_per_job_seconds": ANCHORED_PER_JOB_SECONDS,
        "expected_total_elapsed": _format_duration(_expected_total_seconds()),
        "predecessor_output_dir": _relative_path(predecessor_dir),
        "predecessor_status": "running",
    }
    _write_json(state_path, state_payload)
    _append_jsonl(
        events_path,
        {
            "event": "run_started",
            "ts_utc": _utc_now_iso(),
            "output_dir": _relative_path(output_dir),
            "predecessor_output_dir": _relative_path(predecessor_dir),
            "family_planned_jobs": len(FAMILY_SEARCH_SEEDS),
            "followon_planned_jobs": len(FOLLOWON_SEARCH_SEEDS),
            "budget_hours": INTENDED_WALLCLOCK_BUDGET_HOURS,
        },
    )
    _print_progress(
        "run_started "
        f"label={RUN_LABEL} "
        f"output_dir={_relative_path(output_dir)} "
        f"predecessor_output_dir={_relative_path(predecessor_dir)} "
        f"family_jobs={len(FAMILY_SEARCH_SEEDS)} "
        f"followon_jobs={len(FOLLOWON_SEARCH_SEEDS)} "
        f"budget_hours={INTENDED_WALLCLOCK_BUDGET_HOURS:.1f}"
    )

    predecessor_status = _wait_for_predecessor_completion(
        predecessor_dir=predecessor_dir,
        state_path=state_path,
        events_path=events_path,
        state_payload=state_payload,
    )
    predecessor_output_dir_relpath = _safe_str(predecessor_status.get("output_dir"))
    predecessor_snapshot_relpath = _safe_str(
        predecessor_status.get("phasea_gate_snapshot_json_relpath")
    )
    predecessor_snapshot_path = (
        REPO_ROOT / Path(predecessor_snapshot_relpath)
        if predecessor_snapshot_relpath
        else Path()
    )
    if not predecessor_snapshot_relpath or not predecessor_snapshot_path.exists():
        state_payload.update(
            {
                "status": "blocked",
                "updated_at_utc": _utc_now_iso(),
                "predecessor_status": "completed_missing_phasea_gate_snapshot",
            }
        )
        _write_json(state_path, state_payload)
        raise RuntimeError(
            "Predecessor completed but did not produce phasea_gate_snapshot.json"
        )

    rows: list[dict[str, Any]] = [
        _build_row_from_output_dir(
            output_dir_relpath=predecessor_output_dir_relpath,
            cell_origin="predecessor_canary",
        )
    ]
    if not _safe_int(rows[0].get("phasea_gate_snapshot_usable")):
        state_payload.update(
            {
                "status": "blocked",
                "updated_at_utc": _utc_now_iso(),
                "predecessor_status": "completed_unusable_phasea_gate_snapshot",
            }
        )
        _write_json(state_path, state_payload)
        raise RuntimeError(
            "Predecessor completed but did not produce a usable phasea_gate_snapshot.json"
        )
    _append_jsonl(
        rows_jsonl_path,
        rows[0],
    )
    state_payload.update(
        {
            "status": "running",
            "updated_at_utc": _utc_now_iso(),
            "predecessor_status": "completed",
            "family_completed_jobs": 1,
        }
    )
    _write_json(state_path, state_payload)
    _print_progress(
        "predecessor_ready "
        f"search_seed={PREDECESSOR_SEARCH_SEED} "
        f"snapshot={_relative_path(predecessor_snapshot_path)} "
        f"snapshot_elapsed={_safe_float(rows[0].get('phasea_gate_snapshot_elapsed_seconds')):.1f}s"
    )

    for index, search_seed in enumerate(FOLLOWON_SEARCH_SEEDS, start=1):
        projected_total_seconds = _project_total_seconds(completed_rows=rows)
        if projected_total_seconds > float(MAX_WALLCLOCK_SECONDS):
            state_payload.update(
                {
                    "status": "stopped_over_budget",
                    "updated_at_utc": _utc_now_iso(),
                    "projected_total_seconds": float(projected_total_seconds),
                    "projected_total_elapsed": _format_duration(projected_total_seconds),
                    "family_completed_jobs": len(rows),
                    "followon_completed_jobs": int(index - 1),
                }
            )
            _write_json(state_path, state_payload)
            _print_progress(
                "run_stopped_over_budget "
                f"completed_family_jobs={len(rows)}/{len(FAMILY_SEARCH_SEEDS)} "
                f"projected_total={_format_duration(projected_total_seconds)} "
                f"budget={_format_duration(MAX_WALLCLOCK_SECONDS)}"
            )
            break

        _append_jsonl(
            events_path,
            {
                "event": "job_started",
                "ts_utc": _utc_now_iso(),
                "search_seed": int(search_seed),
                "followon_job_index": int(index),
                "followon_planned_jobs": len(FOLLOWON_SEARCH_SEEDS),
                "family_completed_jobs_before_launch": len(rows),
            },
        )
        _print_progress(
            "job_started "
            f"followon_job={index}/{len(FOLLOWON_SEARCH_SEEDS)} "
            f"family_coverage={len(rows)}/{len(FAMILY_SEARCH_SEEDS)} "
            f"search_seed={search_seed}"
        )
        old_search_seed, old_run_label = _configure_replay_module_for_seed(search_seed)
        try:
            child_run_summary = replay_mod.run_verification()
        finally:
            _restore_replay_module(old_search_seed, old_run_label)
        row = _build_row_from_output_dir(
            output_dir_relpath=_safe_str(child_run_summary.get("output_dir")),
            cell_origin="followon_matrix",
        )
        rows.append(row)
        _append_jsonl(rows_jsonl_path, row)
        state_payload.update(
            {
                "status": "running",
                "updated_at_utc": _utc_now_iso(),
                "family_completed_jobs": len(rows),
                "followon_completed_jobs": int(index),
                "latest_completed_search_seed": int(search_seed),
                "latest_completed_output_dir": _safe_str(row.get("output_dir")),
                "projected_total_seconds": float(
                    _project_total_seconds(completed_rows=rows)
                ),
            }
        )
        _write_json(state_path, state_payload)
        _print_progress(
            "job_finished "
            f"followon_job={index}/{len(FOLLOWON_SEARCH_SEEDS)} "
            f"family_coverage={len(rows)}/{len(FAMILY_SEARCH_SEEDS)} "
            f"search_seed={search_seed} "
            f"gate_snapshot={_safe_int(row.get('phasea_gate_snapshot_present'))} "
            f"gate_verdict={_safe_str(row.get('gate_verdict'))} "
            f"delta_vs_baseline={_safe_float(row.get('match_delta_vs_baseline')):.3f}"
        )

    recommendation = build_live_read_recommendation(rows)
    coverage = {
        "status": _safe_str(state_payload.get("status")),
        "family_planned_jobs": len(FAMILY_SEARCH_SEEDS),
        "family_completed_jobs": len(rows),
        "followon_planned_jobs": len(FOLLOWON_SEARCH_SEEDS),
        "followon_completed_jobs": max(0, len(rows) - 1),
    }
    _write_rows_csv(rows_csv_path, rows)
    _write_json(summary_path, recommendation)
    _write_markdown(
        readout_path,
        rows=rows,
        recommendation=recommendation,
        coverage=coverage,
    )
    elapsed_seconds = float(monotonic() - started)
    final_status = (
        _safe_str(state_payload.get("status"))
        if _safe_str(state_payload.get("status")) == "stopped_over_budget"
        else "completed"
    )
    state_payload.update(
        {
            "status": final_status,
            "updated_at_utc": _utc_now_iso(),
            "elapsed_seconds": float(elapsed_seconds),
            "elapsed": _format_duration(elapsed_seconds),
            "family_completed_jobs": len(rows),
            "followon_completed_jobs": max(0, len(rows) - 1),
            "recommendation": recommendation,
            "rows_csv": _relative_path(rows_csv_path),
            "rows_jsonl": _relative_path(rows_jsonl_path),
            "summary_json": _relative_path(summary_path),
            "readout_md": _relative_path(readout_path),
        }
    )
    _write_json(state_path, state_payload)
    _append_jsonl(
        events_path,
        {
            "event": "run_finished",
            "ts_utc": _utc_now_iso(),
            "status": final_status,
            "family_completed_jobs": len(rows),
            "followon_completed_jobs": max(0, len(rows) - 1),
            "recommendation": _safe_str(recommendation.get("recommendation")),
            "elapsed_seconds": float(elapsed_seconds),
        },
    )
    _print_progress(
        "run_finished "
        f"label={RUN_LABEL} "
        f"status={final_status} "
        f"elapsed={_format_duration(elapsed_seconds)} "
        f"family_completed_jobs={len(rows)}/{len(FAMILY_SEARCH_SEEDS)} "
        f"recommendation={_safe_str(recommendation.get('recommendation'))} "
        f"output_dir={_relative_path(output_dir)}"
    )
    return {
        "output_dir": _relative_path(output_dir),
        "state_path": _relative_path(state_path),
        "summary_path": _relative_path(summary_path),
        "rows_csv_path": _relative_path(rows_csv_path),
        "readout_path": _relative_path(readout_path),
        "family_completed_jobs": len(rows),
        "followon_completed_jobs": max(0, len(rows) - 1),
        "recommendation": _safe_str(recommendation.get("recommendation")),
    }


def main() -> None:
    summary = run_followon()
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
