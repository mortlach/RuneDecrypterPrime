from __future__ import annotations

import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from typing import Any, Mapping, Sequence


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError(
        "Could not locate repo root from "
        "run_stage2_topk_selected_family_low_edge_phasea_checkpoint_refined_confirmation_microprobe_v1.py"
    )


REPO_ROOT = _find_repo_root()
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.build_output_catalog import (  # noqa: E402
    refresh_catalog_safely,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.fixed_instance_solver_development_v1 import (  # noqa: E402
    verify_stage2_topk_selected_family_low_edge_exact_replay_1111_7004 as replay_mod,
)


RUN_LABEL = (
    "stage2_topk_selected_family_low_edge_phasea_checkpoint_refined_confirmation_microprobe_v1"
)
MECHANISM_LAYER = "selection"
FIXTURE_SEED = 1111
SEARCH_SEEDS = (7001, 7005)
LANE_ROLE_BY_SEED = {
    7001: "filtered_confirmation",
    7005: "kept_confirmation",
}
EXPECTED_GATE_VERDICT_BY_SEED = {
    7001: "filter",
    7005: "keep",
}
CHECKPOINT_COUNTS = (16, 32, 48, 64)
RULE_ID = "rank1_ge_0p30_or_best_ge_0p44"
RANK1_THRESHOLD = 0.30
BEST_THRESHOLD = 0.44
INTENDED_WALLCLOCK_BUDGET_HOURS = 1.0
MAX_WALLCLOCK_SECONDS = INTENDED_WALLCLOCK_BUDGET_HOURS * 3600.0
REFERENCE_BUNDLE_DIR = (
    REPO_ROOT
    / "output"
    / "tools"
    / "benchmarks"
    / "periodic_sub_trans"
    / "no_wli"
    / "analysis"
    / "fixed_instance_solver_development_v1"
    / "20260424T061044Z__stage2_topk_selected_family_low_edge_phasea_gate_live_read_followon_1111_v1"
)
REFERENCE_ROWS_CSV = (
    REFERENCE_BUNDLE_DIR / "selected_family_low_edge_phasea_gate_live_read_followon_rows.csv"
)
NEXT_BRANCH_ADVANCE_LABEL = (
    "stage2_topk_selected_family_low_edge_phasea_checkpoint_refined_action_microprobe"
)
NEXT_BRANCH_HOLD_LABEL = (
    "stage2_topk_selected_family_low_edge_phasea_checkpoint_refined_field_persistence"
)
QUESTION = (
    "Does the refined provisional rule rank1>=0.30 or best>=0.44 hold on one "
    "second filtered 1111 lane and one second kept 1111 lane before the current "
    "late gate surface?"
)
SUSPICION = (
    "The refined provisional rule should confirm on 7001 and 7005 at the same "
    "early restart16 checkpoint that already worked on 7002 and 7003."
)
MAIN_ALTERNATIVE = (
    "The refined rule may overfit the first two canaries, fail on the second "
    "filtered or kept lane, or only confirm too late to matter."
)
DECISION_RULE = (
    "Advance only if both confirmation canaries match the expected verdict at a "
    "shared checkpoint before restart64 with materially earlier timing than the "
    "current late gate. Hold if either lane fails the refined rule."
)
STOP_CONDITION = (
    "This microprobe is anchored from the completed exact replay family: "
    "7001 took about 00:23:41 and 7005 took about 00:24:23, for an anchored "
    "total of about 00:48:04. After the first completed canary, recompute the "
    "projected two-job total from the observed row plus the remaining anchor. "
    "If that projection exceeds 01:00:00, stop before launching the second canary."
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")


def _utc_label() -> str:
    return _utc_now().strftime("%Y%m%dT%H%M%SZ")


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


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _append_jsonl(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(payload), sort_keys=True))
        handle.write("\n")


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"Refusing to write empty CSV: {_relative_path(path)}")
    fieldnames = list(dict(rows[0]).keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _print_progress(message: str) -> None:
    print(f"[{_utc_now_iso()}] {message}", flush=True)


def _mean(values: Sequence[float]) -> float:
    finite = [value for value in values if math.isfinite(value)]
    if not finite:
        return float("nan")
    return float(sum(finite) / float(len(finite)))


def _gate_verdict(*, rank1_init_match: Any, best_init_match: Any) -> str:
    rank1_value = _safe_float(rank1_init_match)
    best_value = _safe_float(best_init_match)
    if math.isfinite(rank1_value) and rank1_value >= float(RANK1_THRESHOLD):
        return "keep"
    if math.isfinite(best_value) and best_value >= float(BEST_THRESHOLD):
        return "keep"
    return "filter"


def _trigger_source(*, rank1_init_match: Any, best_init_match: Any) -> str:
    rank1_value = _safe_float(rank1_init_match)
    best_value = _safe_float(best_init_match)
    if math.isfinite(rank1_value) and rank1_value >= float(RANK1_THRESHOLD):
        return "rank1_floor"
    if math.isfinite(best_value) and best_value >= float(BEST_THRESHOLD):
        return "high_best_rescue"
    return "filter"


def _load_reference_rows() -> dict[int, dict[str, Any]]:
    rows = list(csv.DictReader(REFERENCE_ROWS_CSV.open(encoding="utf-8")))
    out: dict[int, dict[str, Any]] = {}
    for row in rows:
        search_seed = _safe_int(row.get("search_seed"))
        if search_seed not in SEARCH_SEEDS:
            continue
        out[search_seed] = {
            "search_seed": int(search_seed),
            "elapsed_seconds": _safe_float(row.get("elapsed_seconds")),
            "elapsed": _safe_str(row.get("elapsed")),
            "baseline_best_match_ratio": _safe_float(
                row.get("baseline_best_match_ratio")
            ),
            "retained_stage3_reference_match_ratio": _safe_float(
                row.get("retained_stage3_reference_match_ratio")
            ),
            "reference_resume_best_match_ratio": _safe_float(
                row.get("resume_best_match_ratio")
            ),
            "candidate_truth_delta_vs_baseline_row": _safe_float(
                row.get("candidate_truth_delta_vs_baseline_row")
            ),
            "late_gate_elapsed_share": _safe_float(
                row.get("phasea_gate_snapshot_elapsed_share")
            ),
            "late_gate_elapsed_seconds": _safe_float(
                row.get("phasea_gate_snapshot_elapsed_seconds")
            ),
            "expected_gate_verdict": _safe_str(row.get("expected_gate_verdict")),
        }
    missing = [seed for seed in SEARCH_SEEDS if seed not in out]
    if missing:
        raise RuntimeError(f"Missing reference rows for seeds: {missing}")
    return out


def _anchored_total_seconds(reference_rows: Mapping[int, Mapping[str, Any]]) -> float:
    return float(
        sum(_safe_float(reference_rows[seed]["elapsed_seconds"]) for seed in SEARCH_SEEDS)
    )


def _remaining_anchor_seconds(
    *,
    completed_seeds: Sequence[int],
    reference_rows: Mapping[int, Mapping[str, Any]],
) -> float:
    completed_set = {int(seed) for seed in completed_seeds}
    return float(
        sum(
            _safe_float(reference_rows[seed]["elapsed_seconds"])
            for seed in SEARCH_SEEDS
            if int(seed) not in completed_set
        )
    )


def _load_checkpoint_rows(attempt_status: Mapping[str, Any]) -> list[dict[str, Any]]:
    relpath = _safe_str(
        attempt_status.get("phasea_provisional_gate_snapshots_jsonl_relpath")
    )
    if not relpath:
        return []
    path = REPO_ROOT / Path(relpath)
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(dict(json.loads(line)))
    return rows


def _checkpoint_row(
    *,
    search_seed: int,
    lane_role: str,
    expected_gate_verdict: str,
    checkpoint_count: int,
    checkpoint_rows: Mapping[int, Mapping[str, Any]],
    attempt_status: Mapping[str, Any],
    run_summary: Mapping[str, Any],
    reference_row: Mapping[str, Any],
) -> dict[str, Any]:
    checkpoint = dict(checkpoint_rows.get(int(checkpoint_count), {}) or {})
    checkpoint_present = int(1 if checkpoint else 0)
    rank1_value = _safe_float(checkpoint.get("phaseA_rank1_init_match"))
    best_value = _safe_float(checkpoint.get("phaseA_best_init_match"))
    observed_gate_verdict = _gate_verdict(
        rank1_init_match=rank1_value,
        best_init_match=best_value,
    )
    attempt_elapsed_seconds = _safe_float(attempt_status.get("elapsed_seconds"))
    checkpoint_elapsed_seconds = _safe_float(
        checkpoint.get("phaseA_checkpoint_elapsed_seconds")
    )
    checkpoint_elapsed_share = (
        float(checkpoint_elapsed_seconds / attempt_elapsed_seconds)
        if checkpoint_present
        and math.isfinite(checkpoint_elapsed_seconds)
        and math.isfinite(attempt_elapsed_seconds)
        and float(attempt_elapsed_seconds) > 0.0
        else float("nan")
    )
    late_gate_elapsed_share = _safe_float(reference_row.get("late_gate_elapsed_share"))
    return {
        "search_seed": int(search_seed),
        "lane_role": str(lane_role),
        "status": _safe_str(attempt_status.get("status")),
        "output_dir": _safe_str(run_summary.get("output_dir")),
        "elapsed_seconds": attempt_elapsed_seconds,
        "elapsed": _safe_str(attempt_status.get("elapsed")),
        "reference_attempt_elapsed_seconds": _safe_float(
            reference_row.get("elapsed_seconds")
        ),
        "checkpoint_restart_count": int(checkpoint_count),
        "checkpoint_present": int(checkpoint_present),
        "checkpoint_elapsed_seconds": checkpoint_elapsed_seconds,
        "checkpoint_elapsed_share": checkpoint_elapsed_share,
        "late_gate_elapsed_share": late_gate_elapsed_share,
        "checkpoint_share_improvement_vs_late_gate": (
            float(late_gate_elapsed_share - checkpoint_elapsed_share)
            if checkpoint_present
            and math.isfinite(late_gate_elapsed_share)
            and math.isfinite(checkpoint_elapsed_share)
            else float("nan")
        ),
        "rank1_threshold": float(RANK1_THRESHOLD),
        "best_threshold": float(BEST_THRESHOLD),
        "phasea_rank1_init_match": rank1_value,
        "phasea_best_init_match": best_value,
        "trigger_source": _trigger_source(
            rank1_init_match=rank1_value,
            best_init_match=best_value,
        ),
        "observed_gate_verdict": observed_gate_verdict,
        "expected_gate_verdict": str(expected_gate_verdict),
        "verdict_matches_expected": int(
            1 if observed_gate_verdict == str(expected_gate_verdict) else 0
        ),
        "baseline_best_match_ratio": _safe_float(
            reference_row.get("baseline_best_match_ratio")
        ),
        "retained_stage3_reference_match_ratio": _safe_float(
            reference_row.get("retained_stage3_reference_match_ratio")
        ),
        "current_resume_best_match_ratio": _safe_float(
            run_summary.get("resume_best_match_ratio")
        ),
        "delta_vs_baseline": _safe_float(run_summary.get("match_delta_vs_baseline")),
        "candidate_truth_delta_vs_baseline_row": _safe_float(
            reference_row.get("candidate_truth_delta_vs_baseline_row")
        ),
    }


def _build_summary(checkpoint_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_checkpoint: dict[int, list[dict[str, Any]]] = {}
    for row in checkpoint_rows:
        checkpoint = _safe_int(row.get("checkpoint_restart_count"))
        by_checkpoint.setdefault(checkpoint, []).append(dict(row))

    shared_checkpoint_count = 0
    earliest_shared_checkpoint = 0
    earliest_shared_rows: list[dict[str, Any]] = []
    for checkpoint in sorted(by_checkpoint):
        rows = list(by_checkpoint[checkpoint])
        if len(rows) != len(SEARCH_SEEDS):
            continue
        if all(_safe_int(row.get("verdict_matches_expected")) == 1 for row in rows):
            shared_checkpoint_count += 1
            if earliest_shared_checkpoint == 0:
                earliest_shared_checkpoint = int(checkpoint)
                earliest_shared_rows = rows

    earliest_share = _mean(
        [_safe_float(row.get("checkpoint_elapsed_share")) for row in earliest_shared_rows]
    )
    earliest_improvement = _mean(
        [
            _safe_float(row.get("checkpoint_share_improvement_vs_late_gate"))
            for row in earliest_shared_rows
        ]
    )
    if earliest_shared_checkpoint > 0 and math.isfinite(earliest_improvement) and earliest_improvement >= 0.10:
        recommendation = "advance"
        next_branch = NEXT_BRANCH_ADVANCE_LABEL
        reason = (
            "the refined provisional rule confirms on the second filtered/kept "
            "pair at a shared early checkpoint with strong timing headroom"
        )
    elif earliest_shared_checkpoint > 0:
        recommendation = "refine"
        next_branch = NEXT_BRANCH_ADVANCE_LABEL
        reason = (
            "the refined provisional rule confirms on the second pair but the "
            "timing headroom is smaller than expected"
        )
    else:
        recommendation = "hold"
        next_branch = NEXT_BRANCH_HOLD_LABEL
        reason = (
            "the refined provisional rule did not reproduce the expected split "
            "on both confirmation canaries at a shared checkpoint"
        )
    return {
        "completed_canaries": int(len({int(row["search_seed"]) for row in checkpoint_rows})),
        "shared_match_checkpoint_count": int(shared_checkpoint_count),
        "earliest_shared_checkpoint_restart_count": int(earliest_shared_checkpoint),
        "mean_checkpoint_elapsed_share": earliest_share,
        "mean_checkpoint_share_improvement_vs_late_gate": earliest_improvement,
        "rank1_threshold": float(RANK1_THRESHOLD),
        "best_threshold": float(BEST_THRESHOLD),
        "rule_id": str(RULE_ID),
        "recommendation": str(recommendation),
        "next_branch": str(next_branch),
        "reason": str(reason),
    }


def _build_readout(summary: Mapping[str, Any], checkpoint_rows: Sequence[Mapping[str, Any]]) -> str:
    lines = [
        "# Phase-A Checkpoint Refined Confirmation Microprobe",
        "",
        "Question:",
        "- Does the refined provisional rule hold on one second filtered 1111 lane and one second kept 1111 lane before the current late gate surface?",
        "",
        "Coverage:",
        f"- completed canaries: `{_safe_int(summary.get('completed_canaries'))}` / `{len(SEARCH_SEEDS)}`",
        f"- recommendation: `{_safe_str(summary.get('recommendation'))}`",
        f"- selected rule: `{RULE_ID}`",
        f"- earliest shared matching checkpoint: `restart{_safe_int(summary.get('earliest_shared_checkpoint_restart_count'))}`",
        f"- mean checkpoint elapsed share: `{_safe_float(summary.get('mean_checkpoint_elapsed_share')):.3f}`",
        f"- mean share improvement versus late gate: `{_safe_float(summary.get('mean_checkpoint_share_improvement_vs_late_gate')):.3f}`",
        f"- reason: {_safe_str(summary.get('reason'))}",
        "",
        "Per-checkpoint read:",
    ]
    for row in checkpoint_rows:
        lines.extend(
            [
                f"- `search{_safe_int(row.get('search_seed'))}` / `restart{_safe_int(row.get('checkpoint_restart_count'))}`",
                f"  - verdict `{_safe_str(row.get('observed_gate_verdict'))}`",
                f"  - expected `{_safe_str(row.get('expected_gate_verdict'))}`",
                f"  - trigger `{_safe_str(row.get('trigger_source'))}`",
                f"  - rank1 `{_safe_float(row.get('phasea_rank1_init_match')):.3f}`",
                f"  - best `{_safe_float(row.get('phasea_best_init_match')):.3f}`",
                f"  - elapsed share `{_safe_float(row.get('checkpoint_elapsed_share')):.3f}`",
                f"  - share improvement `{_safe_float(row.get('checkpoint_share_improvement_vs_late_gate')):.3f}`",
            ]
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    output_dir = (
        REPO_ROOT
        / "output"
        / "tools"
        / "benchmarks"
        / "periodic_sub_trans"
        / "no_wli"
        / "analysis"
        / "fixed_instance_solver_development_v1"
        / f"{_utc_label()}__{RUN_LABEL}"
    )
    output_dir.mkdir(parents=True, exist_ok=False)
    state_path = output_dir / "matrix_run_state.json"
    events_path = output_dir / "matrix_run_events.jsonl"
    rows_csv_path = (
        output_dir
        / "selected_family_low_edge_phasea_checkpoint_refined_confirmation_rows.csv"
    )
    rows_jsonl_path = (
        output_dir
        / "selected_family_low_edge_phasea_checkpoint_refined_confirmation_rows.jsonl"
    )
    summary_path = (
        output_dir
        / "selected_family_low_edge_phasea_checkpoint_refined_confirmation_summary.json"
    )
    recommendation_path = (
        output_dir
        / "selected_family_low_edge_phasea_checkpoint_refined_confirmation_recommendation.json"
    )
    readout_path = (
        output_dir
        / "selected_family_low_edge_phasea_checkpoint_refined_confirmation_readout.md"
    )

    reference_rows = _load_reference_rows()
    anchored_total_seconds = _anchored_total_seconds(reference_rows)
    started_at = monotonic()
    completed_seeds: list[int] = []
    checkpoint_rows: list[dict[str, Any]] = []

    state = {
        "status": "running",
        "run_label": RUN_LABEL,
        "mechanism_layer": MECHANISM_LAYER,
        "fixture_seed": FIXTURE_SEED,
        "search_seeds": list(SEARCH_SEEDS),
        "question": QUESTION,
        "suspicion": SUSPICION,
        "alternative": MAIN_ALTERNATIVE,
        "decision_rule": DECISION_RULE,
        "stop_condition": STOP_CONDITION,
        "intended_wallclock_budget_hours": float(INTENDED_WALLCLOCK_BUDGET_HOURS),
        "intended_wallclock_budget_seconds": float(MAX_WALLCLOCK_SECONDS),
        "anchored_total_seconds": float(anchored_total_seconds),
        "anchored_total_elapsed": _format_duration(anchored_total_seconds),
        "completed_canaries": 0,
        "remaining_canaries": len(SEARCH_SEEDS),
        "rows_written": 0,
        "updated_at_utc": _utc_now_iso(),
    }
    _write_json(state_path, state)

    _print_progress(
        "run_started "
        f"label={RUN_LABEL} output_dir={_relative_path(output_dir)} "
        f"seeds={','.join(str(seed) for seed in SEARCH_SEEDS)} "
        f"rule_id={RULE_ID} anchored_total={_format_duration(anchored_total_seconds)}"
    )
    _append_jsonl(
        events_path,
        {
            "event": "run_started",
            "ts_utc": _utc_now_iso(),
            "run_label": RUN_LABEL,
            "output_dir": _relative_path(output_dir),
            "rule_id": RULE_ID,
        },
    )

    for index, search_seed in enumerate(SEARCH_SEEDS, start=1):
        elapsed_before = float(monotonic() - started_at)
        if elapsed_before > float(MAX_WALLCLOCK_SECONDS):
            state.update(
                status="stopped_over_budget",
                completed_canaries=int(len(completed_seeds)),
                remaining_canaries=int(len(SEARCH_SEEDS) - len(completed_seeds)),
                rows_written=int(len(checkpoint_rows)),
                updated_at_utc=_utc_now_iso(),
            )
            _write_json(state_path, state)
            break

        lane_role = LANE_ROLE_BY_SEED[search_seed]
        expected_gate_verdict = EXPECTED_GATE_VERDICT_BY_SEED[search_seed]
        child_run_label = (
            "stage2_topk_selected_family_low_edge_phasea_checkpoint_refined_confirm_"
            f"exact_replay_1111_search{search_seed}_v1"
        )
        _print_progress(
            f"canary_started unit={index}/{len(SEARCH_SEEDS)} "
            f"search_seed={search_seed} lane_role={lane_role} "
            f"anchored_elapsed={reference_rows[search_seed]['elapsed']}"
        )
        _append_jsonl(
            events_path,
            {
                "event": "canary_started",
                "ts_utc": _utc_now_iso(),
                "unit": int(index),
                "search_seed": int(search_seed),
                "lane_role": str(lane_role),
                "expected_gate_verdict": str(expected_gate_verdict),
                "child_run_label": str(child_run_label),
            },
        )

        run_summary = replay_mod.run_verification(
            search_seed=int(search_seed),
            run_label=str(child_run_label),
            scope_note_override=(
                "exact retained replay keeps stage35 disabled and exists only to "
                "test the refined provisional checkpoint rule on a second filtered "
                "and kept 1111 pair"
            ),
        )
        child_output_dir = REPO_ROOT / Path(_safe_str(run_summary.get("output_dir")))
        attempt_status = _load_json(child_output_dir / "attempt_status.json")
        provisional_snapshots = _load_checkpoint_rows(attempt_status)
        provisional_by_checkpoint = {
            _safe_int(row.get("phaseA_checkpoint_restart_count")): dict(row)
            for row in provisional_snapshots
            if _safe_int(row.get("phaseA_checkpoint_restart_count")) in CHECKPOINT_COUNTS
        }
        for checkpoint_count in CHECKPOINT_COUNTS:
            checkpoint_rows.append(
                _checkpoint_row(
                    search_seed=int(search_seed),
                    lane_role=str(lane_role),
                    expected_gate_verdict=str(expected_gate_verdict),
                    checkpoint_count=int(checkpoint_count),
                    checkpoint_rows=provisional_by_checkpoint,
                    attempt_status=attempt_status,
                    run_summary=run_summary,
                    reference_row=reference_rows[search_seed],
                )
            )
        completed_seeds.append(int(search_seed))
        state.update(
            completed_canaries=int(len(completed_seeds)),
            remaining_canaries=int(len(SEARCH_SEEDS) - len(completed_seeds)),
            rows_written=int(len(checkpoint_rows)),
            last_completed_search_seed=int(search_seed),
            last_child_output_dir=_safe_str(run_summary.get("output_dir")),
            observed_total_seconds=float(monotonic() - started_at),
            observed_total_elapsed=_format_duration(float(monotonic() - started_at)),
            updated_at_utc=_utc_now_iso(),
        )
        _write_json(state_path, state)
        _append_jsonl(
            events_path,
            {
                "event": "canary_finished",
                "ts_utc": _utc_now_iso(),
                "unit": int(index),
                "search_seed": int(search_seed),
                "lane_role": str(lane_role),
                "resume_best_match_ratio": _safe_float(
                    run_summary.get("resume_best_match_ratio")
                ),
                "delta_vs_baseline": _safe_float(run_summary.get("match_delta_vs_baseline")),
                "output_dir": _safe_str(run_summary.get("output_dir")),
            },
        )

        projected_total_seconds = float(monotonic() - started_at) + _remaining_anchor_seconds(
            completed_seeds=completed_seeds,
            reference_rows=reference_rows,
        )
        state.update(
            projected_total_seconds=float(projected_total_seconds),
            projected_total_elapsed=_format_duration(projected_total_seconds),
            updated_at_utc=_utc_now_iso(),
        )
        _write_json(state_path, state)
        if projected_total_seconds > float(MAX_WALLCLOCK_SECONDS) and len(completed_seeds) < len(SEARCH_SEEDS):
            state.update(
                status="stopped_over_budget",
                stop_reason="projection_exceeds_budget_after_completed_canary",
                completed_canaries=int(len(completed_seeds)),
                remaining_canaries=int(len(SEARCH_SEEDS) - len(completed_seeds)),
                rows_written=int(len(checkpoint_rows)),
                updated_at_utc=_utc_now_iso(),
            )
            _write_json(state_path, state)
            _append_jsonl(
                events_path,
                {
                    "event": "run_stopped_over_budget",
                    "ts_utc": _utc_now_iso(),
                    "projected_total_seconds": float(projected_total_seconds),
                    "budget_seconds": float(MAX_WALLCLOCK_SECONDS),
                },
            )
            break

    _write_csv(rows_csv_path, checkpoint_rows)
    _append_jsonl(events_path, {"event": "rows_written", "ts_utc": _utc_now_iso(), "rows": len(checkpoint_rows)})
    with rows_jsonl_path.open("w", encoding="utf-8") as handle:
        for row in checkpoint_rows:
            handle.write(json.dumps(dict(row), sort_keys=True))
            handle.write("\n")

    summary = _build_summary(checkpoint_rows)
    recommendation = {
        "recommendation": _safe_str(summary.get("recommendation")),
        "next_branch": _safe_str(summary.get("next_branch")),
        "reason": _safe_str(summary.get("reason")),
        "rule_id": RULE_ID,
        "rank1_threshold": float(RANK1_THRESHOLD),
        "best_threshold": float(BEST_THRESHOLD),
    }
    _write_json(summary_path, summary)
    _write_json(recommendation_path, recommendation)
    readout_path.write_text(_build_readout(summary, checkpoint_rows), encoding="utf-8")
    refresh_catalog_safely()

    elapsed_seconds = float(monotonic() - started_at)
    state.update(
        status="completed",
        elapsed_seconds=float(elapsed_seconds),
        elapsed=_format_duration(elapsed_seconds),
        completed_canaries=int(len(completed_seeds)),
        remaining_canaries=int(len(SEARCH_SEEDS) - len(completed_seeds)),
        rows_written=int(len(checkpoint_rows)),
        recommendation=_safe_str(summary.get("recommendation")),
        next_branch=_safe_str(summary.get("next_branch")),
        reason=_safe_str(summary.get("reason")),
        updated_at_utc=_utc_now_iso(),
    )
    _write_json(state_path, state)
    _append_jsonl(
        events_path,
        {
            "event": "run_finished",
            "ts_utc": _utc_now_iso(),
            "elapsed_seconds": float(elapsed_seconds),
            "recommendation": _safe_str(summary.get("recommendation")),
            "next_branch": _safe_str(summary.get("next_branch")),
        },
    )
    _print_progress(
        "run_finished "
        f"label={RUN_LABEL} elapsed={_format_duration(elapsed_seconds)} "
        f"recommendation={_safe_str(summary.get('recommendation'))} "
        f"rule_id={RULE_ID} output_dir={_relative_path(output_dir)}"
    )


if __name__ == "__main__":
    main()
