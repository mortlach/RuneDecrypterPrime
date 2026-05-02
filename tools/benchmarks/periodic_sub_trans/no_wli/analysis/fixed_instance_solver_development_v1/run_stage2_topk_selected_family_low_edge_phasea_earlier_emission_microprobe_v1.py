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
        "run_stage2_topk_selected_family_low_edge_phasea_earlier_emission_microprobe_v1.py"
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


RUN_LABEL = "stage2_topk_selected_family_low_edge_phasea_earlier_emission_microprobe_v1"
MECHANISM_LAYER = "selection"
FIXTURE_SEED = 1111
SEARCH_SEEDS = (7002, 7003)
LANE_ROLE_BY_SEED = {
    7002: "filtered_canary",
    7003: "kept_canary",
}
EXPECTED_GATE_VERDICT_BY_SEED = {
    7002: "filter",
    7003: "keep",
}
CHECKPOINT_COUNTS = (16, 32, 48, 64)
GATE_ID = "rank1_init_ge_0p30"
GATE_METRIC = "phaseA_rank1_init_match"
GATE_THRESHOLD = 0.30
INTENDED_WALLCLOCK_BUDGET_HOURS = 1.25
MAX_WALLCLOCK_SECONDS = INTENDED_WALLCLOCK_BUDGET_HOURS * 3600.0
REFERENCE_MATRIX_BUNDLE_DIR = (
    REPO_ROOT
    / "output"
    / "tools"
    / "benchmarks"
    / "periodic_sub_trans"
    / "no_wli"
    / "analysis"
    / "fixed_instance_solver_development_v1"
    / "20260423T143925Z__stage2_topk_selected_family_low_edge_exact_replay_1111_matrix_v1"
)
REFERENCE_MATRIX_ROWS_CSV = (
    REFERENCE_MATRIX_BUNDLE_DIR
    / "selected_family_low_edge_exact_replay_1111_matrix_rows.csv"
)
LATE_GATE_REFERENCE_BUNDLE_DIR = (
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
LATE_GATE_REFERENCE_ROWS_CSV = (
    LATE_GATE_REFERENCE_BUNDLE_DIR
    / "selected_family_low_edge_phasea_gate_live_read_followon_rows.csv"
)
NEXT_BRANCH_READY_LABEL = (
    "stage2_topk_selected_family_low_edge_phasea_earlier_emission_family_followon"
)
NEXT_BRANCH_REFINE_LABEL = (
    "stage2_topk_selected_family_low_edge_phasea_checkpoint_refinement"
)
QUESTION = (
    "Can a provisional Phase-A checkpoint reproduce the validated keep/filter "
    "split on one filtered and one kept 1111 lane materially earlier than the "
    "current late gate snapshot?"
)
SUSPICION = (
    "A provisional checkpoint at or before restart 48 should already reproduce "
    "the split on 7002 and 7003, which would make an earlier stop or fallback "
    "contract technically honest."
)
MAIN_ALTERNATIVE = (
    "The split may only become reliable at the full restart-64 surface, or the "
    "provisional ranking may drift enough that the earlier checkpoints do not "
    "recover the same verdicts."
)
IF_SUSPICION_TRUE_EXPECT = (
    "At least one shared checkpoint before restart 64 should match the expected "
    "filter/keep verdicts on both canaries with a materially lower elapsed "
    "share than the current late gate."
)
IF_ALTERNATIVE_TRUE_EXPECT = (
    "Either no shared checkpoint before restart 64 will match both canaries, "
    "or the first matching checkpoint will still be too late to matter."
)
DECISION_RULE = (
    "Advance only if both canaries match at a shared checkpoint before restart "
    "64 and that checkpoint lands materially earlier than the current late gate "
    "family mean share. Refine if the split appears but still too late; hold if "
    "the provisional checkpoints do not reproduce the split."
)
STOP_CONDITION = (
    "This microprobe is sized from the retained exact replay anchors on the "
    "same selector family: 7002 took about 00:22:13 and 7003 took about "
    "00:21:54, for an anchored total of about 00:44:08. After the first "
    "completed canary, recompute the projected two-job total from the observed "
    "row plus the remaining retained anchor. If that projection exceeds the "
    "01:15:00 session budget, stop before launching the second canary."
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


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _print_progress(message: str) -> None:
    print(f"[{_utc_now_iso()}] {message}", flush=True)


def _gate_verdict(gate_metric_value: float) -> str:
    if not math.isfinite(float(gate_metric_value)):
        return "unknown"
    if float(gate_metric_value) >= float(GATE_THRESHOLD):
        return "keep"
    return "filter"


def _mean(values: list[float]) -> float:
    finite = [value for value in values if math.isfinite(value)]
    if not finite:
        return float("nan")
    return float(sum(finite) / float(len(finite)))


def _load_reference_rows() -> dict[int, dict[str, Any]]:
    rows = list(csv.DictReader(REFERENCE_MATRIX_ROWS_CSV.open(encoding="utf-8")))
    out: dict[int, dict[str, Any]] = {}
    for row in rows:
        search_seed = _safe_int(row.get("search_seed"))
        if search_seed not in SEARCH_SEEDS:
            continue
        output_dir = REPO_ROOT / Path(_safe_str(row.get("output_dir")))
        attempt_status = _load_json(output_dir / "attempt_status.json")
        out[search_seed] = dict(
            search_seed=int(search_seed),
            output_dir=_safe_str(row.get("output_dir")),
            reference_attempt_elapsed_seconds=_safe_float(
                attempt_status.get("elapsed_seconds")
            ),
            baseline_best_match_ratio=_safe_float(
                row.get("baseline_best_match_ratio")
            ),
            retained_stage3_reference_match_ratio=_safe_float(
                row.get("retained_stage3_reference_match_ratio")
            ),
            reference_resume_best_match_ratio=_safe_float(
                row.get("resume_best_match_ratio")
            ),
            reference_match_delta_vs_baseline=_safe_float(
                row.get("match_delta_vs_baseline")
            ),
            candidate_truth_delta_vs_baseline_row=_safe_float(
                row.get("candidate_truth_delta_vs_baseline_row")
            ),
        )
    missing = [seed for seed in SEARCH_SEEDS if seed not in out]
    if missing:
        raise RuntimeError(f"Missing reference rows for seeds: {missing}")
    return out


def _load_late_gate_reference_rows() -> dict[int, dict[str, Any]]:
    rows = list(csv.DictReader(LATE_GATE_REFERENCE_ROWS_CSV.open(encoding="utf-8")))
    out: dict[int, dict[str, Any]] = {}
    for row in rows:
        search_seed = _safe_int(row.get("search_seed"))
        if search_seed not in SEARCH_SEEDS:
            continue
        out[search_seed] = dict(
            search_seed=int(search_seed),
            late_gate_elapsed_seconds=_safe_float(
                row.get("phasea_gate_snapshot_elapsed_seconds")
            ),
            late_gate_elapsed_share=_safe_float(
                row.get("phasea_gate_snapshot_elapsed_share")
            ),
            expected_gate_verdict=_safe_str(row.get("expected_gate_verdict")),
        )
    missing = [seed for seed in SEARCH_SEEDS if seed not in out]
    if missing:
        raise RuntimeError(f"Missing late-gate reference rows for seeds: {missing}")
    return out


def _anchored_total_seconds(reference_rows: Mapping[int, Mapping[str, Any]]) -> float:
    return float(
        sum(
            _safe_float(reference_rows[int(seed)]["reference_attempt_elapsed_seconds"])
            for seed in SEARCH_SEEDS
        )
    )


def _remaining_anchor_seconds(
    *,
    completed_seeds: list[int],
    reference_rows: Mapping[int, Mapping[str, Any]],
) -> float:
    return float(
        sum(
            _safe_float(reference_rows[int(seed)]["reference_attempt_elapsed_seconds"])
            for seed in SEARCH_SEEDS
            if int(seed) not in completed_seeds
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
    summary: Mapping[str, Any],
    reference_row: Mapping[str, Any],
    late_gate_reference_row: Mapping[str, Any],
) -> dict[str, Any]:
    checkpoint = dict(checkpoint_rows.get(int(checkpoint_count), {}) or {})
    checkpoint_present = int(1 if checkpoint else 0)
    gate_metric_value = _safe_float(checkpoint.get(GATE_METRIC))
    observed_gate_verdict = _gate_verdict(gate_metric_value)
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
    late_gate_elapsed_share = _safe_float(late_gate_reference_row.get("late_gate_elapsed_share"))
    share_improvement = (
        float(late_gate_elapsed_share - checkpoint_elapsed_share)
        if math.isfinite(late_gate_elapsed_share) and math.isfinite(checkpoint_elapsed_share)
        else float("nan")
    )
    return dict(
        search_seed=int(search_seed),
        lane_role=str(lane_role),
        status=_safe_str(attempt_status.get("status")),
        output_dir=_safe_str(attempt_status.get("output_dir")),
        elapsed_seconds=float(attempt_elapsed_seconds),
        elapsed=_safe_str(attempt_status.get("elapsed")),
        reference_attempt_elapsed_seconds=_safe_float(
            reference_row.get("reference_attempt_elapsed_seconds")
        ),
        checkpoint_restart_count=int(checkpoint_count),
        checkpoint_present=int(checkpoint_present),
        checkpoint_elapsed_seconds=float(checkpoint_elapsed_seconds),
        checkpoint_elapsed_share=float(checkpoint_elapsed_share),
        late_gate_elapsed_share=float(late_gate_elapsed_share),
        checkpoint_share_improvement_vs_late_gate=float(share_improvement),
        gate_metric_name=str(GATE_METRIC),
        gate_metric_value=float(gate_metric_value),
        observed_gate_verdict=str(observed_gate_verdict),
        expected_gate_verdict=str(expected_gate_verdict),
        verdict_matches_expected=int(
            1 if checkpoint_present and observed_gate_verdict == expected_gate_verdict else 0
        ),
        baseline_best_match_ratio=_safe_float(summary.get("baseline_best_match_ratio")),
        retained_stage3_reference_match_ratio=_safe_float(
            summary.get("retained_stage3_reference_match_ratio")
        ),
        current_resume_best_match_ratio=_safe_float(summary.get("resume_best_match_ratio")),
        delta_vs_reference_candidate=float(
            _safe_float(summary.get("resume_best_match_ratio"))
            - _safe_float(reference_row.get("reference_resume_best_match_ratio"))
        ),
        delta_vs_baseline=_safe_float(summary.get("match_delta_vs_baseline")),
        candidate_truth_delta_vs_baseline_row=_safe_float(
            reference_row.get("candidate_truth_delta_vs_baseline_row")
        ),
    )


def _build_summary(
    *,
    checkpoint_rows: list[dict[str, Any]],
    late_gate_reference_rows: Mapping[int, Mapping[str, Any]],
) -> dict[str, Any]:
    completed_seeds = sorted({int(row["search_seed"]) for row in checkpoint_rows})
    shared_matches: list[int] = []
    for checkpoint_count in CHECKPOINT_COUNTS:
        rows = [
            row
            for row in checkpoint_rows
            if int(row.get("checkpoint_restart_count", 0)) == int(checkpoint_count)
        ]
        if len(rows) != len(completed_seeds):
            continue
        if all(int(row.get("verdict_matches_expected", 0)) == 1 for row in rows):
            shared_matches.append(int(checkpoint_count))
    earliest_shared_checkpoint_count = (
        int(min(shared_matches)) if shared_matches else 0
    )
    earliest_rows = [
        row
        for row in checkpoint_rows
        if int(row.get("checkpoint_restart_count", 0))
        == int(earliest_shared_checkpoint_count)
    ]
    mean_checkpoint_share = _mean(
        [
            _safe_float(row.get("checkpoint_elapsed_share"))
            for row in earliest_rows
        ]
    )
    mean_share_improvement = _mean(
        [
            _safe_float(row.get("checkpoint_share_improvement_vs_late_gate"))
            for row in earliest_rows
        ]
    )
    mean_late_gate_share = _mean(
        [
            _safe_float(late_gate_reference_rows[int(seed)]["late_gate_elapsed_share"])
            for seed in completed_seeds
        ]
    )
    if shared_matches and earliest_shared_checkpoint_count < 64 and mean_share_improvement >= 0.10:
        recommendation = "advance"
        next_branch = NEXT_BRANCH_READY_LABEL
        reason = (
            "a shared provisional checkpoint before restart 64 reproduced the split "
            "and materially improved checkpoint timing versus the late gate"
        )
    elif shared_matches:
        recommendation = "refine"
        next_branch = NEXT_BRANCH_REFINE_LABEL
        reason = (
            "the split appears on a shared provisional checkpoint, but the first "
            "matching checkpoint is still too late or too weakly improved to claim "
            "a real earlier-emission contract"
        )
    else:
        recommendation = "hold"
        next_branch = NEXT_BRANCH_REFINE_LABEL
        reason = (
            "no shared provisional checkpoint reproduced the expected split on both "
            "canaries before the current full surface"
        )
    return dict(
        completed_canaries=int(len(completed_seeds)),
        shared_match_checkpoint_count=int(len(shared_matches)),
        earliest_shared_checkpoint_restart_count=int(earliest_shared_checkpoint_count),
        mean_checkpoint_elapsed_share=float(mean_checkpoint_share),
        mean_checkpoint_share_improvement_vs_late_gate=float(mean_share_improvement),
        mean_late_gate_elapsed_share=float(mean_late_gate_share),
        recommendation=str(recommendation),
        next_branch=str(next_branch),
        reason=str(reason),
    )


def _write_rows_csv(path: Path, rows: list[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(str(key))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({str(k): v for k, v in row.items()})


def _write_readout(
    *,
    output_dir: Path,
    rows: list[Mapping[str, Any]],
    summary: Mapping[str, Any],
) -> None:
    lines = [
        "# Phase-A Earlier-Emission Microprobe",
        "",
        "Question:",
        f"- {QUESTION}",
        "",
        "Coverage:",
        f"- completed canaries: `{_safe_int(summary.get('completed_canaries'))}` / `{len(SEARCH_SEEDS)}`",
        f"- recommendation: `{_safe_str(summary.get('recommendation'))}`",
        (
            "- earliest shared matching checkpoint: "
            f"`restart{_safe_int(summary.get('earliest_shared_checkpoint_restart_count'))}`"
        ),
        (
            "- mean checkpoint elapsed share: "
            f"`{_safe_float(summary.get('mean_checkpoint_elapsed_share')):.3f}`"
        ),
        (
            "- mean share improvement versus late gate: "
            f"`{_safe_float(summary.get('mean_checkpoint_share_improvement_vs_late_gate')):.3f}`"
        ),
        f"- reason: {_safe_str(summary.get('reason'))}",
        "",
        "Per-checkpoint read:",
    ]
    for row in rows:
        lines.extend(
            [
                (
                    f"- `search{_safe_int(row.get('search_seed'))}` / "
                    f"`restart{_safe_int(row.get('checkpoint_restart_count'))}`"
                ),
                f"  - verdict `{_safe_str(row.get('observed_gate_verdict'))}`",
                f"  - expected `{_safe_str(row.get('expected_gate_verdict'))}`",
                (
                    "  - gate metric "
                    f"`{_safe_float(row.get('gate_metric_value')):.3f}`"
                ),
                (
                    "  - elapsed share "
                    f"`{_safe_float(row.get('checkpoint_elapsed_share')):.3f}`"
                ),
                (
                    "  - share improvement versus late gate "
                    f"`{_safe_float(row.get('checkpoint_share_improvement_vs_late_gate')):.3f}`"
                ),
            ]
        )
    (output_dir / "selected_family_low_edge_phasea_earlier_emission_readout.md").write_text(
        "\n".join(lines).rstrip() + "\n",
        encoding="utf-8",
    )


def main() -> None:
    started_at = monotonic()
    reference_rows = _load_reference_rows()
    late_gate_reference_rows = _load_late_gate_reference_rows()
    anchored_total_seconds = _anchored_total_seconds(reference_rows)
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
    rows_jsonl_path = output_dir / "selected_family_low_edge_phasea_earlier_emission_rows.jsonl"
    rows_csv_path = output_dir / "selected_family_low_edge_phasea_earlier_emission_rows.csv"
    summary_path = output_dir / "selected_family_low_edge_phasea_earlier_emission_summary.json"
    recommendation_path = (
        output_dir / "selected_family_low_edge_phasea_earlier_emission_recommendation.json"
    )

    state = dict(
        run_label=str(RUN_LABEL),
        mechanism_layer=str(MECHANISM_LAYER),
        fixture_seed=int(FIXTURE_SEED),
        search_seeds=[int(seed) for seed in SEARCH_SEEDS],
        status="running",
        started_at_utc=_utc_now_iso(),
        intended_wallclock_budget_hours=float(INTENDED_WALLCLOCK_BUDGET_HOURS),
        intended_wallclock_budget_seconds=float(MAX_WALLCLOCK_SECONDS),
        anchored_total_seconds=float(anchored_total_seconds),
        anchored_total_elapsed=_format_duration(anchored_total_seconds),
        question=str(QUESTION),
        suspicion=str(SUSPICION),
        alternative=str(MAIN_ALTERNATIVE),
        decision_rule=str(DECISION_RULE),
        stop_condition=str(STOP_CONDITION),
        completed_canaries=0,
        remaining_canaries=len(SEARCH_SEEDS),
        rows_written=0,
        last_completed_search_seed=0,
        projected_total_seconds=float(anchored_total_seconds),
    )
    _write_json(state_path, state)
    _append_jsonl(
        events_path,
        {
            "ts_utc": _utc_now_iso(),
            "event": "run_started",
            "run_label": str(RUN_LABEL),
            "output_dir": _relative_path(output_dir),
            "question": str(QUESTION),
            "suspicion": str(SUSPICION),
            "alternative": str(MAIN_ALTERNATIVE),
            "decision_rule": str(DECISION_RULE),
            "stop_condition": str(STOP_CONDITION),
        },
    )
    _print_progress(
        "run_started "
        f"label={RUN_LABEL} "
        f"output_dir={_relative_path(output_dir)} "
        f"units={len(SEARCH_SEEDS)} "
        f"budget={_format_duration(MAX_WALLCLOCK_SECONDS)} "
        f"anchored_total={_format_duration(anchored_total_seconds)}"
    )

    rows: list[dict[str, Any]] = []
    completed_seeds: list[int] = []
    for index, search_seed in enumerate(SEARCH_SEEDS, start=1):
        if completed_seeds:
            projected_total_seconds = float(
                sum(
                    _safe_float(row.get("elapsed_seconds"))
                    for row in rows
                    if int(row.get("checkpoint_restart_count", 0)) == int(CHECKPOINT_COUNTS[0])
                )
                + _remaining_anchor_seconds(
                    completed_seeds=completed_seeds,
                    reference_rows=reference_rows,
                )
            )
            state.update(
                projected_total_seconds=float(projected_total_seconds),
                projected_total_elapsed=_format_duration(projected_total_seconds),
            )
            _write_json(state_path, state)
            if float(projected_total_seconds) > float(MAX_WALLCLOCK_SECONDS):
                state.update(
                    status="stopped_over_budget",
                    stopped_before_search_seed=int(search_seed),
                    updated_at_utc=_utc_now_iso(),
                )
                _write_json(state_path, state)
                _append_jsonl(
                    events_path,
                    {
                        "ts_utc": _utc_now_iso(),
                        "event": "run_stopped_over_budget",
                        "stopped_before_search_seed": int(search_seed),
                        "projected_total_seconds": float(projected_total_seconds),
                        "projected_total_elapsed": _format_duration(projected_total_seconds),
                    },
                )
                _print_progress(
                    "run_stopped_over_budget "
                    f"completed={len(completed_seeds)}/{len(SEARCH_SEEDS)} "
                    f"projected_total={_format_duration(projected_total_seconds)} "
                    f"budget={_format_duration(MAX_WALLCLOCK_SECONDS)}"
                )
                break

        lane_role = str(LANE_ROLE_BY_SEED[int(search_seed)])
        expected_gate_verdict = str(EXPECTED_GATE_VERDICT_BY_SEED[int(search_seed)])
        _append_jsonl(
            events_path,
            {
                "ts_utc": _utc_now_iso(),
                "event": "job_started",
                "search_seed": int(search_seed),
                "lane_role": str(lane_role),
                "index": int(index),
                "total": len(SEARCH_SEEDS),
                "expected_gate_verdict": str(expected_gate_verdict),
            },
        )
        _print_progress(
            f"job_started unit={index}/{len(SEARCH_SEEDS)} "
            f"search_seed={int(search_seed)} "
            f"lane_role={lane_role} "
            f"expected_gate_verdict={expected_gate_verdict}"
        )
        replay_output = replay_mod.run_verification(
            search_seed=int(search_seed),
            run_label=f"{RUN_LABEL.replace('_microprobe_v1', '')}_exact_replay_1111_search{int(search_seed)}_v1",
            scope_note_override=(
                "provisional Phase-A checkpoint microprobe keeps stage35 disabled and "
                "tests whether earlier checkpoint emission can recover the validated "
                "keep/filter split before the current late gate"
            ),
        )
        child_output_dir = REPO_ROOT / Path(_safe_str(replay_output.get("output_dir")))
        attempt_status = _load_json(child_output_dir / "attempt_status.json")
        summary = _load_json(
            child_output_dir / "selected_family_low_edge_exact_replay_summary.json"
        )
        checkpoint_rows_raw = _load_checkpoint_rows(attempt_status)
        checkpoint_rows = {
            int(_safe_int(row.get("phaseA_checkpoint_restart_count"))): dict(row)
            for row in checkpoint_rows_raw
        }
        for checkpoint_count in CHECKPOINT_COUNTS:
            row = _checkpoint_row(
                search_seed=int(search_seed),
                lane_role=str(lane_role),
                expected_gate_verdict=str(expected_gate_verdict),
                checkpoint_count=int(checkpoint_count),
                checkpoint_rows=checkpoint_rows,
                attempt_status=attempt_status,
                summary=summary,
                reference_row=reference_rows[int(search_seed)],
                late_gate_reference_row=late_gate_reference_rows[int(search_seed)],
            )
            rows.append(dict(row))
            _append_jsonl(rows_jsonl_path, row)
        completed_seeds.append(int(search_seed))
        completed_rows = [
            row
            for row in rows
            if int(row.get("checkpoint_restart_count", 0)) == int(CHECKPOINT_COUNTS[0])
        ]
        observed_total_seconds = float(
            sum(_safe_float(row.get("elapsed_seconds")) for row in completed_rows)
            + _remaining_anchor_seconds(
                completed_seeds=completed_seeds,
                reference_rows=reference_rows,
            )
        )
        elapsed_run_seconds = float(monotonic() - started_at)
        state.update(
            updated_at_utc=_utc_now_iso(),
            completed_canaries=len(completed_seeds),
            remaining_canaries=max(0, len(SEARCH_SEEDS) - len(completed_seeds)),
            rows_written=len(rows),
            last_completed_search_seed=int(search_seed),
            last_child_output_dir=_relative_path(child_output_dir),
            observed_total_seconds=float(observed_total_seconds),
            observed_total_elapsed=_format_duration(observed_total_seconds),
            elapsed_seconds=float(elapsed_run_seconds),
            elapsed=_format_duration(elapsed_run_seconds),
        )
        _write_json(state_path, state)
        _append_jsonl(
            events_path,
            {
                "ts_utc": _utc_now_iso(),
                "event": "job_completed",
                "search_seed": int(search_seed),
                "lane_role": str(lane_role),
                "elapsed_seconds": _safe_float(attempt_status.get("elapsed_seconds")),
                "elapsed": _safe_str(attempt_status.get("elapsed")),
                "child_output_dir": _relative_path(child_output_dir),
                "checkpoint_count": len(checkpoint_rows),
            },
        )
        _print_progress(
            f"job_completed unit={len(completed_seeds)}/{len(SEARCH_SEEDS)} "
            f"search_seed={int(search_seed)} "
            f"elapsed={_safe_str(attempt_status.get('elapsed'))} "
            f"checkpoints={len(checkpoint_rows)} "
            f"run_elapsed={_format_duration(elapsed_run_seconds)} "
            f"eta={_format_duration(max(0.0, observed_total_seconds - elapsed_run_seconds))}"
        )

    _write_rows_csv(rows_csv_path, rows)
    summary = _build_summary(
        checkpoint_rows=rows,
        late_gate_reference_rows=late_gate_reference_rows,
    )
    recommendation = dict(summary)
    recommendation.update(
        output_dir=_relative_path(output_dir),
        fixture_seed=int(FIXTURE_SEED),
        search_seeds=[int(seed) for seed in SEARCH_SEEDS],
        checkpoint_counts=[int(value) for value in CHECKPOINT_COUNTS],
    )
    _write_json(summary_path, summary)
    _write_json(recommendation_path, recommendation)
    _write_readout(output_dir=output_dir, rows=rows, summary=summary)
    state.update(
        updated_at_utc=_utc_now_iso(),
        status="completed" if state.get("status") == "running" else state.get("status"),
        completed_at_utc=_utc_now_iso(),
        recommendation=str(summary.get("recommendation", "")),
        next_branch=str(summary.get("next_branch", "")),
        reason=str(summary.get("reason", "")),
    )
    _write_json(state_path, state)
    _append_jsonl(
        events_path,
        {
            "ts_utc": _utc_now_iso(),
            "event": "run_finished",
            "status": str(state.get("status", "")),
            "recommendation": str(summary.get("recommendation", "")),
            "next_branch": str(summary.get("next_branch", "")),
            "reason": str(summary.get("reason", "")),
        },
    )
    refresh_catalog_safely()
    _print_progress(
        "run_finished "
        f"label={RUN_LABEL} "
        f"status={_safe_str(state.get('status'))} "
        f"recommendation={_safe_str(summary.get('recommendation'))} "
        f"output_dir={_relative_path(output_dir)}"
    )


if __name__ == "__main__":
    main()
